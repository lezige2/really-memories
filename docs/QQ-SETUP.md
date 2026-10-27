# QQ 接入设置（NapCat 反向 WS → 本地记忆助手）

> 目标：把本机助手服务（`http://127.0.0.1:8765`）接进 QQ。**CPU-only**；本文写**本机实际安装位置**与**启动顺序**。
> **只用小号**；NapCat/Lagrange 等第三方协议端可能被封号、可能违反腾讯 ToS，风险自担。
> **禁止把 token / QQ 账号 / 密码写进仓库**（含 README、docs、脚本、配置模板、日志）；token 只走环境变量，配置/凭据留在 `third_party/` 且不入库。

---

## 0 实际安装位置（本机已验证）

| 对象 | 实际路径 / 事实 | 说明 |
|---|---|---|
| **NapCat（隔离实例）** | `D:\llama-mem\third_party\_napcat_onekey\NapCat.52230.Shell\` | 由 OneKey 安装器装入；**独立于用户自己的 QQ** |
| 内置 QQ（QQNT 内核） | 同上目录下 `QQ.exe`；版本 **9.9.33-52230**（`versions\9.9.33-52230\`，含 `QQNT.dll`） | 本目录这一份 QQ 只给 NapCat 用 |
| NapCat 本体 | `…\NapCat.52230.Shell\versions\9.9.33-52230\resources\app\napcat\`（含 `config\napcat.json`） | 配置在 `napcat\config\` 下 |
| 启动器 | `…\NapCat.52230.Shell\napcat.bat`（内部调用 `NapCatWinBootMain.exe`） | **双击或命令行运行它** |
| OneKey 安装器残留 | `D:\llama-mem\third_party\_napcat_onekey\`（`NapCatInstaller.exe`、`QQ.exe`、`NapCat.Shell.zip`、`7z.exe`） | 仅安装用；备份/重装时可复用 |
| **你自己的 QQ** | `E:\Program Files\qq`（`QQ.exe` / `QQEX.exe`） | **未改动**；我们另装隔离实例，互不影响 |
| **bridge** | `tools/qq_bridge.py`（桥）、`start_qq_bridge.cmd`（启动器） | 反向 WS **监听 8766**（`qq_bridge.py` 默认 `ws_port: 8766`） |
| bridge 配置 | `tools/qq_bridge.local.json`（模板 `tools/qq_bridge.local.example.json`） | **当前盘上只有模板**；首次使用需复制并改 |
| 助手服务 | `python -X utf8 tools\chat_daily.py`（或 `start_service.cmd`），`127.0.0.1:8765` | 先起它 |
| WebUI（扫码登录用） | `http://127.0.0.1:6099/webui`（NapCat 控制台默认端口） | 以 NapCat 控制台实际输出为准 |
| token / 凭据 | 存 `third_party/`（如 NapCat 配置/凭据文件），**不入库** | 见 §3/§7 禁写清单 |

> **为什么另装一份 QQ**：NapCat 需要接管 QQNT 实例；用隔离副本避免动用户自己的 QQ 与聊天数据。用户自己的 QQ 继续用 `E:\Program Files\qq`。

---

## 1 文件与前置

| 件 | 作用 |
|---|---|
| `tools/qq_bridge.py` | 桥：OneBot v11 反向 WS ↔ 本地助手 HTTP；纯标准库、默认监听 8766 |
| `tools/qq_bridge.local.example.json` | 配置模板（**复制**成 `tools/qq_bridge.local.json` 再改） |
| `start_qq_bridge.cmd` | 启动器：校验 `QQ_BRIDGE_TOKEN` 环境变量、日志写 `kvmem/qq_logs/bridge.log` |
| `docs/QQ-BRIDGE.md` | 桥的完整说明（数据流/命令/日志字段） |
| 本地助手服务 | `127.0.0.1:8765`（CLI 或 `start_service.cmd`） |
| NapCat（隔离实例） | `D:\llama-mem\third_party\_napcat_onekey\NapCat.52230.Shell\`（§0） |

**一次性配置**：复制模板 → 按需改 `trigger_mode`（`at`/`prefix`）、`prefix`（默认 `/`）、`allowed_groups`（空=所有群）；`timeout_s` 固定 120。
**token 只走环境变量**：`set QQ_BRIDGE_TOKEN=<随机串>`（与 NapCat 反向 WS 的 token 一致；**不写进 JSON/文档**）。

---

## 2 启动顺序（必须按序，四步）

1. **① 助手服务（8765）**：`start_service.cmd`（或 `python -X utf8 tools\chat_daily.py`），等到 `/status` 可用。
2. **② bridge（8766）**：`start_qq_bridge.cmd`，日志出现 `reverse 模式：WS 服务器监听 …:8766`。
3. **③ NapCat**：运行 `D:\llama-mem\third_party\_napcat_onekey\NapCat.52230.Shell\napcat.bat`（= 拉起隔离 QQ + `NapCatWinBootMain.exe`）。
4. **④ 扫码登录**：首次登录用 NapCat WebUI `http://127.0.0.1:6099/webui`（或控制台提示的二维码）用**小号**扫码；登录后 NapCat 主动连 `ws://127.0.0.1:8766`。

> 顺序反了会报 `connection refused 8766`（bridge 未起）或 401（token 不一致）；见 §8。

---

## 3 扫码登录（首次）

1. 先完成 §2 的 ①②，再运行 `napcat.bat`。
2. 打开 `http://127.0.0.1:6099/webui`（端口以控制台为准），按提示用**小号**扫码登录。
3. 登录成功后：NapCat 控制台应显示 QQ 已上线；bridge 日志出现连接/事件。
4. **token 位置**：NapCat WebUI 里配置反向 WS 时填入（与 `QQ_BRIDGE_TOKEN` 同值）；落在 `third_party/` 的 NapCat 配置里，**不要提交/复制进仓库**。
5. 登录态/扫码凭据属于个人敏感数据：**不写文档、不截图入库、不进群聊**。

---

## 4 NapCat 侧反向 WS 配置（WebUI 内）

新建 **「WebSocket 客户端 / 反向 WS」**：

- 地址：`ws://127.0.0.1:8766`（bridge 是服务端，NapCat 主动连它；**不是**让 NapCat 开 WS 服务器）
- token：与 `QQ_BRIDGE_TOKEN` 相同（若只能 URL 传 token：`ws://127.0.0.1:8766?access_token=…`）
- 消息格式：`array` → 启用

---

## 5 验证

**A. CPU 自测（不需要 QQ/服务）**：`python -X utf8 tools/test_qq_bridge_cpu.py` → 预期 `Ran 16 tests … OK`，rc=0（已实测）。
**B. 端口/链路**：`netstat -ano | findstr :8766` 应有 LISTEN；bridge 日志出现反向 WS 连接与事件。
**C. mock 端到端（不需要真 QQ）**：假助手 + 假 NapCat 客户端连 `ws://127.0.0.1:8766` 发群消息事件（@机器人+文本），应收 `send_group_msg` 且含助手回答。
**D. 真号（用户做，小号）**：私聊「你好」→ 固定问候；群里 `@机器人 /status` → 服务状态；`/remember 我的车停在 B2 层 37 号位` → `/memories` 可见；日志 `kvmem/qq_logs/bridge.log` 只应有元数据、**无消息正文**。

---

## 6 停用 / 卸载

1. NapCat 控制台退出/停用该反向 WS 配置（或关 `napcat.bat` 窗口）；
2. bridge 窗口 `Ctrl+C`（或关窗口）；
3. 助手服务按需停止；
4. 清理：删除 `tools/qq_bridge.local.json`、`kvmem/qq_logs/`（保留助手服务与记忆数据不受影响）；NapCat 隔离实例整目录 `third_party/_napcat_onekey/` 可删（**不动** `E:\Program Files\qq`）。

---

## 7 风险与禁写清单（必读）

- **封号/ToS**：非官方协议端，**只用小号**，不用主号；封号风险自担。
- **内容可见**：群回答对群成员可见，别在群里喂隐私；私聊也可能被平台留痕。
- **禁写**：**token / QQ 号 / 密码 / 扫码凭据 / Cookie** 一律**不得**写进仓库（README、docs、脚本、配置模板、日志、提交信息）；只存环境变量与 `third_party/`（不入库）。
- **端口暴露**：8765/8766/6099 只绑回环；不要把端口暴露到公网。
- **token 泄露**：立即换 token 并重启 bridge 与 NapCat 反向 WS。

---

## 8 故障排查

| 现象 | 先查 |
|---|---|
| `connection refused 8766` | bridge 没起 / 端口被改；先跑 `start_qq_bridge.cmd` |
| 握手 401 / 连上即断 | 两侧 token 不一致（`QQ_BRIDGE_TOKEN` vs NapCat 配置） |
| 连不上助手 8765 | 助手服务没起；先 `start_service.cmd` 或 `chat_daily.py` |
| 群里没反应 | 没 @ / `allowed_groups` 不含该群 / `trigger_mode` 与发法不符 |
| WebUI 打不开 6099 | NapCat 未启动或端口被占；看 NapCat 控制台实际端口 |
| 回答被截断 | `reply_max_chars`/`reply_max_parts` 限制；改配置后重启 bridge |