# -*- coding: utf-8 -*-
"""chat_daily.py -- C 版「14B 本地记忆助手」日常入口（交互 REPL + 可复用 API）。

设计要点（与验收口径 docs/_work/PRODUCT-C-SPEC.md 694ebbad136efbec 对齐）：

  * 记忆 = KV 块（磁盘派生层）。prompt 里**不拼接**任何记忆文本；问句原样交给引擎。
  * 复用既有产品路径，不复制引擎：
      - tools/kvslots.py  : KVEngine（真实模式才 import；--dry-run/测试用 StubEngine）
      - tools/memory_source.py : memory_source/memory_block 权威层 + build_block/load_into
      - tools/session_state.py : save_session/restore_session（原子会话快照）
      - tools/chat_lease.py    : GuardedLeases（每次 reset 必须过它）
      - tools/retrieval.py     : 检索选择（只决定「有没有记忆证据」，不决定 prompt）
      - tools/evidence.py      : 三态证据决策（memory_hit / chat_only / no_evidence）
  * 与 tools/chat.py 的差异（详见 docs/_work/PRODUCT-C-CHANGELOG.md）：
      - 独立数据面 kvmem/daily.db + kvmem/daily_blocks/（不污染研究库 kvmem/chat.db）
      - 记忆条目前缀 mem-<sha12>（按内容去重），上限 6 条（seq 1..6；seq 7 作 preflight）
      - 全部记忆一次性挂载在对话起点下方（紧凑排布，slot_capacity=None）
      - 拒答策略：检索无命中 + 具体事实问句 => 固定拒答文本，不调用模型
      - 会话默认 kvmem/sessions/daily.json；退出自动保存，重开自动恢复
  * 本文件零 GPU：只有 make_real_engine() 才 import kvslots；测试/干跑走 StubEngine。
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import memory_source as ms
import web_lookup
try:
    import memory_isolated as _iso
except Exception:                                        # noqa: BLE001
    _iso = None          # noqa: E402  (CPU: sqlite + hashlib)
import session_state as ss          # noqa: E402  (CPU: snapshot/restore)
import evidence as E                # noqa: E402  (CPU: rule-based decision)
from chat_lease import GuardedLeases  # noqa: E402  (imports m3_lease; no engine yet)
import assistant_log as alog            # noqa: E402  (个体日志：只追加 JSONL)
import memory_service as memo           # noqa: E402  (记忆数据层：抽取/去重/检索/判据)

try:                                                     # Windows 控制台 UTF-8
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                        # noqa: BLE001
    pass

VERSION = "c-1.0"

MODEL = ms.MODEL
DLL_NAME = "kvshim_vk.dll"

DB_DEFAULT = os.environ.get("CHAT_DAILY_DB") or os.path.join(ROOT, "kvmem", "daily.db")
BLOCKS_DEFAULT = os.environ.get("CHAT_DAILY_BLOCKS") or os.path.join(ROOT, "kvmem", "daily_blocks")
SESSIONS_DEFAULT = os.environ.get("CHAT_DAILY_SESSIONS") or os.path.join(ROOT, "kvmem", "sessions")
SESSION_DEFAULT = os.path.join(SESSIONS_DEFAULT, "daily.json")

N_CTX_DEFAULT = 16384      # GPU 实测选型：16384 @ 34 层（11.36 tok/s，VRAM 峰 8.003 GiB）
CHAT_START_DEFAULT = 8192  # GPU 实测选型：对话窗 8192、块区预算 8192-512=7680
N_CTX = N_CTX_DEFAULT      # 兼容旧引用（新代码请用实例属性 self.n_ctx）
CHAT_START = CHAT_START_DEFAULT
N_SEQ = 8                  # seq 0 = 对话；seq 1..MAX_MEMORIES = 记忆块；seq N_SEQ-1 = preflight
MAX_MEMORIES = 6                 # 同时挂载上限（seq 1..6）
MAX_TOTAL_MEMORY_TOKENS = 3840   # 默认记忆区预算：CHAT_START - 256 安全余量
MEMORY_SAFETY_MARGIN = 512
LIBRARY_MAX = 200                # 检索模式下库容量上限（块仍按需挂载）
N_GPU_LAYERS_DEFAULT = 34        # GPU 实测选型：34 层留 0.6 GiB 余量（36 层仅 0.22）
RETRIEVAL_MODES = ("off", "topk")
DEFAULT_TOPK = 4
ROLLOVER_AT_DEFAULT = 0.75      # 对话窗 ≥75% 触发自动压缩；=1.0 关闭
ROLLOVER_DROP_FRACTION = 0.35   # 分层 rollover：最旧 30–40% 原文写成块
ROLLOVER_KEEP_FRACTION = 0.65   # 最近 60–70% 原文保留在 KV
ROLLOVER_KEEP_TURNS = 2         # 兼容旧常量（不再作为主判据）
ROLLOVER_SUMMARY_NPREDICT = 200
ROLLOVER_FALLBACK_CHARS = 1500
ARCHIVE_MAX_CHARS = 3000
ARCHIVE_TAG = "auto_archive"
ROLLOVER_SUMMARY_PROMPT = ("请把下面这段较早的对话压缩成不超过 200 字的要点摘要，"
                           "只输出摘要本身，不要复述原句：\n")
MAX_TEXT_CHARS = 600
CHAT_BUDGET = CHAT_START_DEFAULT  # 兼容旧引用；实例值为 self.chat_budget = n_ctx-chat_start
N_PREDICT_DEFAULT = 192    # SPEC §4 输出 ≤200 token；Lead 建议 160–256 省时口径
MAX_N_PREDICT = 200
LOG_SPEC_REL = os.path.join("docs", "_work", "PRODUCT-C-LOG-SPEC.md")
CODE_FILES = ("tools/chat_daily.py", "tools/assistant_log.py", "tools/chat_service.py")

PRODUCT_REFUSAL = "记忆里没有这条，我不想猜。直接告诉我一句事实，我会记住（也可以 /remember）。"

# 命中记忆时的应用层指令（**不是记忆文本**；记忆仍然只以 KV 块进入注意力）。
# 依据：GPU 基线冒烟显示无记忆时模型会编造（「我的车牌号是京A12345」）⇒ 必须显式约束。
import os

NATURAL_MODE = os.environ.get("LLAMA_MEM_MODE", "natural").lower() != "strict"
ISOLATED_ENABLED = os.environ.get("LLAMA_MEM_ISOLATED", "0").strip().lower() in ("1", "true", "yes")
BOUNDARY_ENABLED = os.environ.get("LLAMA_MEM_BOUNDARY", "0").strip().lower() in ("1", "true", "yes")

VERIFY_ENABLED = os.environ.get("LLAMA_MEM_VERIFY", "1").strip().lower() not in (
    "0", "off", "false", "no")
VERIFY_FALLBACK_SENTENCE = "这条我没法从记忆里核对，先不猜。"
VERIFY_REPAIR_BUDGET_S = 90.0        # one repair only; degrade past this budget


def _get_verifier():
    """Late import: tools/answer_verifier.py may land after this module is loaded."""
    try:
        import answer_verifier as av  # noqa: F401
        return av
    except Exception:                # noqa: BLE001
        return None


def _verify_strip(answer, av):
    """strip_continuation when the verifier provides it; otherwise no-op."""
    if av is not None and hasattr(av, "strip_continuation") and answer is not None:
        try:
            return av.strip_continuation(answer)
        except Exception:            # noqa: BLE001
            return answer
    return answer


def _tidy_answer(ans):
    """Drop continuation markers and immediately repeated sentences."""
    if not ans:
        return None
    for marker in ("\n用户：", " 用户：", "\n答：", " 答：", "用户：我需要",
                   "\n问题：", "  response", "\nresponse", " response "):
        if marker in ans:
            ans = ans.split(marker)[0]
    ans = ans.strip() or None
    if ans:
        parts = [p_.strip() for p_ in ans.replace("。", "。\n").split("\n") if p_.strip()]
        uniq = []
        for p_ in parts:
            if not uniq or p_ != uniq[-1]:
                uniq.append(p_)
        ans = ("".join(uniq)).strip() or None
    return ans


SYSTEM_POLICY = (
    "你是用户身边的本地记忆助手，说话自然、简短、口语化，像朋友聊天。直接给出回答，不要输出思考过程/think 标签。"
    "用户告诉你事实时系统会在后台记住，你自然接话即可，不要说“已记住 id=…”这类系统话。"
    "回答个人事实优先依据记忆，记不清就自然说记不清，不要编造或用无关旧内容顶替。"
    "你不能操作任何应用（加好友/发消息/转账/删除等），被要求时自然说做不了，不要承诺、不要假装做过。"
    "你不是联网模型；只有本轮给了“检索资料”时才可引用并注明来源。"
    "不要自称某个具体模型或公司，你是本地记忆助手。"
)

ANSWER_INSTRUCTION = ("只依据记忆回答；记忆里没有就说不知道；"
                      "只回答当前这一个问题，不要复述问题也不要续写问答模板；"
                      "若有多条相似记忆，按标签/时间区分，拿不准就说不确定。")

SPEC_REL = os.path.join("docs", "_work", "PRODUCT-C-SPEC.md")
SPEC_FREEZE_REL = os.path.join("kvmem", "m2_visibility", "m5", "out", "PRODUCT-C-SPEC-FREEZE.json")

_DLL_CACHE = {}   # path -> pin dict（50 MB dll 的 sha16 只算一次）
_FAKE_MODEL_PATH = None   # install_fake_model() 设置；真实模式保持 None


class DailyError(Exception):
    """可读错误：code 进服务层 JSON，message 给人看。"""

    def __init__(self, code, message):
        self.code = str(code)
        self.message = str(message)
        Exception.__init__(self, "%s: %s" % (self.code, self.message))


# ---------------------------------------------------------------------------
# 小工具（所有 JSON 落盘走 tmp + os.replace，显式 newline="\n"）
# ---------------------------------------------------------------------------
def sha16_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def atomic_write_json(path, obj, indent=2):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return path


_THINK_BLOCK = re.compile(r"<think\b.*?</think\s*>", re.S | re.I)
_THINK_OPEN = re.compile(r"<think\b.*$", re.S | re.I)
_THINK_STRAY = re.compile(r"</?think\s*>", re.I)


def strip_think(text):
    """剥离 DeepSeek-R1-distill 的思考段：成对  thinking…、未闭合  thinking 到结尾、孤立标签。"""
    t = _THINK_BLOCK.sub("", str(text or ""))
    t = _THINK_OPEN.sub("", t)
    t = _THINK_STRAY.sub("", t)
    return t


_POLICY_ECHO_MARKERS = (
    "说话自然", "简短、口语化", "像朋友聊天", "不要输出思考过程", "think 标签",
    "用户告诉你事实时", "在后台记住", "已记住 id", "记不清就自然说记不清",
    "不要编造", "无关旧内容", "不能操作任何应用", "加好友", "发消息", "转账",
    "被要求时自然说做不了", "不要假装做过", "不是联网模型", "检索资料", "注明来源",
    "不要自称某个具体模型", "你是本地记忆助手", "本地记忆助手",
)


def strip_policy_echo(text):
    """删掉模型复读出来的系统策略句子（长会话 general 路径的已知回归）。

    按句切分，丢弃含策略标记的句子；同一字符连续重复 >6 次折叠；若最后只剩
    标点/策略残渣则返回空，由调用方回退「我记不清了」。不依赖提示词。
    """
    t = str(text or "")
    if not t.strip():
        return ""
    t = re.sub(r"(.)\1{6,}", r"\1\1\1", t)          # 标标标标… -> 标标标
    parts = re.split(r"(?<=[。！？!?\n；;])", t)
    kept = []
    for part in parts:
        if not part.strip():
            continue
        if any(m in part for m in _POLICY_ECHO_MARKERS):
            continue
        kept.append(part)
    out = "".join(kept).strip()
    # 粘连在开头/结尾、没有句读的策略片段，按标记直接剔除
    for m in _POLICY_ECHO_MARKERS:
        while m in out:
            out = out.replace(m, "")
    if len(out) < 16 and any(ch in out for ch in "标源"):
        out = re.sub(r"[标源…;；,，、]+", "", out)
    out = re.sub(r"\s+", " ", out).strip()
    if not out or all(ch in "标源…;；,，" for ch in out):
        return ""
    return out


def clean_answer(raw):
    """回答清洗（REPL 与 HTTP/SSE 共用，服务端不得把 think/模板残留吐给用户）。

    步骤：剥 think 标签 → 去特殊 token → 去指令回显 → 取第一段 → 截断模型续写的
    「问：/答：」模板 → 收尾去空白。prompt 本身仍只含「指令 + 问题」，不含记忆原文。
    """
    t = strip_think(raw)
    t = t.replace("<|im_end|>", "").replace("<|endoftext|>", "")
    t = t.strip()
    if t.startswith(ANSWER_INSTRUCTION):
        t = t[len(ANSWER_INSTRUCTION):].lstrip(" \n\t，,。：:")
    if t.startswith("答："):
        t = t[2:].lstrip()
    if t.startswith("问："):
        return ""
    out = []
    for line in t.splitlines():
        if not line.strip():
            break
        out.append(line.strip())
    t = " ".join(out).strip()
    # 截断续写模板：模型有时答完一题继续编「下一问/下一答」
    for marker in ("问：", "答：", ANSWER_INSTRUCTION):
        idx = t.find(marker)
        if idx > 0:
            t = t[:idx]
    # 截断「回显问题」：答案里不应再出现问句；若出现，砍到该问句前一句边界
    qm = re.search(r"[？?]", t)
    if qm:
        idx = qm.start()
        cut = max(t.rfind(ch, 0, idx) for ch in "。！？\n")
        t = t[:cut + 1] if cut > 0 else t[:idx]
    t = strip_policy_echo(t)
    return t.strip(" 　\t，,。;；")


def first_line(text, limit=48):
    s = str(text or "").strip().splitlines()
    head = s[0] if s else ""
    return head[:limit] + ("…" if len(head) > limit else "")


def _ok(obj):
    return obj


# ---------------------------------------------------------------------------
# 零 GPU 假引擎（--dry-run 与 CPU 测试专用；真实路径不碰它）
# ---------------------------------------------------------------------------
class StubEngine:
    """只模拟 KV 记账（cells/pos_max/share/drop）与文件往返，不做任何前向。

    它写出的 .kvmem / .chat.kvmem 是 JSON 记账文件，**不能**被真实引擎加载；
    因此 --dry-run 使用独立数据目录，绝不可与真实 daily.db 混用。
    """

    mode = "stub"

    def __init__(self, answer_prefix="（干跑假引擎）", n_ctx=N_CTX_DEFAULT):
        self.cells = {}
        self.posmax = {}
        self.visible = {}
        self.ask_calls = 0
        self.ask_active = 0
        self.max_active_asks = 0
        self.share_calls = 0
        self.drop_calls = 0
        self.reset_calls = 0
        self.n_seq = N_SEQ
        self.n_ctx = int(n_ctx)
        self.answer_prefix = answer_prefix

    # -- accounting -----------------------------------------------------
    def n_tokens(self, seq):
        return int(self.cells.get(int(seq), 0))

    def pos_max(self, seq):
        return int(self.posmax.get(int(seq), -1))

    def bytes_per_token(self):
        return 1024

    def pool_bytes(self):
        return 0

    def reset(self, seq):
        self.reset_calls += 1
        self.cells[int(seq)] = 0
        self.posmax[int(seq)] = -1

    # -- text -> cells (crude estimate; deterministic) -------------------
    @staticmethod
    def _guess_tokens(text):
        return max(1, (len(str(text or "")) + 1) // 2)

    def write(self, seq, text, add_bos=True):
        seq = int(seq)
        n = self._guess_tokens(text)
        self.cells[seq] = n
        self.posmax[seq] = n - 1
        return n

    def write_at(self, seq, text, pos, add_bos=True):
        seq = int(seq)
        n = self._guess_tokens(text)
        self.cells[seq] = n
        self.posmax[seq] = int(pos) + n - 1
        return n

    # -- state files -----------------------------------------------------
    def save(self, seq, path):
        payload = {"stub": True, "n": int(self.n_tokens(seq)),
                   "pos_max": int(self.pos_max(seq))}
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return os.stat(path).st_size

    def load(self, seq, path):
        tmp = path + ".loadcheck"
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
            if not payload.get("stub"):
                return -1
            seq = int(seq)
            self.cells[seq] = int(payload["n"])
            self.posmax[seq] = int(payload["pos_max"])
            return int(payload["n"])
        except Exception:                                # noqa: BLE001
            return -1
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    def load_strict(self, seq, path):
        return self.load(seq, path)

    # -- kv geometry -----------------------------------------------------
    def share(self, block_seq, dst_seq, lo, hi):
        self.share_calls += 1
        self.visible.setdefault(int(dst_seq), set()).add(int(block_seq))

    def drop(self, dst_seq, lo, hi):
        self.drop_calls += 1
        seq = int(dst_seq)
        # 只清掉本区间对应的 block 可见性记账；不模拟 cell 引用计数。
        self.visible.setdefault(seq, set())

    def repos_local(self, seq, delta, p0=0, p1=-1):
        seq = int(seq)
        self.posmax[seq] = int(self.posmax.get(seq, -1)) + int(delta)
        return int(self.cells.get(seq, 0))

    # -- generation ------------------------------------------------------
    def ask(self, seq, text, n_predict=32, pos=None):
        seq = int(seq)
        if "__STUB_ERROR__" in str(text):
            # 零 GPU 测试钩子：只存在于 StubEngine，用于验证错误映射链路
            raise DailyError("model_error", "stub engine forced failure (test hook)")
        if "__STUB_THINK__" in str(text):
            # 零 GPU 测试钩子：模拟 DeepSeek-R1-distill 的 think 段与「续写问答模板」
            self.ask_calls += 1
            self.cells[int(seq)] = int(self.cells.get(int(seq), 0)) + 16
            return ("好的，我来回答。\n我的车牌号是京A88888。 我的车型是什么？ "
                    "答：我的车型是比亚迪汉。 ")
        self.ask_calls += 1
        self.ask_active += 1
        self.max_active_asks = max(self.max_active_asks, self.ask_active)
        try:
            n_new = self._guess_tokens(text) + min(int(n_predict), 32)
            start = int(pos) if pos is not None else (int(self.posmax.get(seq, -1)) + 1)
            self.cells[seq] = int(self.cells.get(seq, 0)) + n_new
            self.posmax[seq] = max(int(self.posmax.get(seq, -1)), start + n_new - 1)
            return "%s我不掌握这条记忆。" % self.answer_prefix
        finally:
            self.ask_active -= 1

    def stats(self):
        return {"mode": self.mode, "ask_calls": self.ask_calls,
                "max_active_asks": self.max_active_asks,
                "share_calls": self.share_calls, "drop_calls": self.drop_calls,
                "reset_calls": self.reset_calls}

    def close(self):
        pass


# ---------------------------------------------------------------------------
# 真实引擎（只有这里 import kvslots；测试/干跑不进入）
# ---------------------------------------------------------------------------
def make_real_engine(model=None, n_ctx=N_CTX_DEFAULT,
                     n_gpu_layers=N_GPU_LAYERS_DEFAULT):
    from kvslots import KVEngine                             # noqa: E402  延迟 import
    return KVEngine(model or MODEL, n_ctx=int(n_ctx), n_seq=N_SEQ,
                    gpu=int(n_gpu_layers), kv="q8_0")


def install_fake_model(model_path):
    """零 GPU 测试/干跑辅助：造占位模型文件，并让 memory_source 的默认模型路径也指向它。

    背景（不改既有文件，只在本进程打薄补丁）：memory_source.load_into 与
    session_state.restore_session 的 model_path 默认值在 import 时绑定为 9 GB GGUF 的
    真实路径；stub 引擎不加载模型，但 check_compatible 会比对 model_size/mtime。
    因此补一层「默认 model_path」注入，让 CPU 测试无需真实模型也可走完整的
    build_block / save_session / restore_session 路径。
    """
    parent = os.path.dirname(os.path.abspath(model_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    if not os.path.exists(model_path):
        tmp = model_path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write("placeholder model for zero-GPU dry-run/tests\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, model_path)
    global _FAKE_MODEL_PATH
    _FAKE_MODEL_PATH = os.path.abspath(model_path)
    orig = ms.load_into
    if not getattr(orig, "_chat_daily_fake_default", False):
        def load_into(eng, row, seq, model_path=None, kv_type="q8_0"):
            return orig(eng, row, seq,
                        model_path=model_path or _FAKE_MODEL_PATH, kv_type=kv_type)
        load_into._chat_daily_fake_default = True
        load_into._chat_daily_original = orig
        ms.load_into = load_into
    return _FAKE_MODEL_PATH


# ---------------------------------------------------------------------------
# 核心应用
# ---------------------------------------------------------------------------
class DailyApp:
    """日常助手状态机；REPL 与 HTTP 服务共用这一层。"""

    def __init__(self, engine, db_path=DB_DEFAULT, blocks_dir=BLOCKS_DEFAULT,
                 sessions_dir=SESSIONS_DEFAULT, session_path=None,
                 model_path=MODEL, control=False, n_predict=N_PREDICT_DEFAULT,
                 restore=True, verbose=False, log_root=None, log_mode=None,
                 log=True, display_name=None, logger=None,
                 retrieval_mode="off", topk=DEFAULT_TOPK,
                 rollover_at=ROLLOVER_AT_DEFAULT,
                 n_ctx=N_CTX_DEFAULT, chat_start=CHAT_START_DEFAULT,
                 n_gpu_layers=N_GPU_LAYERS_DEFAULT):
        self.eng = engine
        self.model_path = model_path
        _fmt = os.environ.get("LLAMA_MEM_CHAT_FORMAT", "").strip().lower()
        self._chatml = (_fmt == "chatml") or ("qwen2.5" in str(model_path).lower())
        self._policy_sent = False        # 政策只在会话开头写一次，避免 KV 里堆满重复指令
        self.n_ctx = int(n_ctx)
        self.n_gpu_layers = int(n_gpu_layers)
        self.chat_start = int(chat_start)
        if not (0 < self.chat_start < self.n_ctx):
            raise DailyError("bad_request",
                             "chat_start(%d) 必须落在 (0, n_ctx=%d) 内"
                             % (self.chat_start, self.n_ctx))
        self.chat_budget = self.n_ctx - self.chat_start
        if self.chat_budget < 512:
            raise DailyError("bad_request",
                             "对话窗预算 %d token 过小（n_ctx-chat_start）" % self.chat_budget)
        self.memory_budget = max(256, self.chat_start - MEMORY_SAFETY_MARGIN)
        self.control = bool(control)
        mode = str(retrieval_mode or "off").lower()
        if mode not in RETRIEVAL_MODES:
            raise DailyError("bad_request",
                             "--retrieval 只能取 %s" % "/".join(RETRIEVAL_MODES))
        self.retrieval_mode = mode
        self.topk = max(1, min(int(topk), MAX_MEMORIES))
        self._last_query = None
        self._last_selection = []      # [{name, score, source_id, signals}]
        self._last_candidate_count = 0
        self._last_related_count = 0
        self._last_truncation = None
        self._last_rollover = None
        try:
            self.rollover_at = min(1.0, max(0.0, float(rollover_at)))
        except (TypeError, ValueError):
            self.rollover_at = ROLLOVER_AT_DEFAULT
        self.n_predict = max(1, min(int(n_predict), MAX_N_PREDICT))
        self.verbose = bool(verbose)
        self.db_path = db_path
        self.blocks_dir = blocks_dir
        self.sessions_dir = sessions_dir
        if session_path and not os.path.isabs(session_path):
            session_path = os.path.join(sessions_dir, session_path)
        self.session_path = session_path or os.path.join(sessions_dir, "daily.json")
        self.mounted = {}          # name -> (seq, lo, hi)
        self.mounted_blocks = []   # top-down, 交给 session_state.save_session
        self.history = []          # [{q, a, refused}]，最多 20 轮
        self.warnings = []

        os.makedirs(self.blocks_dir, exist_ok=True)
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.con = ms.connect(self.db_path)
        self._ensure_meta()
        self.leases = GuardedLeases(self.eng, site_prefix="daily")
        self._scratch = N_SEQ - 1      # seq 7；挂载只占 1..MAX_MEMORIES
        self._first_ask = True
        self.logger = logger
        self.log_enabled = bool(log or logger is not None)
        if self.logger is None and self.log_enabled:
            root = log_root or os.path.join(os.path.dirname(os.path.abspath(db_path)),
                                            "assistant")
            self.logger = alog.AssistantLog(root=root, mode=log_mode,
                                            display_name=display_name,
                                            resume_crash_check=False)
        if self.logger is not None:
            self._log_begin()

        if restore:
            self._bootstrap()

    # -- 个体日志 ---------------------------------------------------------
    def _log_pins(self):
        model = self.model_path
        dll = os.path.join(HERE, DLL_NAME)
        spec = os.path.join(ROOT, SPEC_REL)
        specs = [spec, os.path.join(ROOT, LOG_SPEC_REL)]
        pins = {}
        try:
            pins = self.logger.pins_snapshot(model_path=model, dll_path=dll,
                                             spec_path=spec,
                                             code_paths=[os.path.join(ROOT, p)
                                                         for p in CODE_FILES])
            if os.path.exists(specs[1]):
                pins["log_spec_pin"] = alog.sha16_file(specs[1])
        except Exception as exc:                             # noqa: BLE001
            self.warnings.append("日志 pins 计算失败：%s" % exc)
        self._pins = pins
        return pins

    def _log_begin(self):
        try:
            sid = self.logger.current_session_id()
            ev = "session_resume" if getattr(self.logger, "resumed", False) else "session_start"
            self.logger.event(ev, pins=self._log_pins(),
                              log_config={"mode": self.logger.mode},
                              engine={"n_ctx": self.n_ctx,
                                      "n_gpu_layers": self.n_gpu_layers,
                                      "chat_start": self.chat_start,
                                      "chat_budget": self.chat_budget,
                                      "memory_budget": int(self.memory_budget)})
            prev = self.logger.crash_check()
            if prev:
                self.logger.event("crash_recovered",
                                  last_seq=prev.get("seq"),
                                  last_event=prev.get("event"),
                                  last_ts=prev.get("ts"),
                                  unclean=True,
                                  recovered_memories=len(self._rows()) if hasattr(self, "con") else None,
                                  source_session=prev.get("session_id"))
                self.warnings.append("上次异常退出（会话 %s，末事件 %s@seq %s），"
                                     "已写 crash_recovered 可核对"
                                     % (prev.get("session_id"), prev.get("event"),
                                        prev.get("seq")))
        except Exception as exc:                             # noqa: BLE001
            self.warnings.append("个体日志初始化失败：%s" % exc)

    def log_session(self, session_id=None):
        """服务模式：按 X-Session-Id 切换会话并写 session_start/resume。"""
        if not self.logger:
            return None
        self.logger.new_session(session_id)
        ev = "session_resume" if getattr(self.logger, "resumed", False) else "session_start"
        self.logger.event(ev, pins=self._pins,
                          log_config={"mode": self.logger.mode})
        return self.logger.current_session_id()

    def _log(self, event, **fields):
        if not self.logger:
            return None
        try:
            return self.logger.event(event, **fields)
        except Exception:                                    # noqa: BLE001
            return None

    # -- 生命周期 ---------------------------------------------------------
    def _bootstrap(self):
        restored = False
        if os.path.exists(self.session_path):
            try:
                self.load(self.session_path)
                restored = True
            except Exception as exc:                         # noqa: BLE001
                self.warnings.append("自动恢复失败（%s），从空对话开始" % exc)
        if not restored:
            self.history = []
        if self.control:
            self._unmount_all()
            self.warnings.append("control 模式：不挂载任何长期记忆（用于 S5 对照）")
        else:
            try:
                self._sync_mounts()
            except Exception as exc:                         # noqa: BLE001
                self.warnings.append("挂载记忆失败：%s" % exc)
        self._first_ask = self.eng.n_tokens(0) == 0

    def close(self, save=False, reason="user_quit"):
        err = None
        if save:
            try:
                self.save()
            except Exception as exc:                         # noqa: BLE001
                err = exc
        try:
            self._unmount_all()
        except Exception as exc:                             # noqa: BLE001
            if err is None:
                err = exc
        try:
            # 收尾：preflight 用的 scratch seq 也要清空，保证下次启动干净
            self.leases.reset(self._scratch, site="daily.close.scratch")
        except Exception:                                    # noqa: BLE001
            pass
        if self.logger:
            try:
                self.logger.session_end(reason=reason)
            except Exception:                                # noqa: BLE001
                pass
        try:
            self.eng.close()
        finally:
            self.con.close()
        return {"saved": save and err is None, "error": (str(err) if err else None)}

    # -- 记忆元数据（标签/来源/关联；独立小表，不改 memory_source 结构）------
    def _ensure_meta(self):
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS daily_memory_meta ("
            "source_id INTEGER PRIMARY KEY, tags TEXT, source TEXT, related_ids TEXT, "
            "slots TEXT)")
        # 旧库迁移：缺 slots 列则 ALTER（不改 memory_source；已有数据 slots=NULL）
        cols = {r[1] for r in self.con.execute(
            "PRAGMA table_info(daily_memory_meta)").fetchall()}
        if "slots" not in cols:
            self.con.execute("ALTER TABLE daily_memory_meta ADD COLUMN slots TEXT")
        self.con.commit()

    def _meta_get(self, sid):
        row = self.con.execute(
            "SELECT tags, source, related_ids, slots FROM daily_memory_meta "
            "WHERE source_id=?", (int(sid),)).fetchone()
        if not row:
            return {"tags": [], "source": "manual", "related_ids": [], "slots": {}}
        try:
            tags = json.loads(row[0] or "[]")
        except ValueError:
            tags = []
        try:
            rel = json.loads(row[2] or "[]")
        except ValueError:
            rel = []
        try:
            slots = json.loads(row[3] or "{}")
        except (ValueError, IndexError):
            slots = {}
        return {"tags": [str(t) for t in tags], "source": row[1] or "manual",
                "related_ids": [int(x) for x in rel],
                "slots": slots if isinstance(slots, dict) else {}}

    def _meta_set(self, sid, tags=None, source=None, related_ids=None, slots=None):
        cur = self._meta_get(sid)
        tags = cur["tags"] if tags is None else [str(t) for t in tags]
        source = cur["source"] if source is None else str(source)
        rel = cur["related_ids"] if related_ids is None else [int(x) for x in related_ids]
        sl = (cur.get("slots") or {}) if slots is None else dict(slots)
        self.con.execute(
            "INSERT INTO daily_memory_meta (source_id,tags,source,related_ids,slots) "
            "VALUES (?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET tags=excluded.tags,"
            "source=excluded.source,related_ids=excluded.related_ids,"
            "slots=excluded.slots",
            (int(sid), json.dumps(tags, ensure_ascii=False), source,
             json.dumps(rel, ensure_ascii=False),
             json.dumps(sl, ensure_ascii=False)))
        self.con.commit()
        return {"tags": tags, "source": source, "related_ids": rel, "slots": sl}

    _SLOT_EVENT_CANON = {"开会": "会议", "会议": "会议", "组会": "会议", "例会": "会议"}
    _SLOT_YM_RE = re.compile(
        r"(?:今年|明年|去年|前年)?(?:[一二三四五六七八九十]{1,2}|\d{1,2})月"
        r"(?:[一二三四五六七八九十]{1,2}|\d{1,2})?[日号]?|"
        r"(?:本周|这周|下周|下个?月|每?(?:周|星期)|周|星期)[一二三四五六日天]|"
        r"今天|明天|后天|昨天|前天")
    _PET_NAME_RE = re.compile(
        r"(?:猫|狗|宠物)[^。；;\n]{0,8}?叫\s*([\u4e00-\u9fffA-Za-z0-9]{2,8})")

    @classmethod
    def _canon_slots(cls, slots):
        out = dict(slots or {})
        ev = out.get("event")
        if ev and str(ev) in cls._SLOT_EVENT_CANON:
            out["event"] = cls._SLOT_EVENT_CANON[str(ev)]
        return out

    @classmethod
    def _augment_slots(cls, slots, text):
        """补齐数据层没抽到的中文年月/宠物槽位（只影响比对，不改库内 meta）。"""
        out = dict(slots or {})
        blob = str(text or "")
        if not out.get("time"):
            m = cls._SLOT_YM_RE.search(blob)
            if m:
                out["time"] = m.group(0).strip()
        if not out.get("object"):
            m = cls._PET_NAME_RE.search(blob)
            if m:
                out["object"] = m.group(1).strip()
        if not out.get("event") and any(p in blob for p in ("猫", "狗", "宠物")):
            out["event"] = "养宠物"
        return cls._canon_slots(out)

    @classmethod
    def _canon_qslots(cls, qslots, text=""):
        q = dict(qslots or {})
        slots = dict(q.get("slots") or {})
        slots = cls._augment_slots(slots, text) if text else cls._canon_slots(slots)
        q["slots"] = slots
        return q

    def _slots_of(self, sid):
        """读记忆的槽位（含旧库兼容 + 数据层漏抽的中文年月/宠物补齐）。"""
        try:
            row = self.con.execute(
                "SELECT slots FROM daily_memory_meta WHERE source_id=?", (int(sid),)).fetchone()
        except Exception:                                # noqa: BLE001
            row = None
        slots = {}
        if row and row[0]:
            try:
                slots = json.loads(row[0]) or {}
            except ValueError:
                slots = {}
        r = self._row_by_id(sid)
        text = str(r[3]) if r else ""
        return self._augment_slots(slots, text)

    def _insert_memory_block(self, text, label="日常记忆", mode="chat",
                             tags=None, related_ids=None, max_chars=None):
        """插入源行 + 建 KV 块；返回 dict（不挂载、不重选、不写 remember 日志）。

        超限/建块失败会回滚 source/block/文件；off 模式仍查记忆区总预算，
        topk 模式库容量为 LIBRARY_MAX（挂载时才按预算截断）。
        """
        text = str(text or "").strip()
        if not text:
            raise DailyError("bad_request", "记忆文本为空")
        text_cap = int(max_chars or MAX_TEXT_CHARS)
        if len(text) > text_cap:
            raise DailyError("bad_request",
                             "记忆过长（%d 字 > 上限 %d 字）" % (len(text), text_cap))
        cap = MAX_MEMORIES if self.retrieval_mode != "topk" else LIBRARY_MAX
        if len(self._rows()) >= cap:
            raise DailyError("memory_full", "记忆已达上限 %d 条" % cap)
        slots = memo.extract_slots(text)
        put = self._put_memory_source(text, label=label, mode=mode)
        if put["duplicate"]:
            if tags is not None:
                self._meta_set(put["id"], tags=tags,
                               source=("auto_summary" if mode == "auto_summary"
                                       else "auto_archive" if mode == "auto_archive"
                                       else "manual"),
                               related_ids=related_ids, slots=slots)
            return {"id": put["id"], "name": put["name"], "duplicate": True,
                    "n_tokens": self._n_tokens_of(put["id"]),
                    "created_at": self._created_at(put["id"]), "path": None,
                    "block_sha16": None}
        sid = put["id"]
        try:
            src_row = (sid, "default", "private", str(mode), put["name"], str(label),
                       text, ms.sha256_text(text), put["created_at"])
            bs = ms.build_block(self.eng, self.con, src_row, blocks_dir=self.blocks_dir,
                                model_path=self.model_path, seq=self._scratch)
        except Exception as exc:                             # noqa: BLE001
            self._rollback_source(sid)
            raise DailyError("internal", "建块失败（已回滚该条记忆）：%s" % exc)
        if self.retrieval_mode != "topk" and self._total_tokens() > int(self.memory_budget):
            self._rollback_source(sid)
            raise DailyError("memory_full",
                             "记忆总 token 超过预算 %d，已回滚本条"
                             % int(self.memory_budget))
        try:
            import retrieval as R
            R.build_index(self.con, verbose=False)
        except Exception as exc:                             # noqa: BLE001
            self.warnings.append("检索索引重建失败：%s" % exc)
        src_kind = ("auto_summary" if mode == "auto_summary"
                    else "auto_archive" if mode == "auto_archive" else "manual")
        meta = self._meta_set(sid, tags=(tags or []), source=src_kind,
                              related_ids=(related_ids or []), slots=slots)
        return {"id": sid, "name": put["name"], "duplicate": False,
                "n_tokens": int(bs["n_tokens"]), "created_at": put["created_at"],
                "path": bs.get("path"), "block_sha16": None,
                "tags": meta["tags"], "source": meta["source"],
                "related_ids": meta["related_ids"], "slots": meta["slots"],
                "slots_unverified": memo.unverified_slots(meta["slots"])}

    def _n_tokens_of(self, sid):
        row = self._row_by_id(sid)
        return int(row[7]) if row else None

    def _created_at(self, sid):
        t = self.con.execute("SELECT created_at FROM memory_source WHERE id=?",
                             (int(sid),)).fetchone()
        return t[0] if t else None

    def memories(self):
        """记忆清单（内省走 memory_service.introspect；字段与拆分前一致）。"""
        rows = self._rows()
        by_name = {int(r[0]): r[1] for r in rows}
        out = []
        for it in memo.introspect(rows, meta_fn=self._meta_get):
            it = dict(it)
            it["name"] = by_name.get(int(it["id"]))
            out.append(it)
        self._log("memories_list", count=len(out))
        return out

    def introspect(self):
        """给工具/服务用的内省入口（记忆清单 + 来源/时间/标签）。"""
        return self.memories()

    def forget(self, target):
        raw = str(target or "").strip()
        if not raw:
            raise DailyError("bad_request", "用法：/forget <id> 或 /forget all")
        rows = self._rows()
        if raw.lower() == "all":
            ids = [int(r[0]) for r in rows]
        else:
            try:
                ids = [int(raw)]
            except ValueError:
                raise DailyError("bad_request", "id 必须是数字或 all：%r" % raw)
        existing = [int(r[0]) for r in rows]
        missing = [i for i in ids if i not in existing]
        if not ids:
            raise DailyError("not_found", "没有可删除的记忆")
        if missing and raw.lower() != "all":
            raise DailyError("not_found", "没有 id=%s 的记忆" % ",".join(map(str, missing)))
        self._unmount_all()
        paths = []
        for sid in ids:
            r = self._row_by_id(sid)
            if r is None:
                continue
            if r[6]:
                paths.append(r[6])
            self.con.execute("DELETE FROM memory_source WHERE id=?", (sid,))
        self.con.commit()
        removed = 0
        for p in paths:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                    removed += 1
                except OSError:
                    pass
        try:
            import retrieval as R
            R.build_index(self.con, verbose=False)
        except Exception as exc:                             # noqa: BLE001
            self.warnings.append("检索索引重建失败：%s" % exc)
        # S4 的可判前提：删除记忆时同时结束当前对话——否则旧对话的 KV 仍可能复述被删事实。
        # 顺序 = 先 detach（已在 _unmount_all 做过）→ reset seq0 → 再挂回剩余记忆。
        try:
            self.leases.reset(0, site="daily.forget.reset_chat")
        except Exception as exc:                             # noqa: BLE001
            self.warnings.append("清空当前对话失败：%s" % exc)
        self.history = []
        self._last_query = None
        self._last_selection = []
        self._sync_mounts()
        self._log("forget", id=(raw.lower() if raw.lower() == "all" else int(ids[0])),
                  deleted_count=len(ids), confirm=True, memories_after=len(self._rows()))
        return {"deleted": len(ids), "ids": ids, "files_removed": removed,
                "dialogue_reset": True}

    # -- 对话窗自动滚动（上下文自动压缩；用户无需 /save 重开）----------------
    def _rollover_threshold(self):
        if self.rollover_at <= 0.0 or self.rollover_at >= 1.0:
            return None
        return max(64, int(self.chat_budget * self.rollover_at))

    @staticmethod
    def _turns_text(turns):
        return "\n".join("用户：%s\n助手：%s" % (t.get("q") or "", t.get("a") or "")
                         for t in turns)

    def _summarize(self, dropped_text):
        """一次 ≤200 token 前向生成摘要；失败返回 (None, reason)。"""
        prompt = ROLLOVER_SUMMARY_PROMPT + dropped_text
        try:
            raw = self.eng.ask(0, prompt, n_predict=ROLLOVER_SUMMARY_NPREDICT, pos=None)
        except Exception as exc:                             # noqa: BLE001
            return None, "summary_forward_failed: %s" % exc
        summ = clean_answer(raw)
        if not summ:
            return None, "summary_empty"
        return summ[:2000], None

    def _archive_dir(self):
        return os.path.join(os.path.dirname(os.path.abspath(self.db_path)), "daily", "archive")

    def _write_archive_file(self, text):
        """把被移出的对话全文原子写入 kvmem/daily/archive/<ts>-<hex>.txt。"""
        d = self._archive_dir()
        os.makedirs(d, exist_ok=True)
        name = "%s-%s.txt" % (datetime.now().strftime("%Y%m%d-%H%M%S"),
                              uuid.uuid4().hex[:6])
        path = os.path.join(d, name)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(str(text))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return path

    def _maybe_rollover(self):
        """ask 前调用：分层 rollover（75% 触发）。

        把最旧 30–40% 对话**原文**逐轮写成记忆块（auto_turn，原文+KV 块），
        另写一条 auto_archive 全文块 + 一条 auto_summary 索引块（related_ids 指向
        原文块与归档块），全文再归档到 daily/archive/*.txt（含 sidecar 交叉引用）。
        最近 60–70% 原文保留在对话 seq。硬保护：先保存；重建失败尝试恢复并报错。
        """
        threshold = self._rollover_threshold()
        if self.control or threshold is None:
            return None
        before = int(self.eng.n_tokens(0))
        if before < threshold:
            return None
        turns = list(self.history)
        # 至少 3 轮才有"丢 30–40%、留 60–70%"的空间；否则推迟到下一轮
        if len(turns) < 3:
            return None
        # 以字符占比近似 token 占比：丢最旧 35%，至少 1 轮、至少留 1 轮
        chars = [len(str(t.get("q") or "")) + len(str(t.get("a") or ""))
                 for t in turns]
        total_chars = sum(chars) or 1
        # 取"最接近 35% 字符量"的切点（至少丢 1 轮、至少留 1 轮），
        # 使保留比例尽量落在 60–70%。
        acc = 0
        best_err, best_n = abs(0.0 - ROLLOVER_DROP_FRACTION), 0
        for i in range(len(turns) - 1):
            acc += chars[i]
            err = abs(acc / float(total_chars) - ROLLOVER_DROP_FRACTION)
            if err < best_err:
                best_err, best_n = err, i + 1
        n_drop = max(1, best_n)
        # 约束：至少保留 2 轮，且保留字符占比尽量 >= 0.60（60–70% 目标）
        n_drop = min(n_drop, len(turns) - 2)
        while n_drop > 1:
            kept_chars = total_chars - sum(chars[:n_drop])
            if kept_chars / float(total_chars) >= 0.60:
                break
            n_drop -= 1
        if n_drop <= 0:
            return None
        dropped, kept = turns[:n_drop], turns[n_drop:]
        if not dropped:
            return None
        dropped_text = self._turns_text(dropped)
        # a) 先原子保存
        try:
            saved = self.save()
        except Exception as exc:                             # noqa: BLE001
            self._log("error", code="rollover_failed",
                      message="上下文压缩前会话保存失败：%s" % exc, where="rollover.save")
            raise DailyError("rollover_failed",
                             "上下文压缩前会话保存失败，未压缩：%s" % exc)
        # b) 摘要（失败 => 退化原文截取并记 warning，不静默）
        summary, err = self._summarize(dropped_text)
        fallback = False
        if summary is None:
            fallback = True
            summary = dropped_text[:ROLLOVER_FALLBACK_CHARS]
            self._log("warning", code="rollover_summary_fallback",
                      message=str(err or "summary_failed"),
                      evidence={"dropped_turns": len(dropped),
                                "fallback_chars": len(summary)})
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        date_tag = datetime.now().strftime("%Y-%m-%d")
        archive_path = None
        archive_id = None
        turn_ids = []
        summary_id = None
        try:
            # c1) 全文归档文件（原文完整）
            archive_path = self._write_archive_file(dropped_text)
            # c2) 逐轮原文块（保留原文 + KV 块；来源=turn）
            for i, t in enumerate(dropped, start=1):
                turn_text = "用户：%s\n助手：%s" % (t.get("q") or "", t.get("a") or "")
                res_t = self._insert_memory_block(
                    turn_text, label="对话原文 %s #%d" % (ts, i), mode="auto_turn",
                    tags=["auto_turn", date_tag, "archive:%s" % os.path.basename(archive_path)],
                    max_chars=MAX_TEXT_CHARS)
                turn_ids.append(int(res_t["id"]))
            # c3) 全文聚合块（带归档抬头，避免与单轮原文块同文本被判重；
            #     原文仍完整保留在块内 + 归档文件里）
            archive_text = ("对话归档 %s（原文）：\n%s"
                            % (ts, dropped_text[:ARCHIVE_MAX_CHARS]))
            res_a = self._insert_memory_block(
                archive_text, label="对话归档 %s" % ts, mode="auto_archive",
                tags=[ARCHIVE_TAG, date_tag,
                      "archive:%s" % os.path.basename(archive_path)],
                max_chars=ARCHIVE_MAX_CHARS + 64)
            archive_id = int(res_a["id"])
            # c4) 摘要索引块：related_ids 指向原文块 + 归档块
            related = list(turn_ids) + ([archive_id] if archive_id else [])
            res_s = self._insert_memory_block(
                "自动摘要 %s：%s" % (ts, summary),
                label="自动摘要 %s" % ts, mode="auto_summary",
                tags=["auto_summary", date_tag,
                      "archive:%s" % os.path.basename(archive_path)],
                related_ids=related)
            summary_id = int(res_s["id"])
            # c5) 双向引用：原文块/归档块回指摘要；sidecar 记录三元组
            for sid in turn_ids + ([archive_id] if archive_id else []):
                m = self._meta_get(sid)
                self._meta_set(sid, tags=m["tags"], related_ids=[summary_id])
            sidecar = archive_path + ".meta.json"
            tmp = sidecar + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                json.dump({"archive_path": archive_path, "summary_id": summary_id,
                           "turn_ids": turn_ids, "archive_id": archive_id,
                           "created_at": datetime.now().isoformat(timespec="seconds")},
                          f, ensure_ascii=False, indent=1)
                f.write("\n")
            os.replace(tmp, sidecar)
        except Exception as exc:                             # noqa: BLE001
            self._log("warning", code="rollover_archive_failed",
                      message=str(exc), evidence={"dropped_turns": len(dropped)})
        # d) detach -> reset 对话 seq -> 保留最近 60–70% 原文 -> 重新挂载
        try:
            self._unmount_all()
            self.leases.reset(0, site="rollover.reset_chat")
            self.history = kept
            if kept:
                self.eng.write_at(0, self._turns_text(kept), self.chat_start)
            self._last_selection = []
            self._last_query = None
            self._sync_mounts()
        except Exception as exc:                             # noqa: BLE001
            self._log("error", code="rollover_failed",
                      message="压缩后对话重建失败：%s" % exc, where="rollover.rebuild")
            try:
                self.load(saved["path"])
            except Exception as exc2:                        # noqa: BLE001
                self.warnings.append("压缩失败后恢复会话也失败：%s" % exc2)
                raise DailyError("rollover_failed",
                                 "上下文压缩失败且恢复失败：%s / %s" % (exc, exc2))
            raise DailyError("rollover_failed",
                             "上下文压缩失败，已恢复压缩前会话：%s" % exc)
        after = int(self.eng.n_tokens(0))
        kept_ratio = (sum(len(str(t.get("q") or "")) + len(str(t.get("a") or ""))
                          for t in kept) / float(total_chars or 1))
        info = {"notice": ("（上下文已自动压缩：最旧 %d 轮原文已存入记忆 %s，"
                           "另有摘要索引与归档）"
                           % (len(dropped),
                              ("#%d+%d 块" % (summary_id, len(turn_ids)))
                              if summary_id else "（未入库）")),
                "summary_id": summary_id, "turn_ids": turn_ids,
                "archive_id": archive_id, "archive_path": archive_path,
                "before_tokens": before, "after_tokens": after,
                "dropped_turns": len(dropped), "kept_turns": len(kept),
                "kept_ratio": round(kept_ratio, 4), "fallback": fallback}
        self._last_rollover = dict(info)
        self._log("context_rollover", before_tokens=before, after_tokens=after,
                  summary_id=summary_id, dropped_turns=len(dropped),
                  kept_turns=len(kept), fallback=fallback,
                  archive_id=archive_id, archive_path=archive_path,
                  turn_ids=turn_ids, kept_ratio=info["kept_ratio"],
                  saved_sha16=saved.get("sha16"))
        return info

    # -- verify + one-shot repair (LLAMA_MEM_VERIFY, default on) -----------
    def _verify_run(self, text, answer, blocks, mode, av):
        try:
            v = av.verify_answer(text, answer, list(blocks or []), mode=mode) or {}
        except Exception as exc:                     # noqa: BLE001
            return {"verdict": "error", "mismatches": [],
                    "hint": "%s: %s" % (type(exc).__name__, exc)}
        return {"verdict": v.get("verdict", "error"),
                "mismatches": list(v.get("mismatches") or []),
                "hint": v.get("hint")}

    @staticmethod
    def _block_text(b):
        if isinstance(b, dict):
            return str(b.get("text") or "")
        return str(b)

    def _now_line(self):
        """时间意识：每轮注入当前本地时间（含星期），供“今天/明天/下周”推理。"""
        try:
            now = datetime.now()
            wd = "一二三四五六日"[now.weekday()]
            return "当前时间：%s 星期%s %s。" % (now.strftime("%Y-%m-%d"), wd,
                                             now.strftime("%H:%M"))
        except Exception:                            # noqa: BLE001
            return ""

    def _chat_prompt(self, system, user, hint=""):
        """按模型类型拼 prompt：Qwen2.5 用 ChatML；其它保持原有“用户/回答”格式。

        关键：system/policy 只在会话开头写一次——每轮重复会把政策堆进 KV，
        模型几轮后开始复述政策（训练集里第 9–11 轮出现的“背政策”就是这原因）。
        """
        tl = self._now_line()
        if not getattr(self, "_policy_sent", False):
            if tl:
                system = tl + "\n" + system
            head = system
            self._policy_sent = True
        else:
            head = tl or "继续对话。"
        body = (hint + "\n" + user) if hint else user
        if getattr(self, "_chatml", False):
            return ("<|im_start|>system\n" + head + "<|im_end|>\n"
                    "<|im_start|>user\n" + body + "<|im_end|>\n"
                    "<|im_start|>assistant\n")
        return head + "\n用户：" + body + "\n回答："

    def _repair_prompt(self, text, answer, blocks):
        return self._chat_prompt(
            SYSTEM_POLICY,
            "只能使用以下记忆原文，逐条核对；不确定就说不知道。\n记忆原文：\n"
            + "\n".join(self._block_text(b) for b in blocks)
            + "\n你上一版回答：\n" + str(answer)
            + "\n问题：\n" + str(text)
            + "\n请重答（只输出一行）：")

    def _verify_event(self, code, **evidence):
        if not self.logger:
            return
        try:
            self.logger.log_warning(code, "verify pipeline", evidence=evidence)
        except Exception:                            # noqa: BLE001
            pass

    def _verified_finalize(self, text, answer, blocks, mode, repair_generate,
                           t0, base_state):
        """verify -> optional ONE repair -> verify; fail-closed to a fixed line.

        Returns (final_answer, info).  info carries verified/verify/state; no memory
        text or answer text is ever put into the logs.
        """
        budget = float(getattr(self, "verify_repair_budget_s",
                               VERIFY_REPAIR_BUDGET_S))
        info = {"verified": False, "attempts": 0, "mode": mode,
                "repair_latency_ms": 0.0, "state": None,
                "verify": {"verdict": "skipped", "mismatches": []}}
        av = _get_verifier()
        if not VERIFY_ENABLED:
            info["verify"] = {"verdict": "disabled", "mismatches": []}
            return _verify_strip(answer, av), info
        if av is None:
            info["verify"] = {"verdict": "verifier_missing", "mismatches": []}
            return _verify_strip(answer, av), info
        if not blocks and mode != "personal":
            info["verify"] = {"verdict": "skipped_general_no_memory",
                              "mismatches": []}
            return _verify_strip(answer, av), info

        v1 = self._verify_run(text, answer, blocks, mode, av)
        info["verify"] = v1
        if v1["verdict"] == "pass":
            info["verified"] = True
            return _verify_strip(answer, av), info
        if v1["verdict"] not in ("unsupported", "no_evidence"):
            # unknown verdict: keep the answer, but do not claim it was verified
            return _verify_strip(answer, av), info
        if v1["verdict"] == "no_evidence":
            info["state"] = "verify_fallback"
            self._verify_event("verify_fallback", mode=mode,
                               verdict="no_evidence", attempts=0)
            return _verify_strip(VERIFY_FALLBACK_SENTENCE, av), info

        # -- exactly one repair attempt (unsupported only) ------------------
        t_rep = time.perf_counter()
        if t_rep - t0 > budget:
            info["state"] = "verify_fallback"
            self._verify_event("verify_fallback", mode=mode,
                               verdict="unsupported", attempts=0,
                               reason="budget_before_repair")
            return _verify_strip(VERIFY_FALLBACK_SENTENCE, av), info
        info["attempts"] = 1
        self._verify_event("verify_repair", mode=mode, verdict="unsupported",
                           mismatches=len(v1.get("mismatches") or []),
                           attempts=1)
        try:
            repaired = repair_generate(self._repair_prompt(text, answer, blocks))
        except Exception as exc:                     # noqa: BLE001
            repaired = None
            info["repair_error"] = "%s: %s" % (type(exc).__name__, exc)
        info["repair_latency_ms"] = round(
            (time.perf_counter() - t_rep) * 1000.0, 1)
        repaired = _tidy_answer(repaired)
        if not repaired:
            info["state"] = "verify_fallback"
            self._verify_event("verify_fallback", mode=mode,
                               verdict="unsupported", attempts=1,
                               reason="repair_empty")
            return _verify_strip(VERIFY_FALLBACK_SENTENCE, av), info
        if info["repair_latency_ms"] > budget * 1000.0:
            info["state"] = "verify_fallback"
            self._verify_event("verify_fallback", mode=mode, attempts=1,
                               reason="repair_budget", latency_ms=info["repair_latency_ms"])
            return _verify_strip(VERIFY_FALLBACK_SENTENCE, av), info
        v2 = self._verify_run(text, repaired, blocks, mode, av)
        info["verify_first"] = v1
        info["verify"] = v2
        if v2["verdict"] == "pass":
            info["verified"] = True
            return _verify_strip(repaired, av), info
        info["state"] = "verify_fallback"
        self._verify_event("verify_fallback", mode=mode,
                           verdict=v2["verdict"], attempts=1)
        return _verify_strip(VERIFY_FALLBACK_SENTENCE, av), info

    def _degraded_reply(self, text, sentence, t0, state):
        """F2: fixed-line degradation; records elapsed, never hangs silently."""
        latency = time.perf_counter() - t0
        if self.logger:
            try:
                ev = self.logger.log_ask(text, session_tokens=int(self.eng.n_tokens(0)))
                seq = ev.get("seq") if ev else None
                if seq is not None:
                    self.logger.log_answer(sentence, seq, [], {"seq_ids": [], "cells": 0},
                                           latency * 1000.0, vram_gib=None, refused=False)
            except Exception:                        # noqa: BLE001
                pass
        self.history.append({"q": text, "a": sentence, "refused": False})
        self.history = self.history[-40:]
        return {"answer": sentence, "block_ids": [], "latency_s": round(latency, 4),
                "refused": False, "state": state, "chars": len(sentence),
                "verified": False,
                "verify": {"verdict": "not_run", "mismatches": []},
                "retrieval": None, "notice": (notice or {}).get("notice"), "rollover": notice}

    def _try_isolated(self, text, selection, t0, n_predict=None):
        """独立 seq 作答（不含对话历史）；失败返回 None 由调用方回退。"""
        if _iso is None or self.control:
            return None
        try:
            # F3 (degraded): seq6 is the isolated generation seq; if a memory block
            # currently occupies it, do NOT reset it -- fall back to the mount path.
            if int(self.eng.n_tokens(6)) != 0:
                if self.logger:
                    try:
                        self.logger.log_warning(
                            "isolated_seq_busy",
                            "seq6 occupied; falling back to mount path")
                    except Exception:                # noqa: BLE001
                        pass
                return None
        except Exception:                            # noqa: BLE001
            pass
        try:
            rows = []
            if selection:
                for sel in selection:
                    row = self._row_by_id(sel.get("source_id"))
                    if row is not None:
                        rows.append(row)
            note = ""
            if rows:
                note = ("\n（本轮已挂载 %d 条相关记忆，按新→旧排序；只依据它们回答个人事实，"
                        "冲突以较新者为准；都没有就说不知道。）" % len(rows))
            prompt = self._chat_prompt(
                SYSTEM_POLICY,
                text + "\n（只输出一行回答，不要续写对话。）", hint=note)
            self._unmount_all()
            _np = min(int(n_predict or self.n_predict), 192)
            ans, prov = _iso.answer_isolated(
                self.eng, rows, prompt, n_predict=_np,
                scratch=self._scratch, model_path=self.model_path, gen_seq=6)
            if not ans:
                return None
            ans = _tidy_answer(ans)
            if not ans:
                return None
            # ---- verify + one repair (isolated seq; T3/T4) ----
            blocks = [{"id": int(r[0]), "text": str(r[3])}
                      for r in rows if len(r) > 3 and r[3]]

            def _repair_isolated(p, _rows=rows):
                t_rep = time.perf_counter()
                ra = None
                try:
                    ra, _rprov = _iso.answer_isolated(
                        self.eng, _rows, p, n_predict=_np,
                        scratch=self._scratch, model_path=self.model_path,
                        gen_seq=6)
                finally:
                    # T4: seq6/7 must be empty after any repair attempt
                    for _s in (6, 7):
                        try:
                            if int(self.eng.n_tokens(_s)) != 0:
                                self.eng.reset(_s)
                        except Exception:            # noqa: BLE001
                            pass
                _log = int((time.perf_counter() - t_rep) * 1000.0)
                return _tidy_answer(ra), _log

            mode = "personal" if (rows or E.intent_of(text) != "general") else "general"
            ans, _vinfo = self._verified_finalize(
                text, ans, blocks, mode,
                lambda p: _repair_isolated(p)[0], t0, "isolated")
            state = _vinfo.get("state") or "isolated"
            _iso_elapsed = time.perf_counter() - t0
            if _iso_elapsed > VERIFY_REPAIR_BUDGET_S:
                if self.logger:
                    try:
                        self.logger.log_warning(
                            "verify_timeout", "isolated elapsed %.1fs > %.0fs"
                            % (_iso_elapsed, VERIFY_REPAIR_BUDGET_S),
                            evidence={"elapsed_ms": round(_iso_elapsed * 1000.0)})
                    except Exception:                # noqa: BLE001
                        pass
                ans = VERIFY_FALLBACK_SENTENCE
                state = "verify_timeout"
            latency = time.perf_counter() - t0
            block_ids = [int(r[0]) for r in rows]
            if self.logger:
                ev = self.logger.log_ask(text, session_tokens=int(self.eng.n_tokens(0)))
                seq = ev.get("seq") if ev else None
                if seq is not None:
                    self.logger.log_answer(ans, seq, block_ids,
                                           {"seq_ids": [], "cells": 0},
                                           latency * 1000.0, vram_gib=None, refused=False)
            self.history.append({"q": text, "a": ans, "refused": False})
            self.history = self.history[-40:]
            return {"answer": ans, "block_ids": block_ids,
                    "latency_s": round(latency, 4), "refused": False,
                    "state": state, "chars": len(ans), "retrieval": None,
                    "notice": None, "rollover": None,
                    "verified": bool(_vinfo.get("verified")),
                    "verify": _vinfo.get("verify"),
                    "verify_attempts": _vinfo.get("attempts", 0),
                    "isolated": {"seq": prov.get("isolated_seq"),
                                 "n_rows": prov.get("n_rows")}}
        except Exception as exc:                         # noqa: BLE001
            try:
                if self.logger:
                    self.logger.log_warning("isolated_fallback",
                                            "independent seq failed: %s: %s"
                                            % (type(exc).__name__, exc))
            except Exception:                            # noqa: BLE001
                pass
            return None
        finally:
            # T4/F3: the isolated seqs must never be left dirty
            for _s in (6, 7):
                try:
                    if int(self.eng.n_tokens(_s)) != 0:
                        self.eng.reset(_s)
                except Exception:                    # noqa: BLE001
                    pass

    _ACTION_RE = re.compile(
        r"同意一下|同意下|同意吧|通过一下|通过吧|加一下|加个好友|加好友|加他|加她|加我|"
        r"添加好友|拉我进|拉个群|建个群|发给他|发给她|发消息给|发给|替我(发|加|删|改|转)|"
        r"帮我(发|加|删|改|转|同意|通过)|删了他|删了她|转账给|打个电话|发个邮件|发个短信",
        re.I)

    def _auto_remember_candidate(self, text):
        """陈述"我的事实"-> 应静默写入（判据在 memory_service.needs_auto_remember）。

        T15 重构时该方法被误删；补回以兼容 natural 路径与旧测试。
        """
        try:
            return memo.needs_auto_remember(text, control=self.control)
        except TypeError:
            return memo.needs_auto_remember(text)

    def _boundary_reply(self, text):
        """动作类请求：确定性拒绝（不承诺、不假装执行），避免"我会同意/已添加"式幻觉。"""
        if self._ACTION_RE.search(str(text or "")):
            return ("我做不到：我只能聊天和记住你告诉我事实，不能操作 QQ、加好友、替你发消息或做任何账号动作。")
        return None

    def ask(self, text):
        text = str(text or "").strip()
        if not text:
            raise DailyError("bad_request", "问题为空")
        t0 = time.perf_counter()
        if NATURAL_MODE:
            return self._ask_natural(text, t0)
        return self._ask_strict(text, t0)

    def _ask_natural(self, text, t0):
        """自然对话模式：代码只负责记忆读写/检索/联网，不替模型决定措辞。"""
        np_ = min(int(self.n_predict), 128)      # 自然模式：短回答上限，避免长思考拖慢
        # 1) 静默自动记忆（陈述句事实）
        if not self.control and self._auto_remember_candidate(text):
            try:
                self.remember(text)
            except Exception:                            # noqa: BLE001
                pass
        # 上下文压缩：自然模式也必须在 ≥75% 时 rollover，否则 KV 无限累积（复述/卡死根因）
        try:
            notice = self._maybe_rollover()
        except Exception:                            # noqa: BLE001
            notice = None
        if notice and notice.get("rollover"):
            self._policy_sent = False      # 压缩后上下文重建，重新注入一次政策
        bnd = self._boundary_reply(text) if BOUNDARY_ENABLED else None
        if bnd is not None:
            latency = time.perf_counter() - t0
            if self.logger:
                ev = self.logger.log_ask(text, session_tokens=int(self.eng.n_tokens(0)))
                seq = ev.get("seq") if ev else None
                if seq is not None:
                    self.logger.log_answer(bnd, seq, [], {"seq_ids": [], "cells": 0},
                                           latency * 1000.0, vram_gib=None, refused=False)
            self.history.append({"q": text, "a": bnd, "refused": False})
            self.history = self.history[-40:]
            return {"answer": bnd, "block_ids": [], "latency_s": round(latency, 4),
                    "refused": False, "state": "boundary", "chars": len(bnd),
                    "retrieval": None, "notice": (notice or {}).get("notice"), "rollover": notice}
        is_question = bool(E.QUESTION.search(text))
        selection = []
        if (not is_question and not self.control
                and self._auto_remember_candidate(text)):
            # 陈述句：静默记忆 + 交给模型自然接话（不再用固定回执）
            try:
                self._unmount_all()
            except Exception:                            # noqa: BLE001
                pass
        # 检索选择（P0 修复：自然模式此前把 selection 初始化为 [] 却从不调用
        # _retrieval_select —— strict 分支才做检索，自然模式因此永远挂 0 条记忆。
        if is_question and not self.control:
            if self.retrieval_mode == "topk":
                selection = self._retrieval_select(text)
                self._last_query = text
                self._last_selection = selection
            else:
                selection = self._select(text)
        # 时间感知：问句带时间词时，只保留时间匹配的记忆并取最新一条；无匹配则交给后面的时间对齐断言
        if is_question and "我" in text and selection:
            _TRE = re.compile(r"今天|明天|后天|昨天|前天|本周|这周|下周|下个?月|周[一二三四五六日天]|"
                              r"星期[一二三四五六日天]|每(?:周|天|月)[一二三四五六日天]?|\d{1,2}月\d{1,2}日")
            _qt = set(_TRE.findall(text))
            if _qt:
                _rows_by = {}
                for _sel in selection:
                    _r = self._row_by_id(_sel.get("source_id"))
                    _blob = str(_r[3]) if _r is not None else ""
                    if _qt & set(_TRE.findall(_blob)):
                        _rows_by[int(_sel["source_id"])] = _sel
                if _rows_by:
                    _newest = max(_rows_by)
                    selection = [_rows_by[_newest]]
                    self._last_selection = selection
        # 报时/日期：本地直接回答（不联网、不标来源）
        _t_reply = self._local_time_reply(text)
        if _t_reply is not None:
            latency = time.perf_counter() - t0
            if self.logger:
                try:
                    ev = self.logger.log_ask(text, session_tokens=int(self.eng.n_tokens(0)))
                    seq = ev.get("seq") if ev else None
                    if seq is not None:
                        self.logger.log_answer(_t_reply, seq, [], {"seq_ids": [], "cells": 0},
                                               latency * 1000.0, vram_gib=None, refused=False)
                except Exception:                    # noqa: BLE001
                    pass
            self.history.append({"q": text, "a": _t_reply, "refused": False})
            self.history = self.history[-40:]
            return {"answer": _t_reply, "block_ids": [], "latency_s": round(latency, 4),
                    "refused": False, "state": "time_local", "chars": len(_t_reply),
                    "retrieval": None, "notice": (notice or {}).get("notice"),
                    "rollover": notice}
        # 只读联网：仅在用户明确要求“查一下/搜一下”时检索（不自动抢答）
        if self._explicit_search(text):
            web = self._web_answer(text)
            if web:
                latency = time.perf_counter() - t0
                if self.logger:
                    ev = self.logger.log_ask(text, session_tokens=int(self.eng.n_tokens(0)))
                    seq = ev.get("seq") if ev else None
                    if seq is not None:
                        self.logger.log_answer(web, seq, [], {"seq_ids": [], "cells": 0},
                                               latency * 1000.0, vram_gib=None,
                                               refused=False)
                self.history.append({"q": text, "a": web, "refused": False})
                self.history = self.history[-40:]
                return {"answer": web, "block_ids": [], "latency_s": round(latency, 4),
                        "refused": False, "state": "web", "chars": len(web),
                        "retrieval": None, "notice": (notice or {}).get("notice"), "rollover": notice}
            # 明确要查、但检索无可靠结果：诚实说不确定，不甩建议、不标来源
            _fail = "我无法联网确认这个信息，先不猜。"
            latency = time.perf_counter() - t0
            if self.logger:
                try:
                    ev = self.logger.log_ask(text, session_tokens=int(self.eng.n_tokens(0)))
                    seq = ev.get("seq") if ev else None
                    if seq is not None:
                        self.logger.log_answer(_fail, seq, [], {"seq_ids": [], "cells": 0},
                                               latency * 1000.0, vram_gib=None, refused=True)
                except Exception:                    # noqa: BLE001
                    pass
            self.history.append({"q": text, "a": _fail, "refused": True})
            self.history = self.history[-40:]
            return {"answer": _fail, "block_ids": [], "latency_s": round(latency, 4),
                    "refused": True, "state": "web_fail", "chars": len(_fail),
                    "retrieval": None, "notice": (notice or {}).get("notice"),
                    "rollover": notice}
        # 时间对齐：问“明天/下周五…”但没有任何记忆提到该时间 -> 明确说没给过，不拿别的日期硬答
        # 先匹配更具体的日期（下周三 > 下周），避免"下周"把下周四/五也当成同时间。
        TIME_RE = re.compile(
            r"(?:今年|明年|去年|前年)?(?:[一二三四五六七八九十]{1,2}|\d{1,2})月"
            r"(?:[一二三四五六七八九十]{1,2}|\d{1,2})?[日号]?|"
            r"(?:本周|这周|下周|下个?月|每?(?:周|星期)|周|星期)[一二三四五六日天]|"
            r"今天|明天|后天|昨天|前天|本周|这周|下周|下个?月")
        if is_question and "我" in text:
            q_times = set(TIME_RE.findall(text))
            if q_times:
                # 时间对齐：只保留与问句同时间词的已选记忆；一个都没有再扫库。
                same = []
                for sel in (selection or []):
                    row = self._row_by_id(sel.get("source_id"))
                    blob = str(row[3]) if row is not None else ""
                    if q_times & set(TIME_RE.findall(blob)):
                        same.append(sel)
                if same:
                    selection = same
                    matched = True
                else:
                    matched = False
                if not matched:
                    # 检索没挂上，但记忆库里可能有同时间的事实：按时间扫库，取最新
                    hits = []
                    for r in self._rows():
                        blob = str(r[3]) if len(r) > 3 else ""
                        if q_times & set(TIME_RE.findall(blob)):
                            hits.append(int(r[0]))
                    if hits:
                        newest = sorted(hits, reverse=True)[:1]
                        by_id = {int(r[0]): r for r in self._rows()}
                        selection = [{"source_id": i, "name": by_id[i][1],
                                      "score": 1.0, "signals": {}} for i in newest]
                        self._last_query = text
                        self._last_selection = selection
                        matched = True
                if not matched:
                    reply = "这个我没法确认：你没跟我提过%s的安排。" % "、".join(sorted(q_times))
                    latency = time.perf_counter() - t0
                    if self.logger:
                        ev = self.logger.log_ask(text, session_tokens=int(self.eng.n_tokens(0)))
                        seq = ev.get("seq") if ev else None
                        if seq is not None:
                            self.logger.log_answer(reply, seq, [], {"seq_ids": [], "cells": 0},
                                                   latency * 1000.0, vram_gib=None, refused=False)
                    self.history.append({"q": text, "a": reply, "refused": False})
                    self.history = self.history[-40:]
                    return {"answer": reply, "block_ids": [], "latency_s": round(latency, 4),
                            "refused": False, "state": "no_time_match", "chars": len(reply),
                            "retrieval": None, "notice": (notice or {}).get("notice"), "rollover": notice}

        # natural mode 兜底：直接生成（不进入 strict 的拒答/证据分支）
        if selection and not self.control:
            kept_rows, _trunc = self._fit_budget(self._rows_for_selection(selection))
            kept_ids = {int(r[0]) for r in kept_rows}
            selection = [s_ for s_ in selection
                         if int(s_.get("source_id") or -1) in kept_ids]
            self._last_query = text
            self._last_selection = selection
            self._sync_mounts()
        elif not selection and not self.control:
            try:
                self._unmount_all()
            except Exception:                            # noqa: BLE001
                pass
        note = ""
        if selection:
            note = "\n（本轮有 %d 条相关记忆可用；回答个人事实时优先使用，记不清就说记不清。）" % len(selection)
        prompt = self._chat_prompt(SYSTEM_POLICY, text, hint=note)
        pos = self.chat_start if int(self.eng.n_tokens(0)) == 0 else None
        raw = self.eng.ask(0, prompt, n_predict=np_, pos=pos)
        answer = clean_answer(raw) or "我记不清了"
        # 去重复/续写（模型偶发复读），不改语义
        try:
            answer = _verify_strip(answer, _get_verifier())
        except Exception:                            # noqa: BLE001
            pass
        _vinfo = {"verified": False, "attempts": 0, "state": None,
                  "verify": {"verdict": "disabled", "mismatches": []}}
        if VERIFY_ENABLED:
            _blocks = [{"id": int(r[0]), "text": str(r[3])}
                       for r in (self._row_by_id(b.get("source_id"))
                                 for b in (self.mounted_blocks or []))
                       if r is not None and len(r) > 3 and r[3]]

            def _repair_nat(p):
                return clean_answer(self.eng.ask(0, p, n_predict=np_))

            _mode = "personal" if selection else "general"
            answer, _vinfo = self._verified_finalize(
                text, answer, _blocks, _mode, _repair_nat, t0, "natural")
            if time.perf_counter() - t0 > VERIFY_REPAIR_BUDGET_S:
                if self.logger:
                    try:
                        self.logger.log_warning(
                            "verify_timeout", "natural elapsed > %.0fs"
                            % VERIFY_REPAIR_BUDGET_S)
                    except Exception:                # noqa: BLE001
                        pass
                answer = VERIFY_FALLBACK_SENTENCE
                _vinfo = dict(_vinfo, state="verify_timeout", verified=False)
        latency = time.perf_counter() - t0
        if self.logger:
            ev = self.logger.log_ask(text, session_tokens=int(self.eng.n_tokens(0)))
            seq = ev.get("seq") if ev else None
            if seq is not None:
                self.logger.log_answer(answer, seq,
                                       [int(b["source_id"]) for b in self.mounted_blocks],
                                       {"seq_ids": [int(b["seq"]) for b in self.mounted_blocks],
                                        "cells": sum(int(b["n_tokens"]) for b in self.mounted_blocks)},
                                       latency * 1000.0, vram_gib=None, refused=False)
        self.history.append({"q": text, "a": answer, "refused": False})
        self.history = self.history[-40:]
        return {"answer": answer,
                "block_ids": [int(b["source_id"]) for b in self.mounted_blocks],
                "latency_s": round(latency, 4), "refused": False,
                "state": (_vinfo.get("state") or "natural"),
                "chars": len(answer),
                "verified": bool(_vinfo.get("verified")),
                "verify": _vinfo.get("verify"),
                "verify_attempts": _vinfo.get("attempts", 0),
                "retrieval": None, "notice": (notice or {}).get("notice"), "rollover": notice}

    def _ask_strict(self, text, t0):
        np_ = min(int(self.n_predict), 128)      # 自然模式：短回答上限，避免长思考拖慢
        notice = self._maybe_rollover()

        # 1) 选择：off = 旧证据选择（retrieval.py + 逐字兜底）；topk = 本地确定性 bigram 选择器
        if self.control:
            selection = []
        elif self.retrieval_mode == "topk":
            selection = self._retrieval_select(text)
            self._last_query = text
            self._last_selection = selection
        else:
            selection = self._select(text)

        # 2) 检索预算（topk 模式：按分数序累计 token，超 3840 截断并记 warning）
        retrieval = None
        if self.retrieval_mode == "topk":
            sel_rows = self._rows_for_selection(selection)
            kept_rows, trunc = self._fit_budget(sel_rows)
            retrieval = {"query_sha16": alog.sha16(text),
                         "candidates": len(self._rows()) if not self.control else 0,
                         "selected_ids": [] if self.control else [int(r[0]) for r in kept_rows],
                         "scores": [] if self.control else
                         [[int(s["source_id"]), s["score"]] for s in selection],
                         "truncated": bool(trunc) and not self.control}
        ask_ev = self.logger.log_ask(text, session_tokens=int(self.eng.n_tokens(0)),
                                     extra=({"retrieval": retrieval} if retrieval else None)) \
            if self.logger else None
        ask_seq = ask_ev.get("seq") if ask_ev else None

        d = E.decide(text, selection, self._history_text())
        if not d.get("refuse") and not selection:
            # 根因修复：个人具体事实问句在无记忆命中时一律拒答，
            # 不再用"对话历史里提过"放行（旧逻辑导致模型拿对话内容当记忆、复读车牌）。
            if self._product_fact_question(text):
                d = dict(d)
                d.update({"refuse": True, "reply": PRODUCT_REFUSAL,
                          "state": "no_evidence",
                          "reason": "fact question without memory hit"})
            else:
                try:
                    in_chat = E.dialogue_evidence(text, self._history_text())
                except Exception:                        # noqa: BLE001
                    in_chat = False
                if not in_chat and E.QUESTION.search(text):
                    d = dict(d)
                    d.update({"refuse": True, "reply": PRODUCT_REFUSAL,
                              "state": "no_evidence",
                              "reason": "question without memory hit"})
        if d.get("refuse"):
            answer = d.get("reply") or PRODUCT_REFUSAL
            latency = time.perf_counter() - t0
            self.history.append({"q": text, "a": answer, "refused": True})
            self.history = self.history[-40:]
            if self.logger and ask_seq is not None:
                self.logger.log_refuse(str(d.get("reason") or d.get("state") or "no_memory"),
                                       ask_seq, text=answer,
                                       latency_ms=latency * 1000.0)
            return {"answer": answer, "block_ids": [], "latency_s": round(latency, 4),
                    "refused": True, "state": d.get("state"),
                    "retrieval": retrieval,
                    "notice": (notice or {}).get("notice"),
                    "rollover": notice}

        # 3) 挂载（内部顺序：detach -> reset/load/repos -> attach；块集不变则不动）
        if not self.control:
            self._sync_mounts()
            if self.retrieval_mode == "topk" and retrieval is not None and \
                    self._last_truncation:
                retrieval["truncated"] = True
        # F1: isolated seq path first (natural mode only; strict contract unchanged)
        if NATURAL_MODE and (not self.control) and selection:
            iso = (self._try_isolated(text, selection, t0, n_predict=np_)
                   if ISOLATED_ENABLED else None)
            if iso is not None:
                return iso
        if int(self.eng.n_tokens(0)) + max(64, (len(text) + 1) // 2) + np_ \
                > self.chat_budget:
            raise DailyError("chat_full",
                             "本轮对话窗口将超过 %d token；请 /save 后 /quit 重开"
                             % self.chat_budget)
        pos = self.chat_start if int(self.eng.n_tokens(0)) == 0 else None
        # 命中记忆 => 在提问前加一句应用层指令（不是记忆文本）；未命中/对照 => 原样提问。
        ask_text = (ANSWER_INSTRUCTION + "\n" + text) if selection else text
        raw = self.eng.ask(0, ask_text, n_predict=np_, pos=pos)
        answer = clean_answer(raw) or "（模型没有返回文本）"
        # ---- F1: verify + ONE repair on the mount path (same seq0, same blocks) ----
        _blocks = []
        for _b in (self.mounted_blocks or []):
            _row = self._row_by_id(_b.get("source_id"))
            if _row is not None and len(_row) > 3 and _row[3]:
                _blocks.append({"id": int(_row[0]), "text": str(_row[3])})
        _mode = ("personal" if (selection or E.intent_of(text) != "general")
                 else "general")

        def _repair_mount(p):
            _raw2 = self.eng.ask(0, p, n_predict=np_)
            return clean_answer(_raw2)

        if NATURAL_MODE:
            answer, _vinfo = self._verified_finalize(
                text, answer, _blocks, _mode, _repair_mount, t0, d.get("state"))
        else:
            _vinfo = {"verified": False, "attempts": 0, "state": None,
                      "verify": {"verdict": "strict_mode", "mismatches": []}}
        _lat_v = time.perf_counter() - t0
        if _lat_v > VERIFY_REPAIR_BUDGET_S:
            if self.logger:
                try:
                    self.logger.log_warning(
                        "verify_timeout", "request elapsed %.1fs > %.0fs"
                        % (_lat_v, VERIFY_REPAIR_BUDGET_S),
                        evidence={"elapsed_ms": round(_lat_v * 1000.0)})
                except Exception:                    # noqa: BLE001
                    pass
            answer = VERIFY_FALLBACK_SENTENCE
            _vinfo = dict(_vinfo, state="verify_timeout", verified=False)
        latency = time.perf_counter() - t0
        if self.retrieval_mode == "topk":
            block_ids = [int(b["source_id"]) for b in self.mounted_blocks]
        else:
            block_ids = [int(s["source_id"]) for s in selection
                         if s.get("source_id") is not None]
        self.history.append({"q": text, "a": answer, "refused": False})
        self.history = self.history[-40:]
        self._first_ask = False
        if self.logger and ask_seq is not None:
            seq_ids = [int(b["seq"]) for b in self.mounted_blocks]
            cells = sum(int(b["n_tokens"]) for b in self.mounted_blocks)
            self.logger.log_answer(answer, ask_seq, block_ids,
                                   {"seq_ids": seq_ids, "cells": cells},
                                   latency * 1000.0, vram_gib=None,
                                   refused=False)
        return {"answer": answer, "block_ids": block_ids,
                "latency_s": round(latency, 4), "refused": False,
                "state": (_vinfo.get("state") or d.get("state")),
                "chars": len(answer),
                "verified": bool(_vinfo.get("verified")),
                "verify": _vinfo.get("verify"),
                "verify_attempts": _vinfo.get("attempts", 0),
                "retrieval": retrieval,
                "notice": (notice or {}).get("notice"),
                "rollover": notice}

    # -- 会话 -------------------------------------------------------------
    def _chat_file(self, path):
        return os.path.splitext(os.path.abspath(path))[0] + ".chat.kvmem"

    def _transcript_path(self, path):
        return os.path.splitext(os.path.abspath(path))[0] + ".transcript.json"

    def save(self, path=None):
        path = os.path.abspath(path or self.session_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        blocks = list(self.mounted_blocks)
        chat_n = int(self.eng.n_tokens(0))
        if blocks:
            manifest = ss.save_session(self.eng, self.con, path, blocks,
                                       anchor=self.chat_start, slot_capacity=None,
                                       model_path=self.model_path,
                                       selection={"history": len(self.history),
                                                  "control": self.control})
        else:
            manifest = self._save_chat_only(path, chat_n)
        atomic_write_json(self._transcript_path(path),
                          {"schema": "chat_daily_transcript_v1",
                           "turns": list(self.history[-40:])})
        res = {"path": path, "sha16": sha16_file(path),
               "n_blocks": len(blocks), "chat_tokens": chat_n,
               "schema": manifest.get("schema", "session_manifest_v2")}
        self._log("save", path=res["path"], sha16=res["sha16"],
                  bytes=os.path.getsize(path), n_blocks=len(blocks),
                  chat_tokens=chat_n)
        return res

    def _save_chat_only(self, path, chat_n):
        root = os.path.splitext(path)[0]
        chat_file = root + ".chat.kvmem"
        chat_entry = {"state": None, "n_tokens": chat_n, "start": self.chat_start,
                      "end": self.chat_start + chat_n}
        if chat_n:
            if self.eng.save(0, chat_file) <= 0:
                raise DailyError("internal", "对话 KV 落盘失败")
            chat_entry = {"state": os.path.basename(chat_file), "n_tokens": chat_n,
                          "start": self.chat_start, "bytes": os.stat(chat_file).st_size,
                          "end": int(self.eng.pos_max(0)) + 1}
        manifest = {"schema": "chat_daily_chat_only_v1", "version": VERSION,
                    "anchor": self.chat_start, "chat": chat_entry,
                    "saved_at": datetime.now().isoformat(timespec="seconds")}
        atomic_write_json(path, manifest)
        return manifest

    def load(self, path=None):
        path = os.path.abspath(path or self.session_path)
        if not os.path.exists(path):
            raise DailyError("not_found", "没有会话文件：%s" % path)
        with open(path, encoding="utf-8") as f:
            head = json.load(f)
        if head.get("schema") == "chat_daily_chat_only_v1":
            self._unmount_all()
            self._load_chat_only(path, head)
        else:
            self._unmount_all()
            self.leases = GuardedLeases.from_manifest(self.eng, path, site_prefix="daily.load")
            rep = ss.restore_session(self.eng, self.con, path,
                                     model_path=self.model_path)
            self.mounted = {}
            self.mounted_blocks = []
            for b in rep.get("blocks", []):
                seq = int(b["slot_id"]) + 1
                self.mounted[b["block"]] = (seq, int(b["start"]), int(b["end"]))
                self.mounted_blocks.append({"seq": seq, "source_id": self._sid_of(b["block"]),
                                            "name": b["block"], "lo": int(b["start"]),
                                            "hi": int(b["end"]), "n_tokens": int(b["n_tokens"]),
                                            "path": self._path_of(b["block"])})
        self._load_transcript(path)
        self._first_ask = int(self.eng.n_tokens(0)) == 0
        try:
            self._sync_mounts()
        except Exception as exc:                             # noqa: BLE001
            self.warnings.append("恢复后对齐记忆挂载失败：%s" % exc)
        res = {"path": path, "sha16": sha16_file(path),
               "chat_tokens": int(self.eng.n_tokens(0)),
               "blocks": len(self.mounted_blocks)}
        self._log("load", path=res["path"], sha16=res["sha16"],
                  bytes=os.path.getsize(path), chat_tokens=res["chat_tokens"])
        return res

    def _load_chat_only(self, path, manifest):
        chat = manifest.get("chat") or {}
        if chat.get("state"):
            root = os.path.splitext(os.path.abspath(path))[0]
            chat_file = root + ".chat.kvmem"
            if not os.path.exists(chat_file):
                raise DailyError("not_found", "会话的对话 KV 文件缺失：%s" % chat_file)
            n = self.eng.load_strict(0, chat_file)
            if int(n) < 0:
                raise DailyError("internal", "对话 KV 加载被引擎拒绝")
        self.history = []

    def _load_transcript(self, path):
        tp = self._transcript_path(path)
        self.history = []
        if not os.path.exists(tp):
            return
        try:
            with open(tp, encoding="utf-8") as f:
                d = json.load(f)
            turns = d.get("turns") or []
            self.history = [t for t in turns if isinstance(t, dict)][-40:]
        except Exception as exc:                             # noqa: BLE001
            self.warnings.append("对话记录读取失败：%s" % exc)

    def _sid_of(self, name):
        r = [x for x in self._rows() if x[1] == name]
        return int(r[0][0]) if r else None

    def _path_of(self, name):
        r = [x for x in self._rows() if x[1] == name]
        return r[0][6] if r else None

    # -- 状态 -------------------------------------------------------------
    def _dll_pin(self):
        path = os.path.join(HERE, DLL_NAME)
        if not os.path.exists(path):
            return {"path": path, "present": False}
        if path not in _DLL_CACHE:
            st = os.stat(path)
            _DLL_CACHE[path] = {"path": path, "present": True, "bytes": st.st_size,
                                "sha16": sha16_file(path)}
        return dict(_DLL_CACHE[path])

    def _spec_pin(self):
        md = os.path.join(ROOT, SPEC_REL)
        pin = os.path.join(ROOT, SPEC_FREEZE_REL)
        out = {}
        try:
            out["spec_sha16"] = sha16_file(md)
            out["spec_bytes"] = os.stat(md).st_size
        except OSError:
            out["spec_sha16"] = None
        try:
            with open(pin, encoding="utf-8") as f:
                out["freeze"] = json.load(f).get("md", {}).get("sha16")
            out["freeze_sha16"] = sha16_file(pin)
        except (OSError, ValueError):
            out["freeze"] = None
        return out

    def status(self):
        st = self._status_impl()
        self._log("status", vram_gib=st.get("vram_gib"),
                  memories=st["memories"]["count"],
                  session_tokens=st["session"]["chat_tokens"])
        return st

    def _status_impl(self):
        eng = self.eng
        engine = {"mode": getattr(eng, "mode", "real"), "type": type(eng).__name__,
                  "n_ctx": int(getattr(eng, "n_ctx", self.n_ctx)),
                  "n_seq": int(getattr(eng, "n_seq", N_SEQ)),
                  "n_gpu_layers": self.n_gpu_layers}
        try:
            engine["bytes_per_token"] = int(eng.bytes_per_token())
            engine["kv_pool_gib"] = round(float(eng.pool_bytes()) / (1024 ** 3), 3)
        except Exception:                                    # noqa: BLE001
            engine["bytes_per_token"] = None
            engine["kv_pool_gib"] = None
        try:
            engine["mem_total_gib"] = round(float(eng.pool_bytes()) / (1024 ** 3), 3)
        except Exception:                                    # noqa: BLE001
            pass
        if hasattr(eng, "stats") and callable(getattr(eng, "stats")):
            try:
                engine.update(eng.stats())
            except Exception:                                # noqa: BLE001
                pass
        try:
            model = ms.model_fp(self.model_path)
        except OSError:
            model = {"model_path": self.model_path, "present": False}
        rows = self._rows()
        return {
            "version": VERSION,
            "engine_meta": {"n_ctx": self.n_ctx,
                            "n_gpu_layers": self.n_gpu_layers,
                            "chat_start": self.chat_start,
                            "chat_budget": self.chat_budget,
                            "memory_budget": int(self.memory_budget),
                            "kv": "q8_0", "n_seq": N_SEQ},
            "spec": self._spec_pin(),
            "model_pin": model,
            "dll_pin": self._dll_pin(),
            "engine": engine,
            "vram_gib": None,
            "vram_gib_source": "external_sampler_required",
            "vram_gib_note": ("C 版不直接读驱动显存，null 不是 0；SPEC §4 的峰值由验收臂"
                              " tools/run_c_acceptance.py 用 nvidia-smi/PowerShell GPU 计数器外部采样，"
                              "结果写 C-V1-ACCEPT.json:resources.peak_gib"),
            "kv_pool_gib": (engine or {}).get("kv_pool_gib"),
            "memories": {"count": len(rows), "total_tokens": self._total_tokens(),
                         "max_memories": (MAX_MEMORIES if self.retrieval_mode != "topk"
                                          else LIBRARY_MAX),
                         "max_total_tokens": int(self.memory_budget)},
            "retrieval": {"mode": self.retrieval_mode, "topk": self.topk,
                          "library_count": len(rows),
                          "library_max": (MAX_MEMORIES if self.retrieval_mode != "topk"
                                          else LIBRARY_MAX),
                          "mounted_ids": [int(b["source_id"])
                                          for b in self.mounted_blocks],
                          "mounted_count": len(self.mounted_blocks),
                          "candidates": int(self._last_candidate_count or len(rows)),
                          "related": int(self._last_related_count),
                          "memory_budget": int(self.memory_budget),
                          "last_truncation": self._last_truncation},
            "session": {"path": self.session_path,
                        "exists": os.path.exists(self.session_path),
                        "chat_tokens": int(self.eng.n_tokens(0)),
                        "chat_budget": self.chat_budget,
                        "chat_start": self.chat_start,
                        "n_ctx": self.n_ctx,
                        "mounted": len(self.mounted_blocks),
                        "control": self.control,
                        "n_predict": self.n_predict,
                        "rollover_at": self.rollover_at,
                        "rollover_threshold_tokens": self._rollover_threshold()},
            "rollover": {"at": self.rollover_at,
                         "threshold_tokens": self._rollover_threshold(),
                         "last": self._last_rollover},
            "warnings": list(self.warnings),
        }

    def health(self):
        st = self.status()
        rows = self._rows()
        return {"status": "ok", "model_pin": st["model_pin"], "dll_pin": st["dll_pin"],
                "vram_gib": st["vram_gib"], "memories": len(rows),
                "session": st["session"], "engine": st["engine"],
                "retrieval": st.get("retrieval"),
                "version": VERSION}


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------
HELP = """命令：
  /remember <文本>   记住一段事实（立即可用）
  /memories          列出已存记忆
  /forget <id>|all   删除记忆（会二次确认）
  /ask <问题>        提问（等价于直接输入）
  /save [路径]       保存会话（默认 kvmem/sessions/daily.json）
  /load [路径]       恢复会话
  /status            模型/dll/记忆/会话状态
  /log [status|mode <full|redacted|hash_only>|purge all|purge before <YYYY-MM-DD>]
                     个体日志：查看/切隐私模式/清理（清理需二次确认）
  /quit              退出（自动保存）
直接输入一句话 = 提问。记忆里没有的具体事实会明确拒答，不编造。"""


def _print_result(out, cmd, res, app=None):
    if cmd == "remember":
        extra = "（已存在，未重复建块）" if res.get("duplicate") else ""
        out("已记住 #%d%s：%d token" % (res["id"], extra, res.get("n_tokens") or 0)
            + ("；可直接提问。" if not res.get("duplicate") else "。"))
    elif cmd == "memories":
        if not res:
            out("（还没有记忆，用 /remember 记一条）")
        for m in res:
            out("  #%-4d %-4d token  %s  %s"
                % (m["id"], m.get("n_tokens") or 0, m["created_at"] or "", m["first_line"]))
        out("库共 %d 条；当前挂载 %d 条；检索模式 %s%s"
            % (len(res), len(app.mounted_blocks) if app else 0,
               app.retrieval_mode if app else "off",
               ("（topk=%d）" % app.topk) if (app and app.retrieval_mode == "topk") else ""))
    elif cmd == "forget":
        out("已删除 %d 条记忆（移除块文件 %d 个）" % (res["deleted"], res.get("files_removed", 0)))
    elif cmd == "ask":
        if res.get("notice"):
            out(res["notice"])
        out("答：%s" % res["answer"])
        extra = "拒答" if res.get("refused") else "%.2fs" % res.get("latency_s", 0)
        tail = ("依据块 id：%s" % ", ".join(str(x) for x in res["block_ids"])) \
            if res.get("block_ids") else "依据：无（未命中长期记忆）"
        out("   （%s；%s）" % (extra, tail))
    elif cmd == "save":
        out("会话已保存：%s（sha16 %s，块 %d，对话 %d token）"
            % (res["path"], res["sha16"], res["n_blocks"], res["chat_tokens"]))
    elif cmd == "load":
        out("会话已恢复：%s（对话 %d token，挂载 %d 块）"
            % (res["path"], res["chat_tokens"], res["blocks"]))
    elif cmd == "status":
        out(json.dumps(res, ensure_ascii=False, indent=1))


def _confirm(readline, out, prompt):
    try:
        ans = readline(prompt)
    except (EOFError, KeyboardInterrupt):
        out("")
        return False
    return str(ans).strip().lower() in ("y", "yes", "是")


def run_repl(app, readline=None, out=None, banner=True):
    readline = readline or (lambda prompt: input(prompt))
    out = out or print
    if banner:
        out("=" * 66)
        out("C 版本地记忆助手 %s（14B / KV 记忆 / 不拼 prompt / 无网络）" % VERSION)
        out("=" * 66)
        for w in app.warnings:
            out("[提示] %s" % w)
        st = app.status()
        out("模型：%s" % st["model_pin"].get("model_path"))
        out("记忆：%d 条 / 会话：%s" % (st["memories"]["count"], st["session"]["path"]))
        if app.logger:
            out("个体日志：%s（assistant_id %s / session %s / 隐私模式 %s）"
                % (app.logger.root, app.logger.assistant_id,
                   app.logger.current_session_id(), app.logger.mode))
        out("输入 /help 看命令；/quit 退出（自动保存）。")
        out("就绪（READY）")
    reason = "user_quit"
    while True:
        try:
            line = readline("你> ")
        except EOFError:
            out("")
            reason = "eof"
            break
        except KeyboardInterrupt:
            out("")
            reason = "interrupt"
            break
        line = str(line or "").strip()
        if not line:
            continue
        try:
            if not line.startswith("/"):
                _print_result(out, "ask", app.ask(line))
                continue
            head, _, rest = line.partition(" ")
            head = head.lower()
            rest = rest.strip()
            if head in ("/quit", "/exit", "/q"):
                reason = "user_quit"
                break
            if head == "/help":
                out(HELP)
            elif head == "/remember":
                if not rest:
                    out("用法：/remember <要记住的事实> [#标签...]")
                    continue
                _print_result(out, "remember", app.remember(rest))
            elif head == "/memories":
                _print_result(out, "memories", app.memories(), app=app)
            elif head == "/forget":
                target = rest
                if not target:
                    out("用法：/forget <id> 或 /forget all")
                    continue
                label = target
                if target.lower() != "all":
                    try:
                        label = "#%d" % int(target)
                    except ValueError:
                        out("错误[bad_request]：id 必须是数字或 all")
                        continue
                if not _confirm(readline, out, "确认删除记忆 %s？输入 y 确认，其它键取消：" % label):
                    out("已取消。")
                    continue
                _print_result(out, "forget", app.forget(target))
            elif head == "/ask":
                if not rest:
                    out("用法：/ask <问题>")
                    continue
                _print_result(out, "ask", app.ask(rest))
            elif head == "/save":
                _print_result(out, "save", app.save(rest or None))
            elif head == "/load":
                _print_result(out, "load", app.load(rest or None))
            elif head == "/status":
                _print_result(out, "status", app.status())
            elif head == "/log":
                if not app.logger:
                    out("个体日志未启用。")
                else:
                    sub = rest.split()
                    if not sub or sub[0] == "status":
                        lg = app.logger
                        out("日志根目录：%s" % lg.root)
                        out("assistant_id：%s" % lg.assistant_id)
                        out("当前会话：%s（%s）" % (lg.current_session_id(),
                                                   lg._session["path"]))
                        out("隐私模式：%s；会话行数：%d" % (lg.mode, lg._session["lines"]))
                    elif sub[0] == "mode" and len(sub) >= 2:
                        try:
                            out("隐私模式已切换为：%s" % app.logger.set_mode(sub[1]))
                        except Exception as exc:             # noqa: BLE001
                            out("错误[bad_request]：%s（可选 full/redacted/hash_only）" % exc)
                    elif sub[0] == "purge":
                        if len(sub) >= 2 and sub[1] == "all":
                            if _confirm(readline, out, "确认删除全部日志？输入 y 确认："):
                                r = app.logger.purge("all")
                                out("已删除 %d 个日志文件。" % r["removed"])
                            else:
                                out("已取消。")
                        elif len(sub) >= 3 and sub[1] == "before":
                            if _confirm(readline, out, "确认删除 %s 之前的日志？输入 y 确认：" % sub[2]):
                                r = app.logger.purge("before", sub[2])
                                out("已删除 %d 个日志文件。" % r["removed"])
                            else:
                                out("已取消。")
                        else:
                            out("用法：/log purge all 或 /log purge before <YYYY-MM-DD>")
                    else:
                        out("用法：/log [status|mode <full|redacted|hash_only>|purge ...]")
            else:
                out("未知命令：%s（输入 /help）" % head)
        except DailyError as exc:
            out("错误[%s]：%s" % (exc.code, exc.message))
            if app.logger:
                app.logger.log_error(exc.code, exc.message, where="repl")
        except KeyboardInterrupt:
            out("")
            break
        except Exception as exc:                             # noqa: BLE001
            import traceback
            out("错误[internal]：%s" % exc)
            if app.logger:
                app.logger.log_error("internal", str(exc),
                                     stack=traceback.format_exc(), where="repl",
                                     fatal=False)
    try:
        out("正在保存会话…")
        res = app.save()
        out("已保存：%s（sha16 %s）" % (res["path"], res["sha16"]))
    except Exception as exc:                                 # noqa: BLE001
        out("[警告] 会话保存失败：%s" % exc)
    app.close(save=False, reason=reason)
    return 0


# ---------------------------------------------------------------------------
# 干跑目录（--dry-run 专用，throwaway）
# ---------------------------------------------------------------------------
def dryrun_paths():
    base = os.path.join(ROOT, "kvmem", "_dryrun_daily")
    model = os.path.join(base, "dryrun_model.stub")
    os.makedirs(base, exist_ok=True)
    if not os.path.exists(model):
        tmp = model + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write("dry-run placeholder model (zero GPU)\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, model)
    return {"db": os.path.join(base, "daily.db"),
            "blocks": os.path.join(base, "blocks"),
            "sessions": os.path.join(base, "sessions"),
            "model": model}


def main(argv=None):
    ap = argparse.ArgumentParser(description="C 版本地记忆助手（交互）")
    ap.add_argument("--db", default=None, help="记忆库 sqlite 路径")
    ap.add_argument("--blocks", default=None, help="KV 块目录")
    ap.add_argument("--sessions", default=None, help="会话目录")
    ap.add_argument("--session", default=None, help="默认会话文件")
    ap.add_argument("--model", default=None, help="GGUF 模型路径")
    ap.add_argument("--n-predict", type=int, default=N_PREDICT_DEFAULT,
                    help="单次回答输出 token 上限（≤%d）" % MAX_N_PREDICT)
    ap.add_argument("--control", action="store_true",
                    help="S5 对照臂：不挂载任何长期记忆")
    ap.add_argument("--retrieval", choices=list(RETRIEVAL_MODES), default="off",
                    help="挂载模式：off=全部挂载（默认，保持 S1–S7 行为）；"
                         "topk=每问只挂最相关的 topk 条")
    ap.add_argument("--n-ctx", type=int, default=N_CTX_DEFAULT,
                    help="上下文长度（默认 %d；GPU 选型后可调大）" % N_CTX_DEFAULT)
    ap.add_argument("--n-gpu-layers", type=int, default=N_GPU_LAYERS_DEFAULT,
                    help="GPU 层数（默认 %d；实测 34 层留 VRAM 余量）" % N_GPU_LAYERS_DEFAULT)
    ap.add_argument("--chat-start", type=int, default=CHAT_START_DEFAULT,
                    help="对话起点/记忆区上界（默认 %d）" % CHAT_START_DEFAULT)
    ap.add_argument("--rollover-at", type=float, default=ROLLOVER_AT_DEFAULT,
                    help="对话窗占用达该比例时自动压缩（0.75 默认；1.0 关闭）")
    ap.add_argument("--topk", type=int, default=DEFAULT_TOPK,
                    help="topk 模式每问挂载条数（1..%d，默认 %d）"
                         % (MAX_MEMORIES, DEFAULT_TOPK))
    ap.add_argument("--dry-run", action="store_true",
                    help="零 GPU 干跑（StubEngine + kvmem/_dryrun_daily 独立目录）")
    args = ap.parse_args(argv)

    if args.dry_run:
        p = dryrun_paths()
        paths = {"db": args.db or p["db"], "blocks": args.blocks or p["blocks"],
                 "sessions": args.sessions or p["sessions"],
                 "model": args.model or p["model"]}
        install_fake_model(paths["model"])
        eng = StubEngine()
    else:
        paths = {"db": args.db or DB_DEFAULT, "blocks": args.blocks or BLOCKS_DEFAULT,
                 "sessions": args.sessions or SESSIONS_DEFAULT, "model": args.model or MODEL}
        if not os.path.exists(paths["model"]):
            print("error: 模型不存在：%s" % paths["model"])
            return 2
        eng = make_real_engine(paths["model"], n_ctx=args.n_ctx,
                               n_gpu_layers=args.n_gpu_layers)
    try:
        app = DailyApp(eng, db_path=paths["db"], blocks_dir=paths["blocks"],
                       sessions_dir=paths["sessions"], session_path=args.session,
                       model_path=paths["model"], control=args.control,
                       n_predict=args.n_predict, retrieval_mode=args.retrieval,
                       topk=args.topk, rollover_at=args.rollover_at,
                       n_ctx=args.n_ctx, chat_start=args.chat_start,
                       n_gpu_layers=args.n_gpu_layers)
        return run_repl(app)
    except DailyError as exc:
        print("error[%s]: %s" % (exc.code, exc.message))
        try:
            eng.close()
        except Exception:                                    # noqa: BLE001
            pass
        return 1
    except Exception as exc:                                 # noqa: BLE001
        print("error: %s" % exc)
        try:
            eng.close()
        except Exception:                                    # noqa: BLE001
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())