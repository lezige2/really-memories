# 08:00 验收页（2026-10-30 00:40）

> 电脑 08:00 断电；以下内容均已落本机 `D:\llama-mem\out\` 与 `D:\models\autonomy\`，不依赖 A10。

## 1 一句话

自主性 SFT 做完了，但**判定不通过 / do-not-deploy**：`<SILENCE>` 标签有效（静默召回 96–100%，负例误触发 55→1），但 dev 漏触发 54.5%、test 20.5%，跨族不稳；本窗口**无可用自主性交付**。

## 2 交付物（本机）

| 项 | 路径 | sha256 |
|---|---|---|
| run2 adapter | `D:\models\autonomy\run2\adapter` | `c15e3a2c10f95f024e4b998bf82f147fd1a292d39c61f6c5e6925954bf5ce432` |
| run1 adapter（exploratory） | `D:\models\autonomy\run1\adapter` | `b02f38c0cd9010e9fbbe68ee36b1f22a565bb706b1bb95ec86b48ec475169495` |
| 最终判定 | `out/AUTONOMY-FINAL-VERDICT.md` | 见 E commit |
| run2 eval | `out/AUTONOMY-RUN2-EVAL.json` | 见 D 日志 |
| run2 train.log | `out/AUTONOMY-RUN2-TRAIN.log` | `99e3c42b…` |
| v3 数据/冻结 | `out/autonomy600_v3/` | train `7594812b…` / FREEZE `AF87B91B…` |
| B 100 锚 | `out/autonomy600/B-ANCHOR-100.jsonl` | `047c5ccf…` |
| sim cases（N/A） | `out/AUTONOMY-SIM-CASES.jsonl` | `2ad36c18…` |

## 3 关键数字

| split | acc | 静默召回 | 漏触发 | pred_silence |
|---|---|---|---|---|
| dev 72 | 65.3% | 96.4% | **54.5%** | 51 |
| test 71 | 87.3% | 100% | **20.5%** | 36 |

- run1（v2 标签缺陷）全触发：pred_silence=0，acc 61%；run2 证明 `<SILENCE>` 监督有效，但 dev 过度沉默（应沉默 38.9%→实际 70.8%）。
- dev/test 各 4 族×约 10 条：±1 条≈10pp，**样本量不支持任何“达标”声明**。

## 4 未决/缺陷

1. **SIM-SPEC v1 缺陷**：40 条 cases 只有元数据、无 system/user 输入，`autonomy_trigger_sim.py` 只能对 pred 打分，无法生成 pred → **sim N/A**；下一版 cases 必须内嵌输入。
2. **D 类内容无据 5/100（15.6%）未验证**：锚点发现 5 条与记忆矛盾/无据，因 sim 跑不了，只能写“未验证”，不能写“已修”。
3. v2 数据 RED-02（false 行用普通接话、无 `<SILENCE>`）已由 v3 修复；v2 不再用于训练。
4. 产品路径未变：14B + KV + K2/时间锚点 + verifier v1；日常不靠 prompt/提示词；未切默认、未 push。

## 5 其他线状态

- **K2/verifier（V2b，干净单进程）**：81 **81/81**、extra **19/20**、MT20 **18/20**；repair 1/121（L09 修好），prompt 审计 `contains_kv_text/hint/expected_value/with_time` 全 False；K2d v1 复核因影子服务事故作废。
- **TTS**：只有 D10 规格，未实现；定案 CPU + SAPI 先行、默认关闭、QQ 语音只播回答不播块原文。
- **40k（更新 2026-10-30 14:02）**：n20/n50 已于 01:11–01:22 建库并出斜率；**n200 首建库遭 K2E runner 污染、已作废并在 8766 隔离重建**——重建后 **200 行 / 200 块 / 200 文件、孤儿 0、零字节 0、缺文件 0、总 token 43,205**，`DATA-AUDIT-n200.json` **ok=true**；n200 k2off 评测进行中（14:01 时 32/40）。
- **E2E**：仍未跑；本窗口让路。
- **开源自主性数据**：HF 直连不通、mirror 大文件超时，未混入。

## 5.1 事故与防复发（2026-10-30 新增）

> 规则正文：`out/EXPERIMENT-ISOLATION.md`（sha16 `56ED2AE0FB01B3BD`）。D 摘要如下。

**RED-03 · 40k n200 被并发实验污染（实验事故，非产品事故）**
- 现象：n200 库在 **8765**（产品端口）上被 **C2 的 K2E runner 重连**后 `/reset`+`/remember` → **200 行→115、200 块→20**。
- 根因：①规模实验复用产品端口 8765 ②旧 runner 未杀 ③服务重启后客户端自动重连 ④**写库前无 DB 指纹门禁**。
- 后果：n200 首建库 + **K2E 首轮数据（n=20 / valid 17 / pass 5 / 29.4%）全部作废，不得引用**。
- 修复：**8766 独立端口 + 独立库**重建（200/200/200，审计 ok），旧数据仅留指纹。

**五条硬规则（防复发）**
1. **端口/库租约**：8765=产品验收（`kvmem/daily/chat.db`）；8766=40k（`kvmem/scale40k/n*/chat.db`）；8767+ 按需。**禁止 8765 跑规模实验**；起服务前写 `out/EXPERIMENT-LEASE.json`（port/db/owner/pid/started_at）。
2. **停/起服务**：停后必须 `netstat` 无 LISTENING **且无 runner/客户端进程**；起后记 PID/uptime/`/health`；**同端口双 PID = RED**。
3. **runner 指纹门禁**：`/health` 校 `model_size=8988110976` + `memories` 预期；直读 DB 校 **rows/sha256 前缀**，**不符即 ABORT 不写库**；`reset/remember` 前再校一次。
4. **数据保护**：评测前 `cp chat.db chat.db.bak-<ts>` 记 sha；污染只能用备份重建，**禁止手改绕过**；**重建后必跑 DATA-AUDIT**。
5. **复盘模板**：时间线 / PID·端口 / 被污染文件+sha / 根因分类 / 修复 / **复发判据**。

**当前环境（14:02）**：**8765 未在跑**（仅 8766 PID 3700 存活）→ 产品服务需按租约重启后做验收；`kvmem/scale40k/n200/chat.db` 被 8766 占用（取 sha 须先停服）。

## 6 8:00 需要你拍板

1. 接受“自主性本窗口不通过”，还是下一窗口扩族（≥10 族×≥30 条）重做数据再训？
2. K2/verifier 是否作为产品候选继续（V2b 81 满分、extra 19、MT20 18，但仍有 V9MT17/18 旧值泄漏）？
3. TTS 是否按 CPU/SAPI 先行落地？