# QQ Bridge（NapCat / Lagrange → 本地助手）

把本机的助手 HTTP 服务（`http://127.0.0.1:8765`）接进 QQ。CPU-only、纯标准库、默认不联网；
QQ 侧通过 **OneBot v11 反向 WebSocket** 与 NapCat / Lagrange 等第三方协议端通讯。

> ⚠️ **风险披露（先读）**
> - 使用 NapCat / Lagrange 等**第三方协议端**接入 QQ，属于非官方客户端，**可能被封号、可能违反腾讯用户协议**。
> - **不要用主号**。请使用**小号**自测，并假设该号随时可能被限制/封禁。
> - 本工具不做任何协议逆向，只对接 NapCat 已实现的 OneBot v11；封号/ToS 风险由使用者承担。
> - 机器人回复与记忆内容可能被群成员看到；不要在群里喂隐私数据。

---

## 1. 组成与数据流

```
QQ 用户 ──> QQ 服务器 ──> NapCat(协议端) ──OneBot v11 反向 WS──> tools/qq_bridge.py
                                                                     │
                                                                     ├─ POST /ask        {"text": ...}   → 回答
                                                                     ├─ POST /remember   {"text": ...}   → 记住
                                                                     ├─ GET  /memories                     → 记忆列表
                                                                     ├─ POST /forget     {"id": ...}     → 删除
                                                                     └─ GET  /status                      → 状态
                                                                     ↓
                                                          回复消息（send_group_msg / send_private_msg）
```

文件：

| 文件 | 作用 |
| --- | --- |
| `tools/qq_bridge.py` | 适配器主程序（bridge） |
| `tools/qq_bridge.example.json` | 配置样例（复制成 `tools/qq_bridge.json` 再改） |
| `tools/test_qq_bridge_cpu.py` | CPU-only 测试（mock WS + mock 助手，零外网） |
| `docs/QQ-BRIDGE.md` | 本文档 |

## 2. 安装与配置 NapCat（Windows）

1. 下载 NapCat（<https://github.com/NapNeko/NapCatQQ> 的 release；或用 NapCat Installer）。
   本机路径示例：`D:\NapCat\`。
2. 启动 NapCat，用**小号**扫码登录。
3. 打开 NapCat 的「网络配置」，启用 **WebSocket 服务器**（给 bridge 主动来连的接法叫 *反向 WS*，
   指 NapCat 作为服务器、bridge 作为客户端；若用 NapCat 的「WebSocket 客户端」则改成 bridge 监听）。
4. 记下 **端口**（默认常用 `3001`）和 **token**（自己设一个随机串，不要留空、不要用 `CHANGE_ME`）。
5. 建议只监听 `127.0.0.1`，不要暴露到公网/局域网；token 与端口不要发到群里或截图外传。

### 两种接法（bridge 配置 `mode` 切换）

| NapCat 侧 | bridge `mode` | bridge 配置 | 谁连谁 |
| --- | --- | --- | --- |
| WebSocket **服务器**（端口 3001，带 token） | `forward` | `ws_url: "ws://127.0.0.1:3001/?access_token=<token>"` | bridge 连 NapCat |
| WebSocket **客户端**（连到 bridge） | `reverse` | `ws_host` / `ws_port`（默认 8766）、`token` | NapCat 连 bridge |

> OneBot v11 的鉴权：`Authorization: Bearer <token>` 或 URL 参数 `?access_token=<token>`，两者 bridge 都接受。

## 3. 配置 bridge

```bash
cp tools/qq_bridge.example.json tools/qq_bridge.json
```

最小改动：
- `mode`：`reverse`（默认，NapCat 连 bridge）或 `forward`
- `token`：与 NapCat 侧一致（随机串）
- `ws_url` / `ws_host` / `ws_port`：按上面的接法填
- `http_base`：本地助手地址，默认 `http://127.0.0.1:8765`
- `trigger_mode`：群聊触发方式
  - `at`（默认）：仅 @机器人 时响应
  - `prefix`：仅消息以 `prefix`（默认 `/`）开头时响应
  - `both`：两者任一
  - `none`：群聊完全不响应（只私下聊）
- `allowed_groups`：`[]` = 所有群；填群号列表则只响应这些群
- `admin_qq`：`[]` = 所有人可 `/remember` `/forget`；填 QQ 号则仅管理员可用这两条
- `timeout_s`：单次问答应答超时（建议 30–120；默认 60）
- `reply_max_chars` / `reply_max_parts`：长回答分条阈值（默认 600 字/最多 4 条）
- `log_dir`：元数据日志目录（默认 `kvmem/qq_logs/`，**只记时间/群号/是否命中**，不记正文）

启动：

```bash
# 反向（NapCat 连 bridge）
python -X utf8 tools/qq_bridge.py --config tools/qq_bridge.json --mode reverse

# 正向（bridge 连 NapCat）
python -X utf8 tools/qq_bridge.py --config tools/qq_bridge.json --mode forward
```

命令行可覆盖配置：`--ws-url`、`--ws-host`、`--ws-port`、`--token`、`--http-base`、
`--trigger-mode`、`--prefix`、`--allowed-groups 123,456`、`--admin-qq 789`、`--timeout 45`、
`--verbose` 等（`--help` 查看全部）。

## 4. 启动顺序（推荐）

1. 先起**本地助手服务**（`127.0.0.1:8765`），确认 `curl http://127.0.0.1:8765/health` 正常。
2. 起 **NapCat**，确认小号在线、WS 服务器/客户端配置正确。
3. 起 **bridge**：看到 `WS 已连接` / `reverse 模式：WS 服务器监听 ...` 即就绪。
4. 用小号在**单聊**里发「你好」自测；再拉一个测试群 @ 机器人自测。

## 5. 命令

| 命令 | 作用 | 谁可用 |
| --- | --- | --- |
| 直接说话 | `POST /ask`，返回助手回答 | 所有人 |
| `/remember <内容>` | `POST /remember`，写入记忆 | 所有人 / 仅 `admin_qq` |
| `/memories` | `GET /memories`，列出最近的记忆 | 所有人 |
| `/forget <id>` | `POST /forget`，删除指定记忆 | 所有人 / 仅 `admin_qq` |
| `/status` | `GET /status`，服务状态 | 所有人 |
| `/health` | `GET /health` | 所有人 |
| `/help` | 帮助文本 | 所有人 |

群聊里：`@机器人 /status`、`@机器人 你好`；或前缀模式 `!你好`（`prefix` 可改）。

## 6. 行为与边界

- **单会话串行**：同一群 / 同一私聊的上一条回答完才处理下一条；不同会话可并行。
- **超时**：`timeout_s` 内没有回答 → 回执「（本地助手超时 …）」，不会吞消息。
- **错误回执**：助手 500 / 连不上 / 返回非 JSON → 回执「（本地助手错误…）」；NapCat 发送失败会记日志不重发。
- **长回答**：按 `reply_max_chars` 分条发送，最多 `reply_max_parts` 条，超出部分截断并标注。
- **不落盘敏感内容**：`kvmem/qq_logs/bridge-YYYYMMDD.jsonl` 仅含
  `ts / kind / group_id / user_id / hit / command / error`；**不写消息正文、不写回答正文**。
- **不联网**：除本机助手与 NapCat 的 localhost WS 外，bridge 不发起任何外网请求。
- **图片/语音/文件**：当前只处理文本消息段；其他消息段忽略（不报错）。
- **CQ 码**：命令解析优先用 `message` 段的 `text`，回退 `raw_message`；不做 CQ 码执行。

## 7. 测试（零 GPU / 零外网）

```bash
python -X utf8 tools/test_qq_bridge_cpu.py -v
```

覆盖：收消息→调 `/ask`→回包、四个命令、@/前缀/白名单触发、超时回执、500 回执、
助手不可达、断线重连退避、同会话串行、长回答分条、日志脱敏、反向模式（含坏 token 拒绝）。
测试只用本机 mock（`http.server` + asyncio WS），不连真 QQ、不调真助手、不读冻结件。

## 8. 排错 Checklist

| 现象 | 检查 |
| --- | --- |
| bridge 起不来 / 端口占用 | `netstat -ano | findstr :8766`，换 `ws_port` |
| reverse 模式 NapCat 连不上 | NapCat 的 WS 客户端地址是否 `ws://127.0.0.1:8766/`；token 是否一致；本机防火墙是否拦 localhost（一般不会） |
| forward 模式一直重连 | `ws_url` 端口/token 是否对；NapCat 的 WS 服务器是否启用；看日志退避间隔是否在增大 |
| 收不到群消息 | 群是否在 `allowed_groups`；`trigger_mode` 是否需要 @；机器人是否被禁言/被踢；NapCat 是否掉线 |
| 单聊正常、群聊不答 | 多半是 `at` 触发：确认 @ 的是机器人小号本身（不是同名） |
| 回包「本地助手超时」 | 助手是否卡住；`--timeout` 调大；先 `curl /health` |
| 回包「本地助手错误 500」 | 看助手服务日志；用 `curl -X POST /ask -d '{"text":"hi"}'` 复现 |
| 分条太碎/太少 | 调 `reply_max_chars`、`reply_max_parts` |
| 想彻底停掉 | Ctrl+C；QQ 侧删掉对应 WS 配置；小号退出登录 |

## 9. 安全与合规

- 只监听 `127.0.0.1`；不要把 WS 端口/token 暴露到公网。
- token 用随机串（如 `python -c "import secrets;print(secrets.token_urlsafe(24))"`），不要复用密码。
- 日志里只有元数据；如仍担心，可把 `log_dir` 指到临时目录或定期清理。
- 群聊建议配 `allowed_groups` + `at` 触发，避免刷屏/被举报。
- 再次强调：**第三方协议端有封号风险，使用小号，不要用主号。**