# T-018 证据（iso_topgap 一条 run 原件副本）

副本来自 `kvmem/m2_visibility/runs_mask/`。逐字节校验：**2/2 与原文件相同，bad=0**。

## 命令行（原样）

```
python -X utf8 _mask_run.py --layout iso_topgap --target home --debug --run-json t018_v1_topgap.json
```

布局：`iso_topgap = [(2,home),(3,project),(4,habit),(5,car)]`，四块俱全、home 在场，但**顶端空出 64 格**。

## sha256

| 文件 | sha256 |
|---|---|
| t018_v1_topgap.json | 7d5a0ecb11c82d7992b0864f2b62bfc1018a340c0403bc9bc9e64459d56dc387 |
| t018_v1_topgap.log | 65b8c0ba4579e5a44d711d986611e86a017b02e93f467ab00f1045348e55fb04 |

## 结果

```
ask.ok       = False
ask.answer   = ""            (len 0, 空串)
ask.expected = 广陵路
cell_count   = 70
coverage     = home[4011,4032,21] project[3950,3968,18] habit[3892,3904,12] car[3821,3840,19]
span_lo/hi   = 3821 / 4032   head_gap_cells = 64
form = empty  cloze = n  len = 0
trace 四类   = SUM=0 SUM2=0 blk=0 OK=4      ← 引擎 0 行；OK=4 是驱动自己打的
assert rc=5（trace empty ｜ 期望 25 条 p1 行，实得 0）
gate: DIMS=A:fail B:pass 3a:fail 3b:pass C:pass ｜ OVERALL: RED (5 项 AND) ｜ rc=6
```

## 结论归属

空答案 + 引擎零 trace ⇒ 空洞时记忆没有被铺进 KV：**不是"答错"，是"没有生成可供判读的记忆上下文"**。
按预登记映射：**A（顶部空洞说）成立**。
