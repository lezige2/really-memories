# 自主性 SFT · 最终结论（2026-10-30 00:35）

## 1 一句话

`<SILENCE>` 标签修复有效（静默召回 96–100%，负例误触发 dev 28→1、test 27→0、合计 55→1），但 **run2 跨族不稳定**：dev 漏触发 54.5%、test 20.5%（差 34pp），acc 65.3% vs 87.3%（差 21.9pp）；按 B 预注册判 **不通过 / do-not-deploy**，不再训 run3。**本窗口无可用自主性交付。**

## 2 数据

| 版本 | 内容 | 结果 |
|---|---|---|
| v2 | 715 行，负例 215（30.07%），但 false 行 assistant 是普通接话 | **RED-02 数据缺陷**：全库 `<SILENCE>` 计数 0/715，模型学不到闭嘴；run1 的 61% 是标签后果 |
| v3 | 仅把 215 条 false 行 assistant 改 `<SILENCE>`，行/切分/字段不变 | 门禁三 split real_fail=0、pass_rate_real=1.0；G2/G8 各 215 条 known_fp（`<SILENCE>` 短答案），与负例一一对应 |

- v3 sha256：train `7594812b…`、dev `b34707b0…`、test `0131c282…`；FREEZE-v3 `45EAF986…`。
- dev/test 各 4 族、每族约 10 条：**±1 条≈10pp，样本量不支持“达标”声明**。

## 3 训练

| run | 数据 | 配方 | adapter sha256 |
|---|---|---|---|
| run1 | v2（缺陷） | r8/1ep/lr1e-4/dropout0.1/7 模块/4bit-nf4 | `b02f38c0…`（exploratory-data-bug，不交付） |
| run2 | v3 | 同上 | `c15e3a2c10f95f024e4b998bf82f147fd1a292d39c61f6c5e6925954bf5ce432` |

- run2 adapter：137,714,904 B，路径 `D:\models\autonomy\run2\adapter`；train_loss 2.27，无 NaN，greedy eval。
- train_loss 不得与历史 SFT 臂（v2 0.2808）横比；数据/任务/损失口径不同。

## 4 评测（预注册三向 + 漏触发）

| split | n | tp | fp | tn | fn | acc | 静默召回 | 漏触发 |
|---|---|---|---|---|---|---|---|---|
| dev | 72 | 20 | 1 | 27 | 24 | 65.3% | 96.4% | **54.5%** |
| test | 71 | 35 | 0 | 27 | 9 | 87.3% | 100% | **20.5%** |

- run1→run2：`pred_silence` 0→51/36；负例误触发 55→1，证明 `<SILENCE>` 监督有效；
- dev 过度沉默坐实：应沉默 38.9%，实际 70.8%（+31.9pp）；
- acc 落差 21.9pp、漏触发差 34pp，单点不成立；3pp 级差异不可判定（1 条=2.3pp）；dev/test 各 4 族×约 10 条，样本量不支持任何达标声明。

## 5 判定（B）

- **不通过**：漏触发是预注册硬指标，dev 54.5% 等于砍掉一半主动性；
- **不许 test-only 报“部分可用”**：跨族不稳定不是能力；
- **不再训 run3**；v3 数据与 run2 adapter 留档，标 `do-not-deploy`；
- simulator 40 条：**N/A（SIM-SPEC v1 缺陷）**——`AUTONOMY-SIM-CASES.jsonl` 只有元数据、无 system/user 输入，`autonomy_trigger_sim.py` 只吃 `--pred` 打分，无法用 adapter 生成 pred；40 条冻结保留、不删、标 `N/A: missing input field`；下一版 cases 必须内嵌输入。
- **D 类内容无据 5/100（15.6%）未验证**：锚点发现“快递该到/望江里安静/陶艺课泥”等 5 条与记忆矛盾或无据，但因 sim 无法跑，**没有实测数据**；报告只能写“未验证”，不能写“已修/无问题”。

## 6 产品影响

- 产品路径不变：现有 14B + KV 记忆 + K2/时间锚点 + verifier v1；**日常使用不靠 prompt/提示词**；
- 自主性 adapter 不进产品、不切默认、不引用为能力；
- TTS 仍只是 D10 规格（CPU/SAPI 先行），未实现；
- 结论不是“自主性不可做”，而是“**当前 SFT 配方在 4 族×10 条的样本上跨族不稳，缺环境/触发器/更多族数据**”；下一窗口需扩族、加负例、按 split 均衡，再谈训练。

## 7 教训

1. 数据标签必须显式包含“沉默”信号（v2 用普通接话，模型学不到闭嘴）；
2. 只看 acc 会被“全触发”刷分；必须报 tn/fp/静默召回/漏触发；
3. dev/test 各 4 族太小，±1 条 10pp；结论只能写 band，不能写“达标”；
4. sim 工具与训练数据格式必须先对齐（本次 cases 无输入，无法生成 pred）。