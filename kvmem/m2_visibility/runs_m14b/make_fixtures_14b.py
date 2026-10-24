# -*- coding: utf-8 -*-
"""Generate fixtures_14b.json. Generated, never hand-filled."""
import hashlib, json, os

M = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
D = "D:/llama-mem/kvmem/m2_v1_14b"
DLL = "D:/llama-mem/tools/kvshim_vk.dll"
OUT = "D:/llama-mem/kvmem/m2_visibility/runs_m14b/fixtures_14b.json"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


man = {
    "schema": "fixtures_14b_v1",
    "sentinel": "FIXTURES_14B_V1_SENTINEL_9edbafa1",
    "engine": {
        "model": M,
        "model_size": os.path.getsize(M),
        "n_ctx": 8192,
        "n_seq": 8,
        "gpu": 99,
        "kv": "q8_0",
        "flash_attn": "on",
        "dll": DLL,
        "dll_sha256": sha(DLL),
        "dll_sha256_source": "measured_at_fixtures_creation",
    },
    "blocks": {
        "m2": {
            "home":    {"path": D + "/home.kvmem",    "cells": 21},
            "project": {"path": D + "/project.kvmem", "cells": 18},
            "habit":   {"path": D + "/habit.kvmem",   "cells": 12},
        },
        "variant": {
            "project_paraphrase18": {"path": D + "/project_paraphrase18.kvmem", "cells": 18},
        },
    },
}
# P2 conflict probe: 14B re-encode of the 7B X0 unrelated fact (18 cells incl. BOS).
G18 = D + "/g18_bos_c18_14b.kvmem"
if os.path.exists(G18):
    man["blocks"]["variant"]["g18_bos_c18"] = {"path": G18, "cells": 18}

for fam in man["blocks"].values():
    for name, meta in fam.items():
        meta["sha256"] = sha(meta["path"])
        meta["size"] = os.path.getsize(meta["path"])
        meta["family"] = "14B re-encoded"

json.dump(man, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("wrote", OUT)
print("dll_sha256 =", man["engine"]["dll_sha256"])
print("model_size =", man["engine"]["model_size"])
for fam, d in man["blocks"].items():
    for k, v in d.items():
        print("  %-8s %-22s cells=%-3d size=%-8d sha16=%s" % (fam, k, v["cells"], v["size"], v["sha256"][:16]))
