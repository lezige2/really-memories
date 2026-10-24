# -*- coding: utf-8 -*-
"""Assert two smoke runs differ in exactly one env key: LLAMA_KV_MASK_SEQ."""
import argparse, json, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    a = ap.parse_args()
    A = json.load(open(a.a, encoding="utf-8"))
    B = json.load(open(a.b, encoding="utf-8"))
    diffs = []

    def cmp(key, va, vb):
        if va != vb:
            diffs.append((key, va, vb))

    def masked(argv):
        # --run-json is an output path, not a control variable: drop its value
        out, skip = [], False
        for i, tok in enumerate(argv or []):
            if skip:
                out.append("<out>"); skip = False; continue
            if tok == "--run-json":
                out.append(tok); skip = True; continue
            out.append(tok)
        return out

    cmp("argv(without --run-json value)", masked(A.get("cmdline")), masked(B.get("cmdline")))
    cmp("q_sha", A.get("q_sha"), B.get("q_sha"))
    cmp("question", A.get("question"), B.get("question"))
    cmp("layout.windows", (A.get("layout") or {}).get("windows"), (B.get("layout") or {}).get("windows"))
    cmp("layout.segments", (A.get("layout") or {}).get("segments"), (B.get("layout") or {}).get("segments"))
    ea, eb = A.get("mask_env") or {}, B.get("mask_env") or {}
    for k in sorted(set(ea) | set(eb)):
        if k == "LLAMA_KV_MASK_SEQ":
            continue
        cmp("mask_env." + k, ea.get(k), eb.get(k))
    cmp("seq_a_expected_null", ea.get("LLAMA_KV_MASK_SEQ"), None)
    cmp("seq_b_expected_99", eb.get("LLAMA_KV_MASK_SEQ"), "99")
    print("A env SEQ =", ea.get("LLAMA_KV_MASK_SEQ"), " B env SEQ =", eb.get("LLAMA_KV_MASK_SEQ"))
    print("A argv  =", " ".join(masked(A.get("cmdline"))))
    print("B argv  =", " ".join(masked(B.get("cmdline"))))
    if diffs:
        print("PAIR FAILED -- %d unexpected difference(s):" % len(diffs))
        for k, va, vb in diffs:
            print("  key=%s\n    A=%r\n    B=%r" % (k, va, vb))
        return 1
    print("PAIR OK -- only LLAMA_KV_MASK_SEQ differs (A=null, B=99); every other key is byte-identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())