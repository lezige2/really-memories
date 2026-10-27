#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Real-engine smoke test for tools/memory_isolated.py (GPU window required).

Two near-duplicate memories are built into a throw-away sqlite/blocks dir:
  old: "每周三组会，B 座 302。"
  new: "下周三去上海开会。"
Then the SAME question ("下周三去哪开会") is asked two ways:

  baseline   ordinary dialogue path: seq 0 carries an older Q/A turn in its KV
             history ("每周三组会，B 座 302"), no memory blocks -> the model may
             read the old answer out of the dialogue history (the plate-number
             contamination this prototype targets).
  isolated   tools.memory_isolated.answer_isolated(): both memory blocks + the
             question only, generated on seq 7.  Expect 上海 and no 302/组会.

Pass criterion (isolated only): answer mentions 上海 AND does not mention
"302"/"组会"; seq 0 must be byte-for-byte untouched by the isolated call.

Run (needs GPU; nothing here runs without one):
  python -X utf8 tools/test_memory_isolated_gpu.py
  python -X utf8 tools/test_memory_isolated_gpu.py --n-gpu-layers 34 --n-ctx 16384 \
      --n-predict 64 --keep
"""
import argparse
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

import kvslots  # noqa: E402
import memory_source as ms  # noqa: E402
import memory_isolated as MI  # noqa: E402

OLD_TEXT = "每周三组会，B 座 302。"
NEW_TEXT = "下周三去上海开会。"
QUESTION = "下周三去哪开会"
HISTORY = "\n问：下周三去哪开会\n答：每周三组会，B 座 302。\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=ms.MODEL)
    ap.add_argument("--n-ctx", type=int, default=16384)
    ap.add_argument("--n-gpu-layers", type=int, default=34)
    ap.add_argument("--n-predict", type=int, default=64)
    ap.add_argument("--keep", action="store_true",
                    help="keep the temporary db/blocks dir for inspection")
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="miso_", dir=os.environ.get("TEMP"))
    db = os.path.join(tmp, "miso.db")
    blocks = os.path.join(tmp, "blocks")
    eng = None
    out = {"temp_dir": tmp, "model": os.path.basename(a.model),
           "n_ctx": a.n_ctx, "n_gpu_layers": a.n_gpu_layers,
           "n_predict": a.n_predict}
    try:
        eng = kvslots.KVEngine(a.model, n_ctx=a.n_ctx, n_seq=8,
                               gpu=a.n_gpu_layers, kv="q8_0")
        con = ms.connect(db)
        for name, text in (("miso-old", OLD_TEXT), ("miso-new", NEW_TEXT)):
            ms.put_source(con, name, "", text)
        for name in ("miso-old", "miso-new"):
            src = ms.get_source(con, name)
            ms.build_block(eng, con, src, blocks_dir=blocks,
                           model_path=a.model, seq=6)
        rows = {r[1]: r for r in ms.block_rows(con)}
        old_row, new_row = rows["miso-old"], rows["miso-new"]

        # -- baseline: ordinary path, dialogue history holds the old answer ----
        eng.reset(0)
        eng.write_at(0, HISTORY, 0)
        hist_tokens = int(eng.n_tokens(0))
        base_ans = eng.ask(0, QUESTION, n_predict=a.n_predict, pos=None)
        out["baseline"] = {"history_tokens": hist_tokens, "answer": base_ans}
        eng.reset(0)

        # -- isolated: both blocks + question on seq 7, no dialogue at all ----
        seq0_before = int(eng.n_tokens(0))
        iso_ans, prov = MI.answer_isolated(
            eng, [old_row, new_row], QUESTION, n_predict=a.n_predict,
            scratch=6, model_path=a.model)
        seq0_after = int(eng.n_tokens(0))
        out["isolated"] = {
            "answer": iso_ans,
            "fallback": prov.get("fallback"),
            "error": prov.get("error"),
            "blocks": prov.get("blocks"),
            "question_pos": prov.get("question_pos"),
            "cleaned": prov.get("cleaned"),
        }
        out["seq0_untouched_by_isolated"] = (seq0_before == 0 == seq0_after)
        ans = iso_ans or ""
        out["pass_iso"] = bool(ans) and ("上海" in ans) and \
            ("302" not in ans) and ("组会" not in ans)
        out["baseline_contaminated"] = bool(
            base_ans and ("302" in base_ans or "组会" in base_ans))
        out["verdict"] = "pass" if out["pass_iso"] else "FAIL"
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0 if out["pass_iso"] else 1
    finally:
        if eng is not None:
            try:
                eng.close()
            except Exception:  # noqa: BLE001
                pass
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())