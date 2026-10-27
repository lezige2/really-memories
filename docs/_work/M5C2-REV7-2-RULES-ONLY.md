# M5C2-REV7-2-RULES-ONLY（清盲实现用规则摘录）

> 性质：**派生摘录**，只给"清盲审计者"实现 rev7.2 用；**不含任何验收断言与判定口径说明**，不含读法结论。
> 修订：2026-10-27T11:16 按顾问要求脱敏第 3 行（原稿曾逐项点名验收件，已删）；C2 审计使用的是脱敏前版本，属已披露局限。
> 来源：`docs/_work/RULING-M5C2-B7.md 3dfafd1253f0a833` 的 R3/R4/R5′ 原文；base = `run_m5c2_rev7_1_offline.py 88256d274c9993cc`。
> 要求：实现者只按下列规则改 rev7.1；自行决定"evidence ⊂ 答案句"的读法并在产物中**声明**。

## R3（M1）：闭集归一化

evidence↔源文匹配前做**闭集**归一化，禁止相似度/模糊匹配/阈值：

| # | 归一化项 | 规则 | 例 |
|---|---|---|---|
| N-1 | 全半角 | 全角数字/字母/标点映射到半角 | `４Ｓ店` → `4S店` |
| N-2 | 千分位 | 数字内部逗号删除 | `4,560` → `4560` |
| N-3 | 数字-单位空白 | 数字与单位/量词之间的空白删除 | `2 万公里` → `2万公里` |
| N-4′ | 纯虚词（闭集，收窄） | 只删 `{的, 是}`；`做`/`了` 移出；**只在锚点（数字/实体）±6 字符窗口内删**，不做全文删除 | `做的是 2 万公里保养` → `做2万公里保养` |
| N-5 | 其余空白 | 全部空白删除（仅匹配副本） | `顺 丰` → `顺丰` |

归一化只作用于**匹配副本**，不改写证据/源文原文；表外不允许任何规则。

## R4（M2）：抽取器假阴性

当 item 字面（含 R3 归一化后）在源文出现、且 evidence 非答案句时，**忽略**抽取器的"未提及"标记；逐句记录 `override_count`，产物报总数。

## R5′（M3′）：重定位 + 第四态 `ungrounded`

- `evidence` 仅在能在源文定位到 span 时才算 effective。若 `evidence ⊂ 答案句`：用 **item 在源文中重新定位**；成功 ⇒ 用源文 span 作证据（该 item 记为 present）。
- **第四态 `ungrounded`**：evidence 无法在源文定位（含"仅出现在答案句"且 item 在源文重定位失败）。
- **U1**：`ungrounded` 不计入 absent、不产生 fabricated_evidence 惩罚（不采信，非惩罚）。
- **U2**：supported 必须由 ≥1 条 grounded-supported（有源文 span）的 item 正面支撑；若一句的 item 全为 ungrounded ⇒ 该句判 **not-supported**，reason 记 `all_items_ungrounded`。
- 禁止写成 `absent-soft`（absent 描述模型行为，ungrounded 描述判据的落地状态）。

## 输入/输出

- 输入：`kvmem/m2_visibility/m5/out/M5C2-B5-EXTRACT.json 93505eecc539634a`（只读）。
- 输出：`out/M5C2-REV7-2-CLEANBLIND.json`，含：`reading_declaration`（你采用"整句自证据"还是"任意子串包含"，并说明依据）、`verdicts`（326 句 sid→verdict）、`verdict_map_sha16`、以及两种读法各自的 verdict map sha 与二者 diff。
- 不读：rev7-impl 的 `run_m5c2_rev7_2_offline.py`、`M5C2-REV7-2-DEV.json`（比对阶段除外）、任何验收断言件。