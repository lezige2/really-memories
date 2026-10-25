# -*- coding: utf-8 -*-
"""E10 探针：用 14B 编码 car 块（19 cells）。

文本不手抄，运行时从 runs_m14b/control_texts_14b.json 读那句车牌原文
（lead 要求：与 7B 的 car 块同文本、不改措辞）。
编码路径、常量、校验全部复用 runs_m14b/make_blocks_14b.py，不改那个文件。
"""
import argparse, hashlib, json, os, sys

RUNS14 = r"D:/llama-mem/kvmem/m2_visibility/runs_m14b"
sys.path.insert(0, RUNS14)
from make_blocks_14b import P, parse14, BOS, HDR14, CELL14   # noqa: E402

# car 的原文不在 fixtures.json 里（那里只有 path/cells/sha256），权威来源是
# tools/m2_visibility_probe.py 的 FULL["car"]["text"]（代码 > 产物 > 文档）。
# 用 ast 取字面量，不 import 那个脚本（避免触发它的副作用）。
import ast

def _full_table():
    src = open(r"D:/llama-mem/tools/m2_visibility_probe.py", encoding="utf-8").read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "FULL" for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit("STOP: m2_visibility_probe.py 里找不到 FULL")

CAR_TEXT = _full_table()["car"]["text"]
WANT = 19


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    text = CAR_TEXT
    print("[car] text = %r  (len=%d)" % (text, len(text)))
    if len(text) > 40 or "日常记录" in text:
        raise SystemExit("STOP: 取到的不是车牌那一条，而是更长的文本")
    if os.path.exists(a.out):
        raise SystemExit("refusing to overwrite %s" % a.out)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    eng = P.open_engine()
    try:
        n = P.measure(eng, text)
        print("[car] measure(add_bos=True) = %d cells, want %d" % (n, WANT))
        if n != WANT:
            raise SystemExit("STOP: 14B 把车牌文本切成 %d cells（7B 是 19）-> 先报告，不落盘" % n)
        eng.reset(2)
        w = eng.write_at(2, text, 0, add_bos=True)
        if w != WANT:
            raise SystemExit("STOP: wrote %d of %d" % (w, WANT))
        if eng.save(2, a.out) <= 0:
            raise SystemExit("STOP: save failed")
        eng.reset(2)
        h = parse14(a.out)
        checks = {"cells_19": h["n_tokens"] == WANT,
                  "size_1188_plus_104464n": h["size"] == HDR14 + CELL14 * WANT,
                  "first_token_bos": h["first_token"] == BOS,
                  "n_layer_48": h["n_layer"] == 48,
                  "k_type_q8_0": h["k_type"] == 8, "v_type_q8_0": h["v_type"] == 8,
                  "k_row_1088": h["k_row"] == 1088, "v_row_1088": h["v_row"] == 1088,
                  "to_eof": h["consumed_to_eof"]}
        if not all(checks.values()):
            raise SystemExit("STOP: %s" % [k for k, v in checks.items() if not v])
        print(json.dumps({"path": os.path.abspath(a.out), "text": text,
                          "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                          "cells": h["n_tokens"], "size": h["size"], "sha256": h["sha256"],
                          "sha16": h["sha256"][:16], "checks": checks},
                         ensure_ascii=False, indent=1))
    finally:
        eng.close()


if __name__ == "__main__":
    sys.exit(main())
