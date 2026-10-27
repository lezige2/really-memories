# PREREG-M5-PROBE：36 层 14B Vulkan 的 (a)/(c) 重探（试跑）

> 状态：预登记，**未执行**。只写**当前仍未办**的两个 36 层重探：**(a) 改写对先跑**，**(c) 长生成后跑**。旧 M5 两探针（非 36 层）已跑并判通过，见 `INSPECTOR-M5-STATUS.md`；本预登记**不继承旧读数**，`supersedes: null`，`extends: "M5-(a)/(c) 旧装置"`。
> 判据变更方向：**(a) 改对象（旧 20 对 → 36 层 30 对试跑）**；**(c) 改对象/扩面（旧“编造率/存疑率” → 逐句 leak/false 双率）**。旧 M5 判词保留，不追改。

## 0 装置（写死，不重建）

| 项 | 值 |
|---|---|
| 模型 | `D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` = **8,988,110,240 B** |
| 后端 / DLL | Vulkan；`tools/kvshim_vk.dll` = **`9edbafa150700614` / 50,007,552 B**（**不重建**） |
| 层数 | `n_gpu_layers=36`；必须读回 `n_gpu_layers_readback=36`、`vulkan_imported=true`、日志含 `offloaded 36/49 layers to GPU` |
| 几何 | `n_ctx=8192`、`N_SEQ=8`、`kv=q8_0`、`CHAT_START=4096` |
| 禁止 | 不换模型、不重建 DLL、不改几何；任何替换即 **未接上（装置不合格）**，不是“未通过” |

## 1 角色分离（防“自己既当考生又当阅卷人”）

| 角色 | 谁 | 能做 | 不能做 |
|---|---|---|---|
| **CAND 候选作者** | 独立 executor/agent（**不是** JUDGE/ADJ） | 写 (a) 改写对；跑 (c) 模型生成并**原样**收集；冻结候选文件 | 不能看 JUDGE 结果后改候选；不能改判定器；不能给自己标“正确” |
| **JUDGE 判定器** | 冻结 `m5_ground.py` = **`86b7c501ab9904aa`**，由 **JUDGE runner（inspector 侧）** 执行；CAND 不见其输出直到候选冻结 | 只跑冻结规则，输出 verdict/reason | 不能生成候选；不能改分母；不能看 ADJ 标签后改判 |
| **ADJ 裁决者** | inspector（**不是** CAND/JUDGE） | 对试跑**全部** pair/句做**独立盲标**；先封存标签再比 JUDGE | 不能写候选；不能改 JUDGE；不能看 JUDGE 结果后补标 |
| **LEAD** | lead | 只裁流程/身份/异常；不代替 ADJ 标 | 不能直接把某行判成“通过” |

**判错复核**：JUDGE 与 ADJ 不一致时，由 **LEAD + 第二名未参与候选的复核者**按同一冻结 rubric 复标；**三个标签全部保留**（JUDGE / ADJ / REVIEW），报告 `disagreement` 与 `review_label`。**不得当场改 JUDGE、不得删行、不得改分母**；若 JUDGE 有系统性错误，本轮判 **`判据作废`**，另立预登记 v2。CAND 只能提交源文证据申诉，不能改标签。

## 2 (a) 改写对：先跑

- **样本**：**30 对**（预登记冻结；不足/超出都按实际全报，不许事后挑）。每对 = 原句 + 同义改写句；CAND 写对时**不知道** JUDGE 输出。
- **候选冻结**：`pairs.json` 先落盘并记 sha16；CAND 的“意图标签”（原句是否含无中生有）**单独封存**，JUDGE 只看文本，不看意图标签。
- **判定**：JUDGE 逐对跑；ADJ 逐对盲标；**按对统计**。
- **两率定义（分别报，禁单一准确率）**：
  - **漏判率** = 原句为 unsupported、改写后 JUDGE 判 supported 的对数 / **原句为 unsupported 的合格对数**（先报）。
  - **误判率** = 原句为 supported、改写后 JUDGE 判 unsupported 的对数 / **原句为 supported 的合格对数**。
- **分母与剔除**：总对数 30；**pair-void**（抽取器对改写不稳定、无法判定）单列 `excluded[]` 及理由；**剔除后两个分母分别写**；**原始全 30 对的计数也并列**；禁止只报剔后数字。
- **不设通过阈值**；试跑只回答“装置/判据可用”，不判 M5 质量。

## 3 (c) 长生成：后跑

- **样本（试跑）**：2 题（`addr`、`project`，与旧 evidence 逐字一致）；`n_predict=256`；**目标 20–40 个 counted 句**；若超过 40，**按句序全报，不事后截断**。
- **生成**：每题独立引擎会话；CAND 只收集原文，**不得改句、不得删句、不得重生成挑好看**。
- **切句**：冻结 `m5_ground.split_sentences`；**逐句判定、按句统计**；空段、末句未终止（tail）、重复句的处置**跑前冻结**：tail/空段不进分母并单列；重复句**照判不去重**；模型自问句**不排除**（单列计数）。
- **两率定义（分别报，禁单一准确率）**：
  - **漏判率** = ADJ 判 fabricated 的句中被 JUDGE 判 **非 unsupported**（supported/undecidable/no_fact）的句数 / **ADJ 判 fabricated 的句数**（先报）。
  - **误判率** = ADJ 判 **supported** 的句中被 JUDGE 判 **非 supported**（unsupported/undecidable/no_fact）的句数 / **ADJ 判 supported 的句数**。
  - 另报 `no_fact`、`tail`、`empty`、`duplicate`、`self_question` 计数；**不合成 accuracy/F1/总分**。
- **分母**：总句数、counted 句、两率各自分母、被剔除数及理由（tail/空段/不可判/pair-void）全部列出；**ADJ 盲标先于 JUDGE 结果封存**。

## 4 中止与安全

- **每场景 ≤900 s**（(a) 试跑总时长；(c) 试跑总时长；全量另立）。
- **显存 >8.6 GiB dedicated 熔断**：child 采样 100 ms，超限置 `_m5_stop.flag` 并退出；目标运行 ≤8.0 GiB。
- **父进程绝不发信号**：不 `kill`/`terminate`/`Stop-Process`/`SIGKILL`；只写 `_m5_stop.flag`；child 每 100 ms 轮询并自行收尾。
- **蓝屏/重启**：before/after 记录 `LastBootUpTime` 与 Minidump；`voided_by_reboot=true` ⇒ **判据作废，重跑**。
- **超时/不响应**：超过 900 s 仍未退出 ⇒ 记 `unclean_stop`，标 **装置不合格**；**不补杀、不截取已完成部分当结果**。

## 5 试跑目标与通过条件（只出“装置/判据可用性”）

试跑**不出最终判决**；只有以下 **可用性清单**全绿才允许谈全量：
1. 36 层读回、`vulkan_imported=true`、`offloaded 36/49` 三件齐；
2. (a) 30 对全部有 JUDGE+ADJ 标签，两率分母可复算；无单一准确率；
3. (c) 逐句台账闭合（总句=counted+剔除），两率分母可复算；无单一准确率；
4. 角色分离证据齐（CAND 冻结 sha、ADJ 盲标封存 sha、JUDGE sha 跑前跑后一致）；
5. 无父进程信号、无熔断误触、无蓝屏/重启；
6. `runner_sha16`、`prereg_sha16`、装置 sha 全在产物内。
任一项不满足 ⇒ **装置/判据不合格**，不进入全量；**不得写成“未通过”**。

## 6 产物坐标与四态

- 预登记：`docs/_work/PREREG-M5-PROBE.md`（本文件）。
- 试跑产物：`kvmem/m2_visibility/m5/out/M5-36A-pilot.json`、`M5-36C-pilot.json`；候选/盲标封存：`M5-36A-pairs.json`、`M5-36A-adj.json`、`M5-36C-adj.json`。
- 全量（试跑通过后另立）：`M5-36A-full.json`、`M5-36C-full.json`。
- 四态：
  - **未做**：本轮预登记落盘时；
  - **未接上**：装置/DLL/模型/角色任一不满足，或 JUDGE/切句缺失；
  - **判据作废**：蓝屏重启、熔断、unclean_stop、ADJ 盲标未封存、JUDGE 事后被改；
  - **未通过**：仅在试跑可用性清单失败时用于“装置/判据不可用”，**不是** M5 质量判决。
- **判据作废 ≠ 未通过；未接上 ≠ 未通过。** 试跑通过只表示“可开全量”，不表示 M5 通过。

## 7 执行顺序与旧件关系

1. **(a) 30 对试跑** → 2. **(c) 2 题试跑** → 3. 可用性评审 → 4. 全量另立预登记（(a) 60 对；(c) 4 题）。
- 旧 M5 `(a)`（`be112847`）与 `(c)`（`2fc02488`）**保留为旧装置读数**，不与本 36 层试跑混算；旧判词不改。
- 本预登记遵守 `PROGRESS §13.3`：`(a)` 漏判/误判分开，`(c)` 逐句按句；**不重犯 L1829 的“把 (a) 双率套到 (c)”**。若试跑发现需要改判据，必须**先停、标方向（放松/收紧/改对象）、另立 v2**，不得拿结果改本文件。