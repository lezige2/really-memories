# -*- coding: utf-8 -*-
"""`explain_version: 2` 补正产物（不回改原产物）：

原产物 `kvmem/m2_visibility/m2_planner/out/S1-default-unchanged.json`（12cebec6e516fd3b）
与 `S1-real-default-regression.json`（39aa2505d74724a4）里的 `m1_explain` 坐标
（3e8aae60685d2e55 / 654 B）是 **explain_version 1**；G4a-3 后该坐标作废，
以本补正登记新坐标与可逆性/containment 证据。
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
PRODUCT = os.path.join(OUT, "S1-default-unchanged-explain-v2-addendum.json")
CONT = os.path.join(OUT, "G4a2-containment.json")


def sha16(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def main():
    orig = os.path.join(ROOT, "kvmem", "m2_visibility", "m2_planner", "out",
                        "S1-default-unchanged.json")
    reg = os.path.join(ROOT, "kvmem", "m2_visibility", "m2_planner", "out",
                       "S1-real-default-regression.json")
    cont = json.load(open(CONT, encoding="utf-8"))
    e = cont["explain_v2"]
    prod = {
        "schema": "s1_default_unchanged_explain_v2_addendum_v1",
        "supersedes_coordinate": {
            "original_products": [
                {"path": "kvmem/m2_visibility/m2_planner/out/S1-default-unchanged.json",
                 "sha16": sha16(orig),
                 "m1_explain": {"stdout_sha16": "3e8aae60685d2e55", "stdout_bytes": 654,
                                "explain_version": 1, "status": "v1 已作废"}},
                {"path": "kvmem/m2_visibility/m2_planner/out/S1-real-default-regression.json",
                 "sha16": sha16(reg),
                 "m1_explain": {"stdout_sha16": "3e8aae60685d2e55", "stdout_bytes": 872,
                                "explain_version": 1, "status": "v1 已作废"}},
            ],
            "original_readings_intact": True,
            "meaning": "原产物未被改写（sha16 如上）；其 m1_explain 坐标只对 explain_version 1 有效",
        },
        "current": {
            "chat_py_sha16": cont["chat_py"]["after_sha16"],
            "explain_version": 2,
            "bytes": e["bytes"], "sha16": e["sha16"],
            "version_line": e["version_line"],
            "annotation": "检索行尾部 [可挂载]/[无块行→不可挂载] + 每问一行「可挂载集：…」",
            "reversible": e["reversible"],
            "containment_product": {"path": "kvmem/m2_visibility/chat_lease/out/G4a2-containment.json",
                                    "sha16": sha16(CONT)},
            "containment_evidence": {
                "cmd_chat_zero_diff": cont["cmd_chat_zero_diff"]["identical"],
                "m1_nonexplain_same_except_control_q": cont["m1_nonexplain"]["same"]["all"],
                "two_dryrun_checks_equal": cont["two_dryrun"].get("checks_equal"),
            },
        },
        "how_to_verify": "python tools/chat.py m1 --explain（temp DB）→ 取 stdout：sha16=%s；"
                         "去掉首行 explain_version: 2、行尾标注与可挂载集行后 sha16 必为 %s"
                         % (e["sha16"], e["reversible"]["old_anchor_sha16"]),
        "note": "explain 从回归硬锚改为『可逆性断言 + containment 三条』；v1 坐标不再作为回归锚。",
    }
    with open(PRODUCT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(prod, fh, ensure_ascii=False, indent=1)
    print("product: %s (%d B, sha16=%s)" % (PRODUCT, os.path.getsize(PRODUCT), sha16(PRODUCT)))
    print("original intact:", sha16(orig), "| current:", e["sha16"], e["bytes"])
    return 0


if __name__ == "__main__":
    sys.exit(main())