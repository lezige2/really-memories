# T-020 证据（缺陷样本：产物自述 spacing=64，实际几何 128）

> **引用本目录时，`layout.spacing` 一律作废，以 `coverage` 反算为准：`4096 − 3968 = 128`。**
> 这三份是"产物写错自己几何"这个缺陷的**现场**，修复前原样保留，不得据此目录判断 spacing。

## 它为什么被刻意保留

修复前 `_mask_run.py` 把 spacing 写成硬编码字面量：
`res["layout"] = {"key": a.layout, "spacing": 64, ...}`。
此前所有布局 spacing 恰好都是 64，错得"恰好正确"，直到 `iso_dup4_s128` 才暴露。
**一个在自己身上写错数的产物，比没有这个字段更坏**——它会把别人引到错的地方。
故：不修产物、不删目录，留作缺陷样本；修复见 `evidence/t021/`。

## 命令行（原样，三条相同，仅换 --run-json）

```
python -X utf8 _mask_run.py --layout iso_dup4_s128 --target home --debug --run-json t020_s1_dup4s128.json
```

布局：`iso_dup4_s128 = [(1,home),(2,project),(3,habit),(4,project2)]`，`spacing = 128`，与通过的 `iso_dup4` 只差 spacing。

## sha256

| 文件 | sha256 |
|---|---|
| t020_s1_dup4s128.json | 1e24da6d8129cffa28e7a5b335e7091311ad8b5714517708f5e369f166f74afc |
| t020_s1_dup4s128.log | b48b9767a14687963ed1345e8114e9f95ce73e8874bdd67666bd55176dc42ca8 |
| t020_s2_dup4s128.json | ef3559e3b46ac4427b43da843b55a9d22d97445b91dbe40fe1a50fd6633ea2ee |
| t020_s2_dup4s128.log | b48b9767a14687963ed1345e8114e9f95ce73e8874bdd67666bd55176dc42ca8 |
| t020_s3_dup4s128.json | 6c56482551186a96611794bec672cc006c967c8145843e51fcb9c27efe642f51 |
| t020_s3_dup4s128.log | b48b9767a14687963ed1345e8114e9f95ce73e8874bdd67666bd55176dc42ca8 |

（三份 log 同 sha：同一布局三次，引擎 trace 逐字节一致。）

## 结果（三次全 TRUE，同 sha）

```
ask.ok        = True  x3
answer        = "你住在广陵路12号2单元602。\n\n解析：根据给出的地址信息，可以确定"（len=35）
answer_sha256 = e6a0807c298d30e0c02b5e976d9072c331aab83de8abe22a667c9a59a7c968f0（三条相同）
cell_count    = 69
coverage      = home[4075,4096,21] project[3950,3968,18] habit[3828,3840,12] project2[3694,3712,18]
span_lo/hi    = 3694 / 4096 ｜ head_gap_cells = 0
layout.spacing= 64   ← **错误字段，见文首**
form=plain ｜ cloze=n ｜ trace SUM=25 SUM2=25 blk=100 OK=4 ｜ VERDICT=GREEN DIMS=A:pass B:pass 3a:pass 3b:pass C:pass rc=0
```

几何反算（这就是本目录唯一可信的 spacing 来源）：

```
home.pos_hi = 4096 ｜ project.pos_hi = 3968  ⇒ 4096 - 3968 = 128，(slot2-1)=1 ⇒ spacing = 128
验算 habit：4096 - 2*128 - 12 = 3828 = coverage.habit.lo ✔
验算 project2：4096 - 3*128 - 18 = 3694 = coverage.project2.lo ✔
```

## 结论归属

三次全 TRUE ⇒ 预登记判读："几何阈值说（副本源必须距 home ≤64）判死"。
（后续裁定补正：纯距离/纯内容/纯结构三条单变量说**全部判死**；现存唯一形式是合取式，**那是拟合，不是机制**。）
