# TTS 本机播放冒烟（不启服务）

- 时间：2026-10-31 · 命令：
  `python -X utf8 tools/tts_sapi.py --text "TTS 本机播放冒烟，一二三。" --out out/tts/playback.wav --speak --json`
- 未启 8765/8766；未写 daily；未 commit。

## 结果

| 项 | 值 |
|---|---|
| 退出码 | **0** |
| ok / invoked / speak | true / true / **true** |
| 延迟 | **5352.3 ms**（含合成 + SoundPlayer PlaySync） |
| wav | `out/tts/playback.wav`，173,066 B，sha256 `f336db301fec1278…` |
| stderr | 空 |

- **SAPI 调用**：PowerShell 脚本实际执行 `Add-Type System.Speech` → `SpeechSynthesizer.Speak($t)` →
  `SoundPlayer.PlaySync()`，整体 rc=0、无异常输出 → 播放调用未被拒绝。
- **音频设备**：系统存在 `Realtek High Definition Audio`、`AMD High Definition Audio`、
  `VB-Audio Cable A` 等。
- **可闻性**：无法从进程侧证明“人耳实际听到”（无声学回采），仅能确认播放 API 调用成功。

## 判定

- 播放调用 **PASS**（若环境无声卡会 rc≠0 并写 stderr；本次未出现）。
- 限制：是否真正出声需人工确认；`VB-Audio Cable` 可能截走默认输出。
