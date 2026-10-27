# QQ NapCat OneBot v11 反向 WS 配置（llama-mem bridge）

> 只读任务产物：仅新增/备份 NapCat 配置；**未启动 QQ、未登录、未动 E:\Program Files\qq**。
> Token 已写入配置文件，源自 `third_party/qq_token.txt`（32 hex）；本文档**不记录 token 明文**。

## 1 安装与路径

- NapCat Shell 安装目录：`third_party/_napcat_onekey/NapCat.52230.Shell/`
- QQ 内核：`versions/9.9.33-52230/`（QQNT，NapCat 4.18.41 注入）
- NapCat 本体：`versions/9.9.33-52230/resources/app/napcat/`
- 配置目录（实际生效）：`versions/9.9.33-52230/resources/app/napcat/config/`

## 2 OneBot v11 反向 WS 配置

- 文件：`D:\llama-mem\third_party\_napcat_onekey\NapCat.52230.Shell\versions\9.9.33-52230\resources\app\napcat\config\onebot11_3059718036.json`（账号 3059718036）
- sha256：`d1ee16884e5b4f28ebfbcf0ad278a1f603b756edb8b8ad07fca618747df56b9b`
- 文件名符合 NapCat 的 `onebot11_<uin>.json` 查找规则（另 `onebot11.json` 为兜底）。

| 字段 | 值 |
|---|---|
| network.httpServers | [] |
| network.httpSseServers | [] |
| network.httpClients | [] |
| network.websocketServers | [] |
| network.websocketClients[0].name | llama-mem-bridge |
| network.websocketClients[0].enable | true |
| network.websocketClients[0].url | ws://127.0.0.1:8766 |
| network.websocketClients[0].messagePostFormat | array |
| network.websocketClients[0].reportSelfMessage | false |
| network.websocketClients[0].token | 已写入 token（源自 third_party/qq_token.txt，32 hex） |
| network.websocketClients[0].debug | false |
| network.websocketClients[0].heartInterval | 30000 |
| network.websocketClients[0].reconnectInterval | 3000 |
| network.plugins | [] |
| musicSignUrl | "" |
| enableLocalFile2Url | false |
| parseMultMsg | false |
| imageDownloadProxy | "" |
| timeout | baseTimeout 10000 / upload 256 / download 256 / maxTimeout 1800000 |

Schema 依据：`napcat.mjs` 内 onebot11 配置 schema（websocketClients 项含 name/enable/url/messagePostFormat/reportSelfMessage/reconnectInterval/token/debug/heartInterval[/verifyCertificate]）。`verifyCertificate` 为可选（本配置省略，走默认 true；ws:// 明文不影响）。

## 3 备份

- `D:\llama-mem\third_party\_napcat_onekey\NapCat.52230.Shell\versions\9.9.33-52230\resources\app\napcat\config\napcat.json.bak-20261027T165100`（sha256 `28b2416e4579cce687309bc9071df4f41acfe03b3670e0b4a1d81fe46967ff0b`）

## 4 NapCat WebUI（只读核对，未启动）

- `config/napcat.json` 当前**无 webui 段**（仅 fileLog/consoleLog/packetBackend/o3HookMode/bypass）；WebUI 配置独立在 `config/webui.json`，由 NapCat 首次启动时生成。
- 预期访问地址：**http://127.0.0.1:6099/webui**（NapCat 默认端口 6099；首次启动后 `webui.json` 会生成端口/密码/token，需按其实际值与登录态确认）。
- napcat.json 现值（核对）：fileLog=false, consoleLog=true, fileLogLevel=debug, consoleLogLevel=info, packetBackend=auto, packetServer="", o3HookMode=1, bypass 全 false。

## 5 状态

- JSON 可解析、字段齐全已断言；配置文件已原子写入。
- **未启动任何进程**；QQ/NapCat 均未拉起。准备好启动（启动后由 NapCat 读取该 onebot11 配置去连 `ws://127.0.0.1:8766` 反向 WS）。
