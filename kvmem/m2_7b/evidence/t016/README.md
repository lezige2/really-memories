# T-016 证据（三条 run 原件副本）

副本来自 `kvmem/m2_visibility/runs_mask/`。逐字节校验：**6/6 与原文件相同，bad=0**。

## 命令行（原样）

```
python -X utf8 _mask_run.py --layout iso_dup_p3 --target home --debug --run-json t016_z1_dup_p3.json
（Z2 / Z3 同上，仅换 --run-json 名）
```

布局：`iso_dup_p3 = [(1,home),(2,habit),(3,project),(4,project2)]`，与通过的 `iso_dup4` 同 69 cells，
唯一差别是 slot2/slot3 互换（被重复的 project 到 home 的距离 61 → 119）。

## sha256

| 文件 | sha256 |
|---|---|
| t016_z1_dup_p3.json | 1536b5f8c5d1fcb1768e7c08a5e5cde485cb67b7b85bd17a85fd9ac891434e20 |
| t016_z1_dup_p3.log | 156bd6cda6492bff4ee2abbfc0259f9341cd142455cffcacd2dba2bae5b51077 |
| t016_z2_dup_p3.json | 5b690ad27fdf7c4d30d6244ef360aaeaccedd3f824938d0b105787a0cebb7803 |
| t016_z2_dup_p3.log | 156bd6cda6492bff4ee2abbfc0259f9341cd142455cffcacd2dba2bae5b51077 |
| t016_z3_dup_p3.json | ef4e60c1b2d689d5837644aa3127bcd6294e588fe2538f84a200a8bc1512c17f |
| t016_z3_dup_p3.log | 156bd6cda6492bff4ee2abbfc0259f9341cd142455cffcacd2dba2bae5b51077 |

（三条 log 同 sha：同一布局三次，引擎输出的 trace 行逐字节一致。）

## 结果（预测 FALSE ×3，实测 FALSE ×3）

| run | ask.ok | answer_sha256 | answer（原文） | cell_count |
|---|---|---|---|---|
| Z1 | False | 6ac446329b6afadfd3e19284c10255d0770e9204cb9747175b4ab7473fa716f6 | 我住在\_\_\_\_\_\_。\n\n根据以上对话，填空。\n\n首先，我需要理解对话内容 | 69 |
| Z2 | False | 同上 | 同上 | 69 |
| Z3 | False | 同上 | 同上 | 69 |

`coverage`：home[4075,4096,21] ｜ habit[4020,4032,12] ｜ project[3950,3968,18] ｜ project2[3886,3904,18]
`form=plain`（严格口径）｜ `cloze=Y` ｜ maxUnd=1 ｜ escUS=6 ｜ len=42
trace 四类：SUM=25 SUM2=25 blk=100 OK=4 ｜ 门禁 `GREEN (5 项 AND)` rc=0

## 复算

```bash
cd /d/llama-mem/kvmem/m2_visibility/runs_mask
python -X utf8 _form.py ../../kvmem/m2_visibility/evidence/t016/t016_z1_dup_p3.json
python -X utf8 _gate.py --log t016_z1_dup_p3.log --run-json t016_z1_dup_p3.json
```
