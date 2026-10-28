# -*- coding: utf-8 -*-
import os as _os_env
_os_env.environ.setdefault("LLAMA_MEM_MODE", "strict")  # 这些用例验证 strict 模式的既有契约
"""test_logging_cpu.py -- C 版个体日志的零 GPU 测试（PRODUCT-C-LOG-SPEC S7a/S7b/S7c）。

覆盖：
  T1 身份：assistant_id 首次生成且不可变；改名不改 id
  T2 会话事件完整性：remember/ask/answer/refuse/save/load + session_start/session_end
     => inspect_logs --verify exit 0；ask 均有 answer/refuse；seq 连续
  T3 redacted 打码：手机号/身份证/密码不出现在日志；input_sha16 保留
  T4 崩溃恢复：子进程写半会话后 os._exit(7)（无 session_end）→ 新进程识别并写
     crash_recovered；--verify 仍 exit 0
  T5 chain 篡改 1 字节 => --verify 报 broken_chain 且 exit 1
  T6 --summary / --export：计数正确、导出脱敏（无原文）
  T7 /log purge：清理后目录为空
运行： python -X utf8 tools/test_logging_cpu.py ；exit 0 = 全过
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

import assistant_log as L          # noqa: E402
import chat_daily as D             # noqa: E402

FAILS = []
CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(name)
    if not cond:
        FAILS.append("%s %s" % (name, detail))
        print("FAIL %s %s" % (name, detail))
    else:
        print("ok   %s" % name)


def run_tool(root, *args, timeout=120):
    cmd = [sys.executable, "-X", "utf8", os.path.join(HERE, "inspect_logs.py"),
           "--root", root] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       cwd=ROOT, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def mkapp(tmp, root, model, **kw):
    return D.DailyApp(
        D.StubEngine(), db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=model, restore=False, log_root=root, **kw)


SENSITIVE = ("我的手机号是 13800138000，身份证 110101199001011234，"
             "登录密码是 Passw0rd#2026，常用邮箱 lin@example.com。")


def main():
    tmp = tempfile.mkdtemp(prefix="log_cpu_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    root = os.path.join(tmp, "assistant")
    try:
        # T1 身份
        app = mkapp(tmp, root, model)
        aid = app.logger.assistant_id
        check("T1.uuid_like", len(aid) == 36 and aid.count("-") == 4, aid)
        name = app.logger.set_display_name("阿记")
        first = app.remember(SENSITIVE)
        app.ask("我的手机号是多少？")
        app.ask("我的车牌号是多少？")
        app.save()
        app.load()
        app.status()
        app.close(save=False, reason="user_quit")
        man = json.load(open(os.path.join(root, "manifest.json"), encoding="utf-8"))
        check("T1.id_stable", man["assistant_id"] == aid, str(man.get("assistant_id")))
        check("T1.display_name", man["display_name"] == name, str(man.get("display_name")))
        check("T1.mode_default_redacted", man["log_config"]["mode"] == "redacted",
              str(man.get("log_config")))
        check("T1.pins", bool(man.get("pins", {}).get("model_sha16")) and
              bool(man["pins"].get("dll_sha16")), str(list(man.get("pins", {}).keys())))

        # T2 完整性 + S7a
        rc, out = run_tool(root, "--verify")
        check("T2.verify_exit0", rc == 0, out[:400])
        rc, out = run_tool(root, "--summary", "--json")
        s = json.loads(out)
        check("T2.summary_asks", s["asks"] == 2, json.dumps(s.get("events")))
        check("T2.summary_answers", s["answers"] == 1, json.dumps(s.get("events")))
        check("T2.summary_refuses", s["refuses"] == 1, json.dumps(s.get("events")))
        # 每个 ask 都有 answer/refuse：verify 已覆盖；再显式确认没有缺号
        sess = [os.path.join(root, "sessions", x)
                for x in os.listdir(os.path.join(root, "sessions"))]
        seqs = []
        for p in sess:
            for _, _, obj in L.read_session(p):
                seqs.append(obj.get("seq"))
        check("T2.seq_contiguous", seqs == list(range(1, len(seqs) + 1)), str(seqs))

        # T3 隐私打码
        blob = ""
        for p in sess:
            blob += open(p, encoding="utf-8").read()
        check("T3.phone_masked", "13800138000" not in blob, "raw phone leaked")
        check("T3.id_masked", ("110101199001011234" not in blob) and ("110***********1234" in blob),
              "id18 mask issue")
        check("T3.password_masked", "Passw0rd#2026" not in blob, "password leaked")
        check("T3.phone_mask_present", "138****8000" in blob, "phone mask missing")
        asks = [json.loads(x) for p in sess for x in open(p, encoding="utf-8")
                if '"event":"ask"' in x]
        check("T3.input_sha16", bool(asks) and len(asks[0].get("input_sha16", "")) == 16,
              str(asks[:1]))
        check("T3.input_text_kept_redacted", any("input_text" in a for a in asks),
              "redacted 模式应保留打码后的 input_text")

        # T4 崩溃恢复（子进程写半会话后强退）
        crash_root = os.path.join(tmp, "crash_assistant")
        script = r'''
import os, sys
sys.path.insert(0, r"%s")
import assistant_log as L
root = r"%s"
lg = L.AssistantLog(root=root, resume_crash_check=False)
lg.event("session_start", pins={"model_sha16":"x","model_bytes":1,"dll_sha16":"y",
                                "spec_pin":"z","code_sha16":"w"},
         log_config={"mode": "redacted"})
lg.log_ask("崩溃前的最后一个问题")
os._exit(7)
''' % (HERE, crash_root)
        r = subprocess.run([sys.executable, "-X", "utf8", "-c", script],
                           capture_output=True, text=True, timeout=120, cwd=ROOT)
        check("T4.subprocess_died", r.returncode == 7, "rc=%r %s" % (r.returncode, r.stderr[:200]))
        app2 = mkapp(tmp, crash_root, model)
        check("T4.crash_warning", any("异常退出" in w for w in app2.warnings),
              str(app2.warnings))
        app2.close(save=False, reason="user_quit")
        rc, out = run_tool(crash_root, "--verify")
        check("T4.crash_verify_exit0", rc == 0, out[:400])
        evs = [obj for p in L._iter_text_files(os.path.join(crash_root, "sessions"))
               for _, _, obj in L.read_session(p)]
        crashes = [e for e in evs if e.get("event") == "crash_recovered"]
        check("T4.crash_event", len(crashes) == 1 and crashes[0].get("last_seq") == 2,
              json.dumps(crashes[:1], ensure_ascii=False)[:300])
        check("T4.crash_incident",
              os.path.exists(os.path.join(crash_root, "incidents.jsonl")))

        # T5 chain 篡改 1 字节
        tam_root = os.path.join(tmp, "tamper_assistant")
        shutil.copytree(root, tam_root)
        p = L._iter_text_files(os.path.join(tam_root, "sessions"))[0]
        raw = open(p, "rb").read()
        lines = raw.split(b"\n")
        idx = None
        for i, line in enumerate(lines):
            if b'"event":"answer"' in line or b'"event":"remember"' in line:
                idx = i
                break
        check("T5.target_line", idx is not None, "no target line")
        if idx is not None:
            lines[idx] = lines[idx].replace(b'"remember"', b'"remembex"', 1)
            open(p, "wb").write(b"\n".join(lines))
            rc, out = run_tool(tam_root, "--verify")
            check("T5.tamper_exit1", rc == 1, out[:300])
            check("T5.tamper_broken_chain", "broken_chain" in out, out[:300])

        # T6 export 脱敏
        exp = os.path.join(tmp, "export.json")
        rc, out = run_tool(root, "--export", exp)
        check("T6.export_exit0", rc == 0, out[:200])
        if os.path.exists(exp):
            text = open(exp, encoding="utf-8").read()
            check("T6.export_no_raw", ("13800138000" not in text) and
                  ("Passw0rd" not in text), "export leaked raw text")
            check("T6.export_schema", json.loads(text).get("schema") ==
                  "assistant_log_export_v1", text[:120])

        # T7 purge
        app3 = mkapp(tmp, root, model)
        before = len(L._iter_text_files(os.path.join(root, "sessions")))
        r = app3.logger.purge("all")
        after = len(L._iter_text_files(os.path.join(root, "sessions")))
        app3.close(save=False, reason="eof")
        check("T7.purge", before > 0 and r["removed"] > 0, str(r))
        check("T7.purge_empty", after == 0, "sessions left=%d" % after)

        # T8 fsync 预算：每轮 remember+ask 的 fsync ≤1（批量后应为 0）
        app4 = mkapp(tmp, os.path.join(tmp, "fs_assistant"), model)
        L.FSYNC_CALLS[0] = 0          # 初始化/manifest 的 1 次 fsync 不算每轮
        app4.remember("我的车牌号是京A88888。")
        app4.ask("我的车牌号是多少？")
        check("fsync_per_turn_le_1", L.FSYNC_CALLS[0] <= 1, L.FSYNC_CALLS[0])
        app4.close(save=False, reason="eof")
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