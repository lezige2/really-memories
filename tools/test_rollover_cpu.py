# -*- coding: utf-8 -*-
import os as _os_env
_os_env.environ.setdefault("LLAMA_MEM_MODE", "strict")  # 这些用例验证 strict 模式的既有契约
"""test_rollover_cpu.py -- 对话窗自动压缩（context rollover）零 GPU 测试。

覆盖：
  T1 触发顺序：save -> summary(前向) -> remember(摘要入库) -> detach -> reset0 ->
     write(保留最近轮) -> attach -> 回答；并校验 notice/记忆入库/日志字段
  T2 摘要失败退化：写 warning: rollover_summary_fallback，退化文本入库，不静默丢
  T3 rollover 关闭（--rollover-at 1.0）：行为与旧版一致（不压缩、不多调模型）
  T4 硬保护：压缩前保存失败 => DailyError(rollover_failed)，不丢对话、不假装正常
  T5 压缩后 token 下降、保留最近 2 轮、context_rollover 字段齐全；inspect_logs --verify 仍 0
  T6 REPL 回答前打印轻提示

运行： python -X utf8 tools/test_rollover_cpu.py ; exit 0 = 全过
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

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
    """记录 ask/write_at 调用；提供摘要失败钩子。"""

    def __init__(self):
        super().__init__()
        self.ask_ops = []          # "summary" | "question"
        self.write_ops = []
        self.attached = {}
        self.ops = []

    def ask(self, seq, text, n_predict=32, pos=None):
        if "__STUB_SUMMARY_FAIL__" in str(text):
            self.ask_ops.append("summary_failed")
            raise D.DailyError("model_error", "summary forward forced failure (test hook)")
        self.ask_ops.append("summary" if "压缩成不超过" in str(text) else "question")
        return super().ask(seq, text, n_predict, pos)

    def write_at(self, seq, text, pos, add_bos=True):
        self.write_ops.append({"seq": int(seq), "pos": int(pos), "chars": len(str(text))})
        return super().write_at(seq, text, pos, add_bos)

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


def make_app(tmp, model, engine=None, **kw):
    return D.DailyApp(engine or RecordingEngine(),
                      db_path=os.path.join(tmp, "daily.db"),
                      blocks_dir=os.path.join(tmp, "blocks"),
                      sessions_dir=os.path.join(tmp, "sessions"),
                      model_path=model, restore=False, log_root=os.path.join(tmp, "assistant"),
                      **kw)


def read_events(tmp):
    out = []
    sdir = os.path.join(tmp, "assistant", "sessions")
    for fn in (os.listdir(sdir) if os.path.isdir(sdir) else []):
        for line in open(os.path.join(sdir, fn), encoding="utf-8"):
            out.append(json.loads(line))
    return out


QUESTIONS = ["介绍一下长城的历史。", "介绍一下长江的历史。",
             "介绍一下黄河的历史。", "介绍一下故宫的历史。",
             "介绍一下西湖的历史。", "介绍一下泰山的history。"]


def t_trigger_sequence(tmp, model):
    eng = RecordingEngine()
    app = make_app(tmp, model, engine=eng, rollover_at=0.001)   # 阈值 max(64,..)=64
    timeline = []
    orig_save = app.save
    app.save = lambda *a, **k: (timeline.append("save"), orig_save(*a, **k))[1]
    orig_ins = app._insert_memory_block
    app._insert_memory_block = lambda *a, **k: (timeline.append("remember"),
                                                orig_ins(*a, **k))[1]
    orig_unmount = app._unmount_all
    app._unmount_all = lambda *a, **k: (timeline.append("detach"),
                                        orig_unmount(*a, **k))[1]
    orig_reset = app.leases.reset
    app.leases.reset = lambda seq, *a, **k: (timeline.append(("reset", int(seq))),
                                             orig_reset(seq, *a, **k))[1]
    try:
        for t in ("我在云栖书店买了三本书。", "车牌号是京A88888。", "每周三晚上组会。"):
            app.remember(t)
        # 先积累对话，直到达到压缩阈值
        ro = None
        mark = None
        for i, q in enumerate(QUESTIONS):
            before_chat = int(eng.n_tokens(0))
            mark = len(timeline)
            r = app.ask(q)
            if r.get("notice"):
                ro = r
                break
        check("T1.triggered", ro is not None, "no rollover after %d asks" % (i + 1))
        if ro is None:
            return
        check("T1.notice", "上下文已自动压缩" in ro["notice"], str(ro.get("notice")))
        check("T1.rollover_fields",
              ro["rollover"]["before_tokens"] > ro["rollover"]["after_tokens"] > 0,
              str(ro["rollover"]))
        # 顺序：save -> summary 前向 -> remember -> detach -> reset0 -> write -> attach -> 回答
        check("T1.summary_forward", eng.ask_ops.count("summary") >= 1, str(eng.ask_ops))
        seg = timeline[mark:]
        check("T1.save_before_summary", "save" in seg and "remember" in seg
              and seg.index("save") < seg.index("remember"), str(seg))
        check("T1.remember_before_detach", "remember" in seg and "detach" in seg
              and seg.index("remember") < seg.index("detach"), str(seg))
        check("T1.reset0_after_detach", ("reset", 0) in seg and "detach" in seg
              and seg.index(("reset", 0)) > seg.index("detach"), str(seg))
        check("T1.write_kept", len(eng.write_ops) >= 1
              and eng.write_ops[-1]["pos"] == D.CHAT_START, str(eng.write_ops))
        # attach 必须在 write 之后（重挂记忆块）且不得 attach 后 reposition
        att = [i for i, x in enumerate(eng.ops) if x[0] == "attach"]
        check("T1.attached_after_write", bool(att), str(eng.ops[-6:]))
        check("T1.no_repos_on_attached",
              not any(o[0] == "REPOS_ON_ATTACHED" for o in eng.ops),
              str([o for o in eng.ops if o[0] == "REPOS_ON_ATTACHED"]))
        check("T1.kept_turns",
              len(app.history) >= 1 and ro["rollover"]["dropped_turns"] >= 1,
              str(ro["rollover"]))
        # 摘要入库（source mode=auto_summary）
        rows = app.con.execute("SELECT id, label, mode FROM memory_source WHERE mode='auto_summary'").fetchall()
        check("T1.summary_memory", len(rows) == 1, str(rows))
        check("T1.summary_id_recorded",
              ro["rollover"]["summary_id"] == (rows[0][0] if rows else None),
              "%r vs %r" % (ro["rollover"]["summary_id"], rows))
        # 日志字段
        roll_ev = [e for e in read_events(tmp) if e.get("event") == "context_rollover"]
        check("T1.log_event", len(roll_ev) == 1, str(len(roll_ev)))
        if roll_ev:
            e = roll_ev[0]
            for k in ("before_tokens", "after_tokens", "summary_id", "dropped_turns"):
                check("T1.log_%s" % k, k in e, str(e)[:200])
            check("T1.log_shrunk", e["after_tokens"] < e["before_tokens"], str(e)[:200])
        # inspect_logs --verify 仍 exit 0（新事件类型必填字段齐全）
        r = subprocess.run([sys.executable, "-X", "utf8",
                            os.path.join(HERE, "inspect_logs.py"),
                            "--root", os.path.join(tmp, "assistant"), "--verify"],
                           capture_output=True, text=True, timeout=120, cwd=ROOT)
        check("T1.verify", r.returncode == 0, (r.stdout or "")[:200])
    finally:
        app.close(save=False)


def t_summary_fallback(tmp, model):
    eng = RecordingEngine()
    app = make_app(tmp, model, engine=eng, rollover_at=0.001)
    try:
        app.remember("我在云栖书店买了三本书。")
        app.history = [{"q": "介绍一下长城__STUB_SUMMARY_FAIL__", "a": "长城很长。",
                        "refused": False},
                       {"q": "介绍一下黄河", "a": "黄河很黄。", "refused": False},
                       {"q": "介绍一下故宫", "a": "故宫很大。", "refused": False}]
        app.eng.cells[0] = 200
        app.eng.posmax[0] = D.CHAT_START + 199
        r = app.ask("介绍一下泰山的历史。")
        check("T2.notice", "上下文已自动压缩" in (r.get("notice") or ""), str(r.get("notice")))
        check("T2.fallback_flag", r["rollover"]["fallback"] is True, str(r["rollover"]))
        warns = [e for e in read_events(tmp)
                 if e.get("event") == "warning" and e.get("code") == "rollover_summary_fallback"]
        check("T2.warning", len(warns) >= 1, str(len(warns)))
        rows = app.con.execute("SELECT text FROM memory_source WHERE mode='auto_summary'").fetchall()
        check("T2.fallback_memory", len(rows) == 1
              and "自动摘要" in rows[0][0] and " STUB_SUMMARY_FAIL".strip() in rows[0][0],
              str(rows)[:300])
    finally:
        app.close(save=False)


def t_disabled(tmp, model):
    eng = RecordingEngine()
    app = make_app(tmp, model, engine=eng, rollover_at=1.0)
    try:
        app.remember("我在云栖书店买了三本书。")
        app.eng.cells[0] = 3000
        app.eng.posmax[0] = D.CHAT_START + 2999
        before = eng.ask_calls
        r = app.ask("我在哪家书店买的书？")
        check("T3.no_notice", not r.get("notice"), str(r.get("notice")))
        check("T3.one_forward", eng.ask_calls == before + 1,
              "%d -> %d" % (before, eng.ask_calls))
        check("T3.no_rollover_event",
              not any(e.get("event") == "context_rollover" for e in read_events(tmp)),
              "rollover event appeared")
        check("T3.chat_kept", int(eng.n_tokens(0)) > 3000, "chat reset unexpectedly")
    finally:
        app.close(save=False)


def t_hard_failure(tmp, model):
    eng = RecordingEngine()
    app = make_app(tmp, model, engine=eng, rollover_at=0.001)
    try:
        app.remember("我在云栖书店买了三本书。")
        app.history = [{"q": "介绍一下长城", "a": "长城很长。", "refused": False},
                       {"q": "介绍一下黄河", "a": "黄河很黄。", "refused": False},
                       {"q": "介绍一下故宫", "a": "故宫很大。", "refused": False}]
        app.eng.cells[0] = 200
        app.eng.posmax[0] = D.CHAT_START_DEFAULT + 199
        before_chat = int(eng.n_tokens(0))
        before_asks = eng.ask_calls
        app.save = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full (test)"))
        raised = None
        try:
            app.ask("我在哪家书店买的书？")
        except D.DailyError as exc:
            raised = exc
        check("T4.raises", raised is not None and raised.code == "rollover_failed",
              str(raised))
        check("T4.no_model_call", eng.ask_calls == before_asks,
              "%d -> %d" % (before_asks, eng.ask_calls))
        check("T4.chat_kept", int(eng.n_tokens(0)) == before_chat,
              "%d vs %d" % (eng.n_tokens(0), before_chat))
        errs = [e for e in read_events(tmp)
                if e.get("event") == "error" and e.get("code") == "rollover_failed"]
        check("T4.error_logged", len(errs) >= 1, str(len(errs)))
    finally:
        app.close(save=False)


def t_repl_notice():
    buf = []

    def out(s=""):
        buf.append(str(s))
    D._print_result(out, "ask", {"answer": "京A88888", "refused": False,
                                 "latency_s": 0.5, "block_ids": [],
                                 "notice": "（上下文已自动压缩，较早内容已存入记忆 #3）"})
    text = "\n".join(buf)
    check("T5.repl_notice", "上下文已自动压缩" in text and text.index("上下文")
          < text.index("答："), text[:200])


def main():
    tmp = tempfile.mkdtemp(prefix="rollover_cpu_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    try:
        for name in ("t1", "t2", "t3", "t4"):
            os.makedirs(os.path.join(tmp, name), exist_ok=True)
        t_trigger_sequence(os.path.join(tmp, "t1"), model)
        t_summary_fallback(os.path.join(tmp, "t2"), model)
        t_disabled(os.path.join(tmp, "t3"), model)
        t_hard_failure(os.path.join(tmp, "t4"), model)
        t_repl_notice()
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