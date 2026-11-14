# out/autonomy600 —— 自主性 SFT 数据 **v2（715 行，当前版本）**，未训练

> v1（600 行，无 should_trigger）已归档在 `v1/`，不要再用。生成：`out/build_autonomy715.py` + `out/autonomy600_data.py`（seed 60000，CPU only）。

## 交付

| 文件 | 说明 |
|---|---|
| `train.jsonl` 572 / `dev.jsonl` 72 / `test.jsonl` 71 | **715 行**，每行 `{messages:[system,user,assistant], should_trigger:bool, trigger_reason:str}` |
| `manifest-v2.json` | 计数 / family·category·split 逐行 / 负例率 / should_trigger 计数 / sha256 / 留出核验 / **mapping（M1–M4）** |
| `GATE-v2.json` | G1–G13（全量 + 每 split）；**G10 = PARTIAL，未标 pass** |
| `SAMPLES-v2.md` | 每类 6 条人工抽检（带 should_trigger） |
| `_gate_input_all.jsonl` | 三 split 拼接，仅供门禁一次跑 |

## 标签口径

- `should_trigger=true` = 500 条：A 主动记忆 120 / B 主动追问 100 / C 主动提醒 120 / D 主动发起 160。
- `should_trigger=false` = **215 条**：沉默 95 / 无关 95 / 敏感情绪不播 25（v1 负例池 100 + v2 新池 115）。
- 负例率：train 160/572 = **27.97%**、dev 28/72 = **38.89%**、test 27/71 = **38.03%**，合计 **215/715 = 30.07%**；**每 split 均 ≥25%**。

## 格式映射层（simulator 按此对齐，详见 `manifest-v2.json.mapping`）

- **M1** assistant 为空或 `<SILENCE>` → `trigger=false, content=null`（本批不用该写法，门禁要求 8–60 字）。
- **M2** `should_trigger=false` → `trigger=false, content=null`；assistant 文本只是“对话内最低接话”（≤20 字、无记忆锚点、不追问、不建议），**不得当作待发消息**。
- **M3** `should_trigger=true` → `trigger=true, content=messages[-1].content`（该句即应发出的消息）。
- **M4** 普通接话（只回应当下、不引记忆）→ `trigger=false`，等价 M2。

## 三重留出

train 16 族 / dev 4 族 / test 4 族，test 与 train 族不重叠；`template_id`（类别_族）与负例场景池（v1 34/8/8、v2 92/12/11）同样按 split 切分；`manifest-v2.holdout_check` 全 true，test↔train user 文本重叠 0。

## 门禁（G1–G13，715 行）

`real_fail_rows=0`，`pass_rate=1.0`，退出码 0；G1–G13 逐规则命中 0（G8 仅 1 条数据集级提示：沉默场景文本唯一，非模板重复）。
**G10 = PARTIAL**：行级 (system,user) 唯一性 0 命中；A/C 配额由门校验通过（A 189≥100、C 120≥60）；B/D 配额 **N/A**——门内 classify() 把带记忆块问句一律判 C，且 D 需 user 含“主动/请”（与 G1 冲突），不可测，故不标 pass。

## 复现

```bash
python -X utf8 out/build_autonomy715.py      # 生成 + 自检（族/模板/锚点/长度/触发标注/唯一性）
python -X utf8 out/compose_gate_v2.py        # 跑 G1–G13，合成 GATE-v2.json
```