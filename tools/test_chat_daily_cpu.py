# -*- coding: utf-8 -*-
import os as _os_env
_os_env.environ.setdefault("LLAMA_MEM_MODE", "strict")  # 这些用例验证 strict 模式的既有契约
"""test_chat_daily_cpu.py -- C 版日常助手的零 GPU 测试。

覆盖（全部走 StubEngine + 临时目录，不加载模型 / 不碰 DLL / 不联网）：
  T1  命令解析与 REPL 分发（含未知命令、空输入、缺参数）
  T2  remember -> /memories -> 追问命中（三类真实用例：个人信息/每周任务/待办）
  T3  拒答：记忆里没有的具体事实 => 固定拒答文本，且模型未被调用
  T4  save -> 新进程对象自动恢复 -> 对话 token 与记忆仍在（S3 的 CPU 版）
  T5  forget：二次确认取消不删；确认后删除块文件与索引行；同题再问不再命中（S4 的 CPU 版）
  T6  异常输入：空文本 / 超长 / 不存在 id / 非数字 id / 空问题 / 未知会话文件
  T7  容量：记忆条数上限与重复内容去重
  T8  /status 字段齐全；/health 汇总字段齐全
  T9  零 GPU 断言：本测试进程从未 import kvslots（真实引擎模块）
  T10 退出自动保存（run_repl /quit 后 daily.json 存在且可被新对象恢复）

运行： python -X utf8 tools/test_chat_daily_cpu.py ; 退出码 0 = 全过
"""

import io
import json
import re
import os
import shutil
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
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


def make_app(tmp, restore=False, model=None, **kw):
    app = D.DailyApp(
        D.StubEngine(),
        db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=model or os.path.join(tmp, "model.stub"),
        restore=restore,
        **kw
    )
    return app


# 三类真实用例（个人信息 / 每周任务纲要 / 待办事项）
FACTS = {
    "personal": "我的工位在 6 楼 B 区，分机号 8042，常用邮箱是 lin@example.com。",
    "weekly": "我每周三晚上 7 点有组会，地点在 2 号会议室，主持人是老周。",
    "todo": "本周要交周报、周三体检、周五复盘；咖啡不加糖，会议用中文。",
}
ASK_HIT = {
    "personal": "我的工位分机号是多少？",
    "weekly": "每周三晚上的组会在哪个会议室？",
    "todo": "本周要交什么？",
}
ASK_MISS = "我的车牌号是多少？"


def t_repl_dispatch(tmp, model):
    app = make_app(tmp, model=model)
    try:
        script = [
            "/help",
            "/remember " + FACTS["personal"],
            "/memories",
            ASK_HIT["personal"],
            "/ask " + ASK_HIT["personal"],
            "/bogus",
            "/forget",
            "/remember",
            "/quit",
        ]
        it = iter(script)

        def readline(prompt=""):
            try:
                return next(it)
            except StopIteration:
                raise EOFError()

        buf = io.StringIO()
        rc = D.run_repl(app, readline=readline, out=lambda s="": buf.write(str(s) + "\n"),
                        banner=False)
        text = buf.getvalue()
        check("T1.repl.rc", rc == 0, "rc=%r" % rc)
        check("T1.repl.remember", "已记住 #1" in text, text[:200])
        check("T1.repl.memories", "共 1 条" in text, text[:200])
        check("T1.repl.answer", "答：" in text, text[:200])
        check("T1.repl.unknown", "未知命令" in text, text[:200])
        check("T1.repl.usage_forget", "用法：/forget" in text, text[:200])
        check("T1.repl.usage_remember", "用法：/remember" in text, text[:200])
        check("T1.repl.saved_on_quit", "已保存" in text, text[:200])
        check("T1.repl.session_file", os.path.exists(os.path.join(tmp, "sessions", "daily.json")))
    finally:
        app.close(save=False)


def t_remember_and_ask(tmp, model):
    app = make_app(tmp, model=model)
    try:
        ids = {}
        for key, text in FACTS.items():
            r = app.remember(text)
            ids[key] = r["id"]
            check("T2.remember.%s" % key, r["id"] > 0 and r["n_tokens"] > 0, str(r))
        check("T2.memories.count", len(app.memories()) == 3, str(app.memories()))
        # 记住后立即可用（同一进程，下一条问题即命中）
        for key, q in ASK_HIT.items():
            a = app.ask(q)
            check("T2.ask_hit.%s" % key, (not a["refused"]) and a["block_ids"], str(a))
            check("T2.ask_hit_ids.%s" % key, ids[key] in a["block_ids"], str(a))
        # 重复内容去重
        dup = app.remember(FACTS["weekly"])
        check("T2.dedupe", dup.get("duplicate") is True and len(app.memories()) == 3, str(dup))
    finally:
        app.close(save=False)


def t_refusal(tmp, model):
    app = make_app(tmp, model=model)
    try:
        app.remember(FACTS["personal"])
        before = app.eng.ask_calls
        a = app.ask(ASK_MISS)
        check("T3.refused", a["refused"] is True, str(a))
        check("T3.fixed_text", "不想猜" in a["answer"], str(a))
        check("T3.no_model_call", app.eng.ask_calls == before,
              "ask_calls %d -> %d" % (before, app.eng.ask_calls))
        check("T3.no_block_ids", a["block_ids"] == [], str(a))
        # 一般性问题（世界知识）不拒答，允许模型回答
        g = app.ask("介绍一下长城的历史")
        check("T3.general_generates", g["refused"] is False, str(g))
    finally:
        app.close(save=False)


def t_save_restore(tmp, model):
    app = make_app(tmp, model=model)
    try:
        for text in FACTS.values():
            app.remember(text)
        app.ask(ASK_HIT["weekly"])
        n_chat = int(app.eng.n_tokens(0))
        s = app.save()
        check("T4.save.file", os.path.exists(s["path"]), str(s))
        check("T4.save.sha16", len(s["sha16"]) == 16, str(s))
        check("T4.save.blocks", s["n_blocks"] == 3, str(s))
    finally:
        app.close(save=False)
    # 新对象 = 模拟重开进程：不显式 /load，自动恢复最近的 daily.json
    eng2 = D.StubEngine()
    app2 = D.DailyApp(eng2, db_path=os.path.join(tmp, "daily.db"),
                      blocks_dir=os.path.join(tmp, "blocks"),
                      sessions_dir=os.path.join(tmp, "sessions"),
                      model_path=model, restore=True)
    try:
        check("T4.restore.warnings", not app2.warnings, str(app2.warnings))
        check("T4.restore.chat_tokens", int(eng2.n_tokens(0)) == n_chat,
              "%d vs %d" % (eng2.n_tokens(0), n_chat))
        check("T4.restore.mounted", len(app2.mounted) == 3, str(app2.mounted))
        check("T4.restore.history", len(app2.history) >= 1, str(app2.history))
        a = app2.ask(ASK_HIT["todo"])
        check("T4.restore.ask_hit", (not a["refused"]) and a["block_ids"], str(a))
        # 显式 /load 到自定义路径
        p2 = os.path.join(tmp, "sessions", "other.json")
        app2.save(p2)
        app2.load(p2)
        check("T4.explicit_load", int(eng2.n_tokens(0)) > 0, "chat=%d" % eng2.n_tokens(0))
    finally:
        app2.close(save=False)


def t_forget(tmp, model):
    # A. app 层语义：删除后索引/块文件消失，同题再问不再命中（对话也被重置）
    app = make_app(tmp, model=model)
    try:
        for text in FACTS.values():
            app.remember(text)
        sid = app.memories()[0]["id"]
        block_path = [r for r in app._rows() if int(r[0]) == sid][0][6]
        r = app.forget(sid)
        check("T5.deleted", r["deleted"] == 1, str(r))
        check("T5.row_gone", all(int(x[0]) != sid for x in app._rows()), str(app.memories()))
        check("T5.file_gone", not os.path.exists(block_path), block_path)
        check("T5.dialogue_reset", r.get("dialogue_reset") is True, str(r))
        a = app.ask(ASK_HIT["personal"])
        check("T5.after_forget_refused", a["refused"] is True, str(a))
    finally:
        app.close(save=False)
    # B. REPL 二次确认：先回 n 取消，再回 y 删除
    sub = os.path.join(tmp, "repl")
    os.makedirs(sub, exist_ok=True)
    app2 = make_app(sub, model=model)
    try:
        sid2 = app2.remember(FACTS["weekly"])["id"]
        script = ["/forget %d" % sid2, "n", "/forget %d" % sid2, "y", "/quit"]
        it = iter(script)

        def readline(prompt=""):
            try:
                return next(it)
            except StopIteration:
                raise EOFError()

        buf = io.StringIO()
        rc = D.run_repl(app2, readline=readline,
                        out=lambda s="": buf.write(str(s) + "\n"), banner=False)
        text = buf.getvalue()
        check("T5.repl.rc", rc == 0, str(rc))
        check("T5.cancel_kept", "已取消" in text, text[:300])
        check("T5.repl.deleted", "已删除 1 条记忆" in text, text[:300])
        check("T5.repl.saved", os.path.exists(os.path.join(sub, "sessions", "daily.json")))
        import sqlite3
        con = sqlite3.connect(os.path.join(sub, "daily.db"))
        try:
            n = con.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
        finally:
            con.close()
        check("T5.repl.row_gone", n == 0, "rows=%d" % n)
    finally:
        app2.close(save=False)


def t_bad_input(tmp, model):
    app = make_app(tmp, model=model)
    try:
        def expect_err(fn, code):
            try:
                fn()
            except D.DailyError as exc:
                return exc.code == code, "code=%s" % exc.code
            return False, "no error"
        ok, d = expect_err(lambda: app.remember("   "), "bad_request")
        check("T6.empty_remember", ok, d)
        ok, d = expect_err(lambda: app.remember("长" * (D.MAX_TEXT_CHARS + 1)), "bad_request")
        check("T6.too_long", ok, d)
        ok, d = expect_err(lambda: app.forget("abc"), "bad_request")
        check("T6.forget_bad_id", ok, d)
        ok, d = expect_err(lambda: app.forget("999"), "not_found")
        check("T6.forget_missing", ok, d)
        ok, d = expect_err(lambda: app.forget("all"), "not_found")
        check("T6.forget_all_empty", ok, d)
        ok, d = expect_err(lambda: app.ask("  "), "bad_request")
        check("T6.empty_ask", ok, d)
        ok, d = expect_err(lambda: app.load(os.path.join(tmp, "nope.json")), "not_found")
        check("T6.load_missing", ok, d)
    finally:
        app.close(save=False)


def t_capacity(tmp, model):
    app = make_app(tmp, model=model)
    try:
        for i in range(D.MAX_MEMORIES):
            app.remember("容量测试第 %d 条：编号 CAP-%04d。" % (i + 1, i + 1))
        check("T7.max_memories", len(app.memories()) == D.MAX_MEMORIES, str(app.memories()))
        try:
            app.remember("第 7 条应该被拒绝。")
            check("T7.over_limit", False, "no error")
        except D.DailyError as exc:
            check("T7.over_limit", exc.code == "memory_full", exc.code)
        # /forget all 清空
        r = app.forget("all")
        check("T7.forget_all", r["deleted"] == D.MAX_MEMORIES, str(r))
        check("T7.empty_after_all", app.memories() == [], str(app.memories()))
    finally:
        app.close(save=False)


class GuardedStubEngine(D.StubEngine):
    """模拟 M3 守卫（真实 fail-closed 行为）：

    - 被 attach 到对话 seq 0 的块 seq，禁止 repos_local（真实 Engine 会静默移动共享 cell，
      所以 GuardedLeases 先拒绝）；
    - drop 掉对应区间后解除；
    - 记录最后一次 ask 的文本，用于验证「指令前缀」与「prompt 不含记忆原文」。
    这样若产品代码把「先 reposition 再 attach」的顺序写反，本测试会直接炸。
    """

    def __init__(self):
        super().__init__()
        self.attached = {}
        self.repos_refused = 0
        self.last_ask_text = None

    def share(self, block_seq, dst_seq, lo, hi):
        self.attached[int(block_seq)] = (int(lo), int(hi))
        return super().share(block_seq, dst_seq, lo, hi)

    def drop(self, dst_seq, lo, hi):
        if int(dst_seq) == 0:
            for seq, (l, h) in list(self.attached.items()):
                if int(l) == int(lo) and int(h) == int(hi):
                    del self.attached[seq]
        return super().drop(dst_seq, lo, hi)

    def repos_local(self, seq, delta, p0=0, p1=-1):
        if int(seq) in self.attached:
            self.repos_refused += 1
            raise D.DailyError("internal",
                              "M3-guard simulation: repos_local(seq %d) while attached"
                              % int(seq))
        return super().repos_local(seq, delta, p0, p1)

    def ask(self, seq, text, n_predict=32, pos=None):
        self.last_ask_text = str(text)
        return super().ask(seq, text, n_predict, pos)


def t_placement_guard(tmp, model):
    """attach 之后再改块集：必须先 detach 才能 reset/load/repos（Lead 的 GPU 冒烟教训）。"""
    eng = GuardedStubEngine()
    app = D.DailyApp(eng, db_path=os.path.join(tmp, "daily.db"),
                     blocks_dir=os.path.join(tmp, "blocks"),
                     sessions_dir=os.path.join(tmp, "sessions"),
                     model_path=model, restore=False)
    try:
        app.remember(FACTS["weekly"])
        r1 = app.ask("每周三晚上的组会在哪个会议室？")
        check("T10.first_mount_ok", (not r1["refused"]) and eng.repos_refused == 0,
              "repos_refused=%d" % eng.repos_refused)
        # 命中记忆 => prompt = 指令 + 问题，且不含记忆原文
        check("T10.instruction_prefix",
              (eng.last_ask_text or "").startswith(D.ANSWER_INSTRUCTION),
              repr((eng.last_ask_text or "")[:80]))
        check("T10.no_memory_text_in_prompt", "2 号会议室" not in (eng.last_ask_text or ""),
              repr((eng.last_ask_text or "")[:120]))
        # 块集变化 => detach 旧区间 -> reset/load/repos -> attach 新区间（顺序不能反）
        app.remember(FACTS["todo"])
        r2 = app.ask("本周要交什么？")
        check("T10.remount_ok", (not r2["refused"]) and eng.repos_refused == 0,
              "repos_refused=%d mounted=%r" % (eng.repos_refused, sorted(app.mounted)))
        check("T10.two_mounted", len(app.mounted) == 2, str(sorted(app.mounted)))
        # 守卫确实生效：直接对被 attach 的块 seq 调 repos_local 必须被拒（否则本测试无意义）
        seq = app.mounted[FACTS.keys().__iter__().__next__()] if False else None
        any_seq = sorted(v[0] for v in app.mounted.values())[0]
        refused = False
        try:
            eng.repos_local(any_seq, +8)
        except Exception:                                # M3 守卫抛 LeaseError（非 DailyError）
            refused = True
        check("T10.guard_is_real", refused, "repos_local on attached seq was allowed")
        # QUIT 前 detach + reset：关闭后不应残留 attach 引用与块 cell
        app.save()
        app.close(save=False, reason="user_quit")
        check("T10.close_detached", eng.attached == {}, str(eng.attached))
        check("T10.close_reset",
              all(eng.n_tokens(s) == 0 for s in range(1, D.N_SEQ)),
              str({s: eng.n_tokens(s) for s in range(1, D.N_SEQ)}))
    finally:
        try:
            app.close(save=False)
        except Exception:                                # noqa: BLE001
            pass


def t_clean_answer():
    """think 标签 / 指令回显 / 续写问答模板都必须被剥离（REPL 与 HTTP/SSE 共用）。"""
    LT, GT = chr(60), chr(62)                      # 尖括号用 chr 构造，避免补丁吞字符
    think_open, think_close = LT + "think" + GT, LT + "/think" + GT
    cases = [
        ("think_pair",
         think_open + "先想一下用户问什么" + think_close + "我的车牌号是京A88888。",
         "我的车牌号是京A88888"),
        ("think_unclosed", think_open + "先想一下用户问什么", ""),
        ("stray_think", "我的车牌号是京A88888。" + think_close, "我的车牌号是京A88888"),
        ("template_echo",
         "好的，我来回答。\n我的车牌号是京A88888。 我的车型是什么？ 答：我的车型是比亚迪汉。 ",
         "好的，我来回答。 我的车牌号是京A88888"),
        ("stray_think", "我的车牌号是京A88888。 ", "我的车牌号是京A88888"),
        ("template_echo",
         "好的，我来回答。\n我的车牌号是京A88888。 我的车型是什么？ 答：我的车型是比亚迪汉。 ",
         "好的，我来回答。 我的车牌号是京A88888"),
        ("instruction_echo",
         D.ANSWER_INSTRUCTION + "\n我的车牌号是京A88888。", "我的车牌号是京A88888"),
        ("special_tokens", "我的车牌号是京A88888。 <|im_end|>", "我的车牌号是京A88888"),
    ]
    for name, raw, expect in cases:
        got = D.clean_answer(raw)
        check("T11.%s" % name, got == expect, "got=%r expect=%r" % (got, expect))
    for bad in ("think", "答：", "？", "? ", D.ANSWER_INSTRUCTION):
        check("T11.no_%s" % re.sub(r"\W+", "_", bad).strip("_"),
              bad not in D.clean_answer(cases[3][1]), "%r leaked" % bad)


def t_status(tmp, model):
    app = make_app(tmp, model=model)
    try:
        app.remember(FACTS["weekly"])
        st = app.status()
        for k in ("version", "model_pin", "dll_pin", "engine", "memories", "session",
                  "vram_gib", "warnings"):
            check("T8.status.%s" % k, k in st, sorted(st.keys()))
        h = app.health()
        for k in ("status", "model_pin", "dll_pin", "vram_gib", "memories", "session"):
            check("T8.health.%s" % k, k in h, sorted(h.keys()))
        check("T8.health.ok", h["status"] == "ok", str(h))
        check("T8.control_default_off", st["session"]["control"] is False, str(st["session"]))
    finally:
        app.close(save=False)


def t_no_gpu_import():
    check("T9.no_kvslots_import", "kvslots" not in sys.modules,
          "kvslots was imported: %r" % ("kvslots" in sys.modules))


def main():
    tmp = tempfile.mkdtemp(prefix="chat_daily_cpu_")
    model = os.path.join(tmp, "model.stub")
    try:
        D.install_fake_model(model)
        t_no_gpu_import()
        t_clean_answer()
        t_repl_dispatch(tmp, model)
        # 每个用例独立目录，避免会话/记忆互相污染
        for fn in (t_remember_and_ask, t_refusal, t_save_restore, t_forget,
                   t_bad_input, t_capacity, t_status, t_placement_guard):
            sub = os.path.join(tmp, fn.__name__)
            os.makedirs(sub, exist_ok=True)
            try:
                fn(sub, model)
            except Exception:                            # noqa: BLE001
                traceback.print_exc()
                FAILS.append("%s raised" % fn.__name__)
                print("FAIL %s raised" % fn.__name__)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d checks, %d failed" % (len(CHECKS), len(FAILS)))
    if FAILS:
        print("FAILURES:")
        for f in FAILS:
            print(" - %s" % f)
        return 1
    print("ALL PASS (zero GPU / zero model / zero network)")
    return 0


if __name__ == "__main__":
    sys.exit(main())