# Stage 2 + I8-C 验收

验收人：inspector ｜ 2026-10-25 ｜ 依据：SRC-CRITERIA.md（I1/I7/I8/I8-b）、M2 几何口径、锚规则
纪律：不采信二级汇总；下面每条都是我自己读出的字段或跑出来的返回值。

## 1 Stage 2（chat.py 改读注册表）：通过（附三条修正）

| 判据 | 裁决 | 我的实测 |
|---|---|---|
| 三问 sha 逐字节 | 通过 | 852a5e5e6ab70eeb… / dacdc1a89ef08165… / 46272e43287c5ff7…（与三条权威值同）|
| 几何 | 通过 | cells_total=51、positions 4045..4095、head_gap_cells=0、overlaps=[]、first_question_pos=4096 |
| 块文件重建相同 | 通过 | profile.kvmem 3251081d12da5678、project.kvmem 981a9c776c720686（我重算文件 sha）|
| MEMORIES 归零 | 通过 | grep 计数 0；:103 为 sources = ms.indexable_sources(con)；文本里「我叫林知远」「我在做蓝鲸项目」均 False |
| 13 是真反向断言 | 内容上是，但它是 8 的重复 | 见修正 1 |
| 投毒负向测试 | 不能判通过 | 只有 README 文档、无产物；且见修正 3 |

注：这两个 chat 块是 7B 引擎产物（memory_block.model_path = DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf），与 M2 的 14B 块是两套；
这里只做「重建前后文件 sha 相同」的自身比较，不涉及任何跨模型数字对照（既有锁保持）。

### 修正 1（重要）：8_fidelity 与 13_no_second_copy_of_memory_text 是同一个布尔

    "8_fidelity":                        res["no_second_copy_of_memory_text"]["ok"],   # :281
    "13_no_second_copy_of_memory_text": res["no_second_copy_of_memory_text"]["ok"],   # :288

⇒ 13 项验收里只有 12 个独立检查；而 8_fidelity 这个名字现在指的不是保真检查（旧的「注册表文本 == chat.py 常量」已无处可比，正确退役）。
要求：删掉 8，或改名并置 retired（值不能是 true）。留着它等于让账本显示 13/13，比实际多一项。

### 修正 2：README 里的 chat.db 锚已过期（内容没变，只是文件级漂移）

- README 记：a699fd1e5aaa9adf -> 5909b978e31e584a；我实测：6d2ff37a4861b08d。
- 诊断：chat.db mtime 04:31:20，正是 m4_layer2_link.py / run_layer2_link.json 写盘那一分钟；README mtime 04:31:45 在其后
  ⇒ 说明锚是在被另一阶段改写之前测的。
- 内容层面无不一致：memory_source 10 行（profile 61/d3e57f11…、project 45/aa9769ad…、conv 127/d8c094c1… + 7 摘录）、
  memory_source_excerpt 7 行、memory_block 2 行、integrity_check=ok、page_count=22 / freelist=1。
⇒ 结论：无内容漂移，只有文件级漂移。要求 README 改成当前值，并在状态报告里写明「04:31:20 有另一阶段写过该库」。

### 修正 3：投毒负向测试已平凡真空

- README 第 2 条写「把删掉的常量投毒回去再建块 ⇒ indexed 2 sources + 2 blocks、rows named poison: 0」。
- 但常量已不存在（grep = 0），投毒一个没有代码路径读取的名字，无论结果如何都不构成证据。这条测试今天不可能失败，因此也不可能证明什么。
- 它原本要防的是「文本被当成依赖」，现在的等价证据是 13 的源码扫描（chat.py 无常量、读 indexable_sources、建块时不写源）+ :103 的实际调用。
  这两条我认可；投毒那条应明确标为已失效/由 13 取代，不要留在负向测试清单里冒充覆盖。
- README 第 3 条「空库 ⇒ die(...)」我没有跑（会动库），记为未验。

## 2 I8-C（9462b88）：通过

- DDL 我逐条核过（sqlite_master 原文）：text_kind DEFAULT conversation、contains_model_turns DEFAULT 1、三条 CHECK IN (...)、
  CHECK (NOT (text_kind=human_memory AND contains_model_turns=1))、CHECK (is_excerpt=0 OR derived_from IS NOT NULL) ⇒ 与我 I8-b 的 1/2 条逐字对应。
- 12 我自己复跑（chat.db 副本，只写老列）：INSERT 后读回 (conversation, 1, 0) ⇒ fail-closed 成立。
- (iii) 我用 scratch 库造一行 human_memory + turns=1（无 CHECK 干扰）⇒ 闸门抛 SourceNotAllowed ⇒ 闸门确实读了 turns 列，装饰性已消除。
- 11 我复跑：conv_2026-10-25 ⇒ SourceNotAllowed（gate_regression 亦记）。
- row_parity 为空（= 无问题），proofs 四条齐（i_legacy_insert / ii_check / i_gate / iii_gate），与我复算一致；trigger_present=true。
- 唯一提醒：row_parity 是一次性迁移的比对结果，不可复跑（迁移只跑一次）。我接受它作为证据，但要求 README 写清「不可复跑」，避免下次有人拿它当回归项。

## 3 锚（我算的）

| 产物 | 我重算 | 说明 |
|---|---|---|
| kvmem/chat.db | 6d2ff37a4861b08d | README 的 5909b978 已过期（见修正 2）|
| m4_memory.db | fd244c80c0cc974d | 未变 ⇒ M4 验收有效 |
| run_m4_verify.json | 857f13c514ad233e | 16/16 true |
| run_m5_grounded.json | d97cdfdcbd6c6d3d | 未变 ⇒ M5「通过」维持 |
| run_m2_after_s2.json | 2e1f2be9b5d51a21 | 与 README 一致 |
| tools/chat.py | 4c8d73e955c108ff | — |
| tools/memory_source.py | 08e2e16557b7030b | — |
| m4_layer2_link.py | c1b0dbed74a417ee | — |

## 4 结论与对 Stage 3 的建议

- Stage 2：通过（行为与几何与旧运行逐字节一致，MEMORIES 归零）；三条修正都是账本层/展示层，不动代码行为。
- I8-C：通过（默认值翻向拒绝态、CHECK 补全、闸门真读两列、12 可复跑）。
- 三条修正（8 重复计数 / README 锚过期 / 投毒测试失效）不阻塞 Stage 3 开工，但必须在 Stage 3 交付前清掉，
  否则最终状态报告里会同时出现「13/13」和「过期锚」两处不可复算 —— 而那正是这一整轮在防的东西。

## 5 追加（2026-10-25 04:42 后重算；上一版结论已过期）

锚规则适用：`check_registry.py`（04:41:41）与 `run_registry_check.json`（04:42:08）在我上版验收后又变过，
因此 §1 里「13 项、12 独立」那组数字**作废**，以下是重算结果（我自己跑的函数，不是读它的自述）。

| 项 | 值 |
|---|---|
| `check_registry.py` | `ed4e84530d16c26c` |
| `run_registry_check.json` | `6923269ba0a40f70` |
| `registry/README.md` | `11f775d898af30b3` |
| acceptance 键数 | **14**，**全 True** |
| `retired_keys` | `[8_fidelity]`（值是说明文本，不进键数）|
| 账本自检 | `key_count 14 / distinct_judgements 14 / duplicate_sources {} / ok True` |
| 负向（14） | 我重跑：`ok=False`、`duplicate_sources={"res['x']['ok']": ["1_a","2_b"]}`、断言要求**恰好这一组** |
| 对照（15） | 我重跑：`ok=True`、`duplicate_sources={}` |
| 双边成立 | **True**（恒 False 的实现过不了 15，恒 True 的过不了 14，报错组不对的过不了 14 的取值比对）|

复核要点：负向断言不是只要求 `ok is False`，而是同时要求**重复组恰好是 `[[1_a, 2_b]]`** —— 这挡住了「乱报一个组也算过」的退路。
提示一处可加强（非阻塞）：对照侧目前只取 `["ok"]`，未显式要求 `duplicate_sources == {}`；若将来 `ok` 定义被改，这条会失去意义。
