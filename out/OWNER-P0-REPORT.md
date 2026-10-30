> **状态更新（2026-10-30 16:05）**：本文件 §3 的 `0.7059 < 0.8235 / P0 未通过` 是 **parser 修复前**的快照，不作为最终结论。修复后 n50 off/on 均为 **0.8235**、chain 6/6、泄漏 0 vs 10，详见 `out/OWNER-P0-RETEST.md`；20 档 81/extra/MT20 由 V2f 另行判定。

# OWNER-P0 研究报告（主体抽取，research only）

> 2026-10-30 · 不改产品默认（`--k2-family` 仍默认 off）· 未跑服务 · 未 commit
> 代码：`tools/k2_family.py`（subject_info / 族键按 subject / 研究用 max_rows 旁路）；`chat_daily.py` 本轮未改
> 数据：`kvmem/scale40k/n50/chat.db`（60 块，只读）+ `queries.jsonl` 40 条 + `RESULT.json`（K2-off 实测挂载）
> 明细：`out/OWNER-P0-RESULT.json`

## 1 主体抽取（确定性规则，无模型）

`subject_info(text) -> (subject, source)`，source 取值：

| source | 规则 | 例 |
|---|---|---|
| lexicon | owner 词表（特斯拉/比亚迪/工作号/私人号/父亲…） | 「我的特斯拉是蓝色」→ 特斯拉 |
| self | 首字 我/俺/本人 | 「我养的猫叫豆豆」→ self |
| possessive | 姓氏词表 + 2–3 字名 + 的/家/养的/养/开着/开 | 「张伟的手机号…」→ name:张伟 |
| cooccur | 名字 + 说/那/在/把/给/和/跟/的（同句共现） | 「赵磊说起过，…」→ name:赵磊 |
| none | 无主体 | 「周三的会在三楼」→ none |

族键 = `(subject, predicate)`：query 带 subject 只并同 subject 的行；同 family 下不同 subject 不互相隐藏。
query 无 subject/self 且族内显式主体 >1 → `owner_missing` 回退。

## 2 n50 模拟（40 条，K2-on 旁路 count 门；K2-off 挂载取 RESULT.json）

| kind | with_target | K2-off recall | K2-on recall | 误隐* | 跨主体隐 | 泄漏 on/off |
|---|---|---|---|---|---|---|
| direct | 3 | 1.000 | 1.000 | 0 | 0 | 0 / 0 |
| paraphrase | 4 | 0.250 | 0.250 | 0 | 0 | 0 / 0 |
| chain_last | 6 | 1.000 | **0.667** | 0 | 0 | 5 / 6 |
| negative | 4 | 1.000 | 1.000 | 0 | 0 | 2 / 4 |
| **overall** | 17 | **0.8235** | **0.7059** | 0 | 0 | 7 / 10 |

\* 误隐按 B 定义：被隐块 subject+predicate 与解析主体一致（0 例）。跨主体隐也为 0。
注意：chain_last 的 recall 掉落主要来自“target 既不进 keep_ids 也不进 hidden（被 subject 过滤后不挂）”，不是显式误隐。

Gate 分布：`no_family` 25 / `ok` 7 / `owner_missing` 8；**多主体且 query 判不出主体却返回 ok = 0 例**（gate 正确率 100%）。

## 3 四条件判定（B 定）

| 条件 | 结果 | 判定 |
|---|---|---|
| 50 档 recall ≥ K2-off | 0.7059 < 0.8235 | **FAIL** |
| 误隐 = 0 | 0 | PASS |
| 泄漏不升 | 7 < 10 | PASS |
| 81 / extra / MT20 不回归 | 未跑服务，未验证 | 待 A |

结论：**P0 未通过**（第 1 条不达标），不得推进 P1；K2 保持 off。**51–199 档未验证**（n200 仍走 count 回退）。

## 4 代码 diff 摘要

- 新增 `subject_info()` 与确定性规则（`_SURNAMES`、`_POSSESSIVE_RE`、`_COOCCUR_RE`、`_is_person_name`）。
- `resolve_family` 用 subject 作为族键、per-row 记录 `subject_sources` / `kept_subject_source`。
- `select_k2_ex(..., max_rows=None)` 研究旁路（产品默认仍 50）；`select_k2` 透传。
- 单测：`tools/test_k2_family_cpu.py` 增 `SubjectTests` 5 例（两类车/两类手机/两只猫/同主体更新/source 断言）；全量 `test_*_cpu.py` = 162 OK。
- `chat_daily.py` 未改；未改默认行为。

## 5 预注册（A 记录）

- V2e 预注册不变：81=81/81、MT20≥18、extra≥19。
- P1（产品化）需用户点头 + 备份 + 回滚；本报告不构成 P1 启动依据。
## 6 口径修正（B 2026-10-30）

- **“误隐=0”定义过窄**：它只覆盖“被隐块 subject+predicate 与解析主体一致”；chain_last 中隐藏中间块后模型答旧值，不属于该定义，故 **chain_last 必须单列**，不能写“误隐 0 所以安全”。
- **K2 门控不能写 ≤50**：20 档通过、50 档 recall 0.7059 < off 0.8235、200 档 K2-on 0.368；正确表述：**仅 20 档验证通过；≥50 关闭；51–199 未验证**。
- **81/extra/MT20 未跑**：P0 数字不完整，结论只对 n50 模拟成立，不外推到产品 20 档。
- P0 未通过 → K2 保持 off；P1 需用户批准，A 不自行开工。
