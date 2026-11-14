# out/autonomy600 —— 自主性 SFT 数据（600 条，CPU 生成，未训练）

- 规格：`out/SFT-AUTONOMY-DATA-SPEC.md`；seed = **60000**；生成脚本 `out/build_autonomy600.py` + 数据源 `out/autonomy600_data.py`
- 规模：**A 主动记忆 120 / B 主动追问 100 / C 主动提醒 120 / D 主动发起 160 / N 负例 100**（共 600）
- 负例：100 条全部是“**沉默 / 无关场景不得开口**”（沉默 50 + 无关闲聊 50），assistant 只接当下这句，不带记忆、不提醒、不建议。
- 三重留出：train 480（16 族）/ dev 60（4 族）/ test 60（4 族）；**test 族与 train 族完全不重叠**，模板 id（`类别_族`）与负例场景池（34/8/8）同样切分。
- 每行仅 `{"messages":[system,user,assistant]}`（训练加载器只读 messages）；类别/族/来源/负例子类见 `manifest.json` 的 `meta`。

## 文件

| 文件 | 说明 |
|---|---|
| `train.jsonl` / `dev.jsonl` / `test.jsonl` | 480 / 60 / 60 行 |
| `manifest.json` | 计数、族、负例比、sha256、留出核验、逐行 meta |
| `GATE.json` | `out/sft_data_gate.py` G1–G13 结果（all + 每 split + 逐规则通过率） |
| `SAMPLES.md` | 每类 6 条人工抽检样本 |
| `_gate_input_all.jsonl` | 三 split 顺序拼接，仅供门禁一次性跑 |
| `_gate_{train,dev,test}.json` | 门禁分 split 原始报告 |

## 复现

```bash
python -X utf8 out/build_autonomy600.py            # 生成 + 自检（族/模板/长度/锚点/唯一性）
python -X utf8 out/compose_gate_autonomy600.py     # 跑 G1–G13 并合成 GATE.json
```

## system 结构（G9 要求）

`当前时间：YYYY-MM-DD 星期X HH:MM。` + 空行 + `记忆：\n- …\n- …\n- 上次聊到：…` + 空行 + **逐字 SYSTEM_POLICY**（`tools/chat_daily.py`，sha16 见 manifest）。

## 结果

- 门禁：600 行，`real_fail_rows = 0`，**逐行通过率 100%**（G1–G13 命中 0；G8/G10 仅剩数据集级提示，见下），退出码 0。
- 值池全虚构且与 train_v8/v9/v10/v3_autonomy 无重叠（芋圆/仙贝/芒果/泉州/云启/桃酥/柳州/星岩/望江里/龟背竹/雾中灯塔/老聂/灰绿色/池姐/中级会计…）。
- 已知提示（非行级失败）：
  1. G8 数据集级提示“152 个 user 只有 1 种答案”——全部是 D 类沉默场景（场景文本与时钟绑定、每条只出现一次），不是模板重复；按 template_id 域每个模板都有 ≥2 种答案。
  2. G10 数据集级配额 3 行（A/B/D），源于门内 `classify()` 启发式（带记忆块的问句一律判 C；D 需要 user 含“主动/请”，而本规格明令禁止指令式输入），逐行 G10 唯一性命中 0；真实配额见 manifest，已由 `GATE.json.quota_by_manifest` 校验通过。