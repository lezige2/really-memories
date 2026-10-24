# -*- coding: utf-8 -*-
import hashlib, json, os, sys
sys.path.insert(0, r"D:/llama-mem/tools")
import m2_visibility_probe as P
SCRATCH = 6
OUTDIR = r"D:/llama-mem/kvmem/m2_visibility/blocks"
T_FILLER = "我上周把阳台的花盆都换了大一号的，绿萝长得比原来快了不少。"
T_G18 = "公司食堂新加了一个窗口卖砂锅，中午排队要等十几分钟，味道还说得过去。"
JOBS = [("filler21", T_FILLER, 21), ("G18", T_G18, 21)]
eng = P.open_engine()
report = []
try:
    for name, text, want in JOBS:
        n = P.measure(eng, text) - 1
        rec = {"name": name, "text": text, "n_tokens": n, "wanted": want, "kv_type": P.KV, "how": "exact_text"}
        if n != want:
            rec["status"] = "REJECTED_token_count"
            report.append(rec)
            print(json.dumps(rec, ensure_ascii=False))
            continue
        path = os.path.join(OUTDIR, name + ".kvmem")
        P.reset_all(eng)
        eng.reset(SCRATCH)
        rc = int(eng.write_at(SCRATCH, text, 0, add_bos=False))
        saved = int(eng.save(SCRATCH, path))
        eng.reset(SCRATCH)
        loaded = int(eng.load_strict(SCRATCH, path))
        cells, poss = P.cell_scan(eng, SCRATCH)
        rec["write_at_rc"] = rc
        rec["bytes_saved"] = saved
        rec["loaded_cells"] = loaded
        rec["cells_on_load"] = cells
        rec["pos_range"] = [poss[0], poss[-1]] if poss else None
        rec["file"] = path
        rec["file_sha256"] = P.sha256_file(path)
        rec["size"] = os.path.getsize(path)
        rec["status"] = "OK" if (loaded == want and cells == want and poss and poss[0] == 0) else "MISMATCH"
        report.append(rec)
        print(json.dumps(rec, ensure_ascii=False))
finally:
    eng.close()
json.dump(report, open("C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/engrave_blocks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
