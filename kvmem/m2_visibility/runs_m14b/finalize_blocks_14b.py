# -*- coding: utf-8 -*-
import hashlib, json, os
D = r"D:/llama-mem/kvmem/m2_visibility/runs_m14b"
p1 = json.load(open(os.path.join(D, "blocks_14b_pass1.json"), encoding="utf-8"))
p2 = json.load(open(os.path.join(D, "blocks_14b_pass2.json"), encoding="utf-8"))

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

m1 = {b["name"]: b for b in p1["blocks"]}
m2 = {b["name"]: b for b in p2["blocks"]}
out = {"schema": "blocks_14b_final_v1",
       "model": p1["model"], "model_size": p1["model_size"],
       "loaded_path": p1["loaded_path"], "dll": p1["dll"],
       "dll_sha256_measured": p1["dll_sha256"],
       "dll_mtime": __import__("time").strftime(
           "%Y-%m-%d %H:%M:%S", __import__("time").localtime(os.path.getmtime(p1["dll"]))),
       "bytes_per_token": p1["bytes_per_token"],
       "assert_constants": p1["assert_constants"],
       "pp18_text_sha256_guard": p1["guard"],
       "determinism": {}, "blocks": []}

for name in ("home", "project", "habit", "project_paraphrase18"):
    a, b = m1[name], m2[name]
    final = os.path.join(r"D:/llama-mem/kvmem/m2_v1_14b", name + ".kvmem")
    disk_sha = sha(final)
    rec = {
        "name": name,
        "path": final,
        "text": a["text"],
        "text_sha256": a["text_sha256"],
        "cells": a["cells"],
        "content_tokens": a["content_tokens"],
        "first_token": a["first_token"],
        "has_bos": a["has_bos"],
        "size": os.path.getsize(final),
        "sha256": disk_sha,
        "sha256_pass1": a["sha256"],
        "sha256_pass2": b["sha256"],
        "two_encodings_identical": a["sha256"] == b["sha256"] == disk_sha,
        "bytes_per_token_snapshot": p1["bytes_per_token"],
        "header_readback": a["parsed"],
        "checks": a["checks"],
        "token_ids": a["token_ids"],
    }
    out["blocks"].append(rec)
    out["determinism"][name] = rec["two_encodings_identical"]

json.dump(out, open(os.path.join(D, "blocks_14b.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)

print("| block | cells | content | first | BOS | size | 1188+104464n | sha256 |")
print("|---|---|---|---|---|---|---|---|")
for r in out["blocks"]:
    exp = 1188 + 104464 * r["cells"]
    print("| %s | %d | %d | %d | %s | %d | %d %s | %s |"
          % (r["name"], r["cells"], r["content_tokens"], r["first_token"], r["has_bos"],
             r["size"], exp, "OK" if r["size"] == exp else "MISMATCH", r["sha256"]))
print()
print("header readback (all four):")
for r in out["blocks"]:
    h = r["header_readback"]
    print("  %-22s nl=%d n_rot_k=%d n_rot_v=%d k=%d/%d v=%d/%d v_trans=%d eof=%s"
          % (r["name"], h["n_layer"], h["n_rot_k"], h["n_rot_v"], h["k_type"], h["k_row"],
             h["v_type"], h["v_row"], h["v_trans"], h["consumed_to_eof"]))
print()
print("determinism (pass1 == pass2 == file on disk):", out["determinism"])
print("loaded_path:", out["loaded_path"])
print("dll sha256:", out["dll_sha256_measured"], "mtime", out["dll_mtime"])
print("bytes_per_token (KV pool stride, NOT per-cell bytes):", out["bytes_per_token"])
print("pp18 text guard:", out["pp18_text_sha256_guard"])
