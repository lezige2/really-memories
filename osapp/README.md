# llama-mem OS shell (MVP)

Windows 托盘常驻壳 + 本地服务管理 + 记忆/聊天 UI。**不改模型，不碰 P1 默认**，只做产品入口。

## 现在能跑
```powershell
cd D:\llama-mem\osapp
$env:PATH="C:\Users\lezige\.dsh\dsh-runtimes\dsh-next-primary-runtime\dependencies\node\bin;$env:PATH"
pnpm install
pnpm build
.\run-osapp.cmd
```
`run-osapp.cmd` 会清掉 `ELECTRON_RUN_AS_NODE` 并直接调用 `node_modules/electron/dist/electron.exe`，避免 Electron 被当成 Node 运行。
首次 `pnpm install` 会下载 Electron 运行时（约 239MB，网络慢时需等）。

### NSIS 安装包（当前正式安装）
```text
osapp\release-builder\llama-mem Setup 0.1.0.exe
```
- 默认安装到 **`D:\llama-mem-os`**；
- 安装包内嵌 `resources\backend`（tools + out/ops + kvmem/daily）；
- 模型不打包，仍读 `D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf`；
- 卸载会删除程序目录和右键菜单项，不删外部模型/原项目数据。

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
- 全局快捷键：`Ctrl+Alt+M` / `Ctrl+Alt+Q` 打开对话并聚焦输入框；`Ctrl+Alt+V` 把剪贴板文本存入记忆；
- 托盘“显示/隐藏”；
- 设置：API/模型/数据目录展示；“启动时启动服务”可选（默认关）；
- NSIS 安装包：`release-builder/llama-mem Setup 0.1.0.exe`；
- 安装路径 `D:\llama-mem-os`，后端/初始数据在 `resources\backend`；
- 文件右键“存入 llama-mem 记忆”（`tools/remember_file.py`，注册在 HKCU）；
- 剪贴板存入 `Ctrl+Alt+V`。

## 未做
- 代码签名/自动更新；
- 屏幕采集（默认不做）；
- 真正的多页路由（当前单 Svelte 组件切换）；
- Python 运行时未打包（使用本机 Python）。

## 注意
- 服务必须用 detached/WMI 方式起，不能用会话后台 job（历史 exit 127）。
- 10G 卡跑 14B 后，其他 GPU 应用可能 OOM。
- 当前 MT20 约 54/100；壳不改质量。
