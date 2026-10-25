# -*- coding: utf-8 -*-
"""P1 pinned 驱逐零 GPU 测试床（预登记 §2.3）。

被测：`evict_policy.select_to_evict(..., pinned=())` 与 `pinned_from_leases(leases, n_seq)`。

纪律：
- 纯函数 + stub，不 import 引擎、不看 `chat.py`、不读块文件、零 GPU；
- 每条 case 只断言一件事；`expect`/`got` 都落盘；期望值**不随实现改**；
- 现盘（L2 后、P1 前）传 `pinned=` 必然 `TypeError` —— 用显式 `expect_raise` 记
  `{raised, type, msg}`，**不用 `try/except` 吞**（捕到只为记录，是否通过由断言判）；
- 红线构造（variant）由本床的 `--policy` 指到临时副本上跑，产物与落地版**成对**。
- 默认输出落系统临时目录；写仓库 `out/` 必须显式 `--out`（L1/L2 工具纪律）。

跑法：
    python -X utf8 _test_evict_pinned.py [--policy /path/to/evict_policy.py] [--out 路径]
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
JUDGE = {"path": "docs/_work/M2-FULL-PREREG-draft.md", "section": "§2.3 P1",
         "sha16": "4978c94474ba050c"}
N_CTX = 8192


def load_policy(path):
    spec = importlib.util.spec_from_file_location("evict_policy_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class StubLeases:
    """只实现 `leased(seq)` 的 duck-typed 租约表（0 GPU；不 import 引擎）。"""

    def __init__(self, leased_seqs):
        self._leased = set(int(s) for s in leased_seqs)
        self.calls = []

    def leased(self, seq):
        self.calls.append(int(seq))
        return int(seq) in self._leased


class NotALeaseTable:
    """没有 `.leased()` 的对象：helper 必须显式拒绝，而不是静默返回空集冒充「未接上」。"""


def call(fn, **kw):
    """显式记录「抛了什么」；不吞异常语义（是否违反期望由 checks 判）。"""
    try:
        return {"raised": False, "raised_type": None, "raised_msg": "",
                "value": fn(**kw)}
    except (TypeError, AttributeError) as exc:
        return {"raised": True, "raised_type": type(exc).__name__, "raised_msg": str(exc),
                "value": None}


def row_of(case, what, got, expect):
    checks = {}
    for k, want in expect.items():
        got_v = got.get(k)
        if isinstance(want, list) and isinstance(got_v, list):
            checks["%s_ok" % k] = got_v == want
        else:
            checks["%s_ok" % k] = got_v == want
    return {"case": case, "what": what, "got": got, "expect": expect,
            "checks": checks, "ok": all(checks.values())}


# ---------------------------------------------------------------- cases
def case_h1_pin_source(EV):
    """helper 从 duck-typed 租约表取 pin：{s in 1..n_seq-1 | leases.leased(s)}。"""
    leases = StubLeases({2, 5})
    if not hasattr(EV, "pinned_from_leases"):
        got = {"raised": True, "raised_type": "AttributeError", "raised_msg":
               "pinned_from_leases 不存在（现盘 L2 后、P1 前无此 helper）", "value": None,
               "probed_seqs": []}
    else:
        got = call(EV.pinned_from_leases, leases=leases, n_seq=8)
        got["probed_seqs"] = sorted(set(leases.calls))
        if isinstance(got.get("value"), set):          # 落盘要可 JSON 化（读数不变）
            got["value"] = sorted(int(x) for x in got["value"])
    return row_of("H1_pin_source", "pin 来源 = {s in range(1,n_seq) | leased(s)}",
                  got, {"raised": False, "value": [2, 5], "probed_seqs": [1, 2, 3, 4, 5, 6, 7]})


def case_h2_contract(EV):
    """契约：只接受有 `.leased()` 的对象；别的对象必须显式 TypeError（不许静默空集）。"""
    if not hasattr(EV, "pinned_from_leases"):
        got = {"raised": False, "raised_type": None,
               "raised_msg": "pinned_from_leases 不存在（AttributeError 在 helper 层）",
               "value": None}
    else:
        got = call(EV.pinned_from_leases, leases=NotALeaseTable(), n_seq=8)
    return row_of("H2_helper_rejects_non_lease", "只接受 duck-typed `.leased()` 对象",
                  got, {"raised": True, "raised_type": "TypeError"})


MIXED = [{"seq": 1, "cells": 1500, "key": 1, "last_used": 10},
         {"seq": 3, "cells": 1500, "key": 2, "last_used": 10},
         {"seq": 4, "cells": 1500, "key": 3, "last_used": 10},
         {"seq": 2, "cells": 1200, "key": 11, "last_used": 0},
         {"seq": 5, "cells": 1200, "key": 12, "last_used": 0},
         {"seq": 7, "cells": 1200, "key": 13, "last_used": 0}]
MIXED_PIN = (2, 5, 7)


def case_m1_mixed(EV):
    """混合集（3 pinned + 3 普通、超预算）：踢非 pinned 就能装下；pinned 一个都不许少。"""
    got = call(EV.select_to_evict, blocks=MIXED, chat_len=100, n_ctx=N_CTX,
               policy="lru", pinned=MIXED_PIN)
    if not got["raised"]:
        sel = got["value"]
        got.update({"evicted": sel.get("evicted"), "kept_seqs": [b["seq"] for b in sel.get("kept", [])],
                    "policy": sel.get("policy"),
                    "over_budget_before": sel.get("over_budget_before"),
                    "over_budget_after": sel.get("over_budget_after"),
                    "refused_reason": sel.get("refused_reason"),
                    "mount_cap_used": sel.get("mount_cap_used"),
                    "evicted_meets_pinned": sorted(set(sel.get("evicted") or []) & set(MIXED_PIN))})
        got.pop("value", None)
    return row_of("M1_mixed_3p3n", "3 pinned + 3 普通、超预算 ⇒ evicted 非空且与 pinned 无交",
                  got, {"raised": False, "evicted": [4], "policy": "lru",
                        "over_budget_before": True, "over_budget_after": False,
                        "refused_reason": None, "evicted_meets_pinned": [],
                        "kept_seqs": [1, 3, 2, 5, 7]})


ALL_PIN = [{"seq": 2, "cells": 3000, "key": 11, "last_used": 10},
           {"seq": 5, "cells": 3000, "key": 12, "last_used": 9},
           {"seq": 7, "cells": 3000, "key": 13, "last_used": 8}]
ALL_PIN_SET = (2, 5, 7)


def case_a1_all_pinned(EV):
    """全 pinned + 超预算：evicted==[]、over_after True、refused_reason=all_pinned ⇒ 调用方拒绝。"""
    got = call(EV.select_to_evict, blocks=ALL_PIN, chat_len=100, n_ctx=N_CTX,
               policy="lru", pinned=ALL_PIN_SET)
    if not got["raised"]:
        sel = got["value"]
        got.update({"evicted": sel.get("evicted"), "kept_seqs": [b["seq"] for b in sel.get("kept", [])],
                    "over_budget_before": sel.get("over_budget_before"),
                    "over_budget_after": sel.get("over_budget_after"),
                    "refused_reason": sel.get("refused_reason"),
                    "caller_action": "PlanRefused" if sel.get("over_budget_after") else "proceed"})
        got.pop("value", None)
    return row_of("A1_all_pinned", "全 pinned 超预算必须响（refused_reason=all_pinned）",
                  got, {"raised": False, "evicted": [], "kept_seqs": [2, 5, 7],
                        "over_budget_before": True, "over_budget_after": True,
                        "refused_reason": "all_pinned", "caller_action": "PlanRefused"})


OFF_BLOCKS = [{"seq": 1, "cells": 1000, "key": 1}, {"seq": 2, "cells": 1000, "key": 2},
              {"seq": 3, "cells": 1000, "key": 3}, {"seq": 4, "cells": 1000, "key": 4}]
OLD_KEYS = ["policy", "kept", "evicted", "over_budget_before", "over_budget_after",
            "mount_cap_used", "note"]


def case_o1_off_default(EV):
    """`policy="off"` 且不传 pinned ⇒ 输出与现盘逐字段相同（含键集不许变）。"""
    got = call(EV.select_to_evict, blocks=OFF_BLOCKS, chat_len=5000, n_ctx=N_CTX)
    if not got["raised"]:
        sel = got["value"]
        got.update({"policy": sel.get("policy"), "evicted": sel.get("evicted"),
                    "kept_seqs": [int(b["seq"]) for b in sel.get("kept", [])],
                    "over_budget_before": sel.get("over_budget_before"),
                    "over_budget_after": sel.get("over_budget_after"),
                    "mount_cap_used": sel.get("mount_cap_used"),
                    "keys": sorted(sel.keys()), "note": sel.get("note")})
        got.pop("value", None)
    return row_of("O1_off_default", "policy=off 且不传 pinned ⇒ 旧输出逐字段不变（键集不许多）",
                  got, {"raised": False, "policy": "off", "evicted": [],
                        "kept_seqs": [1, 2, 3, 4], "over_budget_before": True,
                        "over_budget_after": True, "mount_cap_used": None,
                        "keys": sorted(OLD_KEYS),
                        "note": "evicted 里的块只做 seq_rm（摘引用），磁盘文件不动；"
                                "over_budget_before/after 两读数都必须报，不许只报一个。"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=os.path.join(HERE, "evict_policy.py"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    pol_path = os.path.abspath(args.policy)
    with open(pol_path, "rb") as f:
        pol_sha = hashlib.sha256(f.read()).hexdigest()[:16]
    EV = load_policy(pol_path)

    t0 = time.time()
    rows = [case_h1_pin_source(EV), case_h2_contract(EV), case_m1_mixed(EV),
            case_a1_all_pinned(EV), case_o1_off_default(EV)]
    fail = [r["case"] for r in rows if not r["ok"]]

    def seqs(blocks):
        return [int(b["seq"]) for b in blocks]
    denom = {
        "blocks": len(MIXED) + len(ALL_PIN) + len(OFF_BLOCKS),
        "pinned": len(MIXED_PIN) + len(ALL_PIN_SET),
        "evicted": sum(len(r["got"].get("evicted") or []) for r in rows),
        "note": "三级分母三个数都报：总块数 / pinned 数 / 被踢数（缺一即读数无效）",
    }
    res = {
        "schema": "m3_p1_evict_pinned_v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "judge_source": JUDGE,
        "policy_module": {"path": pol_path, "sha16": pol_sha},
        "stub": "本文件内 StubLeases / NotALeaseTable（只实现 leased()；零 GPU、不 import 引擎）",
        "cases": [{"case": r["case"], "what": r["what"], "got": r["got"],
                   "expect": r["expect"], "checks": r["checks"], "ok": r["ok"]}
                  for r in rows],
        "three_level_denominator": denom,
        "fail_cases": fail,
        "exit": 0 if not fail else 2,
        "elapsed_s": round(time.time() - t0, 3),
    }
    out = args.out or os.path.join(tempfile.gettempdir(), "m3_p1_products",
                                   "P1-%s.json" % time.strftime("%H%M%S"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    for r in rows:
        g = r["got"]
        print("  %-26s raised=%-5s %s"
              % (r["case"], g.get("raised"),
                 json.dumps({k: g[k] for k in ("evicted", "over_budget_after",
                                               "refused_reason", "value")
                             if k in g}, ensure_ascii=False)))
    print("\n三级分母: 总块数 %d / pinned %d / 被踢 %d"
          % (denom["blocks"], denom["pinned"], denom["evicted"]))
    print("policy sha16=%s | fail=%s | exit=%d -> %s"
          % (pol_sha, fail, res["exit"], out))
    return res["exit"]


if __name__ == "__main__":
    sys.exit(main())