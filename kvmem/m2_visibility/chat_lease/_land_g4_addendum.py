# -*- coding: utf-8 -*-
"""LANDED-g4 的时态更正 addendum（不回改原台账）：

原 `LANDED-g4.json`（7a9d6cea08141fb4，task-33 时态）写
`judge_unchanged: "E.decide 仍消费原始 sel"`；G4a-2 之后该句已过期，
`E.decide` 入参改为 `sel_mountable`。本 addendum 登记更正与生效 sha。
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
PRODUCT = os.path.join(OUT, "LANDED-g4-addendum.json")
G4 = os.path.join(HERE, "LANDED-g4.json")
G4A2 = os.path.join(HERE, "LANDED-g4a2.json")
CONT = os.path.join(OUT, "G4a2-containment.json")
EXPL = os.path.join(OUT, "S1-default-unchanged-explain-v2-addendum.json")
SP = os.path.join(OUT, "G4a2-variant-want2sel.json")
PRE = os.path.join(OUT, "G4a2-red-variant.json")


def sha16(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def ent(p):
    return {"path": os.path.relpath(p, ROOT).replace("\\", "/"),
            "sha16": sha16(p), "bytes": os.path.getsize(p)}


def main():
    orig = ent(G4)
    prod = {
        "schema": "landed_g4_addendum_v1",
        "supersedes": "7a9d6cea08141fb4",
        "original": dict(orig, untouched=True,
                         note="原台账未改写；本补正只追加更正与生效坐标"),
        "corrections": [{
            "field": "fix.judge_unchanged",
            "original_text": "E.decide 仍消费原始 sel（状态判定不变）",
            "status": "过期（task-33 时态）",
            "corrected_text": "G4a-2 起 E.decide 入参 = sel_mountable（有 memory_block 行、"
                              "真可挂载的 selection 子集）；evidence.py 冻结未改，判据逻辑/文案未改",
            "effective_chat_py_sha16": "1790f3a9b5e6b865",
            "current_chat_py_sha16": sha16(os.path.join(ROOT, "tools", "chat.py")),
            "authority": ent(G4A2),
        }],
        "unchanged_from_original": [
            "G4b（执行面）：m1 exit 0 / attaches 2 / skip 事件可见 / sha_stable 不变",
            "根因数字：memory_source 10 / memory_block 2 / doc 10 / index_meta.docs=2",
            "M4-C 对照：7/8 一致，loads seq 分配为夹具口径差（G4c 已撤回，夹具臂不读 retrieval 顺序）",
        ],
        "pointers": {
            "g4a2_ledger": ent(G4A2),
            "containment": ent(CONT),
            "explain_addendum": ent(EXPL),
            "single_point_variant": dict(ent(SP), variant_kind="single-point(want→sel)",
                                         base_sha16="1790f3a9b5e6b865"),
            "prefix_regression": dict(ent(PRE), variant_kind="prefix-regression",
                                      base_sha16="bb083a1b71165e97"),
        },
        "no_self_sha": True,
    }
    with open(PRODUCT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(prod, fh, ensure_ascii=False, indent=1)
    print("product: %s (%d B, sha16=%s)" % (PRODUCT, os.path.getsize(PRODUCT), sha16(PRODUCT)))
    print("original untouched:", orig["sha16"], "| g4a2:", sha16(G4A2))
    return 0


if __name__ == "__main__":
    sys.exit(main())