# T-021 证据（spacing 取真值后的两条交叉验证）

> 本目录的 `layout.spacing` **与 coverage 反算一致**（self == 反算），可作为 spacing 的权威值引用。
> 修复前的缺陷现场在 `evidence/t020/`，那里 spacing 一律以 coverage 反算为准。

## PATTERNS

> 判"某说存活/死亡"时，必须把**同表的全部反例**逐条代进该假说，
> 而不是只拿最新一条 run 去撞。（本轮我连续两次把"剩哪一个"读窄：先"只剩内容说"、再"只剩结构说"。）

## 改动（修复本身）

```
kvmem/m2_visibility/runs_iso2/_driver2.py   numstat 1 1
-    return {"key": key, "segments": segs,
+    return {"key": key, "spacing": spec["spacing"], "segments": segs,

kvmem/m2_visibility/runs_mask/_mask_run.py  numstat 3 1
-        res["layout"] = {"key": a.layout, "spacing": 64,
+        res["layout"] = {"key": a.layout, "spacing": layout["spacing"],
```

指纹：`_driver2.py` f5811ff0db2fe41f / 204 行 ｜ `_mask_run.py` b40cd8a5e942d486 / 252 行

## 命令行（原样）

```
python -X utf8 _mask_run.py --layout iso_dup4       --target home --debug --run-json t021_r1_dup4_fixspacing.json
python -X utf8 _mask_run.py --layout iso_dup4_s128  --target home --debug --run-json t021_r2_dup4s128_fixspacing.json
```

## sha256

| 文件 | sha256 |
|---|---|
| t021_r1_dup4_fixspacing.json | 39bbf85d273d27dc449e83140e44964b11ea58d58e1fe64a0187f6c7bd269572 |
| t021_r1_dup4_fixspacing.log | b32cfbbb42de411fe01d3aa41c6efeffb19e3ad0bba96ad732d26e0551061b28 |
| t021_r2_dup4s128_fixspacing.json | 164a902829e18c1a01ccfc72c1296bab99d6f6b80fbc42fb93efbac24272b5ed |
| t021_r2_dup4s128_fixspacing.log | b48b9767a14687963ed1345e8114e9f95ce73e8874bdd67666bd55176dc42ca8 |

## 两处结果

| run | layout.spacing（self） | 反算 | ok | answer_sha256 |
|---|---|---|---|---|
| R1 iso_dup4 | **64** | 4096 − 4032 = 64 ✔ | True | 7ec1430d972d949e5c1d306c6d838c06335bcdd1d1dac8bebde0dbb8a04622fd（= t010_b，逐字相同） |
| R2 iso_dup4_s128 | **128** | 4096 − 3968 = 128 ✔ | True | e6a0807c298d30e0c02b5e976d9072c331aab83de8abe22a667c9a59a7c968f0（= T-020 三条） |

R1 `coverage` = home[4075,4096,21] project[4014,4032,18] habit[3956,3968,12] project2[3886,3904,18]，逐段与 t010_b 相同；
R2 `coverage` = home[4075,4096,21] project[3950,3968,18] habit[3828,3840,12] project2[3694,3712,18]。
两条 `span_lo/hi` 分别为 3886/4096 与 3694/4096，`head_gap_cells` 均为 0；trace 均 SUM=25 SUM2=25 blk=100 OK=4；
`VERDICT=GREEN` / `DIMS=A:pass B:pass 3a:pass 3b:pass C:pass` / rc=0。

## 交叉验证的意义

R2 重跑仍 TRUE 且答案 sha 与 T-020 三条逐字相同 ⇒ **T-020 的结论不依赖那个写错的 spacing 字段**。
