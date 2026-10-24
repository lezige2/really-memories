# 盲写判定清单（BLIND-CHECK）— 14B 四格

撰写：检测员 inspector ｜ 在看到任何 14B 运行结果之前写死 ｜ 交付对象：lead / executor
用途：四格跑完后**照表查**，不允许事后改判据。

---

## 0 盲写边界（先声明，便于审计）

本单期间我**没有打开** runs_m14b/ 下的任何文件，也没有打开 m2_v1_14b/ 下的任何产物或 blocks_14b.json。
我这一单读过的文件只有这些：

- 7B run json：runs_t031/t031_e_dup4_samedriver_r1.json、_r2.json、runs_t031/t031_f_pp18_r1.json、_r2.json、
  runs_t032/t032_f_r1.json、runs_g18/iso_fac_pp18_home_r1.json、runs_g18/iso_fac_G18_home_r1.json、_r2.json、
  runs_t033/x1_r1.json、x1_r2.json、runs_t033/b57_r1.json、b57_r2.json
- 源码：runs_iso2/_driver2.py、runs_t033/_driver4.py、runs_t033/_driver7.py、runs_t033/_judge_t033.py、
  tools/m2_visibility_probe.py、tools/kvslots.py、tools/kvshim.cpp、llama.cpp/src/llama-kv-cache.cpp、llama-context.cpp
- 我自己的 mine/inspector/SPEC-14B-4CELL.md、mine/lead/PREREG-14B-4CELL.md

若我后续不慎看到 14B 结果，会在报告里立刻声明看到了什么。**到目前为止没有看到。**

---

## 1 7B 基线参考值表（每个值附出处）

主表（每格取一个 canonical run json；sha256 是对 answers[0].answer 原文取的，原文已 strip）：

| 格 | layout_key | 段数 | 段（id@slot：pos_lo,pos_hi，cells） | 总格数 | target | 问句 / 期望事实 | 7B 判定 | 7B answer sha256 | 该 run 实测 DLL |
|---|---|---|---|---|---|---|---|---|---|
| E | iso_dup4 | 4 | home@1：4075,4096,21；project@2：4014,4032,18；habit@3：3956,3968,12；project2@4：3886,3904,18 | 69 | home | 我住在哪？ / 广陵路 | 过（ok=true） | 7ec1430d972d949e5c1d306c6d838c06335bcdd1d1dac8bebde0dbb8a04622fd | c7ea09bbc7cb616f4c649d76d8c4839bb7c9934861a70d7999959f44d793e3b8 |
| F | iso_fac_pp18 | 4 | home@1：4075,4096,21；project@2：4014,4032,18；habit@3：3956,3968,12；project_paraphrase18@4：3886,3904,18 | 69 | home | 我住在哪？ / 广陵路 | 败（ok=false） | 11e20d78a1f18a98ec18293ab92ddb2364e092ddaa2e1a20e926ec9203a80e34 | c7ea09bbc7cb616f4c649d76d8c4839bb7c9934861a70d7999959f44d793e3b8 |
| X1 | iso_x1_57copy | 3 | home@1：4075,4096,21；project@2：4014,4032,18；project2@4：3886,3904,18 | 57 | home | 我住在哪？ / 广陵路 | 过（ok=true） | 14dc3f98202c70232f88b0ce5eaac7cc75e7c7f5a386381da8c6f79574b893ff | 3a726dbd9e264facceb32205db8e2daee66c1132cc4c69605c040a86970bbf93 |
| B57 | iso_fac_nb57 | 3 | home@1：4075,4096,21；project@2：4014,4032,18；pp18@4：3886,3904,18 | 57 | home | 我住在哪？ / 广陵路 | 过（ok=true） | e5cc43c360ead6ccc8363970b14b55719cdaf0a4b3ee10866c80b57ebaf90b98 | 3d02c1f8266fb97002bd641f1bb239bd4782037a2eb292dc08aea89b87710b2c |
| X0（参考点，不是四格之一） | iso_fac_G18 | 4 | home@1：4075,4096,21；project@2：4014,4032,18；habit@3：3956,3968,12；blk_G_bos_c18@4：3886,3904,18 | 69 | home | 我住在哪？ / 广陵路 | 败（ok=false） | 3f69de0797a6afb35053f4a04521279021ee7dafc9a3adc451a3b0f71b30d291 | 3a726dbd9e264facceb32205db8e2daee66c1132cc4c69605c040a86970bbf93 |

canonical run json 与键路径（照这个去核，不要照抄别人的表）：

| 格 | canonical 文件 | schema | layout_key 键 | 段列表键 | 总格数键 | 判定键 | DLL 键 |
|---|---|---|---|---|---|---|---|
| E | runs_t031/t031_e_dup4_samedriver_r1.json | iso_run_v2 | layout_key | layout.segments[i].{id,slot,pos_lo,pos_hi,cells} | layout.cells_total | answers[0].ok | engine.dll_sha256 |
| F | runs_t031/t031_f_pp18_r1.json | iso_run_v2 | layout_key | 同上 | layout.cells_total | answers[0].ok | engine.dll_sha256 |
| X1 | runs_t033/x1_r1.json | iso_run_v2 | layout_key | 同上 | layout.cells_total | answers[0].ok | engine.dll_sha256 |
| B57 | runs_t033/b57_r1.json | iso_run_v2 | layout_key | 同上 | layout.cells_total | answers[0].ok | engine.dll_sha256 |
| X0 | runs_g18/iso_fac_G18_home_r1.json | iso_run_v2 | layout_key | 同上 | layout.cells_total | answers[0].ok | engine.dll_sha256 |

问句与期望事实的键：answers[0].question（值 "我住在哪？"）、answers[0].expected（值 "广陵路"）、
answers[0].segment（值 "home"）。target 键：顶层 target（值 "home"）。

其余可复现的旁证：

| 检查项 | 四格实测值 | 出处 |
|---|---|---|
| 几何自检 gap | 0 | layout.head_gap_cells（四个 iso_run_v2 文件都是 0） |
| 覆盖自检 | raw.cell_count = 69/69/57/57；positions_min = 3886；positions_max = 4095；raw.overlaps = [] | raw.*（四个文件） |
| 门禁 | control_ok = true | 顶层 control_ok（四个文件） |
| 第二跑逐字节相同 | E：r2 sha 与 r1 相同；F：r2 相同；X1：r2 相同；B57：r2 相同 | 同目录 _r2.json 的 answers[0].answer |
| F 的独立复现（另一条代码路径） | runs_t032/t032_f_r1.json：schema=t032_run_v1、arm=F_pp18、layout.gap_top、answers[0].ok=false、answer sha 11e20d78…（与 t031 完全一致） | 该文件 argv / arm / answers[0].answer |
| B57 的第三跑 | runs_t033/b57_r3.json：ok=true、answer sha e5cc43c3…（与前两跑一致） | 该文件 answers[0] |
| 引擎参数（四格一致） | engine.n_ctx=8192、n_seq=8、kv=q8_0、gpu=99 | 四个文件的 engine.* |
| 每格字节数（7B） | 30,480 B/格；块尺寸 = 708 + 30480*n | 我的块头解析（附录 A 解析器）与 E10-NEXT2.md:2529 |
| BOS 口径（7B） | 首 token = 151646（四个块文件都是） | 块头 n_tokens 之后的第一个 int32 |

注意 schema 差异（别用错键）：t032_run_v1（runs_t032/t032_f_r1.json）**没有** layout_key 与 layout.head_gap_cells，
它用顶层 arm 与 layout.gap_top，段 id 也与 iso_run_v2 不同（第 4 段叫 "pp18"）。四格判定一律用 iso_run_v2 那套键。

---

## 2 判定规则（可机械执行）

### 2.1 三种终态，只允许这三种

- **过**：所有前置检查通过（§2.2 第 1-3 层）且 answers[0].ok == true，且两跑 answer sha256 相同。
- **败**：所有前置检查通过且 answers[0].ok == false，且答案可被 §2.3 归入某一失败形态，且不是 §2.4 的三种"不算败"情形。
- **实验无效**：§2.2 任一前置检查失败，或命中 §2.4 任一情形。必须写明是哪一条触发。

四词纪律（结论里只许用这四个词描述状态）：未检验 / 实验无效 / 未测出·欠功率 / 无效应。
**"败"不等于"假设被否证"**；"过"也不等于"机制被证明"。

### 2.2 前置检查，按这个顺序，任一失败就停在该层

第 0 层（每格都过一遍）—— 14B 块自证（读 blocks_14b.json，不读引擎）：
- 4 个块的 cells 依次为 21 / 18 / 12 / 18
- 每块 first_token == 151646（与 7B 相同）
- 每块 size == 1188 + 104464 * cells（21→2,194,932；18→1,881,540；12→1,254,756）
- 每块块头 n_layer == 48、k_row == v_row == 1088、k_type == v_type == 8
失败 ⇒ 该格 **实验无效（块不自证）**。

第 1 层 —— 装置与本轮一致性（看 run json 的 engine.*）：
- engine.model 是 14B 路径（不是 7B）
- engine.n_ctx == 8192、n_seq == 8、kv == "q8_0"
- engine.gpu 记录在案；若 != 99，必须同时有降级原因原文，并把该格标 partial offload
- 四格的 engine.dll_sha256 必须是**同一个值**
失败 ⇒ 该格 **实验无效（装置不一致/未记录）**。

第 2 层 —— 几何与门禁（看 run json 的 layout.*、raw.*、control_ok）：
- layout.cells_total == 69（E、F）/ 57（X1、B57）
- 每段 (id, slot, pos_lo, pos_hi, cells) 与 §1 主表逐字段相等（位置 4075/4014/3956/3886 不得移动）
- layout.head_gap_cells == 0
- raw.cell_count == layout.cells_total；raw.positions_min == 3886；raw.positions_max == 4095；raw.overlaps == []
- control_ok == true
任一条失败 ⇒ 该格 **实验无效**；其中 control_ok == false 单独记 **实验无效（门禁不过）**，并**必须**先解决门禁，
不允许在门禁不过的前提下解释四格。

第 3 层 —— 稳定性：
- _r1 与 _r2 的 answers[0].answer 的 sha256 必须相同
不同 ⇒ 该格 **实验无效（不稳定·不取其一）**，该格作废，不得挑一次当结果，也不得说"多数情况下"。

第 4 层 —— 答案判定：只看 answers[0].ok（= P.fact_ok("广陵路", answer) 的布尔值，
定义 tools/m2_visibility_probe.py:164-167）。ok 就是过，非 ok 就是败（前提是过了第 0-3 层）。

### 2.3 失败形态分类（只在"败"时使用，顺序固定，命中即停）

按 kvmem/m2_visibility/runs_t033/_judge_t033.py:4-11 与 :29-44 的顺序：

    1 该文件的 fact_ok（它自己的严格判据）通过     -> none
    2 去空白归一后为空串                          -> 空串
    3 归一后的问句出现在归一后的答案里            -> 复述提问
    4 三个下划线开头 / 含"填空" / 含"选项" / 行首 A-D 加点或顿号 -> 改写成模板
    5 含 不知道 / 无法 / 不能确定 / 没有相关信息  -> 拒答
    6 含数字或地址类字（路|街|道|号|单元|室|楼|巷|村|区） -> 编造具体值
    7 其余                                        -> 其他

两条判据冲突时的处理（会真的发生）：
- _judge_t033.py 的 FACT 是 "广陵路12号2单元602"（该文件 :15），比 driver 的 "广陵路"（probe:108）**更严**。
- 于是可能出现 "driver ok=true 而 judge 第 1 步不通过"。
- 规则：**过/败以 driver 的 answers[0].ok 为准**；judge 只用来命名失败形态。两者不一致时，
  结论里两行都写（例：过（driver）；judge 形态=改写成模板（更严判据）），不许只写一行蒙过去。

### 2.4 三种"不算败"的情形

1. **生成被截断**：若 (answers[0].kvshim_n_tokens_after_ask - answers[0].kvshim_n_tokens_before_ask) == 24
   （= P.N_PREDICT 上限，tools/m2_visibility_probe.py:103），且答案末尾没有句末标点 ⇒ 记 **未测出·欠功率**，
   提高 n_predict 到 64 重跑 2 次后再判；不得记为败。
2. **空答（rc<0 路径）**：answer 为空且 kvshim_ask_at_return_bytes 异常小 ⇒ 记 **实验无效（生成失败）**，
   先查 gap/位置/门禁，不许记为败。
3. **命中 §2.2 第 0-3 层任一失败**：记 **实验无效**，不许记为败。

---

## 3 结论映射表（写死，跑完直接查）

前提：E、F、X1、B57 四格都通过了 §2.2 的 0-3 层。若 E 未通过，跳到 §3.1。

### 3.1 锚点规则（先查这条）

- **E（69 格 + 精确副本）在 14B 上败** ⇒ 整张 14B 表 **作废**。结论只写一行：
  "14B 锚点缺失：E 败，四格不可与 7B 的 2×2 对齐；F/X1/B57 的任何组合都不得用于支持或否证假设。"
  后续动作：先查装置（门禁、块自证、offload、DLL）与 E 的配方，**不许**用 F 的结果讲故事。
- E 过 ⇒ 锚点在，进入 §3.2 / §3.3。

### 3.2 F（69 格 + 改写 pp18）单独看

| 14B 上 F | 允许写的结论 | 不允许写的 |
|---|---|---|
| 过 | 7B 上"69 格 + 改写 = 败"这个现象在 14B 上不复现。支持预登记的规模/分配假设（PREREG-14B-4CELL.md:22-23 的方向）。 | 不得说"机制已解释"；不得与 7B 做 Δ/字节数/logprob 的任何比较。 |
| 败 | 现象在 14B 上以序数复现。对"规模"这个因子构成**未支持**；不得写成"规模假设被否证"。 | 不得说"规模无关"（差异字段共 6 项，见 §4）。 |
| 实验无效 | 什么都没检验。按 §2.2 写明触发层。 | 不得挑其中一跑当结果。 |

### 3.3 X1 与 B57 的组合（都在 14B 上）

| X1 | B57 | 允许写的结论 |
|---|---|---|
| 过 | 过 | 与 7B 形状一致：57 格下副本与改写都过。结合 F 判读：若 F=败 ⇒ 14B 上仍复现"69 格才分化"，与负载解释相容；若 F=过 ⇒ 14B 上分化整体消失。 |
| 过 | 败 | 14B 上出现"57 格也分化，且方向是 改写必败"。即在比 7B 更低的负载下，第 4 块内容的身份重新变成判别量。这是**新现象**，只能记"未测出新的分化点"，不得声称是规模导致。 |
| 败 | 过 | 14B 上"精确副本"在 57 格就败，而改写反而过 ⇒ 与 7B 反向。优先按 **实验无效（装置可疑）** 处理，重跑 2 次仍如此才记"反向现象"，不做机制解释。 |
| 败 | 败 | 14B 上 57 格两格全败 ⇒ "删掉 habit 就能救"这条在 14B 上不成立；负载解释在 14B 上得不到支持。记"未支持（低负载也败）"，不得外推到"机制是 X"。 |

### 3.4 联动一致性检查（写结论前必须过一遍）

- F=过 且 B57=败 ⇒ 内部矛盾（57 格败、69 格过，负载单调性反向）。结论只许写 **实验无效（与负载单调性冲突）**，
  先查装置与判据，不许解释成"参数规模改变了机制"。
- F=败 且 X1=败 ⇒ 也是矛盾（同一 57/69 结构下，副本格在 X1 败而 E 过说明格位差异被别的东西主导）。
  记 **实验无效（与锚点冲突）** 并回查 E/X1 的 pos 与块的 sha256 是否真的是这两个块。
- 上述两条若不成立，按 §3.2/§3.3 正常落结论。

### 3.5 每条结论都不授权的三件事

1. 不许把 14B 的答案与 7B 的答案做数值对比（Δ、logprob、rank、答案长度、字节数、cells 数）。
2. 不许把"过/败"解释成内部机制（哪一层、哪条通路），只能写现象与序数。
3. 不许在台账 E10-NEXT2.md 里写"14B 证实/证伪"，只能写"14B + 本装置下，序数为 X"。

---

## 4 必录字段清单（缺一项，该格降级为"未检验"）

与预登记的差异字段清单对齐（模型 / 每格字节数 / 分词器 / 内容 token 数 / BOS 口径 / DLL sha / -ngl / n_ctx）：

| # | 字段 | 7B 值（出处） | 14B 期望/要求 | 从哪读 | 缺失后果 |
|---|---|---|---|---|---|
| 1 | 模型文件 | D:/models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf，4,683,073,504 B（fixtures.json engine.model/model_size） | 14B 路径 + size + mtime 实测 | run json engine.model；fixtures_14b.json engine.* | 该格未检验 |
| 2 | 每格字节数 | 30,480 B/格（块尺寸 708 + 30480*n） | 104,464 B/格（尺寸 1188 + 104464*n） | blocks_14b.json 的 size/cells 与块头解析 | 该格未检验 |
| 3 | 分词器（格数是否相等） | 21/18/12/18 | 必须仍是 21/18/12/18 | blocks_14b.json cells + run json layout.segments[].cells | 几何不同 ⇒ 该格作废 |
| 4 | 内容 token 数 | 20/17/11/17（首 token 是 BOS） | 同上 | 块头 n_tokens 与首 token | 该格未检验 |
| 5 | BOS 口径 | 首 token = 151646 | 期望 151646；不同则记为口径差异 | 块头第一个 int32 | 未记录 ⇒ 该格未检验 |
| 6 | DLL sha256 | 参见 §1 表（E/F c7ea09bb…、X1 3a726dbd…、B57 3d02c1f8…/648e7244…） | 四格同一个值，且实测 | run json engine.dll_sha256（_driver2.py:147-149 用磁盘实测覆盖） | 未记录 ⇒ 该格未检验 |
| 7 | 层放置（-ngl 语义） | 99 = 全 28 层（kvshim.cpp:145；KV 侧 offload_kqv 默认 true，llama-context.cpp:4028） | 若 99 成功则同语义；若降级必须记 gpu 值 + 失败原文 | run json engine.gpu；执行者的降级记录 | 未记录 ⇒ 该格未检验，且不得与 7B 并表 |
| 8 | n_ctx | 8192（kvshim.cpp:158） | 8192 | run json engine.n_ctx | 该格未检验 |

另外必须一并给（否则同样降级）：每格 _r1/_r2 的 answers[0].answer 全文与 sha256；control_ok；
raw.cell_count / positions_min / positions_max / overlaps；layout.head_gap_cells；
answers[0] 的 question/expected/segment；kvshim_n_tokens_before/after_ask。

---

## 5 预计会导致"无法判定"的情形（逐条列出，命中就照此记）

1. **门禁不过**（control_ok=false）：实验无效（门禁不过）。四格都不解释。
2. **两跑答案不同**：实验无效（不稳定），该格作废，不取其一。
3. **E 锚点败**：整表作废（§3.1）。
4. **run0（单块基线）未过**：装置不可用，四格全部实验无效。
   说明：run0 的 layout 键与判据由执行者报；我不读 runs_m14b，故不预设其取值 —— 只要它"单块能读出记忆"这一条不成立，
   就按本条第 1 句处理。
5. **块 cells 不是 21/18/12/18**（14B 分词器不同）：几何变了，该格作废（§2.2 第 0 层）。
6. **块 size 不等于 1188+104464*n**：块坏了或我的推导错。停，报实测值，不许改断言。
7. **首 token 不是 151646**：BOS 口径变了。可继续跑，但结论降级为"跨 BOS 口径"，且必须写进差异字段。
8. **partial offload（engine.gpu < 48）**：装置变了。四格仍可比序数，但结论只能限定在"14B + 部分 offload 这个装置"，且必须打戳。
9. **四格 DLL 不是同一个值**：装置不一致，实验无效（§2.2 第 1 层）。这是 7B 那边的真实教训（E/F c7ea09bb、X1 3a726dbd、B57 两个值）。
10. **生成被截断**（生成 token 数 == 24）：未测出·欠功率，提高 n_predict 到 64 重跑两次（§2.4 第 1 条）。
11. **空答/rc<0**：实验无效（生成失败），先查 gap=0 与位置（probe:498-538 的三条前置检查）。
12. **control 文本在 14B 上重建后 target_n 不是 210**：记差异字段（与 7B 的门禁文本不等长），
    该格仍可判过/败，但"同门禁文本"这条前提不成立，写结论时必须声明。
13. **两个引擎同时起 / 中途别的执行者插进来**：Vulkan OOM 或 DLL 链接失败，实验无效（装置被占用）。
14. **judge 与 driver 判据不一致**：不是无法判定，但必须两行都写（§2.3）。
15. **只有一次跑**：未检验（预登记要求每格 2 跑，PREREG-14B-4CELL.md:27）。

---

## 6 交付时照这个表填（四行，每行 12 列）

    格 ｜ 14B 判定（过/败/实验无效·原因/未测出·欠功率） ｜ 两跑 answer sha256（是否相同） ｜
    failure_form ｜ control_ok ｜ layout.cells_total ｜ head_gap_cells ｜ raw.positions_min/max ｜
    engine.{model,gpu,n_ctx,n_seq,kv,dll_sha256} ｜ 四块 {cells,first_token,size,sha256} ｜
    差异字段全表（§4 八行） ｜ 结论（§3 表里查出来的那一格原文）

填不出来 ⇒ 该格记"未检验"，并写明缺哪个字段。**不许用"看起来一致/大概/参照交接稿"填空。**
