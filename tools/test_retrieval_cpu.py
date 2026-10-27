# -*- coding: utf-8 -*-
import os as _os_env
_os_env.environ.setdefault("LLAMA_MEM_MODE", "strict")  # 这些用例验证 strict 模式的既有契约
"""test_retrieval_cpu.py -- 检索式挂载（--retrieval topk）零 GPU 测试。

覆盖 LEAD 口径：
  T1 选择器确定性：字符 bigram / 英文词、分数降序、并列按 id 升序、topk 截取
  T2 切换问题触发 detach -> reset/load/repos -> attach（fake engine 断言调用序列，
     且 attach 后 reposition 会被 fake 守卫 raise）
  T3 无重叠问题仍拒答（不调模型）且 retrieval 为空
  T4 超预算按分数截断 + warning: retrieval_truncated
  T5 off 模式行为与旧版一致（全量挂载、库上限 6、lib 满拒记）
  T6 服务层 --retrieval/--topk 透传（/health、/status 反映模式）

运行： python -X utf8 tools/test_retrieval_cpu.py ; exit 0 = 全过
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import chat_daily as D          # noqa: E402

FAILS = []
CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(name)
    if not cond:
        FAILS.append("%s %s" % (name, detail))
        print("FAIL %s %s" % (name, detail))
    else:
        print("ok   %s" % name)


class RecordingEngine(D.StubEngine):
    """StubEngine + 调用序列记录 + M3 式『attach 后禁止 reposition』守卫。"""

    def __init__(self, factor=0.5):
        super().__init__()
        self.factor = float(factor)
        self.ops = []
        self.attached = {}
        self.last_ask_text = None

    def _guess_tokens(self, text):                     # 覆盖静态估算，便于造预算场景
        return max(1, int(len(str(text or "")) * self.factor + 0.5))

    def reset(self, seq):
        self.ops.append(("reset", int(seq)))
        super().reset(seq)

    def load(self, seq, path):
        self.ops.append(("load", int(seq)))
        return super().load(seq, path)

    def load_strict(self, seq, path):
        self.ops.append(("load_strict", int(seq)))
        return super().load_strict(seq, path)

    def repos_local(self, seq, delta, p0=0, p1=-1):
        if int(seq) in self.attached:
            self.ops.append(("REPOS_ON_ATTACHED", int(seq)))
            raise RuntimeError("M3 guard: repos_local on attached seq %d" % int(seq))
        self.ops.append(("repos", int(seq), int(delta)))
        return super().repos_local(seq, delta, p0, p1)

    def share(self, block_seq, dst_seq, lo, hi):
        self.ops.append(("attach", int(block_seq), int(lo), int(hi)))
        self.attached[int(block_seq)] = (int(lo), int(hi))
        return super().share(block_seq, dst_seq, lo, hi)

    def drop(self, dst_seq, lo, hi):
        self.ops.append(("detach", int(dst_seq), int(lo), int(hi)))
        if int(dst_seq) == 0:
            for seq, (l, h) in list(self.attached.items()):
                if int(l) == int(lo) and int(h) == int(hi):
                    del self.attached[seq]
        return super().drop(dst_seq, lo, hi)

    def ask(self, seq, text, n_predict=32, pos=None):
        self.last_ask_text = str(text)
        self.ops.append(("ask", int(seq)))
        return super().ask(seq, text, n_predict, pos)


def make_app(tmp, model, engine=None, **kw):
    return D.DailyApp(engine or RecordingEngine(),
                      db_path=os.path.join(tmp, "daily.db"),
                      blocks_dir=os.path.join(tmp, "blocks"),
                      sessions_dir=os.path.join(tmp, "sessions"),
                      model_path=model, restore=False, **kw)


def seed(app, texts):
    return [app.remember(t)["id"] for t in texts]


TOPIC_TEXTS = [
    "训练记录：周一练腿，负重 60 公斤。",
    "读书笔记：云栖书店买的旧书是《城南旧事》。",
    "车辆信息：车牌号京A88888，车型比亚迪汉。",
    "会议安排：每周三晚上 7 点组会，2 号会议室。",
    "体检结果：周三上午体检，空腹。",
    "待办事项：周五复盘，交付周报。",
    "咖啡偏好：不加糖，只喝美式。",
    "旅行计划：9 月 18 日去杭州，住西湖边。",
    "报销单：发票抬头是云栖科技。",
    "阅读清单：本周读完《长夜难明》。",
]


def t_tokens_and_determinism(tmp, model):
    app = make_app(tmp, model, retrieval_mode="topk", topk=4)
    try:
        seed(app, TOPIC_TEXTS)
        check("T1.library_10", len(app.memories()) == 10, str(len(app.memories())))
        toks = app._retrieval_tokens("车牌号京A88888 组会")
        check("T1.bigram", "车牌" in toks and "组会" in toks, str(sorted(toks)))
        check("T1.latin_word", "a88888" in " ".join(sorted(toks)), str(sorted(toks)))
        s1 = app._retrieval_select("车牌号是多少？")
        s2 = app._retrieval_select("车牌号是多少？")
        check("T1.deterministic", [x["source_id"] for x in s1] == [x["source_id"] for x in s2],
              "%r vs %r" % (s1, s2))
        check("T1.topk_cap", 1 <= len(s1) <= 4, "n=%d" % len(s1))
        check("T1.sorted_desc",
              all(s1[i]["score"] >= s1[i + 1]["score"] for i in range(len(s1) - 1)),
              str([x["score"] for x in s1]))
        check("T1.hit_vehicle", s1[0]["source_id"] == 3, str(s1))
        # topk 截断：6 条都命中「项目」时只取 4 条，且按 id 升序
        app3 = make_app(os.path.join(tmp, "topkcap"), model, retrieval_mode="topk", topk=4)
        try:
            seed(app3, ["项目 %d 号：内容。" % i for i in range(1, 7)])
            cut = app3._retrieval_select("项目")
            check("T1.topk_cut", [x["source_id"] for x in cut] == [1, 2, 3, 4],
                  str([x["source_id"] for x in cut]))
        finally:
            app3.close()
        # 并列按 id 升序：两条都只命中「苹果」时，低 id 在前
        app2 = make_app(os.path.join(tmp, "tie"), model, retrieval_mode="topk", topk=4)
        try:
            seed(app2, ["水果：苹果很甜。", "水果：苹果很酸。", "无关：今天下雨。"])
            tie = app2._retrieval_select("苹果")
            check("T1.tie_id_asc", [x["source_id"] for x in tie] == [1, 2],
                  str([x["source_id"] for x in tie]))
        finally:
            app2.close()
    finally:
        app.close()


def t_switch_order(tmp, model):
    eng = RecordingEngine()
    app = make_app(tmp, model, engine=eng, retrieval_mode="topk", topk=2)
    try:
        seed(app, TOPIC_TEXTS)
        r1 = app.ask("车牌号是多少？")
        check("T2.first_mount", r1["block_ids"] and eng.attached, str(r1["block_ids"]))
        check("T2.no_bad_repos", not any(o[0] == "REPOS_ON_ATTACHED" for o in eng.ops),
              str([o for o in eng.ops if o[0] == "REPOS_ON_ATTACHED"]))
        mark = len(eng.ops)
        r2 = app.ask("每周三组会在哪个会议室？")
        check("T2.second_asked", (not r2["refused"]) and r2["block_ids"],
              str(r2["retrieval"]))
        seq = eng.ops[mark:]
        detach_idx = [i for i, o in enumerate(seq) if o[0] == "detach"]
        check("T2.detach_happened", bool(detach_idx), str(seq[:10]))
        first_detach = detach_idx[0] if detach_idx else None
        if first_detach is not None:
            after = seq[first_detach:]
            # 新块的 reset/load/repos 必须在 detach 之后；repos 必须先于 attach
            for i, o in enumerate(after):
                if o[0] == "repos":
                    later_attach = any(x[0] == "attach" and x[1] == o[1] for x in after[i:])
                    check("T2.repos_before_attach_%d" % o[1], later_attach, str(after[i:i + 4]))
            check("T2.no_bad_repos_switch",
                  not any(o[0] == "REPOS_ON_ATTACHED" for o in seq), str(seq[:8]))
        check("T2.asked_second", eng.last_ask_text and "每周三" in eng.last_ask_text,
              repr(eng.last_ask_text))
    finally:
        app.close()


def t_no_overlap_refuse(tmp, model):
    app = make_app(tmp, model, retrieval_mode="topk", topk=4)
    try:
        seed(app, TOPIC_TEXTS)
        before = app.eng.ask_calls
        r = app.ask("我的护照号码是多少？")
        check("T3.refused", r["refused"] is True, str(r))
        check("T3.no_model", app.eng.ask_calls == before,
              "%d -> %d" % (before, app.eng.ask_calls))
        check("T3.empty_selection",
              r["retrieval"] is not None and r["retrieval"]["selected_ids"] == [],
              str(r["retrieval"]))
    finally:
        app.close()


def t_budget_truncation(tmp, model):
    eng = RecordingEngine(factor=1.0)                  # token ≈ 字符数，便于造超预算
    app = make_app(tmp, model, engine=eng, retrieval_mode="topk", topk=4)
    try:
        seed(app, ["截断测试：关键词 ZXCV 第 1 条，补充内容" * 3,
                   "截断测试：关键词 ZXCV 第 2 条，补充内容" * 3,
                   "截断测试：关键词 ZXCV 第 3 条，补充内容" * 3])
        app.memory_budget = 100                        # 人为压低预算
        r = app.ask("关键词 ZXCV")
        ret = r["retrieval"]
        check("T4.truncated_flag", ret is not None and ret["truncated"] is True, str(ret))
        check("T4.mounted_limited", len(app.mounted_blocks) == 1,
              "mounted=%d" % len(app.mounted_blocks))
        check("T4.scores_kept", ret and ret["scores"] and len(ret["selected_ids"]) == 1,
              str(ret))
        # 日志里有 warning: retrieval_truncated
        warns = 0
        sdir = os.path.join(tmp, "assistant", "sessions")
        for fn in (os.listdir(sdir) if os.path.isdir(sdir) else []):
            for line in open(os.path.join(sdir, fn), encoding="utf-8"):
                obj = json.loads(line)
                if obj.get("event") == "warning" and obj.get("code") == "retrieval_truncated":
                    warns += 1
        check("T4.warning_logged", warns >= 1, "warns=%d" % warns)
        check("T4.truncation_record", app.status()["retrieval"]["last_truncation"] is not None,
              str(app.status()["retrieval"]["last_truncation"]))
        check("T4.no_bad_repos", not any(o[0] == "REPOS_ON_ATTACHED" for o in eng.ops))
    finally:
        app.close()


def t_off_mode_parity(tmp, model):
    app = make_app(tmp, model, retrieval_mode="off")
    try:
        ids = seed(app, TOPIC_TEXTS[:6])
        st = app.status()["retrieval"]
        check("T5.mode_off", st["mode"] == "off" and st["topk"] == 4, str(st))
        check("T5.library_max6", st["library_max"] == 6, str(st))
        r = app.ask("车牌号是多少？")
        check("T5.mounted_all", len(app.mounted_blocks) == 6,
              "mounted=%d" % len(app.mounted_blocks))
        check("T5.block_ids", bool(r["block_ids"]), str(r["block_ids"]))
        try:
            app.remember("第 7 条：应该被 off 模式拒绝。")
            check("T5.cap_enforced", False, "no error")
        except D.DailyError as exc:
            check("T5.cap_enforced", exc.code == "memory_full", exc.code)
    finally:
        app.close()


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def http(base, path):
    with urllib.request.urlopen(base + path, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def t_service_passthrough(tmp, model):
    port = free_port()
    base = "http://127.0.0.1:%d" % port
    work = os.path.join(tmp, "svc")
    logf = open(os.path.join(tmp, "svc.log"), "w+", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", os.path.join(HERE, "chat_service.py"),
         "--fake-engine", "--port", str(port), "--data-dir", work,
         "--retrieval", "topk", "--topk", "2"],
        cwd=ROOT, stdout=logf, stderr=subprocess.STDOUT)
    try:
        up = False
        for _ in range(120):
            try:
                h = http(base, "/health")
                up = h.get("status") == "ok"
                if up:
                    break
            except Exception:                          # noqa: BLE001
                pass
            time.sleep(0.25)
        check("T6.service_up", up, "health timeout")
        if up:
            h = http(base, "/health")
            check("T6.health_retrieval", h.get("retrieval", {}).get("mode") == "topk",
                  str(h.get("retrieval")))
            check("T6.health_topk", h.get("retrieval", {}).get("topk") == 2,
                  str(h.get("retrieval")))
            st = http(base, "/status")
            check("T6.status_retrieval", st.get("retrieval", {}).get("mode") == "topk",
                  str(st.get("retrieval")))
            check("T6.status_library", st.get("retrieval", {}).get("library_max") == 200,
                  str(st.get("retrieval")))
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(10)
        logf.close()


def main():
    tmp = tempfile.mkdtemp(prefix="retr_cpu_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    try:
        t_tokens_and_determinism(os.path.join(tmp, "t1"), model)
        os.makedirs(os.path.join(tmp, "t2"), exist_ok=True)
        t_switch_order(os.path.join(tmp, "t2"), model)
        os.makedirs(os.path.join(tmp, "t3"), exist_ok=True)
        t_no_overlap_refuse(os.path.join(tmp, "t3"), model)
        os.makedirs(os.path.join(tmp, "t4"), exist_ok=True)
        t_budget_truncation(os.path.join(tmp, "t4"), model)
        os.makedirs(os.path.join(tmp, "t5"), exist_ok=True)
        t_off_mode_parity(os.path.join(tmp, "t5"), model)
        t_service_passthrough(tmp, model)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d checks, %d failed" % (len(CHECKS), len(FAILS)))
    if FAILS:
        print("FAILURES:")
        for f in FAILS:
            print(" - %s" % f)
        return 1
    print("ALL PASS (zero GPU / fake engine)")
    return 0


if __name__ == "__main__":
    sys.exit(main())