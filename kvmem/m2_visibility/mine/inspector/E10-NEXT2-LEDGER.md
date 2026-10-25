# E10-NEXT2 台账（14B 四格轮次）· 正式启用

维护者：检测员 inspector ｜ 2026-10-25 ｜ 位置：kvmem/m2_visibility/mine/inspector/E10-NEXT2.md
本文件是**本轮**台账。仓库根目录的 E10-NEXT2.md（3194 行，7B 时期）未改动，本轮结论不并入它，直到 lead 指定合并方式。
一切判定以 run json / 块文件 / 日志**原文**为准；我未采信任何人的转述值，凡是验不动的都在 §5 明写。

证据基线（我实际读过的）：runs_m14b/out 下 28 个 run json（run0 2 / E 2 / F 2 / X1 2 / B57 2 / P1 6 / P2 2 /
np64 10：run0 / E / F / X1 / B57 各 2 跑）；runs_m14b/{fixtures_14b.json, blocks_14b.json, control_texts_14b.json,
_driver14b.py, dll_archive/, logs 只读 loadD_ngl99_c8192.log}；m2_v1_14b 5 个 .kvmem 的块头；
两个模型 GGUF 的完整 sha256（我自己算的）。

---

## 1 判定表（预登记判据 = P.fact_ok，24 token 生成预算）

| 格 | layout | 几何 | 两跑 | 判据结果 | 判定 | 四词纪律标签 |
|---|---|---|---|---|---|---|
| run0 | iso_home_only | home@1 [4075,4096) 21 格，含 BOS | sha 相同（31bff41f） | ok=true | 过 | 无效应（同格重复稳定） |
| E | iso_dup4 | home+project+habit+project 副本 = 69 格 | sha 相同（c7d4e377） | ok=true | 过 | 无效应 |
| F | iso_fac_pp18 | home+project+habit+pp18 = 69 格 | sha 相同（c7d4e377） | ok=true | 过 | 无效应（限 24 token 窗口，见 §7） |
| X1 | iso_x1_57copy | home+project+project 副本 = 57 格 | sha 相同（c7d4e377） | ok=true | 过 | 无效应 |
| B57 | iso_fac_nb57 | home+project+pp18 = 57 格 | sha 相同（c7d4e377） | ok=true | 过 | 无效应 |
| P2 | iso_dup4_g18 | home+project+habit+g18 = 69 格 | sha 相同（63146584） | ok=true | 过（判据）／输出已变 | 输出改变，判据未动 |
| P1_habit | iso_habit_only | habit@1 [4084,4096) 12 格 | sha 相同（2288173d） | ok=true | 过 | 载荷可召回 |
| P1_project | iso_project_only | project@1 [4078,4096) 18 格 | sha 相同（cba55c51） | ok=true | 过 | 载荷可召回 |
| P1_pp18 | iso_pp18_only | pp18@1 [4078,4096) 18 格 | sha 相同（dca59407） | ok=false | 败（判据字面失手） | 未测出·欠功率（判据侧） |
| np64_run0 | iso_home_only | 21 格 | sha 相同（ac52a76b） | ok=true | 过 | 完整性复核批次 |
| np64_E | iso_dup4 | 69 格 | sha 相同（01ea3033） | ok=true | 过 | 完整性复核批次 |
| np64_F | iso_fac_pp18 | 69 格 | sha 相同（b1de8499） | ok=true | 过 | 完整性复核批次（**含污染**，见 §1.1） |
| np64_X1 | iso_x1_57copy | 57 格 | sha 相同（d7b4b1dc） | ok=true | 过 | 完整性复核批次（自问自答退化，无污染） |
| np64_B57 | iso_fac_nb57 | 57 格 | sha 相同（c7b29999） | ok=true | 过 | 完整性复核批次（自我纠错，无污染） |

**64 批次已齐、定稿**：5 个布局各 2 跑共 10 个 np64 文件，每个布局 r1 与 r2 逐字节相同
（E 01ea3033 / F b1de8499 / X1 d7b4b1dc / B57 c7b29999 / run0 ac52a76b）。
"四格齐一"由此**锁定为"前 24 token 齐一"**，不得简写成"齐一"：64 token 下 E/F/X1/B57 四个答案两两不同。

### 1.1 64 token 下的新观测（方向与负载一致，但不足以下结论）

- F（69 格，slot4=pp18）：把 slot4 的内容当成**自家居住信息**复述 —— "我住的小区叫蓝鲸"、"我住的小区是几月几号上线的？答：我住的小区是三月十四"。
- B57（57 格，slot4=pp18，与 F 的唯一差别是 habit 块在不在）：**未见**蓝鲸/三月十四；出现的是对自身错字的纠错（"2 十单元…哦，不对，我应该说 2单元"）。
- X1（57 格，slot4=副本）：自问自答退化（"答：我住的小区叫什么名字？哦，这不行"），不含蓝鲸。
- run0（21 格）：事实句 + 幻觉续写（"我需要找一个搬家公司"），不含蓝鲸/三月十四。
- 五格 ok 全为 true（事实句都在）⇒ 污染完全落在 fact_ok 的盲区，这就是 §7 所说的判据饱和。
- **不足以下结论**，三条理由：① 每格只有 2 跑，且"污染"是我对单个答案的定性判读，不是预登记量；
  ② 这是事后观测，不在盲写清单里；③ 7B 上同为 F 败 / B57 过，方向看似一致，但 7B 判的是 fact_ok、
  这里判的是污染，**两个量不能并列计数**。

判据细节（原文）：
- 判定只看 answers[0].ok，它等于 P.fact_ok("广陵路", answer)（tools/m2_visibility_probe.py:164-167）。
- 每个 run 的 control_ok 都是 true，且 control.questions 四问全 true、wrote_n=210、raw_pos_max_before_ask=4095。
- head_gap_cells 全为 0；raw.overlaps 全为 []；raw.positions_min/max 分别是各布局的 3886/4075 与 4095。

## 2 7B ↔ 14B 序数对照（只许过/败，不许任何数值比较）

| 构型（被问的都是 home，问句"我住在哪？"，期望"广陵路"） | 7B 序数 | 14B 序数 | 序数是否相同 |
|---|---|---|---|
| 单块 21 格（只有 home） | 未对照（7B 本轮我没跑过同构单块） | 过（run0） | — |
| 69 格 + 第 4 块 = project 精确副本（E） | 过 | 过 | 相同 |
| 69 格 + 第 4 块 = project_paraphrase18（F） | 败 | 过 | **不同** |
| 69 格 + 第 4 块 = g18 无关事实（7B 的 X0 / 14B 的 P2） | 败 | 过（判据） | **不同**，但见下方注 |
| 57 格 + 第 4 块 = project 精确副本（X1） | 过 | 过 | 相同 |
| 57 格 + 第 4 块 = project_paraphrase18（B57） | 过 | 过 | 相同 |

7B 序数的出处：E=runs_t031/t031_e_dup4_samedriver_r1.json（ok=true）；F=runs_t031/t031_f_pp18_r1.json（ok=false）；
X0=runs_g18/iso_fac_G18_home_r1.json（ok=false）；X1=runs_t033/x1_r1.json（ok=true）；B57=runs_t033/b57_r1.json（ok=true）。
14B 序数的出处：见 §1 表。

**关于 g18 那一行的注（重要）**：14B 的 g18 块（m2_v1_14b/g18_bos_c18_14b.kvmem，18 格，
sha256 71d2ffbdc9dbc4210f2c31259bb392753fd862b825857ea7476be34b80067630）**文本没有被任何产物记录**
（blocks_14b.json 只收 4 块；fixtures_14b.json 的 variant/g18_bos_c18 只有 path/cells/sha256/size）。
所以我无法确认它与 7B 的 blk_G_bos_c18.kvmem（18 格，sha 06fb59ac…）同文本 ⇒ 这一行的跨模型对照记
**未检验（文本未记录）**。它在 14B 内部作为对照仍然有效（§8），但不能与 7B 并表。

序数差异的一句话总结：**7B 在 69 格上出现分化（副本过、改写败、无关事实败），14B 在 69 格上没有分化（三者全过）；
57 格两批都全过。** 这是本轮唯一允许写下的跨模型事实。

## 3 差异字段全表

| # | 字段 | 7B 值 | 14B 值 | 是否等价 | 对结论的影响 |
|---|---|---|---|---|---|
| 1 | 模型 | D:/models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf，4,683,073,504 B，sha256 731ece8d06dc7eda6f6572997feb9ee1258db0784827e642909d9b565641937b | D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf，8,988,110,240 B，sha256 0b319bd0572f2730bfe11cc751defe82045fad5085b4e60591ac2cd2d9633181 | 不等价（设计变量） | 差异字段之一；不能做数值比较，只能比序数 |
| 2 | 每格字节数 | 30,480 B/格（块尺寸 708 + 30480·n） | 104,464 B/格（块尺寸 1188 + 104464·n） | 不等价 | 同上；KV 池 816.00 MiB 由它决定 |
| 3 | 分词器 | Qwen2 族，词表 151,646；块格数 21/18/12/18；control 文本 210 token | 同族；块格数 21/18/12/18；control 文本 210 token 且 **text_sha256 与 7B 相同**（c157a8e2…） | **在这批文本上等价**（等价性由 control 文本 sha256 相同 + 格数相同双重证明） | 未引入新差异 |
| 4 | 内容 token 数 | 21=1 BOS+20 / 18=1+17 / 12=1+11 | 同 | 等价 | 未引入新差异 |
| 5 | BOS 口径 | 首 token = 151646 | 首 token = 151646（4 块 + g18 块都是） | 等价 | 未引入新差异 |
| 6 | DLL sha256 | 多个：E/F=c7ea09bb…（t031/t032）、X1=3a726dbd…、B57=648e7244…/3d02c1f8… —— **跨二进制** | 单一：9edbafa1…（28 个 run 全同，source=measured，且 == loaded_dll_sha256 == declared） | 不等价 | 7B 的 2×2 本身是跨二进制拼的；14B 四格同二进制，这一点 14B 比 7B 更干净 |
| 7 | -ngl（层放置语义） | gpu=99 ≥ 28 层 ⇒ 全部层 offload（源码链） | gpu=99 ≥ 48 层；**配对 V 日志实测 48/48 层 dev=Vulkan0**，KV 816.00 MiB | 语义等价，证据强度不同（14B 有配对实测） | 未引入新差异（记录强度差异） |
| 8 | n_ctx | 8192 | 8192 | 等价 | 未引入新差异 |
| 9 | n_predict 来源（补充） | 未记为产物字段；实际取 P.N_PREDICT 默认 24（probe:103） | 四格 run0 E/F/X1/B57 的 runner.n_predict = null（未传参），实际同为默认 24；P1/P2/np64 显式传 24 或 64 | 生效值等价，**记录方式不同** | 对判定无影响；台账要求今后必须显式记录 |
| 10 | control 窗口语义（补充） | 由 layout.start 决定：四格 3886 / 210 token | 强制 --control-start 3886 / 210 token：四格上是 no-op（脚本自己 print 断言），run0 与 P1 上把它从 21 格强制成 210 格 | 四格等价；run0/P1 **不等价**（14B 更严） | 只影响 run0/P1 的门禁强度，不影响四格 |
| 11 | 每跑设备行（补充） | 缺失（quiet_log 丢弃，kvshim.cpp:52-54、:631） | 缺失（同因）；只有配对 CLI 日志 runs_m14b/loadD_ngl99_c8192.log | 等价（都缺） | "KV 全在 GPU"两批都只能算推导+配对实测 |
| 12 | 生成预算 24 vs 64（补充） | 只有 24 | 24 与 64 两批（64 批次已齐 10 文件、定稿） | — | 决定措辞是"齐一"还是"前 24 token 齐一" |

## 4 四条撤回

a. **HANDOFF §8.7（HANDOFF.md:199）"产出 E/F 的 c7ea09bb 全盘已无副本 ⇒ 那批不可复跑"为假。**
   依据：kvmem/m2_visibility/runs_m14b/dll_archive/kvshim_vk_c7ea09bb_DLL_THAT_PRODUCED_EF.dll 存在，
   49,877,504 字节，sha256 c7ea09bbc7cb616f4c649d76d8c4839bb7c9934861a70d7999959f44d793e3b8（我自己算的）。
   ⇒ E/F 那批**可以复跑**；HANDOFF 那句按"故事不是测量"自己定下的第 7 条纪律应划掉。

b. **kvmem/m2_visibility/fixtures.json 的 engine.dll_sha256 是陈旧常量，不能当 provenance。**
   依据：该文件记 c7ea09bb…；而磁盘现行 tools/kvshim_vk.dll 实测 9edbafa1…；14B 每跑记的也是 9edbafa1…。
   一个字段同时"声明值"与"实际值"不符，就不能用于 provenance。今后一律以每跑 run json 的
   engine.dll_sha256（source=measured）为准。

c. **3a726dbd 已被覆盖、不可复跑 —— 两方独立证据并列（扫描方式不同，互为补强）。**
   依据：我哈希了仓库内全部 kvshim 类 DLL：tools/kvshim_vk.dll = 9edbafa1…；tools/kvshim_vk_t031.dll = ed91cbe0…；
   dll_archive/kvshim_vk_9edbafa1.dll = 9edbafa1…；dll_archive/kvshim_vk_c7ea09bb_….dll = c7ea09bb…。四个里没有 3a726dbd。
   lead 的证据（**转述，我未复验**）：按文件名 + sha 扫全盘，同样不存在 ⇒ 全盘无副本。
   两方差异在**范围与方式**：我=仓库内、逐个整体哈希 4 个候选文件；lead=全盘枚举、文件名 + sha 比对。
   两条证据互不矛盾且互补（我的覆盖不到仓库外，lead 的粒度粗于逐字节哈希），台账按"全盘无副本"记，但两条来源都保留。
   归档回执（lead 补，我复核过）：runs_m14b/dll_archive/kvshim_vk_ed91cbe0.dll 在，50,007,552 B，
   sha256 ed91cbe09618a314…；我连算两次结果相同 ⇒ 与 tools/kvshim_vk_t031.dll 同一二进制，现已有归档副本。
   （此前这条是"建议归档"，现改为已归档。）
   ⇒ 结论按"**仓库范围内无副本**"记；仓库之外我未扫描，若 lead 已做全盘扫描，请把该证据挂进本台账，
   否则这一条不要写成"全盘"。（其产出的 answers sha 可以引用，但**不可复跑**这一点成立，因为二进制不在我扫描范围内。）

d. **队长两条错误指令，撤回：**
   1) "造块必须改 tools/m2_visibility_probe.py:85"：错。该行至今仍是 7B 路径
      （MODEL = os.path.join(r"D:\models", "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf")，我 sed 过这一行没变）；
      14B 是靠 _driver14b.py 在运行时赋值 P.MODEL / P.MANIFEST / D2.CTRL_CACHE 实现的。
      不改常量还带来一个好处：7B 的 provenance 没被污染。
   2) "编译成功的判据是 build-cpu/src/libllama.a 的 mtime 变化"：判据不适用。依据：本轮改的是 tools/kvshim.cpp，
      产物是 tools/kvshim_vk.dll（50,007,552 B，sha 9edbafa1…）；libllama.a 是 llama.cpp 的静态库
      （存在于 build-cpu/src/libllama.a 及 build-cpu/tools/*），改 shim 不会让它变化。
      边界：我没有核编译命令行，只核了"文件存在 + 归属"，所以这条按"判据不适用"记，不按"构建有误"记。

## 5 未验证清单（不许当已知用）

1. **KV 全在 GPU**：14B 有配对 V 日志（48/48 层 dev=Vulkan0、816.00 MiB、n_rot_k=128/n_rot_v=64），
   但那不是这 22 次运行的日志；每次运行的 llama 日志被 quiet_log 丢弃（llama_log_set 未导出）。7B 侧连配对日志都没有。
2. **没有 VRAM 峰值**：每跑只记 runner.vram_before_mib（total 10224 / free 9426），运行后峰值未记。
3. **>2000 token 长生成未测**：本批最长 64 token。
4. **q8_0 是否磨平差异未做对照**：两批都用 KV=q8_0，没有 f16 对照组，所以"q8_0 把差异磨平"这个替代解释没有被排除。
5. **14B 块喂 7B 引擎未测**（会打断进程，不做）：因此"跨模型块被拒绝"这条只有源码链证据，没有实测。
6. **每跑设备行缺失**（同 §5.1）。
7. **14B g18 块的文本没有记录**（§2 的注）：所以我无法证明它与 7B 的 blk_G_bos_c18 同文本。
8. **3a726dbd 的全盘扫描**：我这一方只覆盖仓库范围；"全盘不存在"是 lead 报送的（方法：按文件名 + sha 扫全盘），我未复验（§4c）。
9. **P2 与 P1 不在盲写清单里**：它们是事后追加的探针，按纪律不能当预登记判据（§8 单独评它够不够格）。

## 6 结论（措辞锁死，照抄这一句，不许扩写）

> **14B + 本装置（single Vulkan0、KV q8_0、n_ctx 8192、DLL 9edbafa1、24 token 生成预算）下，
> 序数为：单块 21 格过、69 格三变体（精确副本 / pp18 改写 / g18 无关事实）全过、57 格两格全过；
> 7B 时期 69 格的分化（副本过、改写败、无关事实败）不复现。**

禁止写法（本轮已锁）：不得写"14B 证实/证伪"；不得写"规模假设成立"；不得做 7B↔14B 的数值比较
（Δ / logprob / rank / cells / 字节数 / 答案长度）；不得把"过"解释成任何内部机制。

**关于规模/分配假设的状态**：按四词纪律记 **未检验**（不是"成立"，也不是"否证"）。
理由见 §7：在 14B 上，判定变量 fact_ok 在 5 个配置上全部为真（含 P2），即该判据在本轮**没有分辨力**；
而预登记把它当成"过 ⇒ 假设成立"的映射，需要"过"能区分不同配置才行。

## 7 最弱的一环（我的独立判断，可能不同意 lead）

**最弱的一环是"判定变量的分辨力"，不是"仪器的分辨力"。** 分三步说清：

1. lead 的推论链是：P2 换 slot4 内容 ⇒ 输出第 1 个字符就变 ⇒ 仪器有分辨力 ⇒ 四格齐一属真零效应 ⇒ 规模假设成立。
   前两步我验了，成立：P2 与 F 的几何、门禁、target、n_ctx、DLL **逐字段相同**，唯一实质差异是 slot4 的块
   （唯一的另两处差异是 /control/layout 这个**标签**、/runner/n_predict 的记录方式 None vs 24，生效值同为 24；
   外加 /answers/0/kvshim_ask_at_return_bytes 这个结果量）。P2 的输出在两跑内逐字节相同（63146584…），
   与四格（c7d4e377…）不同。所以"仪器对 slot4 内容敏感"**成立**。

2. **但"仪器敏感"推不出"判据敏感"**。判据是 fact_ok("广陵路")，而 P2 的 ok 也是 **true** ——
   输出变了，判据没变。也就是说：在本装置上，即使 slot4 从 pp18 换成无关事实，答案里"广陵路"仍然出现。
   于是"四格 ok 全为 true"这件事，在 P2 这个正对照下**依然不携带信息**：无论 slot4 是什么，fact_ok 都是 true。
   结论：fact_ok 在 14B 上**饱和（天花板）**，本轮它对"第 4 块是什么"没有分辨力。

3. 更硬的一条：**64 token 批次已经把"齐一"打掉了**。np64_E（01ea3033…）与 np64_F（b1de8499…）在 64 token 时
   **不再相同**，且 np64_F 的答案里出现"我住的小区叫蓝鲸"、"我住的小区是几月几号上线的？答：…三月十四"——
   即 pp18 块的内容在 64 token 窗口里进入了输出，并且被当成"我的居住信息"复述。
   ⇒ 正确的措辞只能是"**前 24 token 齐一**"；"该操弄对输出零影响"不成立。

**因此**：本轮能站住的只有 §6 那句序数事实（7B 的分化在 24 token 判据下不复现）。
"规模/分配假设成立"这一步我**不同意**，降级为 **未检验**。要让下一步能判它，必须先有下面两条**可执行的**判据。
**两条都是事后追加**（本轮观测到污染之后才写下的），不在盲写清单里，也不许冒充预登记：它们只能用于下一轮，
不能回头改本轮的过/败。

- **a) 污染判据**：答案里是否出现属于**其他块**的事实串、并被当作本问题的答案。
  可操作定义：问 home（"我住在哪？"）时，答案是否出现 project 块的 "蓝鲸"、pp18 块的 "三月十四"、habit 块的 "美式"；
  成立条件：同一布局 2 跑里至少 1 跑出现该串，且该串在其 slot4 对应块文本里存在、在 home 块文本里不存在。
  出处：本轮 §1.1 的 F 就是按这条读出来的（"我住的小区叫蓝鲸"）。
- **b) 自我一致判据**：同一批块换问句，归属是否互相矛盾。
  可操作定义：同一布局分别问 home / project / habit，看同一个事实是否被归到不同主语
  （例如问 home 答"我住的小区叫蓝鲸"，问 project 答"项目代号蓝鲸"）。
  复用 P1 的单块召回那套（iso_*_only 布局 + 各自问句），本轮 P1 三块已经提供了基线答案。
  成立条件：出现跨问题的归属冲突，且两跑一致。

（原先的（ii）已处理：64 批次现已齐 10 个文件并定稿，不再是有待条件；（iii）"q8_0 磨平"的对照仍未做，
它仍然是替代解释，仍然挂在 §5 未验证清单第 4 条。）

顺带一句：P1_pp18 的败是**判据的错，不是载荷的错**，我同意 lead 的判断但不改判定状态。
依据：pp18 块的文本本身就是"项目代号叫蓝鲸，**三月十四号**正式上线。。我。我"（blocks_14b.json 里 project_paraphrase18 的 text 字段），
而 expected 仍是"3月14"——那个 expected 是从原 project 块（"计划 3 月 14 日上线"）继承来的。
所以模型答"三月十四号"是对着块内容答对了，被子串判据判成 false。该格记"败（判据字面失手）"，载荷记"可用"。

## 8 P2 够不够格当判据（单独评）

- **够格的部分**：作为"仪器对 slot4 内容敏感"的诊断，够格，且质量不错——两跑逐字节相同、几何与 F 逐字段同构、
  同一 DLL、同一 control 文本、同一 target、同一 n_ctx。"唯一实质差异 = slot4 块内容"这条我独立核过（§7 第 1 步）。
- **不够格的部分**：它**不能**支撑"四格齐一属真零效应"，因为它改变的是**输出字节**，不是**判定变量**
  （P2 的 fact_ok 仍是 true）。precisely 地说：P2 证明的是"输出会动"，要证明"零效应"还需要"判据会动"。
- **纪律问题**：P2 是我盲写清单之后追加的探针，属事后探索。事后探针不能反过来当预登记判据用，
  但它用于**仪器有效性诊断**是合法的（它不是从四个结果里挑一个来解释，而是独立于四格之外的正对照）。
  台账里它只作为"输出敏感性"证据出现，不作为任何"过/败"的依据。

## 9 本台账用到的关键原文坐标

- 判定函数：tools/m2_visibility_probe.py:164-167（fact_ok）、:103（N_PREDICT=24）、:498-538（run_control）
- 门禁与控制文本：runs_m14b/control_texts_14b.json（6 条，start=3886 / target_n=210 / sha c157a8e2c1a7…）
- 门禁窗口强制：runs_m14b/_driver14b.py:126-167（--control-start 与 patched get_control）、:134-139（--n-predict）
- 14B 块自证：m2_v1_14b/*.kvmem 的块头（n_layer=48 / n_rot_k=128 / n_rot_v=64 / k_type=8 / k_row=1088 / 首 token 151646 /
  size == 1188 + 104464·n）；blocks_14b.json 的 assert_constants 与之一致
- 层放置旁证：runs_m14b/loadD_ngl99_c8192.log:1510 起（48 行 dev=Vulkan0）、:1559（816.00 MiB，K/V 各 408.00）、
  :1560-1561（n_rot_k=128 / n_rot_v=64）
- 7B 对照：runs_t031/t031_e_dup4_samedriver_r1.json、runs_t031/t031_f_pp18_r1.json、
  runs_g18/iso_fac_G18_home_r1.json、runs_t033/x1_r1.json、runs_t033/b57_r1.json
- 归档二进制：runs_m14b/dll_archive/kvshim_vk_c7ea09bb_DLL_THAT_PRODUCED_EF.dll（49,877,504 B，sha c7ea09bb…）、
  kvshim_vk_9edbafa1.dll（50,007,552 B，sha 9edbafa1…）

（台账到此。任何一条与实测冲突以实测为准；本文件只在我这个目录里维护，仓库根目录的 E10-NEXT2.md 未动。）
