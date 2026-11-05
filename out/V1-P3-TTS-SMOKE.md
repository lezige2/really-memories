# V1 · P3 / TTS smoke（副本、8766）

## P3 边界（新增对照）

| 臂 | 行数 | 新增行 |
|---|---|---|
| **P3 off** | 20→**21** | `id21 mode=chat`「请说“我明天提醒你带伞”」 |
| **P3 on** | 20→**22** | `id21 mode=chat`（同上）+ `id22 mode=assistant_commit` |

- ⇒ **id21 是既有 auto-remember**（P3 关着也写），**不是 P3 副作用**。
- **P3 的真实增量只有 id22 一条 assistant_commit**；普通问答（「我的猫叫什么？」）两臂均零写入。

## TTS（`--tts` on、`--tts-speak` off）

| 项 | 结果 |
|---|---|
| 回答文本 | 「你的猫叫豆豆」——与无 TTS 完全一致 |
| 响应含 `tts` 字段 | 否 |
| wav | `tts-6a95bef14984.wav`，89,960 B，RIFF ✅ |
| sha16 | `fc853885a1033aa8` |
| 播放 | **KNOWN**（未开 `--tts-speak`，按约定不验） |

## 结论
- P3：写入边界清晰（auto-remember + 可选 assistant_commit）；承诺触发可用、普通问答无副作用。
- TTS：落盘与文本一致性符合预期；播放未验，记 KNOWN。