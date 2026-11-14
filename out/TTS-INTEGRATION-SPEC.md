# TTS 集成规格（本机扬声器 + QQ 语音）

> 用户目标：本机播放 + QQ 语音；本地 TTS；尝试阿里开源训练方法（CosyVoice/FunAudioLLM 系）；音色自训。
> 原则：TTS 只接“最终文本”，不读 KV、不改 prompt、不进检索链路；本地优先，回答文本不出本机。

## 1 链路

```
14B → verifier（通过/中性 repair）→ clean_answer
→ tts_sanitize（去 markdown/代码/URL/表情，保留标点）
→ TTS 引擎（本地）
→ 本机扬声器 或 QQ 语音文件（wav/ogg/silk）
```

- 异步：先返回文本，TTS 后台合成；首句流式播放，不阻塞 /ask。
- 缓存：`sha256(voice_id + text)` → 音频文件，重复回答不重合成。
- 静音：`<SILENCE>`、拒答、敏感字段不播报（与 AUTONOMY-TRIGGER-SPEC 一致）。

## 2 引擎分两阶段

| 阶段 | 引擎 | 用途 | 资源 |
|---|---|---|---|
| P0 | Windows SAPI（本地） | 立即可用、零依赖、验证链路 | CPU，<0.2s/句 |
| P1 | CosyVoice2-0.5B（本地） | 音色自定义、质量 | GPU 约 2–4GB；**与 14B 共卡会超 10GB**，需按需加载/CPU/或停 14B 时用 |
| 训练 | CosyVoice 微调/zero-shot | 用户自搞音色 | A10 租期内可训，推理仍本地 |

- 14B 服务占 ~9GB；CosyVoice 不能常驻同卡。P1 先做“按需加载 + 用完释放”，或 CPU 推理（慢），或独立机器。
- 若必须低延迟 + 自定义音色，建议 TTS 单独一张卡/机器；本机 10G 不合适双常驻。

## 3 QQ 语音

- 先确认 QQ 桥是否支持语音消息/文件上传；QQ 语音常用 silk/amr，需要 wav→silk 转码（本地 ffmpeg/silk 编码器）。
- 不支持语音消息时，退化为“发音频文件”或只本机播放。
- 不在 TTS 层做发送；由 QQ 桥的 send API 决定格式。

## 4 接口

```http
POST /tts  {"text": "...", "voice": "...", "target": "local|qq"}
→ {"status":"queued|ok", "audio_path": "...", "cached": true|false}
```

- 只接受最终答案文本；禁止把 KV 块/记忆原文直接送 TTS。
- 审计：text_sha、voice_id、engine、时长、是否命中敏感过滤。

## 5 训练数据（用户自搞音色）

- zero-shot：5–10s 参考音频 + 转写；
- 微调：16kHz 单声道 wav，≥30min–1h，切句 3–10s，附文本；
- 产出：CosyVoice 模型目录 + 推理脚本；本机只加载推理，不训练。

## 6 验收

- 本机：首句延迟 ≤1.5s（SAPI）/≤3s（CosyVoice 按需）；
- QQ：音频可播放、时长与文本匹配、无敏感内容；
- 不回归：/ask 文本路径 P95 不受 TTS 影响（异步）；
- 安全：`<SILENCE>`/拒答/敏感字段 0 播报。

## 7 待确认

- 阿里开源具体仓库/版本（CosyVoice2？Fun-CosyVoice3？）与许可证；
- QQ 桥语音能力；
- 是否接受 CosyVoice 按需加载导致的 2–3s 首次延迟；
- 音色训练数据由用户提供，训练放 A10 还是本地。