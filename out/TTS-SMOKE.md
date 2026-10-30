# TTS 冒烟（纯函数，不起服务）

- 时间：2026-10-31 · 方式：直接调用 `tts_sapi.synthesize(...)`；**未启 8765/8766、未写 daily、未 commit**。
- 环境：Windows SAPI `System.Speech` 可用；`speak=False`，**播放未验**（不依赖声卡）。

## 1 正常合成

```python
tts_sapi.synthesize("你好，这是冒烟测试。", enabled=True,
                    out="out/tts/smoke.wav", speak=False)
```

| 项 | 结果 |
|---|---|
| ok / invoked | true / true |
| wav | `out/tts/smoke.wav`（存在） |
| bytes | 136,250 |
| sha256 | `70776087f175d91952f537ed2e43acc912fde2f9ddc750e661d9f4f4fef1ebe9` |
| latency | 1620 ms（含 PowerShell 启动） |

## 2 敏感文本（必须 skipped、不产 wav）

```python
tts_sapi.synthesize("我的手机号是13910002010，密码是 123456。", enabled=True,
                    out="out/tts/smoke-sensitive.wav", speak=False)
```

| 项 | 结果 |
|---|---|
| invoked | **false** |
| skipped | **sensitive** |
| wav | **未生成**（`smoke-sensitive.wav` 不存在） |

- 敏感规则含：手机号/手机号码、11 位手机号、密码/口令/验证码、身份证、银行卡/卡号、
  16–19 位长数字、`secret` / `api key` / `token=`。
- 同步补了单测 `skip_phone`：**18/18 通过**。

## 3 结论

- 纯函数冒烟 PASS；默认 only-wav、不播放；敏感/拒答/SILENCE 不合成。
- 未做：播放验证（需声卡）、服务接入、QQ 桥、音色调优。
