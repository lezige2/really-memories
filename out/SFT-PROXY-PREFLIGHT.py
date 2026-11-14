# -*- coding: utf-8 -*-
"""TASK-034 跑前预检：确认 8767 llama-server /health 与 /props，并输出 adapter sha16（供 --expect-lora-sha）。
不启动/停止任何服务。用法：
  python -X utf8 out/SFT-PROXY-PREFLIGHT.py --arm base --port 8767
  python -X utf8 out/SFT-PROXY-PREFLIGHT.py --arm sft  --port 8767 --lora D:/models/qwen-sft-lora.gguf
退出码：0=通过；3=指纹不符/不可区分/连接失败。
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request


def get(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser(description="preflight for llama-server proxy arms")
    ap.add_argument("--arm", choices=["base", "sft"], required=True)
    ap.add_argument("--port", type=int, default=8767)
    ap.add_argument("--lora", default="")
    ap.add_argument("--expect-lora-sha", default="")
    args = ap.parse_args()
    base = "http://127.0.0.1:%d" % args.port
    try:
        health = get(base + "/health")
        props = get(base + "/props")
        adapters = get(base + "/lora-adapters")
    except Exception as exc:  # noqa: BLE001
        print("ERROR: %s 不可达：%s" % (base, exc), file=sys.stderr)
        return 3
    ptext = json.dumps(props, ensure_ascii=False)
    # v3 判定：以 /lora-adapters 为唯一证据（非空 list + path basename 命中 --lora + scale>0）；不读 /props.lora
    def _evidence(ad, lora_path):
        if not isinstance(ad, list) or not ad: return False
        b = os.path.basename(lora_path) if lora_path else ""
        return any(isinstance(a, dict) and float(a.get("scale") or 0) > 0
                   and (not b or b in os.path.basename(str(a.get("path") or ""))) for a in ad)
    lora_seen = _evidence(adapters, args.lora)
    adapter_sha = ""
    if args.lora and os.path.isfile(args.lora):
        adapter_sha = hashlib.sha256(open(args.lora, "rb").read()).hexdigest()
    summary = {"port": args.port, "arm": args.arm, "health": health, "props": props, "lora_adapters": adapters,
               "lora_seen_in_adapters": bool(lora_seen), "adapter_sha256": adapter_sha,
               "adapter_sha16": adapter_sha[:16], "now_hint": "2026-10-28 21:00"}
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "out", "PROXY-PREFLIGHT-%s.json" % args.arm)
    json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: summary[k] for k in ("port", "arm", "lora_seen_in_adapters", "adapter_sha16")},
                     ensure_ascii=False))
    print("health.status=", health.get("status"), "| adapters=", len(adapters or []), "| out=", os.path.relpath(out))
    if args.arm == "base" and lora_seen:
        print("ERROR: base 臂 /lora-adapters 仍有 scale>0 的 adapter（疑似起错 server）", file=sys.stderr)
        return 3
    if args.arm == "sft":
        if not adapter_sha:
            print("ERROR: sft 预检需要 --lora 存在且可读", file=sys.stderr)
            return 3
        if args.expect_lora_sha and not adapter_sha.startswith(args.expect_lora_sha):
            print("ERROR: adapter sha 与 --expect-lora-sha 不符", file=sys.stderr)
            return 3
        if not lora_seen:
            print("ERROR: /lora-adapters 未证明该 --lora 已加载（path basename/scale>0）", file=sys.stderr)
            return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())