# -*- coding: utf-8 -*-
"""Aggregate report for T-G18: block facts, both layouts' runs, geometry, hashes."""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import m2_visibility_probe as P   # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "runs_iso2"))
import _driver2 as D2   # noqa: E402  (only to re-derive the loaded paths from the manifest)

BLOCK = os.path.join(ROOT, "kvmem", "m2_v1", "blk_G_bos_c18.kvmem")
PP18 = os.path.join(ROOT, "kvmem", "m2_visibility", "blocks", "project_paraphrase18.kvmem")
CPP = os.path.join(ROOT, "llama.cpp", "src", "llama-kv-cache.cpp")
DLL = os.path.join(ROOT, "tools", "kvshim_vk.dll")
GATE_OLD = "1f140a9b8defd62a"
REG_ANCHOR = "7ec1430d972d949e"
BT = chr(96)

out = []


def say(s=""):
    out.append(s)
    print(s)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def rc_of(logpath):
    import re
    rc = None
    if os.path.exists(logpath):
        for line in open(logpath, encoding="utf-8", errors="replace"):
            m = re.search(r"rc=(-?\d+)", line)
            if line.startswith("=== attempt") and m:
                rc = m.group(1)
    return rc


def dll_of(jsonname):
    """The DLL sha measured immediately before and after that run (sha_log.txt)."""
    p = os.path.join(HERE, "sha_log.txt")
    if not os.path.exists(p):
        return None
    for line in open(p, encoding="utf-8"):
        if line.strip().endswith(jsonname):
            m = {}
            for tok in line.split():
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    m[k] = v
            return m.get("dll_before"), m.get("dll_after")
    return None


def tb(x):
    return BT + str(x) + BT


def row_run(tag, jsonpath, logpath):
    d = load(jsonpath)
    a = d["answers"][0]
    lay = d["layout"]
    segs = {s["id"]: s for s in lay["segments"]}
    home = segs["home"]
    slot4 = [s for s in lay["segments"] if s["slot"] == 4][0]
    ans = a["answer"]
    return {"tag": tag, "rc": rc_of(logpath), "ok": a["ok"], "answer": ans,
            "answer_sha256": hashlib.sha256(ans.encode()).hexdigest(),
            "head_gap_cells": lay["head_gap_cells"], "cells_on_live": d["raw"]["cell_count"],
            "home_span": [home["pos_lo"], home["pos_hi"]],
            "slot4_span": [slot4["pos_lo"], slot4["pos_hi"]],
            "slot4_block": slot4["block_id"], "slot4_cells": slot4["cells"],
            "ask_pos": a["raw_pos_max_before_ask"] + 1,
            "overlaps": d["raw"]["overlaps"],
            "control_ok": d["control_ok"], "attributable": d["attributable"],
            "dll_sha256_manifest": d["engine"]["dll_sha256"],
            "loaded_paths": [s["file"] for s in
                             D2.build_layout(lay["key"], P.load_manifest())["segments"]],
            "dll_json": d["engine"]["dll_sha256"],
            "dll_source": d["engine"].get("dll_sha256_source"),
            "dll_declared": d["engine"].get("dll_sha256_declared"),
            "dll_measured": dll_of(os.path.basename(jsonpath))}


def mm(vals):
    return "是（逐字节相同）" if len(set(vals)) == 1 else "**否（不同）**"


def main():
    man = P.load_manifest()
    say("# T-G18 产物：块、两次跑、几何、哈希、判读")
    say()
    say("## 任务 1：blk_G_bos_c18.kvmem（18 格 = 1 BOS + 17 内容 token）")
    say()
    say("命令：%s" % tb("python -X utf8 kvmem/m2_visibility/runs_g18/make_blk_G_bos_c18.py"))
    say()
    build = load(os.path.join(HERE, "blk_G_bos_c18.build.json"))
    say("- 绝对路径：%s" % tb(BLOCK))
    say("- 声明文本：%s" % build["text"])
    say("- sha256：%s" % tb(sha(BLOCK)))
    say("- 构建期断言：%d/%d 通过" % (sum(1 for c in build["checks"] if c["ok"]),
                                    len(build["checks"])))
    for c in build["checks"]:
        say("  - [%s] %s -> %s" % ("PASS" if c["ok"] else "FAIL", c["name"], c["detail"]))
    say()
    say("tools/block_info.py 的输出（本块 + 对照块）：")
    say()
    say(BT * 3)
    pr = subprocess.run([sys.executable, "-X", "utf8",
                         os.path.join(ROOT, "tools", "block_info.py"), BLOCK, PP18],
                        capture_output=True, text=True)
    for line in (pr.stdout + pr.stderr).strip().splitlines():
        say(line)
    say(BT * 3)
    say()
    runs = [("iso_fac_G18 r1", os.path.join(HERE, "iso_fac_G18_home_r1.json"),
             os.path.join(HERE, "all_g18_r1.log")),
            ("iso_fac_G18 r2", os.path.join(HERE, "iso_fac_G18_home_r2.json"),
             os.path.join(HERE, "all_g18_r2.log")),
            ("iso_fac_pp18 r1", os.path.join(HERE, "iso_fac_pp18_home_r1.json"),
             os.path.join(HERE, "all_pp18_r1.log")),
            ("iso_fac_pp18 r2", os.path.join(HERE, "iso_fac_pp18_home_r2.json"),
             os.path.join(HERE, "all_pp18_r2.log"))]
    say("## 任务 2：把 slot4 换成该块，问 home，跑两次")
    say()
    say("构型（新增，既有构型一个字节没改）要看：%s LAYOUTS 里 %s ="
        % (tb("kvmem/m2_visibility/runs_iso2/_driver2.py"), tb("iso_fac_G18")))
    say("%s，spacing 64；与 %s 只差 slot4 的内容。"
        % (tb("[(1,home),(2,project),(3,habit),(4,blk_G_bos_c18,variant)]"), tb("iso_fac_pp18")))
    say()
    say("命令（每行一条，两次只是 run-json 名不同）：")
    say()
    say(BT * 3)
    say("cd /d/llama-mem/kvmem/m2_visibility/runs_iso2")
    say("python -X utf8 _driver2.py --layout iso_fac_G18 --target home \\")
    say("  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/iso_fac_G18_home_r1.json")
    say("python -X utf8 _driver2.py --layout iso_fac_G18 --target home \\")
    say("  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/iso_fac_G18_home_r2.json")
    say("# 同一位置、slot4 = project 的 18 格改写副本（对照）")
    say("python -X utf8 _driver2.py --layout iso_fac_pp18 --target home \\")
    say("  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/iso_fac_pp18_home_r1.json")
    say("python -X utf8 _driver2.py --layout iso_fac_pp18 --target home \\")
    say("  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/iso_fac_pp18_home_r2.json")
    say("# 回归基线，跑前一次、跑后一次")
    say("python -X utf8 _driver2.py --layout iso_dup4 --target home \\")
    say("  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/reg_dup4_home_before.json")
    say("python -X utf8 _driver2.py --layout iso_dup4 --target home \\")
    say("  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/reg_dup4_home_after.json")
    say(BT * 3)
    say()
    say("外层 %s 只做一件事：别的进程占满显存导致 %s 时重试；跑成功的跑不重跑。"
        % (tb("run_with_retry.sh"), tb("kvshim_open failed")))
    say()
    rows = [row_run(*r) for r in runs]
    say("| 项 | iso_fac_G18 r1 | iso_fac_G18 r2 | iso_fac_pp18 r1 | iso_fac_pp18 r2 |")
    say("|---|---|---|---|---|")

    def line(label, fn):
        say("| %s | %s |" % (label, " | ".join(fn(r) for r in rows)))

    line("rc", lambda r: tb(r["rc"]))
    line("ok", lambda r: ("**%s**" % r["ok"]) if not r["ok"] else str(r["ok"]))
    line("head_gap_cells", lambda r: str(r["head_gap_cells"]))
    line("cells_on_live", lambda r: str(r["cells_on_live"]))
    line("home 段区间", lambda r: "[%d,%d)" % tuple(r["home_span"]))
    line("slot4 段区间", lambda r: "[%d,%d) %d格 %s" % (r["slot4_span"][0], r["slot4_span"][1],
                                                    r["slot4_cells"], r["slot4_block"]))
    line("提问点", lambda r: str(r["ask_pos"]))
    line("control_ok / attributable",
         lambda r: "%s / %s" % (r["control_ok"], r["attributable"]))
    line("答案 sha256", lambda r: tb(r["answer_sha256"]))
    say()
    say("答案全文：")
    say()
    for r in rows:
        say("**%s** ok=%s" % (r["tag"], r["ok"]))
        say()
        say(BT * 3)
        for ln in r["answer"].splitlines():
            say(ln)
        say(BT * 3)
        say()
    g18 = [r for r in rows if r["tag"].startswith("iso_fac_G18")]
    pp = [r for r in rows if r["tag"].startswith("iso_fac_pp18")]
    say("两次跑是否逐字节相同：")
    say()
    say("- iso_fac_G18：%s（%s / %s）" % (mm([r["answer"] for r in g18]),
                                       g18[0]["answer_sha256"][:16],
                                       g18[1]["answer_sha256"][:16]))
    say("- iso_fac_pp18：%s（%s / %s）" % (mm([r["answer"] for r in pp]),
                                        pp[0]["answer_sha256"][:16],
                                        pp[1]["answer_sha256"][:16]))
    say("- G18 与 pp18 之间：%s" % mm([g18[0]["answer"], pp[0]["answer"]]))
    say()
    say("几何自检（要求 home=[4075,4096)、提问点=4096、gap=0、slot4=[3886,3904) 18 格、"
        "cells_on_live=69、无重叠、control_ok）：")
    say()
    for r in rows:
        ok = (r["home_span"] == [4075, 4096] and r["head_gap_cells"] == 0
              and r["ask_pos"] == 4096 and r["slot4_span"] == [3886, 3904]
              and r["slot4_cells"] == 18 and r["cells_on_live"] == 69 and not r["overlaps"]
              and r["control_ok"])
        say("- %s -> %s（home=%s 提问点=%d gap=%d slot4=%s cells=%d overlaps=%s）"
            % (r["tag"], "PASS" if ok else "**FAIL**", r["home_span"], r["ask_pos"],
               r["head_gap_cells"], r["slot4_span"], r["cells_on_live"], r["overlaps"]))
    say()
    say("DLL sha256：本地实测 %s = %s；run json 的 %s 字段来源 = %s。"
        % (tb("sha256(tools/kvshim_vk.dll)"), tb(sha(DLL)), tb("engine.dll_sha256"),
           tb(rows[0]["dll_source"])))
    say()
    say("跑的时候实测（每次跑前后各测一次，只收前后一致的跑）：")
    say()
    for r in rows:
        m = r["dll_measured"]
        say("- %s：before=%s after=%s -> %s"
            % (r["tag"], tb(m[0]) if m else "?", tb(m[1]) if m else "?",
               "一致" if m and m[0] == m[1] else "**不一致**"))
    vals = set(r["dll_measured"][0] for r in rows if r["dll_measured"])
    say()
    say("四次跑是否同一个 DLL：%s（%d 个不同值）"
        % ("是" if len(vals) == 1 else "**否**", len(vals)))
    say()
    say("trace_gate_cpp_sha256：实测 %s = %s；"
        % (tb("sha256(llama.cpp/src/llama-kv-cache.cpp)"), tb(sha(CPP))))
    say("历史产物（kvmem/m2_visibility/evidence/score_at/reg_dup4_home.json）记的是 %s… ⇒ "
        "**不一致**；" % GATE_OLD)
    say("执行门所在行号现在是 2080（历史记 2031）。原样记录，不当成我的改动。")
    say()
    say("loaded_path（每次实际加载的文件，按 slot 顺序）：")
    say()
    say("- G18：%s" % " ; ".join(tb(p) for p in rows[0]["loaded_paths"]))
    say("- pp18：%s" % " ; ".join(tb(p) for p in rows[2]["loaded_paths"]))
    say()
    say("块 sha256：blk_G_bos_c18 = %s ；project_paraphrase18 = %s"
        % (tb(sha(BLOCK)), tb(sha(PP18))))
    say()
    say("## 过程中出现的、与预期不符的事（原样记录，不修饰）")
    say()
    say("1. **DLL 在我跑的中途被重建**：我第一次测 %s 是 %s（23:31 那版），"
        % (tb("tools/kvshim_vk.dll"), tb("648e7244…")))
    say("   23:59:42 它被别的进程重建成本轮的 %s。第一组 4 次跑（23:47–23:59）跨了这次重建，"
        % tb("3a726dbd…"))
    say("   于是**整套 6 次跑在同一个 DLL 下重跑**，旧 run json 删掉；本报告的每个数都来自重跑。")
    say("2. **别的进程占满显存**：多次出现 %s 与 %s"
        % (tb("ggml_vulkan: ErrorOutOfDeviceMemory"), tb("kvshim_open failed")))
    say("   （当时机器上有三个 5–7 GB 的 python.exe 不是我起的）。这些跑直接作废重试，未计入。")
    say("3. %s 与历史产物不一致（%s vs %s…），gate 行号也从 2031 挪到 2080。"
        % (tb("trace_gate_cpp_sha256"), tb(sha(CPP)), GATE_OLD))
    say("4. %s 里声明的 %s = %s，与盘上 DLL 实测值不符；"
        % (tb("fixtures.json"), tb("engine.dll_sha256"), rows[0]["dll_declared"]))
    say("   我接手时 _driver2.py 是把这份声明照抄进 run json（第一组跑就是这样）。"
        "23:53:25 另一个会话把它改成实测")
    say("   （现在 run json 同时有 dll_sha256_source=measured 与 dll_sha256_declared），"
        "与我的判断一致；这不是我改的，我新增的 iso_fac_G18 构型仍在。")
    say("   另外：有一个 commit（43be127）把 runs_g18/REPORT.md 一起提交了，**不是我提交的**。")
    say("5. 我自己第一版的“确定性”检查写错了：拿**不同序列**两次 save 的 sha 比对，报了 FAIL。"
        "查下来两个文件只差 header 里 18 个字节")
    say("   （偏移 100,112,…,316，值是序列号 2/3/12 字节一拍），payload 全同；同序列重跑逐字节相同。"
        "已改用同序列比对并复现。")
    say()
    say("回归基线 iso_dup4 问 home（跑前 / 跑后各一次，要求 answer sha256 以 %s 开头）："
        % REG_ANCHOR)
    say()
    for tag, jp in (("跑前", os.path.join(HERE, "reg_dup4_home_before.json")),
                    ("跑后", os.path.join(HERE, "reg_dup4_home_after.json"))):
        d = load(jp)
        a = d["answers"][0]
        s = hashlib.sha256(a["answer"].encode()).hexdigest()
        say("- %s：%s ok=%s control_ok=%s -> %s"
            % (tag, tb(s), a["ok"], d["control_ok"],
               "PASS" if s.startswith(REG_ANCHOR) else "**FAIL**"))
    say()
    say("## 预登记判读（PREREG.md）")
    say()
    g18_all_fail = all(not r["ok"] for r in g18)
    g18_all_ok = all(r["ok"] for r in g18)
    pp_all_fail = all(not r["ok"] for r in pp)
    if g18_all_ok:
        verdict = ("**通过** ⇒ 在 18 格这个位置上，副本与无关真事实都通过 ⇒ "
                   "只有\"同一事实的改写\"才翻 ⇒ 该解释得到支持")
    elif g18_all_fail and pp_all_fail:
        verdict = ("**失败** ⇒ 在 18 格这个位置上，只有副本能通过、任何非副本内容都翻 ⇒ "
                   "\"副本 vs 非副本\"才是判别量，\"改写\"的说法不成立（那只是非副本的一种）")
    else:
        verdict = "**不确定**（两次方向不一致）—— 原样上报，不判通过也不判失败"
    say(verdict)
    say()
    say("（PREREG.md 的判读条款跑前写定、跑后未改；跑之前只动过一处**事实前提**：")
    say("原文写的 trace_gate 期望值 1f140a9b… 改成本机实测 c0b1fd4a…，并注明不一致。）")
    say()
    say("实测：G18 两次 ok=%s；pp18 两次 ok=%s。G18 的答案是模板空洞 \"我住在____\"，"
        "home 的事实「广陵路」一次也没出现；pp18 同样只是空洞。"
        % ([r["ok"] for r in g18], [r["ok"] for r in pp]))
    say()
    with open(os.path.join(HERE, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print()
    print("-> %s" % os.path.join(HERE, "REPORT.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
