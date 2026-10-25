# -*- coding: utf-8 -*-
"""E10 / 14B 探针 wrapper。

为什么不直接跑 runs_m14b/_driver14b.py：那个 wrapper 在写完 run json 之后会拼一段 provenance,
里面用了未定义的全局名 ISO2（NameError）—— 上游文件的 bug，我不改它（它是 4-cell 阶段的产物），
在这里导入后补一个等价绑定（ISO2 = ENGINE，指的是同一个 engine/_driver2.py）。
除此之外一切照旧：同一个 manifest、同一个 DLL、同一个布局定义。
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS14 = r"D:/llama-mem/kvmem/m2_visibility/runs_m14b"
sys.path.insert(0, RUNS14)
import _driver14b as W          # noqa: E402

if not hasattr(W, "ISO2"):
    W.ISO2 = W.ENGINE           # 上游 NameError 的等价绑定：wrapper 实际跑的就是 ENGINE 里的 _driver2.py

def _apply_manifest_override():
    """--manifest PATH: 用探针自己的 manifest（含新造的 car 块），不动 runs_m14b 的冻结文件。"""
    argv = sys.argv
    if "--manifest" in argv:
        i = argv.index("--manifest")
        path = argv[i + 1]
        del argv[i:i + 2]
        W.P.MANIFEST = path
        if hasattr(W, "MANIFEST14"):
            W.MANIFEST14 = path
        print("[PROBE] manifest override = %s" % path)


if __name__ == "__main__":
    _apply_manifest_override()
    sys.exit(W.main())
