# -*- coding: utf-8 -*-
"""T-031 task 3 runner: _driver2's run path, but against an ISOLATED probe DLL.

Why an isolated DLL: another agent holds tools/kvshim_vk.dll open (their probe runs), so the
canonical link target cannot be written.  tools/kvshim_vk_t031.dll is linked from the same
libllama.a with the same flags, so it differs from the canonical DLL only by the [MASKBIAS]
patch that is inert unless LLAMA_KV_MASK_BIAS is set.

The env var is inherited from the shell; this script only records it.
"""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
ISO2 = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2                                            # noqa: E402

P = D2.P
DLL = os.path.join(ROOT, "tools", "kvshim_vk_t031.dll")


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    if not os.path.exists(DLL):
        raise SystemExit("missing probe dll: %s" % DLL)

    # KVEngine signature: (model, n_ctx, n_seq, gpu, kv, dll)
    def patched_open_engine():
        eng = P.K.KVEngine(P.MODEL, n_ctx=P.N_CTX, n_seq=P.N_SEQ, gpu=P.GPU, kv=P.KV, dll=DLL)
        P.bind_raw(eng)
        return eng

    P.open_engine = patched_open_engine
    D2.CTRL_CACHE = os.path.join(HERE, "control_texts.json")

    rc = D2.main()

    out = sys.argv[sys.argv.index("--run-json") + 1]
    if os.path.exists(out):
        d = json.load(open(out, encoding="utf-8"))
        d["engine"]["dll_manifest_sha256"] = d["engine"].get("dll_sha256")
        d["engine"]["dll_sha256"] = sha256(DLL)
        d["engine"]["dll_path"] = DLL
        d["engine"]["dll_mtime"] = os.path.getmtime(DLL)
        d["engine"]["llama_a_mtime"] = os.path.getmtime(
            os.path.join(ROOT, "build-vulkan", "src", "libllama.a"))
        d["maskbias_env"] = os.environ.get("LLAMA_KV_MASK_BIAS")
        # the control gate caches the control text per layout key; a stale cache from another
        # engine would be caught by get_control's own measure() check, so nothing to add.
        with open(out, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
