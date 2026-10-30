# TTS SAPI 最小落地（本地、默认 off、未接服务）

## 1 交付
- `tools/tts_sapi.py`：Windows `System.Speech` 本机合成；写 wav；`--speak` 才播放。
- `tools/test_tts_sapi_cpu.py`：17 项 CPU 单测。
- 默认：库函数 `synthesize(..., enabled=False)` → **零调用**；CLI 只写 wav、不自动播。
- 未接入 `chat_service` / QQ 桥；QQ 语音当前只产 wav 文件。

## 2 用法
```
python -X utf8 tools/tts_sapi.py --text "最终答案" --out tmp/tts/a.wav
python -X utf8 tools/tts_sapi.py --text "最终答案" --out tmp/tts/a.wav --speak
python -X utf8 tools/tts_sapi.py --text "..." --json      # 机器可读
```
可选：`--max-chars`（默认 500）、`--rate`（-10..10）、`--voice`；缺 `--text` 读 stdin。

## 3 安全边界
- **只读最终答案文本**；模块不 import sqlite / memory_source，不触碰块与记忆原文。
- 拒答（`记不清/不知道/无法…`）、`SILENCE`、敏感（密码/验证码/身份证/银行卡/16–19 位长数字/secret/token）→ 不合成、不播放，返回 `skipped`。
- 无网络、无云 TTS、无音色训练；清洗去掉 think/代码块/URL/Markdown 与控制符，超长按句末截断。

## 4 实测（本机，SAPI，默认不播）
| 项 | 结果 |
|---|---|
| 95 字答案 | wav 1,027,834 B；延迟 1493/1161/1256 ms（中位 **1256 ms**） |
| 10 字短句 | wav 140,000 B；1312 ms（含 PowerShell 启动） |
| 1200 字 | 截断到 493 字，`truncated=true` |
| 拒答/SILENCE/密码 | `invoked=false`，skipped=refusal/silence/sensitive |

## 5 测试
- 新增单测：**17/17 通过**（清洗、截断、跳过、disabled 零调用、无 DB 依赖）。
- 全量 `tools/test_*_cpu.py` 40 个：**37 通过**；3 个既有失败，与本次新增文件无关（未改产品代码）：
  - `test_chat_daily_cpu` 1/93（T11.think_unclosed）
  - `test_policy_web_cpu` 3 项
  - `test_verify_wiring_cpu` 1/42
- 未 commit、未重启、未改产品默认。

## 6 限制
- `--speak` 依赖本机音频设备；无声卡环境只写 wav。
- 未做音色/语速调优、未接服务与 QQ 桥；SAPI 中文音色取决于系统已装 voice。
