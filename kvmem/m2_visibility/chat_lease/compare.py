# -*- coding: utf-8 -*-
"""Acceptance table for the chat.py lease wiring.  python compare.py [--chat PATH] [--out PATH]

退出码（与 check_m3_injection.py 对齐）:
  0 = 全部判据满足
  1 = 判据红（静态计数不符, 或别的验收项不成立）
  2 = 用法错（--chat 指向的文件不存在 / 是个目录）
  3 = 环境或数据错（读不了、编码崩、JSON 坏）
错误与警告一律走 stderr, 正常报告走 stdout。
"""
import argparse, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
CHAT = os.path.join(ROOT, "tools", "chat.py")
LABELS = ("before", "after", "revert")

# ---- 静态判据表: 期望值写在这里, 不散在 if 里; 每条都带一句「为什么是这个值」----
# 前四条要求 0: 任何绕过租约的裸调用都会让 holders / ranges 的记账与真实状态脱节,
# 于是「释放时机可证」这件事就断了。#29 = 只有一处记账点, 判据才可核。
STATIC_EXPECT = (
    ("eng.reset(", 0,
     "裸引擎重置绕过租约: 块被清掉但持有计数不减, 释放时机从此不可证"),
    ("eng.share(", 0,
     "共享必须走 leases.share: 裸 eng.share 不增持有计数, 租约账本会漏记一个持有者"),
    ("eng.drop(", 0,
     "丢块必须走租约: 裸 eng.drop 会让 holders / ranges 与本机真实状态脱节"),
    ("safe_reset_all", 0,
     "safe_reset_all 一次清空全部块, 与「只释放自己那一份」的设计正相反"),
    ("leases.reset(", 4,
     "四条写块 / 装载路径各自在动手前释放自己的旧租约: "
     "chat.place.fresh / slots.place.fresh / m1.unmount.after_detach / m1.mount.before_load"),
)

# 四个释放点必须逐一具名。期望值写死成集合, 不是"数目对得上就算"。
# 起因: 把 m1.mount.before_load 改成 m1.mount.beforeLoad, 计数与站点数都不变 => 原来 rc=0 放行。
EXPECTED_RESET_SITES = ("chat.place.fresh", "slots.place.fresh",
                        "m1.unmount.after_detach", "m1.mount.before_load")

STATIC_PATTERNS = {
    "eng.reset(": r"(?<!leases\.)\beng\.reset\(",
    "eng.share(": r"(?<!leases\.)\beng\.share\(",
    "eng.drop(": r"(?<!leases\.)\beng\.drop\(",
    "safe_reset_all": r"safe_reset_all",
    "leases.reset(": r"leases\.reset\(",
}


class UsageError(Exception):
    """「你给错了东西」—— 用法错, rc=2。"""


def _err(msg=""):
    """所有错误与警告的唯一出口: 只抓一路日志的调用方不会漏掉一半。"""
    print(msg, file=sys.stderr)


def load(p):
    return json.load(open(os.path.join(HERE, p), encoding="utf-8")) if os.path.exists(
        os.path.join(HERE, p)) else None


def table():
    rows = {}
    for cmd in ("chat", "m1", "save"):
        rows[cmd] = []
        per = {lb: {p["q"]: p["sha16"] for p in (load("run_%s.json" % lb) or {}).get(cmd, {}).get("pairs", [])}
               for lb in LABELS}
        qs = [p["q"] for p in (load("run_before.json") or {}).get(cmd, {}).get("pairs", [])]
        for q in qs:
            rows[cmd].append({"q": q, **{lb: per[lb].get(q) for lb in LABELS},
                              "identical": len({per[lb].get(q) for lb in LABELS}) == 1})
    return rows


def read_source(path):
    """读被测源码。用法错 / 环境错在这里分开, 别让它们冒充判据红（纪律 34 的形态）。"""
    if os.path.isdir(path):
        raise UsageError("--chat 指向的是目录, 不是文件: %s" % path)
    if not os.path.exists(path):
        raise UsageError("--chat 指向的文件不存在: %s" % path)
    raw = open(path, "rb").read()          # sha256 必须对文件原字节算, 否则「这是哪份源码」无法与 run_*.json 里的记录对齐
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()[:16]


def scan(src):
    return {key: len(re.findall(STATIC_PATTERNS[key], src)) for key, _, _ in STATIC_EXPECT}


def judge_static(bare, src):
    """扫描 -> 判。返回逐条裁决, 供打印、写进产物、并决定 rc。"""
    out = []
    for key, expect, why in STATIC_EXPECT:
        actual = bare[key]
        out.append({"criterion": key, "expected": expect, "actual": actual,
                    "ok": actual == expect, "why": why})
    # 附加不变量: 站点名必须与显式期望集合**逐项相等**。期望值是常数(来自四处释放点),
    # 不是用同一段代码数出来的 total —— 否则计数判据一红, 这条反而恒绿(循环期望)。
    sites = re.findall(r'leases\.reset\([^\n]*?site="([^"]+)"', src)
    got, want = set(sites), set(EXPECTED_RESET_SITES)
    out.append({"criterion": "leases.reset( 的 site 名集合",
                "expected": list(EXPECTED_RESET_SITES), "actual": sorted(got),
                "ok": got == want,
                "why": "四处释放点各自具名; 少一个 / 多一个 / 改名都算红（改名会让「四个站」失去指认力）"
                       + ("" if got == want else
                          " | 缺 %s 多 %s" % (sorted(want - got), sorted(got - want)))})
    return out, sites


def main(argv):
    ap = argparse.ArgumentParser(description="chat.py lease wiring acceptance table")
    ap.add_argument("--chat", default=CHAT, help="被测源码路径（默认 tools/chat.py）")
    ap.add_argument("--out", default=os.path.join(HERE, "run_compare.json"),
                    help="产物路径（默认本目录 run_compare.json）")
    a = ap.parse_args(argv)

    src, src_sha16 = read_source(a.chat)
    bare = scan(src)
    static_verdicts, sites = judge_static(bare, src)
    static_ok = all(v["ok"] for v in static_verdicts)

    rows = table()
    m2b, m2a = load("_m2_before.json"), load("_m2_after.json")
    ref = load("run_refusal.json")
    runs = {lb: load("run_%s.json" % lb) for lb in LABELS}
    res = {
        "schema": "chat_lease_compare_v1",
        "chat_py_sha16": {lb: (runs[lb] or {}).get("chat_py_sha16") for lb in LABELS},
        "answers": rows,
        "m2": {"cells_before": (m2b or {}).get("geometry", {}).get("cells_total"),
               "cells_after": (m2a or {}).get("geometry", {}).get("cells_total"),
               "answers_sha256_before": (m2b or {}).get("answers_sha256"),
               "answers_sha256_after": (m2a or {}).get("answers_sha256"),
               "geometry_identical": (m2b or {}).get("geometry") == (m2a or {}).get("geometry"),
               "all_hits": (m2a or {}).get("all_hits")},
        "static": bare,
        "static_expectation": static_verdicts,
        "static_source": {"path": os.path.abspath(a.chat),
                          "sha16": src_sha16,
                          "sha16_note": "对文件原字节算; 三次 run_*.json 记录的 chat_py_sha16 是历史值, 当前源码已前进",
                          "leases_reset_sites": sites},
        "refusal": {"refused": (ref or {}).get("refused"),
                    "cells_unchanged": ((ref or {}).get("after_refusal") or {}).get("cells_unchanged"),
                    "message": (ref or {}).get("message"),
                    "logged_lines": len((ref or {}).get("log_lines") or [])},
    }
    all_identical = all(r["identical"] for cmd in rows.values() for r in cmd)
    m2_rc = [k.get("kvshim_ask_at_return_bytes") for k in (m2a or {}).get("asks", [])]
    non_empty = all(p["chars"] > 0 for lb in LABELS if runs[lb]
                    for cmd in ("chat", "m1", "save")
                    for p in runs[lb].get(cmd, {}).get("pairs", []))
    res["return_codes"] = {"m2_ask_bytes": m2_rc,
                           "m2_ask_all_positive": bool(m2_rc) and all((x or 0) > 0 for x in m2_rc),
                           "product_answers_non_empty": non_empty}

    # ---- 验收项按「被测量对象」分两组。一个 all_pass 覆盖两个对象 = 自述强于实测。----
    recorded = {lb: (runs[lb] or {}).get("chat_py_sha16") for lb in LABELS}
    hist_src = "historical:" + "+".join(sorted({str(v) for v in recorded.values()}))
    cur_src = "current:" + src_sha16
    checks_current = {
        "2_no_bare_reset_and_no_safe_reset_all": static_ok,
    }
    checks_historical = {
        "1_m2_51cell_sha_identical": bool(res["m2"]["answers_sha256_before"]) and
                                     res["m2"]["answers_sha256_before"] == res["m2"]["answers_sha256_after"],
        "1b_product_answers_identical_3_labels": all_identical,
        "3_refusal_recorded": bool(res["refusal"]["refused"]) and res["refusal"]["logged_lines"] >= 1,
        "4_refusal_engine_untouched": bool(res["refusal"]["cells_unchanged"]),
        "5_revert_still_identical": all(r["identical"] for cmd in rows.values() for r in cmd),
        "6_rc_zero_every_run": all((runs[lb] or {}).get(k, {}).get("rc") == 0
                                   for lb in LABELS if runs[lb]
                                   for k in ("chat", "m1", "save")),
        "7_rc_positive_and_answers_non_empty": bool(
            res["return_codes"]["m2_ask_all_positive"] and non_empty),
    }

    def _tagged(checks, judged_source, purpose):
        return {k: {"ok": bool(v), "judged_source": judged_source, "measures": purpose}
                for k, v in checks.items()}

    cur_ok = all(checks_current.values())
    hist_ok = all(checks_historical.values())
    res["acceptance"] = {
        "judged_current_source": {
            "sha16": src_sha16,
            "path": os.path.abspath(a.chat),
            "checks": _tagged(checks_current, cur_src,
                              "对比今天这份 chat.py 的静态结构（它与历史 run 无关）"),
        },
        "judged_historical_runs": {
            "runs": [{"label": lb, "chat_py_sha16": recorded[lb]} for lb in LABELS],
            "checks": _tagged(checks_historical, hist_src,
                              "三次 run_*.json 记录的答案/rc/拒绝证据；判的是当年那几份 chat.py"),
        },
        # 保留 all_pass（别破坏现有调用方）, 但它只是两组各自的 AND, 不表示一组替另一组背书
        "all_pass": bool(cur_ok and hist_ok),
        "all_pass_means": (
            "本布尔仅表示上面两组各自通过。两组判的是不同源码: judged_current_source 判今天这份 "
            "(sha16=%s), judged_historical_runs 判三次 run 记录时的那几份 (%s)。"
            "任一组的通过都不代表另一组, 尤其不表示当前源码也满足历史项 —— 源码前进是正常的。"
            % (src_sha16, " / ".join("%s=%s" % (k, v) for k, v in recorded.items()))),
        "known_defect": (
            "改前本表用单个 all_pass 覆盖两组不同源码, 读者会读成「今天这份也满足全部九项」;"
            " 台账已为此立 finding。现在的分组是修复后的形态, 历史项仍需重跑才能约束当前源码。"),
    }

    # ---- 判完了才写产物; 写不进去只警告, 不改 rc（产物缺失不该伪装成判据红）----
    try:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        _err("WARN: 产物未写出 (%s): %s -- rc 不受影响" % (a.out, exc))

    # ---- 报告（stdout）----
    recorded = {lb: (runs[lb] or {}).get("chat_py_sha16") for lb in LABELS}
    print("chat.py:", os.path.abspath(a.chat), "| sha16", src_sha16)
    print("  三次 run 记录里的 chat_py_sha16: %s（历史值, 与当前源码不同是正常的; 静态计数针对当前源码, 答案一致性针对那次运行）"
          % " / ".join("%s=%s" % (k, v) for k, v in recorded.items()))
    print("静态计数判据（期望 / 实际 / 是否满足）:")
    for v in static_verdicts:
        print("  %-22s 期望 %-3s 实际 %-3s %s  -- %s"
              % (v["criterion"], v["expected"], v["actual"],
                 "OK" if v["ok"] else "MISMATCH", v["why"]))
    print("static:", json.dumps(bare, ensure_ascii=False))
    for cmd, rs in rows.items():
        for r in rs:
            print("  %-5s %-26s %s %s %s  %s" % (cmd, r["q"][:24], r["before"], r["after"],
                                                 r["revert"], "OK" if r["identical"] else "DIFF"))
    print("m2 cells", res["m2"]["cells_before"], "->", res["m2"]["cells_after"],
          "| sha identical", res["m2"]["answers_sha256_before"] == res["m2"]["answers_sha256_after"])
    print("acceptance（按被测量对象分组）:")
    for group in ("judged_current_source", "judged_historical_runs"):
        g = res["acceptance"][group]
        src = g.get("sha16") or " / ".join("%s=%s" % (r["label"], r["chat_py_sha16"]) for r in g["runs"])
        print("  [%s] 判的源码 sha16: %s" % (group, src))
        for k, v in g["checks"].items():
            print("    %-46s %s  (%s)" % (k, "OK" if v["ok"] else "FAIL", v["judged_source"]))
    print("  all_pass:", res["acceptance"]["all_pass"])
    print("  all_pass_means:", res["acceptance"]["all_pass_means"])

    failed = []
    for group in ("judged_current_source", "judged_historical_runs"):
        for k, v in res["acceptance"][group]["checks"].items():
            if not v["ok"]:
                failed.append((group, k))
    if failed:
        _err()
        for group, k in failed:
            _err("  RED: [%s] %s" % (group, k))
        if not static_ok:
            for v in static_verdicts:
                if not v["ok"]:
                    _err("  RED: 静态计数 %s: 期望 %s, 实际 %s -- %s"
                         % (v["criterion"], v["expected"], v["actual"], v["why"]))
    print()
    print("CHAT-LEASE-COMPARE:", "PASS" if not failed else "FAIL (%d criterion(s))" % len(failed))
    return 0 if not failed else 1


def _cli(argv):
    try:
        return main(argv)
    except SystemExit:
        raise                                   # argparse 自带 2
    except UsageError as exc:
        _err("RED: %s" % exc)
        _err("CHAT-LEASE-COMPARE: USAGE-ERROR (rc=2)")
        return 2
    except (UnicodeError, ValueError) as exc:   # 编码崩 / JSON 坏 = 数据错
        _err("  ENV-ERROR (数据或编码错): %s: %s" % (type(exc).__name__, exc))
        _err("CHAT-LEASE-COMPARE: ENV-ERROR (rc=3) -- 这不是判据红")
        return 3
    except OSError as exc:
        _err("  ENV-ERROR (读写错): %s: %s" % (type(exc).__name__, exc))
        _err("CHAT-LEASE-COMPARE: ENV-ERROR (rc=3) -- 这不是判据红")
        return 3
    except Exception as exc:
        _err("  ENV-ERROR (内部错（非判据红）): %s: %s" % (type(exc).__name__, exc))
        _err("CHAT-LEASE-COMPARE: ENV-ERROR (rc=3) -- 这不是判据红")
        return 3


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
