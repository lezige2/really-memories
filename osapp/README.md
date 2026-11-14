# llama-mem OS shell (MVP)

Windows 托盘常驻壳 + 本地服务管理 + 记忆/聊天 UI。**不改模型，不碰 P1 默认**，只做产品入口。

## 现在能跑
```powershell
cd D:\llama-mem\osapp
$env:PATH="C:\Users\lezige\.dsh\dsh-runtimes\dsh-next-primary-runtime\dependencies\node\bin;$env:PATH"
pnpm install
pnpm build
.\start-osapp.cmd
```
`start-osapp.cmd` 会清掉 `ELECTRON_RUN_AS_NODE` 并直接调用 `node_modules/electron/dist/electron.exe`，避免 Electron 被当成 Node 运行。
首次 `pnpm install` 会下载 Electron 运行时（约 239MB，网络慢时需等）。

## 结构
```text
osapp/
  electron/main.cjs      托盘/窗口/服务启停/IPC
  electron/preload.cjs   contextBridge API
  src/App.svelte         对话/记忆/状态/设置
  src/app.css            深色 UI
  src/main.js
```

## 已接
- 托盘：打开/启动/停止/退出；
- 单实例（Electron 默认）；
- 窗口关闭 → 托盘常驻；
- 启动本地服务：调用 `out/ops/launch_service.py`；
- 健康检查：`127.0.0.1:8765/health`；
- `/ask`、`/memories`、`/forget`；
- 开机自启：`app.setLoginItemSettings`；
- 设置：API/模型/数据目录展示。

## 未做
- 安装器（NSIS/electron-builder 已配，未打包）；
- 全局快捷键；
- 剪贴板/屏幕采集（默认不做）；
- 真正的多页路由（当前单 Svelte 组件切换）。

## 注意
- 服务必须用 detached/WMI 方式起，不能用会话后台 job（历史 exit 127）。
- 10G 卡跑 14B 后，其他 GPU 应用可能 OOM。
- 当前 MT20 约 54/100；壳不改质量。
