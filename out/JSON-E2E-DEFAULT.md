# JSON 输出服务级验收 · 默认组（K2 off + v1 + --json-output）

- 副本 `kvmem/json/def`（daily 重建）；TTS off、memories=20；服务已停，未写 daily

| 件 | JSON on | A 基线 | 判定 | P50 | 展示含花括号 |
|---|---|---|---|---|---|
| 81 | **80/81**（fail: w03） | 81/81 | **回归 ❌** | 4.86s | 无 |
| extra | **19/20**（fail: L07） | 18/20 | +1 | 6.2s | 无 |
| MT20 | **12/20**（8 fail） | 11/20 | +1 | 9.24s | 无 |

## parse_fail / json 解析（10 条探针实测）

- **json_ok = 0/10、fallback = 10/10 ⇒ parse_fail 实质 100%**；每条答案都是纯文本回退，模型从未产出可解析 JSON。
- 展示层无花括号（fallback 走 `render_answer` 纯文本渲染），符合“展示无 JSON”，但代价是**该功能完全未生效**。
- eval 产物不采集 `json`/`json_fallback` 字段，故用独立探针取证（`JSON-PROBE-10.json`）。

## 判定

**JSON FAIL**：① 默认组 81 回归 81→80；② parse_fail=100%（要求 0）。⇒ `--json-output` 保持 off。

## 探索组

- **未跑**：默认组已 FAIL 且探索组不得翻案；若要单独看 V9MT11 请另下指令。