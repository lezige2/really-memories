# llama-mem

本地、单用户、离线的长期记忆助手：记忆以 **KV 块**（`.kvmem`）挂载进推理引擎，而不是把记忆原文拼进 prompt。

## 现在是什么

- **桌面产品**：Windows 托盘常驻壳 + 本地服务 + 记忆库/对话/状态/设置；
- **安装位置**：`D:\llama-mem-os`（NSIS 安装包）；
- **本地服务**：`127.0.0.1:8765`，只监听本机；
- **模型**：`D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf`（不打包进安装包）；
- **数据**：安装目录内 `resources\backend\kvmem\daily`；当前 20 条记忆；
- **能力**：remember / ask / 记忆库 / audit / backup / P1 生命周期；
- **质量边界**：MT20 5× 约 **54/100**，单用户、冲突/多轮弱；不冒充达标。

## 快速使用

```text
D:\llama-mem-os\llama-mem.exe
```

- 托盘常驻；`Ctrl+Alt+M` / `Ctrl+Alt+Q` 打开对话；`Ctrl+Alt+V` 把剪贴板存入记忆；
- 文件右键 → “存入 llama-mem 记忆”；
- 服务未启动时，在“状态”页点“启动”。

开发运行：

```powershell
cd D:\llama-mem\osapp
.\run-osapp.cmd
```

## 仓库结构

```text
osapp/        Electron + Svelte 桌面壳、安装器、便携构建
tools/        Python 记忆服务、检索、生命周期、审计
out/ops/      launch_service.py 等运维脚本
kvmem/        源数据/KV 块/历史隔离目录
docs/         设计与证据文档（入口 docs/README.md）
```

## 文档

- [osapp/README.md](osapp/README.md)：桌面壳、快捷键、安装/便携构建
- [docs/README.md](docs/README.md)：项目设计与证据入口
- `out/HANDOFF-2026-10-31.md`：当前交接与已知边界
- `out/KNOWN-LIMITATIONS.md`：产品已知限制

## 边界

- 模型不打包；安装包只带框架/后端代码和初始数据；
- Python 运行时仍使用本机安装路径；
- 安装包未做代码签名/自动更新；
- 记忆质量未达标（MT20 54/100），时间轴/组配对等实验默认关闭；
- 不做内核驱动/全屏采集；剪贴板只在 `Ctrl+Alt+V` 时读取。
