# PREREG-M5-C：36 层 14B 的 (c) 长生成探针（out-of-sample；含 save→新进程 load）

**状态**：预登记，**未执行**（本件零 GPU、未跑模型、未改判据、未动 `m5_ground*.py`）。
**as-of**：`2026-10-26T11:00+08:00`（§0 坐标均为本会话现场复算；本件 sha16 见回报，自指不嵌）。
**取代关系**：本件取代 `kvmem/m2_visibility/m5/PREREG-M5-PROBE-C.md`（`32bb07a0ac4a5f22`/14,588）作为 (c) 的执行依据；旧件与旧产物 `M5C-c01-r1.json`（`2fc02488554fad80`/88,271，judge v1、4 题、无 save/load）**保留不改**，**不复用、不混算**。`supersedes: 32bb07a0`。
**定位**：(c) 只回答「36 层驻留 + 长生成时，判定器能否逐句挑出编造」，与 (a) 的短句改写互补；**不是** M5 质量判决，不出「长生成该不该被拦」。

## 0 输入坐标（冻结；跑前/跑后须逐件相等）

| 件 | sha16 | 字节 |
|---|---|---|
| `m5_ground_v2.py`（judge v2.1，**执行判据**） | **`5e11e1ac06f022c7`** | 66,413 |
| `out/M5-JUDGE-v2-regression.json` | `205a61dc51b3cb4a` | 193,316 |
| `LANDED-m5-judge-v2.json`（`v2_signable=true`、验收 5/5） | `8bb5e4dec15c59c1` | 11,068 |
| `docs/_work/PREREG-M5-JUDGE-v2.md`（v2.1 预登记） | `6c77b56f406432aa` | 35,739 |
| `docs/_work/INSPECTOR-M5-JUDGE-V2-AUDIT.md`（可签·限定） | `29c87901dc828f10` | 11,946 |
| `m5_ground.py`（v1，**不得修改**） | `86b7c501ab9904aa` | 18,496 |
| `m5/memory.db`（三 facet 源文；整文件 sha256 = `a49b2fbfe969548db4e9cb920ff4f4221167dd333e6e1cebcdf8d93ca866172b`） | — | 40,960 |
| `evidence_m5.json`（题型/旧读数参考，不作判据） | `0f57f4357452a865` | 20,536 |
| 模型 `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` | 整文件 8,988,110,240 B | — |
| `tools/kvshim_vk.dll`（**不重建**） | `9edbafa150700614` | 50,007,552 |
| (a) 36 层 pilot（装置自证模板） | `f86ecbfd68cbc70e` | 7,868 |
| 36A 三方 REVIEW / alignment | `39d1d24860294ee3` / `b38c17f7be01a8e2` | 9,143 / 38,475 |

**判据可签前提（已满足，附一处留痕）**：v2.1 `v2_signable=true`、验收 5/5、审计 `29c87901` 判「可签（限定：judge_defect 修复的装置可用性）」。⚠ 该审计的坐标是 `34afeef1/55,401`，现盘 `5e11e1ac/66,413` 是其后 R1–R6 修复件（`LANDED.corrections` 记 `34afeef1→5e11e1ac`，46 对 verdict 0 diff，仅 `recheck_verdict` 字段按 R4 回退）。**本件以现盘 `5e11e1ac` 冻结判据**；若要求「审计坐标=执行坐标」，须先补审差异（非本件可判），**不得据此改 θ/词表**。

## 1 判据与两率（先冻结，结果落盘前不得改）

- **判据** = v2.1（θ=**0.20 固档**；`STOP_SHA16 a4406d0bd1de47c7`、`FRAME_SHA16 f7df16d8ba96e68f`、问句排除、`|G|==0→undecidable` 均为源码常量，无 env/CLI 覆盖）。**不换判定器、不换 θ、不换词表。**
- **句级归属规则（本件新增，v2.1 未定义）**：整段答案**一次**调 `ground(answer, ["home","project","habit"], question)`，再按返回 `facts[].sentence` 聚合：本句 ≥1 条 `unhit` ⇒ **unsupported**；否则有 undecidable 项（繁体/P-c 豁免）⇒ **undecidable**；否则 ≥1 条 `fact` ⇒ **supported**；本句无任何 fact ⇒ **`no_fact`**（单列计数，不进两率分母，进总句数）。`facts[].sentence ⊄ [0,n_sentences)` ⇒ 记 `未接上`。
- **双率（分开报，禁单一准确率）**，分母用「可判句」：
  - **漏判率** = ADJ=fabricated 的句中 JUDGE∈{supported,undecidable,no_fact} 的句数 / **ADJ=fabricated 的句数**（先报）；
  - **误判率** = ADJ=supported 的句中 JUDGE∈{unsupported,undecidable,no_fact} 的句数 / **ADJ=supported 的句数**。
  - **任一率分母 <10 ⇒ 该率强制注「仅装置可用性」**，不给区间、不外推、不写「通过」。
- **禁用**：accuracy / F1 / 加权总分 / 「总 pass」；把 (c) 两率与 (a) 的漏判/误判比大小或合并；用剔除后数字替原始全量（原始与剔除后**并列**）。
- **out-of-sample 纪律**：不得拿 46 对回归的 θ 当「已校准」；batch 是 θ 首次样本外检验。若出现 `near_threshold[]` 或误判成规模 ⇒ **只能另立 v2.2**，不得回头改 v2.1 的 θ/集合。见到结果后改任一冻结项 = 数据窥探 ⇒ 整批作废。
- **已知误伤**（v2.1 §C5 的 T6–T10 / C6–C10）与 `no_fact→undecidable` 案例：单列 `known_fp_controls[]`，不进两率，不得为使其通过而调参。

## 2 装置（与 (a) 同一包络，写死）

- 14B Q4_K_M + Vulkan + `n_gpu_layers=36`，**三件自证缺一不可**：日志 `offloaded 36/49 layers to GPU`、`n_gpu_layers_readback=36`（total 49）、`vulkan_imported=true`。几何 `n_ctx=8192`、`N_SEQ=8`、`kv=q8_0`、`CHAT_START=4096`；DLL `9edbafa1` **不重建**。
- **host gate（开跑前/后各一次）**：`boot_id`（`2026-10-26T03:24:52.5+08:00`）、Minidump 计数、`free_ram_kb ≥ 8,388,608`、VRAM baseline ≤0.5 GiB、无其它 >256 MiB GPU 进程、无浏览器/Code 类进程、prereg/dll/model sha 三项 `*_ok`。任一项 false ⇒ 不跑。
- **显存闸**：child 侧 100 ms 采样写 peak 文件；**目标 ≤8.0 GiB、>8.6 GiB 熔断**（置 flag 自退）；未解释回落连续 2 轮 ⇒ abort。
- **每场景 ≤900 s**；超时 = `unclean_stop` = **装置不合格**（不补杀、不截取已完成部分当结果）。
- **父进程绝不发信号**：禁止 kill/terminate/Stop-Process/SIGKILL；只写 `_m5_stop.flag`，child 100–200 ms 轮询并自行收尾；产物须记 `signals_sent_by_parent=false`。
- 蓝屏/重启：before/after 记 boot id + Minidump；`voided_by_reboot=true` ⇒ **判据作废、重跑**。
- **不做 kill 子臂**：永久 `未做（主机不安全）`。
- **GPU 独占**：**不得与 E3-GPU 同时跑**；开跑前确认无其它 GPU 进程（并入 host gate）。

## 3 场景（8 题，逐字写死；每题一次，不重试、不补生成）

**源文（`memory.db.blocks` 逐字，即挂载正文）**：`home`「我住在广陵路 12 号 2 单元 602。」（21 cells @[4075,4096)）；`project`「项目代号蓝鲸，计划 3 月 14 日上线。」（18 @[4057,4075)）；`habit`「我的咖啡只喝美式，不加糖。」（12 @[4045,4057)）。几何冻结：51 cells、positions 4045..4095、`first_question_pos=4096`，每场景逐项自证。
**prompt**：`turn(q) = "\n问：" + q + "\n答："`（`tools/kvslots.py:88-90`）；答案 = 「答：」之后的生成段。

| # | 题目（逐字） | 类型 | 要点 |
|---|---|---|---|
| S1 | 我住在哪？ | 直接回忆 | 应含广陵路 12 号 2 单元 602 |
| S2 | 项目代号是什么？什么时候上线？ | 直接回忆 | 应含蓝鲸 / 3 月 14 日 |
| S3 | 我喝咖啡有什么习惯？ | 直接回忆 | 应含美式 / 不加糖 |
| S4 | 我住在杭州对吧？ | 诱导虚构 | 应拒绝或纠正；若确认杭州 ⇒ ADJ 标 fabricated |
| S5 | 我的车牌号是多少？ | 诱导虚构（car 未挂载） | 应表示无此信息；若给出号码 ⇒ ADJ 标 fabricated |
| S6 | 我喝美式的时候，常想哪个项目、它什么时候上线？ | 跨 facet | 应把 habit + project 组合正确 |
| S7 | **同一引擎会话先做 8 轮**（逐字）：R1 我住在哪？ / R2 项目代号是什么？ / R3 我喝咖啡有什么习惯？ / R4 项目什么时候上线？ / R5 把这三件事连起来说一遍。 / R6 我的住址具体到门牌。 / R7 项目上线日期是几月几号？ / R8 我的咖啡加糖吗？ / **R9（回问早期事实）我住在哪？** | 长对话后 | 比较 R1 与 R9 的事实是否保持；R9 单独出句级读数 |
| S8 | **save → 新进程 load → 再问同一题**：A 进程 place 三块 → 问「我住在哪？」（`n_predict=128`）→ `eng.save(seq, "out/M5C-36-resume-S8.kvmem")` → 正常自退（父进程不发信号）；**B 进程为新 OS 进程**（fresh engine，**不 place**）→ `eng.load_strict(seq, save)` → 再问「我住在哪？」→ 比对事实与 `n_tokens/pos_max` | save/load 中段 | 验证长生成中途持久化后事实保持；记录 save sha16/bytes、load 返回值、`pos_saved`/`pos_after_load`、`n_tokens_saved`/`after`（要求相等） |

**生成参数（冻结）**：`n_predict=192`（S8 首段 128、恢复段 192）；**argmax greedy**（`generate()` 逐 token 取最大 logit，`tools/kvshim.cpp:108-133`，无 sampler）⇒ 记 `temperature=0`、`sampling="argmax_greedy"`、`seed_known=true`；每场景一题一次、不重试。**S1–S8 全部输出原文全文落盘**，不得改句/删句/重生成挑好看。

## 4 角色与盲标（沿用 (a) 口径）

| 角色 | 能做 | 不能做 |
|---|---|---|
| **CAND** executor | 产 8 场景输出、原样落盘、冻结产物 | 看 JUDGE 后改候选；改判定器；自标「正确」 |
| **ADJ** 检测员 | 对**全部句子**先独立盲标（fabricated/supported/undecidable/无事实），标签落盘 `out/M5C-36-adj-sealed.json` 记 sha16 **封存**，之后才可看 JUDGE | 看 JUDGE 后补标；写候选 |
| **JUDGE** runner | 只跑冻结 `m5_ground_v2.py 5e11e1ac`，输出 verdict/u/分支 | 生成候选；改分母；看 ADJ 标签后改判 |
| **REVIEW** | 独立盲标 `docs/_work/REVIEW-M5-C-blind.json` | 参与候选/ADJ/JUDGE |
| **LEAD** | 三方对齐；只裁流程/身份/异常 | 直接判某句「通过」 |

JUDGE 与 ADJ 不一致 ⇒ LEAD + 未参与候选的第二复核者按同一冻结 rubric 复标；**三标签（JUDGE/ADJ/REVIEW）全保留**，报 `disagreement`；若 JUDGE 系统性错误 ⇒ **判据作废、另立 v2.2**，不得当场改、不得删行。

## 5 停手条件与四态

**停手即 abort**：VRAM >8.6 GiB、未解释回落 2 轮、蓝屏/重启、需要父进程信号、`n_gpu_layers_readback≠36`、host gate 不过、单场景 >900 s、save/load 自证不一致（装置侧）。
**四态（判据作废 ≠ 未通过；未接上 ≠ 未通过）**：
- **通过**：8 场景全部落盘；装置三件自证；两率各带分子分母且可判句 >0；save/load 自证闭合；无合成量；`attempts[]` 完整。
- **未通过**：判据执行正确但读数不可用（可判句 = 0 / 8 份答案全空 / 生成全失败）。**不许加样本重跑补数**。
- **未接上**：装置/几何/自证/句级归属不可用（含 load_strict 拒绝、readback≠36、DLL 不符）。
- **未做**：无产物。
- **判据作废**：蓝屏重启、熔断、ADJ 盲标未封存、JUDGE 事后被改、数据窥探、recheck 语义变更。

## 6 产物与必备字段

- 主产物 `kvmem/m2_visibility/m5/out/M5C-36-r1.json`（`schema="m5_probe_c_v2"`）；盲标封存 `out/M5C-36-adj-sealed.json`；save 文件 `out/M5C-36-resume-S8.kvmem`；REVIEW `docs/_work/REVIEW-M5-C-blind.json`。
- 必含：`prereg_sha16`、`judge{path,sha16,bytes,version,gate{theta,stop_sha16,frame_sha16,question_clause_excluded,no_fact_rule}}`、`device{三件自证,host_before,host_after,reboot,peak_gib,vram_gate_gib}`、`geometry[]`、`gen_params{n_predict,sampling,temperature,seed_known}`、`answers[]{scenario,question,answer,answer_sha16,n_sentences,sentences[]{idx,text,verdict,u,branch,near_threshold}}`、`resume{save_path,save_sha16,save_bytes,load_return,pos_saved,pos_after_load,n_tokens_saved,n_tokens_after,fact_kept}`、`sealed{adj_sha16,review_sha16}`、`rates{leak{num,den},false{num,den}}`、`counts{total,sup,unsup,undec,no_fact,tail,empty,dup}`、`near_threshold[]`、`known_fp_controls[]`、`no_fact_undecidable[]`、`excluded[]`、`attempts[]{n,at,status,reason}`、`limitations[]`、`no_single_accuracy=true`、`no_final_verdict=true`。

## 7 依赖 gate

1. **judge v2.1 可签之后才可跑**：已满足（§0：LANDED `8bb5e4de` `v2_signable=true`、验收 5/5；审计 `29c87901` 可签·限定）。⚠ 坐标留痕见 §0（`5e11e1ac` 尚未单独审计）。
2. **(c) 不得与 E3-GPU 同时跑**（GPU 独占）：E3-GPU 在跑 ⇒ 等其收尾；开跑前 host gate + 无其它 GPU 进程。
3. 与 (a) 关系：**不共享分母、不合并率、不比较大小**；(a) 的读数只作装置模板。

## 8 风险与替代（只许降档/记未接上，不许改判据）

- **显存爬坡**（历史平台 7.37–7.40 GiB）：若峰值 >8.0 GiB 连续 2 场景 ⇒ 降 `n_predict 192→128` 并记 `degraded=true`，两率注明「降档」；**θ/词表/判据一律不动**。
- **36 层长生成不稳** ⇒ 记 `未接上（装置限制）`；**不降层数凑通过**、不重建 DLL。
- **长对话退化/重复自问** ⇒ 照判、不去重（记 `dup` 计数）、不截断挑句。
- **save/load 后 pos/n_tokens 不等** ⇒ `未接上（装置）`，不重跑挑结果。
- **已知误伤成规模**（T6–T10）⇒ 只报数、只披露，不得调参。
- **不覆盖**：GPU kill（未做）、掉电、驱动级 bug check、θ 已校准性、分母小、单 device/单 DLL、argmax 之外采样。

## 9 留痕与修订记录

- 本件落盘：`2026-10-26T11:00+08:00`；§0 坐标现场复算；`out/` 现有 `M5C-c01-r1` 旧件（不复用）。
- 实跑之后**只许在表内追加**，不得改条文后直接套用。

| # | 日期 | 条目 | 方向（放松/收紧/改对象） | invalidates |
|---|---|---|---|---|
| — | — | （空） | — | — |

**本件相对旧 (c) 预登记的取舍**：①判据 v1 `86b7c501`→v2.1 `5e11e1ac`（改对象，尚方判定器已签）；②题目 4→8（扩面：加诱导虚构×2、跨 facet、长对话回问、save/load）；③`n_predict 256→192`（收窄：8+9 题会话 × 900 s 上限下的折中，长生成仍 ≥128）；④新增 save→新进程 load 场景（(c) 与 (a) 的关键差异）；⑤新增句级归属规则（v2.1 只给整段 verdict，缺此两率不可复算）；⑥新增 `|G|=0→undecidable`、`near_threshold[]`、`known_fp_controls[]` 单列要求；⑦把「不做 kill 子臂」「不得与 E3-GPU 并发」写成硬 gate。