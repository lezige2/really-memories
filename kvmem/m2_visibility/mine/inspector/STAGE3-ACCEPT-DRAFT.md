# STAGE 3 验收单（草案 · 逐项状态机）

判据来源：`SRC-CRITERIA.md` §12.1–§12.21（冻结于实现之前）。本表**先建后填**，状态词表见 §12.15。
状态：**通过** / **未通过** / **按计划未到** / **失锚（待重跑）**；证据强度：**R 重算** / **C 构造性** / **A 锚定转录** / **S 仅自述**。

| # | 判据 | 验证方式（我可复算的） | 强度 | 状态 |
|---|---|---|---|---|
| 1 | 行级追溯 7 对 `(line_index, line_sha256)` | 自己按容器行号重算 7 行 sha，逐对比 | R | 待验 |
| 2 | origin 往返逐字节（139 字符；16/16 形态 91） | `parse_origin(format_origin(x)) == x` 自跑 + 长度 | R | 待验 |
| 3 | `source_text_len` 127->110（与 `profile_blob_len` 114->99 分开记） | 读库两列，分别报 | R | 待验 |
| 4 | ⑧ origin 拼接段 sha256 == 块 `source_text` sha256 | 自算拼接段 sha，与块正文 sha 比 | R | 待验 |
| 5 | 闸门在**返回点**函数体内 + 可达 + 运行时拒绝 | AST `file:line` + 置空注册库令其拒绝 | R | 待验 |
| 6 | `no_todo_stage3 == 0` | grep `TODO(stage3)` 全库计数 | R | 按计划未到 |
| 7 | 单一解析实现（`format_origin`/`parse_origin` 相邻，记录两处 `file:line`） | 读源码 + grep 是否有第二份实现 | R | 待验 |
| 8 | 11 行预登记（独立产物 + 自身锚 + `authored_after_run` + 落盘时刻晚于 run） | 逐行比 case 名/期望；核时刻 | R | 待验 |
| 9 | `lost_keys` / `gained_keys` 两张**显式空表**，五族全列 | 读产物字段，确认是空表不是缺键 | R | 待验 |
| 10 | 行序负向（shuffle 必须失败，且报「顺序不符」） | 我构造打乱输入喂进函数 | R | 待验 |
| 11 | 64 hex 收、16 hex 拒（报错须说「需要 64 hex」） | 两种输入各跑一次 | R | 待验 |
| 12 | NULL/缺失 origin 拒绝（报错说清哪一条判据） | 构造 NULL 行插入 | R | 待验 |
| 13 | 5 条 CHECK ↔ 负向一一对号（§12.13 格式 A，缺号视为未验） | 对表逐条查负向用例 | R | 待验 |
| 14 | `blocks` 逐列 diff：`changed={source_text,text_origin}`、`added/removed` 皆空 | 自己跑列集合比对 | R | 待验 |
| 15 | 块文件与 `kvmem/blocks/*.kvmem` 未变（基线 `0a63717933055e65`） | sha/bytes/mtime 三项 | R | 待验 |
| 16 | 11 行裁决不变 | 9 行重算 + 2 行构造性（轴 = source_text） | R+C | 部分已验（源文本轴 9 行 R 已出，2 行 C 已出）|
| 17 | M5 重锚（旧 `d97cdfdcbd6c6d3d` 已失效，新锚由我重算） | 重跑后自算 sha，写 `invalidated_anchors` 含 `expected_by` | R | 失锚（待重跑）|

**已固定的实测事实（源文本轴，我重算）**
- `joined in container` = **False**（7 行各自 in container = True）；`source_text_len` 127 -> 110；`profile_blob_len` 114 -> 99（两个独立量，不得相减对照）。
- origin(16/64) = **139 字符**；origin(16/16) = 91；joined sha256 = `2b3b6662b883d117f885cb1f5e995b673b1fb8175c226ebd86be92e8c41fade4`。
- 7 条探针 before==after 全 True 且全中期望；`plate_main`/`home_main` supported -> supported（同代码，仅换源）。

**页眉 · 读本表之前必须知道的事（操作指令，不是事实陈述）**
**本表所有 `verdict_before` 均为代码轴（`axis=code`）。源文本轴的值不在本表内，见 #16。禁止跨轴比较。**

**填表规则**：任何一行的强度格**不许留空**；确实无证据写 **S**，不许省略 —— 省略与 S 在纸面上看不出区别，一个是「没证据」，一个是「忘了填」。

**未验 / 缺口（先记，不藏）**
- 空 db 上的行为：**未验**（历史投毒测试因常量已删而退役，见 Stage 2 收尾）。
- 两条 ablated 行：**C 级**，非重算（`ground(db=消融库)` 因该库无 `blocks` 表走不通）。
