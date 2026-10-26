#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M6a-2 probe I4: `n_rot` power-of-two is not checked by the preflight; a
non-power-of-two still reaches `llama_kv_fwht()`'s GGML_ASSERT and aborts.

NON-PRODUCT STUB.  No model, no kvshim, no GPU.  The probe reproduces:

  preflight (llama-kv-cache.cpp:778):
      if (n_rot_k != 0 && n_rot != n_embd_head_k) return 0;  // partial rotary only
      // no check: (n_rot & (n_rot - 1)) == 0

  llama_kv_fwht (llama-kv-cache.cpp:621-622):
      GGML_ASSERT(n > 0 && (n & (n - 1)) == 0 && "hadamard size must be a power of 2");

  use_hadamard = (n_rot_k != 0) (llama-kv-cache.cpp:822)

The red arm picks n_rot = n_embd_head_k = 192 (not a power of two), with
n_rot_k = 64 (the attn_rot_k path at :346 starts at 64).  The preflight allows
it because it compares n_rot to n_embd_head_k; fwht(192) then aborts.
"""
import json
import sys


def preflight(n_rot, n_embd_head_k, n_rot_k):
    # exact condition from llama-kv-cache.cpp:778
    if n_rot_k != 0 and n_rot != n_embd_head_k:
        return {"allow": False, "reason": "partial rotary (n_rot != n_embd_head_k)"}
    return {"allow": True, "reason": "preflight only rejects partial rotary"}


def fwht_assert(n):
    # exact assertion from llama-kv-cache.cpp:622
    assert n > 0 and (n & (n - 1)) == 0, "GGML_ASSERT hadamard size must be a power of 2"
    return True


def run_case(n_rot, n_embd_head_k, n_rot_k, name):
    pf = preflight(n_rot, n_embd_head_k, n_rot_k)
    abort = None
    if pf["allow"]:
        try:
            fwht_assert(n_rot)
        except AssertionError as exc:
            abort = str(exc)
    return {"case": name, "n_rot": n_rot, "n_embd_head_k": n_embd_head_k,
            "n_rot_k": n_rot_k, "preflight": pf, "fwht_abort": abort is not None,
            "abort_message": abort,
            "power_of_two": n_rot > 0 and (n_rot & (n_rot - 1)) == 0}


def main():
    safe = run_case(128, 128, 128, "current-product-14B")
    red = run_case(192, 192, 64, "variant-non-pow2")
    # the red proof is: variant passes preflight and then aborts in fwht
    assert red["preflight"]["allow"] is True
    assert red["fwht_abort"] is True
    out = {
        "schema": "m6a2_probe_i4_v1",
        "invariant": "I4: preflight checks n_rot == n_embd_head_k but not n_rot being a "
                     "power of two; llama_kv_fwht's GGML_ASSERT then aborts the process",
        "stub": "pure Python transcription; no kvshim/DLL/model/GPU",
        "source_anchor": "llama.cpp/src/llama-kv-cache.cpp:346-352 (n_rot_k starts at 64), "
                         ":778 (preflight), :621-622 (fwht GGML_ASSERT), :822 (use_hadamard)",
        "safe_arm": safe,
        "red_arm": red,
        "red_proof": {
            "observed": {"preflight_allow": red["preflight"]["allow"],
                         "n_rot": red["n_rot"], "power_of_two": red["power_of_two"],
                         "fwht_abort": red["fwht_abort"],
                         "abort_message": red["abort_message"]},
            "expected_safe": {"n_rot": 128, "power_of_two": True, "fwht_abort": False},
            "failure_signature": "preflight allowed n_rot=192; fwht(192) hit "
                                 "GGML_ASSERT(n>0 && (n&(n-1))==0) -> process abort",
        },
        "product_reachability": {
            "verdict": "未接上",
            "reason": "current product model 14B has n_rot=n_embd_head_k=128=2^7; "
                      "no product model with a non-power-of-two head_dim is loaded",
            "future_trigger": "head_dim in {192,320,384,448} with K quantization; "
                              "preflight would still allow, then fwht aborts",
        },
        "artificial_note": "n_rot=192 is a model-geometry variant; it is not produced by any "
                            "current product model and does not count as product-reachable",
        "no_gpu": True,
        "no_model": True,
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())