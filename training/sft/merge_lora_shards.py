#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stream-merge a PEFT LoRA adapter into fp16 safetensors shards using only torch + safetensors."""

import argparse, hashlib, json, math, os, random, shutil, sys, traceback

try:
    import resource
except ImportError:
    resource = None

import torch
from safetensors import safe_open
from safetensors import torch as st

PFX = "base_model.model."
MARK = ".lora_"
SKIP = {"lm_head.weight", "model.embed_tokens.weight"}
IDX = "model.safetensors.index.json"


def log(*a):
    print(*a, flush=True)


def fail(msg):
    log("FAIL", msg)
    sys.exit(3)


def load_adapter(adapter_dir):
    with open(os.path.join(adapter_dir, "adapter_config.json"), "r", encoding="utf-8") as f:
        cfg = json.load(f)
    r, alpha = int(cfg["r"]), float(cfg["lora_alpha"])
    scale = alpha / math.sqrt(r) if cfg.get("use_rslora") else alpha / r
    nonempty = lambda k: cfg.get(k) not in (None, {}, [], "")
    if nonempty("rank_pattern") or nonempty("alpha_pattern") or cfg.get("use_dora") \
            or nonempty("modules_to_save") or cfg.get("bias", "none") != "none":
        fail("adapter config unsupported: rank_pattern/alpha_pattern/use_dora/modules_to_save/bias")
    sd = st.load_file(os.path.join(adapter_dir, "adapter_model.safetensors"))
    pairs, skipped = {}, set()
    for k, v in sd.items():
        if MARK not in k:
            continue
        kind = "A" if ".lora_A." in k else ("B" if ".lora_B." in k else "")
        if not kind:
            continue
        name = k[len(PFX):] if k.startswith(PFX) else k
        pairs.setdefault(name.split(MARK)[0] + ".weight", {})[kind] = v
    for k in sorted(SKIP & set(pairs)):
        skipped.add(k)
        log("IGNORED_SKIP tensor=%s (tie/lm_head not merged)" % k)
    active = {k: v for k, v in pairs.items() if "A" in v and "B" in v and k not in skipped}
    if len(active) != len(pairs) - len(skipped):
        fail("incomplete lora_A/lora_B pairs: %d of %d" % (len(active), len(pairs) - len(skipped)))
    return cfg, scale, r, active, skipped


def check_identity(cfg, base_cfg):
    a = str(cfg.get("base_model_name_or_path") or "").strip().rstrip("/\\")
    b = str(base_cfg.get("_name_or_path") or "").strip().rstrip("/\\")
    for key in ("hidden_size", "num_hidden_layers", "num_attention_heads", "vocab_size"):
        if key in cfg and key in base_cfg and int(cfg[key]) != int(base_cfg[key]):
            fail("adapter/base %s mismatch: %r vs %r" % (key, cfg[key], base_cfg[key]))
    arch = any("Qwen2ForCausalLM" in str(x) for x in (base_cfg.get("architectures") or []))
    if not arch:
        fail("base architectures missing Qwen2ForCausalLM: %r" % (base_cfg.get("architectures"),))
    if a and b and os.path.basename(a).lower() != os.path.basename(b).lower():
        if not ALLOW_NAME_MISMATCH[0]:
            fail("adapter/base basename mismatch adapter=%r base=%r; pass --allow-name-mismatch"
                 % (a, b))
        log("WARN basename mismatch adapter=%r base=%r (allowed by flag)" % (a, b))


def merge_shard(src, dst, pairs, scale, stats):
    sd = st.load_file(src)
    n = len(sd)
    peak = n
    merged = 0
    for name in list(sd.keys()):
        p = pairs.get(name)
        if p is None:
            continue
        A, B = p["A"], p["B"]
        W = sd[name]
        if B.shape[0] != W.shape[0] or A.shape[1] != W.shape[1] or B.shape[1] != A.shape[0]:
            raise RuntimeError("shape mismatch %s W=%s A=%s B=%s"
                               % (name, tuple(W.shape), tuple(A.shape), tuple(B.shape)))
        delta = (B.float() @ A.float()).mul_(scale)
        Wf = W.float().add_(delta)
        sd[name] = Wf.to(W.dtype)
        stats["max_abs_delta"] = max(stats["max_abs_delta"], float(delta.abs().max()))
        peak = max(peak, n + 3)
        merged += 1
        stats["merged_tensor_count"] += 1
        del delta, Wf, W
    st.save_file(sd, dst, metadata={"format": "pt"})
    del sd
    stats["peak"][os.path.basename(dst)] = peak
    log("SHARD %s tensors=%d merged=%d peak_tensors=%d" % (os.path.basename(dst), n, merged, peak))


def verify(args, pairs, scale, tensors, out_dir):
    if args.verify <= 0 or not tensors:
        return True
    by_shard = {}
    for shard, name in tensors:
        by_shard.setdefault(shard, []).append(name)
    picked = [(s, random.choice(ns)) for s, ns in sorted(by_shard.items())]
    rest = [t for t in tensors if t not in picked]
    picked += random.sample(rest, min(max(args.verify - len(picked), 0), len(rest)))
    ps = {}
    for shard, name in picked:
        ps.setdefault(shard, []).append(name)
    vmax = 0.0
    for shard, names in sorted(ps.items()):
        bs = st.load_file(os.path.join(args.base, shard))
        ms = st.load_file(os.path.join(out_dir, shard))
        for name in names:
            p = pairs[name]
            delta = (p["B"].float() @ p["A"].float()).mul_(scale)
            expect, got = bs[name].float() + delta, ms[name].float()
            vmax = max(vmax, float(delta.abs().max()))
            if not torch.allclose(expect, got, atol=1e-3, rtol=1e-2):
                log("VERIFY_FAIL shard=%s tensor=%s max_abs_diff=%.6g"
                    % (shard, name, float((expect - got).abs().max())))
                return False
            log("VERIFY_OK shard=%s tensor=%s" % (shard, name))
            del delta, expect, got
        del bs, ms
    if vmax == 0.0:
        log("WARN sampled merged max_abs_delta == 0.0 (adapter all-zero => training had no effect)")
    return True


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def leave_staging(staging):
    total = 0
    for root, _, files in os.walk(staging):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(root, fn))
            except OSError:
                pass
    log("STAGING_LEFT=%s size=%d bytes (%.2f GB), not removed; inspect then cleanup" %
        (staging, total, total / float(1 << 30)))
    log("CLEANUP_CMD: rm -rf %s" % staging)


ALLOW_NAME_MISMATCH = [False]


def main():
    torch.set_num_threads(min(16, os.cpu_count() or 1))
    ap = argparse.ArgumentParser()
    for k in ("--base", "--adapter", "--merged"):
        ap.add_argument(k, required=True)
    ap.add_argument("--verify", type=int, default=32)
    ap.add_argument("--limit-shards", type=int, default=0)
    ap.add_argument("--allow-name-mismatch", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    ALLOW_NAME_MISMATCH[0] = bool(args.allow_name_mismatch)
    if os.path.exists(args.merged) and not args.force:
        fail("merged dir exists: %s (use --force)" % args.merged)
    cfg, scale, r, pairs, skipped = load_adapter(args.adapter)
    if not pairs:
        fail("no complete lora_A/lora_B pairs in adapter")
    log("ADAPTER r=%d scale=%.6f pairs=%d skipped=%d" % (r, scale, len(pairs), len(skipped)))
    with open(os.path.join(args.base, "config.json"), "r", encoding="utf-8") as f:
        base_cfg = json.load(f)
    check_identity(cfg, base_cfg)
    ip = os.path.join(args.base, IDX)
    has_idx = os.path.isfile(ip)
    if has_idx:
        with open(ip, "r", encoding="utf-8") as f:
            wm = json.load(f)["weight_map"]
    else:
        files = sorted(fn for fn in os.listdir(args.base) if fn.endswith(".safetensors"))
        if not files:
            fail("no %s and no *.safetensors under %s" % (IDX, args.base))
        wm = {}
        for fn in files:
            with safe_open(os.path.join(args.base, fn), framework="pt", device="cpu") as f:
                for k in f.keys():
                    wm[k] = fn
    by_shard = {}
    for name, shard in wm.items():
        by_shard.setdefault(shard, []).append(name)
    unknown = sorted(set(pairs) - set(wm))
    if unknown:
        fail("adapter tensors absent from weight_map: %d e.g. %s" % (len(unknown), unknown[:5]))
    shard_names = sorted(by_shard)[:args.limit_shards or None]
    tensors = [(s, n) for s in shard_names for n in by_shard[s] if n in pairs]
    if not args.limit_shards and len(pairs) != len(tensors):
        fail("pre-write assertion failed: pairs=%d tensors=%d" % (len(pairs), len(tensors)))
    log("ADAPTER_TENSOR_PAIRS=%d SHARDS=%d" % (len(tensors), len(shard_names)))
    staging = args.merged + ".tmp"
    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)
    rb, rm = os.path.realpath(args.base), os.path.realpath(args.merged)
    cp = os.path.commonpath([rb, rm])
    root = os.path.splitdrive(rm)[0] + os.sep
    if not (rb != rm and cp != rb and cp != rm and rm != root):
        fail("refuse: merged/base overlap or root (base=%r merged=%r)" % (rb, rm))
    if os.path.exists(args.merged) and not args.force:
        fail("merged exists, use --force")
    open(os.path.join(staging, ".incomplete"), "w").close()
    stats = {"merged_tensor_count": 0, "max_abs_delta": 0.0, "peak": {}}
    for s in shard_names:
        merge_shard(os.path.join(args.base, s), os.path.join(staging, s), pairs, scale, stats)
    if not args.limit_shards and stats["merged_tensor_count"] != len(tensors):
        leave_staging(staging)
        fail("post-write assertion failed: merged=%d tensors=%d"
             % (stats["merged_tensor_count"], len(tensors)))
    copied = []
    for fn in sorted(os.listdir(args.base)):
        if os.path.isfile(os.path.join(args.base, fn)) and not fn.endswith(".safetensors") \
                and not (args.limit_shards and fn == IDX):
            shutil.copy2(os.path.join(args.base, fn), os.path.join(staging, fn))
            copied.append(fn)
    log("COPIED_FILES=%d %s" % (len(copied), copied))
    log("MERGED_TENSORS=%d ADAPTER_TENSOR_PAIRS=%d MAX_ABS_DELTA=%.6g"
        % (stats["merged_tensor_count"], len(tensors), stats["max_abs_delta"]))
    if tensors and stats["max_abs_delta"] == 0.0:
        log("WARN merged max_abs_delta == 0.0 (adapter all-zero => training had no effect)")
    if not args.limit_shards and not verify(args, pairs, scale, tensors, staging):
        leave_staging(staging)
        sys.exit(1)
    if not args.limit_shards:
        lines = ["%s  %s" % (sha256_file(os.path.join(staging, fn)), fn) for fn in shard_names]
        with open(os.path.join(staging, "SHA256SUMS"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        log("SHA256SUMS_WRITTEN shards=%d" % len(lines))
    os.remove(os.path.join(staging, ".incomplete"))
    if args.force and os.path.exists(args.merged):
        shutil.rmtree(args.merged)
    os.rename(staging, args.merged)
    if resource is not None:
        log("PEAK_RSS_KB=%d" % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if args.limit_shards:
        log("SELFTEST_OK shards=%d merged=%d out=%s (index copy/verify/SHA256 skipped)"
            % (len(shard_names), stats["merged_tensor_count"], args.merged))
    else:
        log("MERGE_OK sha256(%s)=%s" % ("index.json" if has_idx else "SHA256SUMS",
            sha256_file(os.path.join(args.merged, IDX if has_idx else "SHA256SUMS"))))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        traceback.print_exc()
        sys.exit(2)