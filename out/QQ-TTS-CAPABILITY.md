# QQ 桥文件/语音能力核查（只读，未写码、未模拟）

结论先行：**不支持**。`tools/qq_bridge.py` 只有**文本**发送路径，没有 image/file/record/voice
任何字段或动作；`out/tts/*.wav` **不能**经桥作为文件或语音发到 QQ。不造旁路。

## 1 发送类型（代码实际支持）

| 类型 | 是否支持 | 证据 |
|---|---|---|
| text | **是** | `send_reply` 只构造 `params={"message": part}`，part 为 str；`send_group_msg`/`send_private_msg`（`qq_bridge.py:870-883`） |
| image / 图片 | 否 | 全文无 `image` 消息段构造；协议声明只用文本字段（`qq_bridge.py:34-35,43`） |
| file / 文件 | 否 | 无 `upload_group_file`/`upload_private_file`/`file` 段；config 无 file 字段（`qq_bridge.py:430-448`） |
| record / voice / 语音 | 否 | 无 `record` 段、无 `upload_*`、无音频字段；grep 无 voice/audio/record 发送路径 |
| video | 否 | 同上，无 video 段 |
| at / reply（收） | 部分 | 仅解析入站 `message` 段里的 `at`/`text` 用于触发（`qq_bridge.py:564-589`） |

## 2 协议与依赖

- 桥是 OneBot v11 客户端/服务端：反向 WS 监听 `ws_port=8766`，NapCat 作为 WS 客户端连入；
  发送仅 `send_group_msg` / `send_private_msg`，`message` 为**字符串**，`auto_escape=false`
  （`qq_bridge.py:34-35, 43, 870-883`）。
- 收发消息段只用到 `at`/`text`（`message_text`/`segments`，`qq_bridge.py:564-589`）；
  `q_bridge` 配置无媒体/上传项（`qq_bridge.py:432-448`，`tools/qq_bridge.example.json`/`.local.json` 同）。
- NapCat：需要（作为 OneBot v11 接入端），但**不需要也不依赖任何上传插件**；即使 NapCat 侧
  支持 `upload_group_file`/record，本桥也没有调用它的代码路径。

## 3 判断

- **能否把 `out/tts/*.wav` 作为文件/语音发到 QQ：不能。**
- 现状只支持把回答**文本**分条发送（`reply_max_chars=600`、`reply_max_parts=4`）。
- 按红线：**不支持即结束，不造旁路**（不改代码、不模拟、不新增上传路径）。

## 4 核查方式

- 只读 `tools/qq_bridge.py`、`tools/qq_bridge.example.json`、`tools/qq_bridge.local.json`；
  未启动桥、未连 NapCat、未写库、未 commit。
