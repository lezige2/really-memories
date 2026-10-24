# T-017 证据（iso_dup_p2 三条 run 原件副本）

副本来自 `kvmem/m2_visibility/runs_mask/`。逐字节校验：**6/6 与原文件相同，bad=0**。

> PATTERNS：**"调用发出去了" ≠ "文件已改"——跑批前先 `import` 一次确认键可见。**
> 由来：本轮给 `_driver2.py` 加 `iso_dup_p2` 的那次编辑整段没执行（同轮 `run_code` 引号解析失败），
> 而我当成已改就去跑批，四条 run 全以 `invalid choice: iso_dup_p2` 退出、一个 json 都没产出；
> 是 `usage: _mask_run.py …` 这几行日志把原因摆出来的。

## 命令行（原样）

```
python -X utf8 _mask_run.py --layout iso_dup_p2 --target home --debug --run-json t017_w1_dup_p2.json
（W2 / W3 同上，仅换 --run-json 名）
```

布局：`iso_dup_p2 = [(1,home),(2,habit),(3,project),(4,habit2)]`，63 cells。
设计意图（队长）：让 **habit 的副本落在 slot2（距 home 64，与通过的 iso_dup4 同距离）**，以拆开"距离说"与"内容类别说"。
实测意义（检测员裁定）：本夹具 spacing 恒 64 ⇒ 相邻 ⟺ 差 1 槽 ⟺ 距离 64，两条命题在此**同一**；因此它没能"分开"，
但**干净地判红了纯距离说**。

## sha256

| 文件 | sha256 |
|---|---|
| t017_w1_dup_p2.json | b39a0f00aa2ec681ac65b018acccd4caa235932c242874f133ae9950abd0aa3d |
| t017_w1_dup_p2.log | f8372383183599f9f5d3749a82a61bd3cc57eed4c3fad5c693802c309f2fbccc |
| t017_w2_dup_p2.json | a87d0c401c43619269a2fbe7356bef88df0a43faeb1c9d360ae8d846e37ea2ef |
| t017_w2_dup_p2.log | f8372383183599f9f5d3749a82a61bd3cc57eed4c3fad5c693802c309f2fbccc |
| t017_w3_dup_p2.json | 99890f00a5c318c676323f4088264e64359b30d549fdf7d1e5b39dcf8c151577 |
| t017_w3_dup_p2.log | f8372383183599f9f5d3749a82a61bd3cc57eed4c3fad5c693802c309f2fbccc |

（三份 log 同 sha：同一布局三次，引擎 trace 行逐字节一致。三份 json 只有时间戳/路径类字段不同。）

## 结果（三次同答）

| run | ask.ok | answer_sha256 |
|---|---|---|
| W1 | False | c246069c6e6f637f01437b4562be2f3c09038781f6adc13835730daaf750e305 |
| W2 | False | 同上 |
| W3 | False | 同上 |

`ask.answer` = `我住在\_\_\_\_\_\_。\n\n根据以上对话，填空。\n\nA. 西南区`（len=36）
`ask.expected` = `广陵路`
`cell_count` = 63 ｜ `coverage` = home[4075,4096,21] ｜ habit[4020,4032,12] ｜ project[3950,3968,18] ｜ habit2[3892,3904,12]
`head_gap_cells` = 0 ｜ `form`=quiz ｜ `cloze`=Y ｜ maxUnd=1 ｜ escUS=6
trace 四类：SUM=25 SUM2=25 blk=100 OK=4 ｜ 门禁 `DIMS=A:pass B:pass 3a:pass 3b:pass C:pass` / `GREEN (5 项 AND)` rc=0

## 结论归属（检测员裁定，引用时请连这句一起引）

纯距离说被 `iso_dup_p2` 判红，纯内容说被 `iso_dup_p3`（第四块是 project 副本、69 cells、fail×3）判红。
现存的合取式（"第四块既是 home/project 副本，且该事实原本在 slot1/slot2"）**是拟合，不是机制**。
