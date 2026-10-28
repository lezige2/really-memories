#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""环境探针：检查驱动/CUDA/torch/bnb/peft，并跑 5 秒矩阵乘估算算力。"""
import os
import time


def main():
    print("== env ==")
    print("python", os.sys.version.split()[0])
    try:
        import torch
        print("torch", torch.__version__, "cuda_built", torch.version.cuda)
        print("cuda_available", torch.cuda.is_available())
        n = torch.cuda.device_count()
        print("gpu_count", n)
        for i in range(n):
            p = torch.cuda.get_device_properties(i)
            print("gpu%d" % i, p.name, "mem=%.1fGB" % (p.total_memory / 1024 ** 3),
                  "cap=%d.%d" % (p.major, p.minor))
        if n == 0:
            print("FAIL no cuda")
            return 1
        # 5s matmul 估算
        dev = torch.device("cuda:0")
        x = torch.randn(4096, 4096, device=dev, dtype=torch.float16)
        torch.cuda.synchronize()
        t0 = time.time()
        it = 0
        while time.time() - t0 < 5:
            x = x @ x
            it += 1
        torch.cuda.synchronize()
        dt = time.time() - t0
        flops = 2 * 4096 ** 3 * it / dt / 1e12
        print("matmul_TFLOPS_fp16 %.1f (it=%d)" % (flops, it))
    except Exception as exc:                       # noqa: BLE001
        print("TOKEN_FAIL", type(exc).__name__, exc)
        return 2

    print("== libs ==")
    for mod in ("transformers", "peft", "bitsandbytes", "accelerate", "datasets", "trl"):
        try:
            m = __import__(mod)
            print(mod, getattr(m, "__version__", "?"))
        except Exception as exc:                   # noqa: BLE001
            print(mod, "MISSING", type(exc).__name__)
            return 3

    print("== bnb 4bit ==")
    try:
        import torch
        import bitsandbytes as bnb
        lin = bnb.nn.Linear4bit(64, 64, compute_dtype=torch.float16, quant_type="nf4")
        x = torch.randn(2, 64, device="cuda", dtype=torch.float16)
        y = lin.to("cuda")(x)
        print("bnb_linear4bit_ok", tuple(y.shape), "bnb", bnb.__version__)
    except Exception as exc:                       # noqa: BLE001
        print("BNB_FAIL", type(exc).__name__, exc)
        return 4

    print("ALL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())