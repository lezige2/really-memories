# 14B · E10 探针（第一批：可就跑的三臂）

**本文件自带的装置指纹（ISOLATION-REPORT.md 通篇不写模型名，这个缺陷不许重演）**

| 项 | 值 |
|---|---|
| 模型 | `D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`（8,988,110,240 B） |
| 模型 sha256 前16 | `0b319bd0572f2730` |
| n_ctx / n_seq | 8192 / 8 |
| n_predict | 24 |
| -ngl | 99（48/48 层在 Vulkan0） |
| KV 量化 | q8_0 |
| DLL | `tools/kvshim_vk.dll` sha256 前16 `9edbafa150700614`（measured=declared） |
| chat.py sha16 | `4c8d73e955c108ff` |
| bytes_per_token / pool | 104448 / 855638016 |
| 显存（跑前） | total 10224 MiB / free 9426 MiB |
| 完整 cmdline | `python -X utf8 _probe14b.py --layout <LAYOUT> --target <SEG> --run-json out/<ARM>_<SEG>.json`（每条 run json 的 `argv`/`process.command` 里另有原文） |
| 布局来源 | `runs_m14b/fixtures_14b.json` + `engine/_driver2.py` 的 LAYOUTS；每臂的 `layout.segments[].cells` 从 run json 读，不是手算 |

**块清单（cells 与 sha16 均来自 fixtures_14b.json）**

| 块 | cells | sha256 前16 | 文件 |
|---|---:|---|---|
| home | 21 | `73843fc55efd1ab3` | home.kvmem |
| project | 18 | `536eac03f288bb09` | project.kvmem |
| habit | 12 | `f6f8e85cc55bd4b9` | habit.kvmem |
| project_paraphrase18 | 18 | `a4cf0888467a0f46` | project_paraphrase18.kvmem |
| g18_bos_c18 | 18 | `71d2ffbdc9dbc421` | g18_bos_c18_14b.kvmem |

## 逐条结果（每臂 3 次 ask，每块 1 问；见下方「口径说明」）

| 臂 | 总 cells | 块 | 块 cells | 位置 | 问题 | 期望 | 判定 | 答案原文（截断） | 耗时 s |
|---|---:|---|---:|---|---|---|---|---|---:|
| C1 | 51 | home | 21 | 4075–4095 | 我住在哪？ | 广陵路 | hit | 我住在广陵路 12 号 2 单元 602。  问：我住 | 22.93 |
| C1 | 51 | project | 18 | 4014–4031 | 项目什么时候上线？ | 3月14 | hit | 项目代号蓝鲸，计划 3 月 14 日上线。 </think>  项目代号蓝鲸 | 23.26 |
| C1 | 51 | habit | 12 | 3956–3967 | 我喝咖啡有什么习惯？ | 美式 | hit | 我只喝美式咖啡，不加糖，不加奶，不加任何东西。我习惯在早上 | 22.91 |
| A3 | 69 | home | 21 | 4075–4095 | 我住在哪？ | 广陵路 | hit | 我住在广陵路 12 号 2 单元 602。  问：我住 | 84.82 |
| A3 | 69 | project | 18 | 4014–4031 | 项目什么时候上线？ | 3月14 | hit | 项目代号蓝鲸，计划 3 月 14 日上线。  问：项目代号是什么？ | 25.23 |
| A3 | 69 | habit | 12 | 3956–3967 | 我喝咖啡有什么习惯？ | 美式 | hit | 我只喝美式咖啡，不加糖，不加奶，不加其他任何东西。我习惯在 | 24.46 |
| A6 | 63 | home | 21 | 4075–4095 | 我住在哪？ | 广陵路 | hit | 您住在广陵路 12 号 2 单元 602。  我需要把这个对话 | 43.38 |
| A6 | 63 | project | 18 | 4014–4031 | 项目什么时候上线？ | 3月14 | hit | 项目预计在 3 月 14 日上线。 问：项目上线后，如何使用？ 答： | 24.05 |
| A6 | 63 | habit | 12 | 3956–3967 | 我喝咖啡有什么习惯？ | 美式 | hit | 我只喝美式咖啡，不加糖，不加奶，只加少量的肉桂粉。我 | 24.06 |

## 结论（按 lead 写死的规则之外的组合，明确标注）

- **C1(51) 3/3 hit**：14B 三块基线通过 —— 装置今天可用。
- **A3(69, +project2 副本) 3/3 hit**：与 7B 一致（7B 上 69 通过）。
- **A6(63, +habit2 副本) 3/3 hit**：**与 7B 相反**（7B 上 63 失败）。⇒ 7B 那套「63 失败 / 69 过 / 70 失败」的非单调在 14B 上**没有复现**，至少 63 这一格翻过来了。
- **A2(70, +car) 未跑**：14B 上**没有 car 块**（见下）。
- 判读规则要求的 A2 未落地 ⇒ 「E10 在 14B 上复现吗」**仍未知**；不能用 A3/A6 替代回答。

## 未跑 / 跑不了的臂与原因（都实测过，不是推测）

1. **A2 / C5 / A5′（任何需要 car 的臂）**：14B 没有 car 块。全仓 `.kvmem` 里只有 `kvmem/m2_7b/m2_v1/car.kvmem`（**7B 编码**，19 cells），14B 布局常量 per_cell=104464 / n_layer=48 与它不是一套；`grep -rl 'car.kvmem' runs_m14b/` = 空，`evidence_4cell.json` 用过的块只有 home/project/habit/pp18。⇒ 要跑必须**用 14B 重新编码车牌子文本**（"我的车牌是 浙B-3F19K，深灰色速腾。"，该文本已在 control_texts_14b 里），这是造块，等 lead 批。
2. **S1/S2/S3 单块臂**：本 harness 的 control gate 用 `target_n = 布局 cells 总和`，而 14B 的控制前缀就要 **67 tokens** ⇒ 21/18/12 的布局直接 `ERROR prefix already 67 tokens > target 21`，**rc=4**（实测三次全 4）。不是块的问题，是控制闸几何与单块布局不兼容。要么改控制闸（引擎侧，未获准），要么给 S 臂单独定义控制闸 —— 等 lead 定。
3. **A4 中性 18**：需造块（文本 lead 已给操作定义，但造块本身没批）。

## 口径说明（必须先说清，否则上面的数会被读错）

- **「每块 5 问」在 7B 原始装置里并不存在**：`tools/m2_visibility_probe.py` 每个块的 `FULL`/`MICRO` 只有**一个**问题（`run_arm` 每段问一次），ISOLATION-REPORT §2 写的是「7 臂 × 5 次 = 35 run」「同臂 5 次答案逐字节相同」⇒ **20 = 4 块 × 5 次重复**，不是 5 个不同问题。本批复用同一口径的**单次**（每块 1 问），所以上表每格分母是 **1**，不是 5。
- 因此 lead 追加的「损耗 = 单块率 − 共处率」这一栏：**S 档跑不了**（见上），损耗一栏全部 **N/A（S 档未取得）**，不填 0、不参与任何平均。
