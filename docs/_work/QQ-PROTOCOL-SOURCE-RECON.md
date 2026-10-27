# QQ 协议端来源侦察（只读网络探测，未下载/未安装）

> 日期 2026-10-27 ｜ 方法：`curl -L -sS --max-time`，记录 `http_code / size_download / url_effective`；探测体存 `D:\llama-mem\third_party\_recon\`。
> **未执行任何下载/安装/解压**；本机已有 QQNT：`E:\Program Files\qq\QQ.exe`（1,637,704 B，2025-07-13）。
> 与任务前提的差异：本次实测 `github.com` 根域 **可达（200, 580,496 B）**，仅 `/releases` HTML 路径返回 000；`api.github.com` 与 release asset CDN 均可用。网络可能分时段/分路径抖动。

## 1 逐项测试

| 测试 | URL（-L 后 final） | 状态 | 结论 |
|---|---|---|---|
| gitee 首页 | https://gitee.com | 200 / 639,558 B | 可达 |
| gitee 搜索 | https://gitee.com/search?q=NapCat → https://so.gitee.com/?q=NapCat | 200 / 849 B（JS 壳） | 无服务端渲染结果 |
| gitee API 搜索 | https://gitee.com/api/v5/search/repositories?q=NapCat（Lagrange/onebot 同） | 200 / 2 B（`[]`） | 无公开命中/需鉴权 |
| gitee 镜像直连 | https://gitee.com/mirrors/NapCatQQ（/lagrange） | 405 / 374 B | 不存在或拒绝 |
| gitee 仓库猜测 | https://gitee.com/napcat/NapCatQQ | 404 / 7,187 B | 无此镜像 |
| github 根 | https://github.com | 200 / 580,496 B | 可达 |
| github releases 页 | https://github.com/NapNeko/NapCatQQ/releases | **000 / 0 B** | HTML 路径不可用（与任务前提一致） |
| github API | https://api.github.com/repos/NapNeko/NapCatQQ/releases?per_page=5 | 200 / 61,057 B | **可用元数据源** |
| github asset（Range） | 见 §2 OneKey URL，-r 0-1 | **206 / 2 B**，final=`release-assets.githubusercontent.com/...` | **可直接下载** |
| ghproxy | https://ghproxy.net/https://github.com/NapNeko/NapCatQQ/releases | 403 / 14 B（asset 502 / 157 B） | 不可用 |
| ghfast | https://ghfast.top/https://github.com/NapNeko/NapCatQQ/releases | 403 / 14 B（asset 403 / 24 B） | 不可用 |
| moeyy | https://github.moeyy.xyz/https://github.com/... | 000 / 0 B | 不可用 |
| gitclone | https://gitclone.com/github.com/NapNeko/NapCatQQ | 000 / 0 B | 不可用 |
| npm | https://registry.npmjs.org/napcat | 200 / 395 B | 占位包：1.0.0–1.0.3 于 2025-04-18 **全部 unpublished**，无 tarball 可用 |
| npm | /napcat-qq | 404 / 21 B | 不存在 |
| npm | /lagrange、/onebot | 200 / 3,145、4,407 B | 同名无关包（插值算法/SDK），非协议端 |
| npmmirror | https://registry.npmmirror.com/napcat | 200 / 206 B | 同为占位/未发布，不可用 |
| pypi | https://pypi.org/pypi/napcat/json | 404 / 24 B | 无此包 |
| pypi | /lagrange、/onebot | 200 / 22,823、16,920 B | 同名无关包 |
| im.qq.com | https://im.qq.com → /index | 200 / 271 B | 可达（首页跳转） |
| QQNT 页面 | https://im.qq.com/pcqq/index.shtml | 200 / 38,718 B | 可达；Windows 安装包 URL 由 JS `config.ntDownloadX64Url` 运行时取，静态页未给 |
| QQ 下载页 | https://im.qq.com/download/ | 200 / 23,210 B | 仅见 macOS NTQQ：`https://dldir1.qq.com/qqfile/qq/QQNT/e9f0c326/QQ_v6.9.6-8827.dmg`；另有旧 PCQQ 9.7.1 exe |
| pc.qq.com | https://pc.qq.com | 200 / 128,583 B | 仅 QQ 电脑管家 exe，非 NTQQ |
| qq.com | https://qq.com | 501 / 325 B | 不可用 |
| baidu | https://www.baidu.com/s?wd=NapCat… | 200 但结果页 1,488 B（反爬） | 不能用于镜像发现 |
| tuna | https://mirrors.tuna.tsinghua.edu.cn | 200 / 22,406 B | 可达，无 QQ/OneBot 镜像（grep 0） |
| aliyun | https://developer.aliyun.com/mirror/ | 200 / 303,365 B | 可达，无相关镜像（grep 0） |

**不可用原因归纳**：gitee 无公开镜像/搜索需 JS+鉴权；GitHub 代理全部失效（403/502/000，且代理有 MITM 风险）；npm/pypi 同名包均为无关包或已下架占位；QQ 官方仅保证 NTQQ 安装（本机已装，不需要）；GitHub 只有 HTML releases 路径 000，**API + release asset CDN 可用**。

## 2 可用下载源清单（精确 URL / 大小 / 预期版本；均未下载）

**A. NapCat（首选；需已装 QQNT，本机满足）— v4.18.41（2026-10-21，latest）**
| 文件 | 大小 B | URL |
|---|---|---|
| NapCat.Shell.Windows.OneKey.zip | 994,134 | https://github.com/NapNeko/NapCatQQ/releases/download/v4.18.41/NapCat.Shell.Windows.OneKey.zip |
| NapCat.Framework.zip | 36,738,019 | https://github.com/NapNeko/NapCatQQ/releases/download/v4.18.41/NapCat.Framework.zip |
| NapCat.Shell.zip | 35,894,640 | https://github.com/NapNeko/NapCatQQ/releases/download/v4.18.41/NapCat.Shell.zip |
| NapCat.Shell.Windows.Node.zip | 124,089,498 | https://github.com/NapNeko/NapCatQQ/releases/download/v4.18.41/NapCat.Shell.Windows.Node.zip |

**B. Lagrange.OneBot（.NET 自包含；nightly 2025-08-02）**
| 文件 | 大小 B | URL |
|---|---|---|
| Lagrange.OneBot_win-x64_net9.0_SelfContained.zip | 34,989,556 | https://github.com/LagrangeDev/Lagrange.Core/releases/download/nightly/Lagrange.OneBot_win-x64_net9.0_SelfContained.zip |
| Lagrange.OneBot_win-x86_net9.0_SelfContained.zip | 32,354,054 | .../nightly/Lagrange.OneBot_win-x86_net9.0_SelfContained.zip |

**C. LuckyLillia（LLOneBot 组织，另一 OneBot 实现；v8.3.2 / 2026-10-12）**
| 文件 | 大小 B | URL |
|---|---|---|
| LuckyLillia-CLI-win-x64.zip | 95,713,510 | https://github.com/LLOneBot/LuckyLilliaBot/releases/download/v8.3.2/LuckyLillia-CLI-win-x64.zip |
| LuckyLillia-Desktop-win-x64.zip | 65,767,668 | https://github.com/LLOneBot/LuckyLilliaBot/releases/download/v8.3.2/LuckyLillia-Desktop-win-x64.zip |

> 预期版本：NapCat v4.18.41（最新稳定）、Lagrange nightly（仅 nightly 通道）、LuckyLillia v8.3.2。下载前用 `curl -L -o D:\llama-mem\third_party\<name>.zip <URL>`，下完核对字节数并 `Get-FileHash -Algorithm SHA256` 留档。

## 3 风险提示

- **封号/ToS**：第三方协议端（NapCat/Lagrange/LuckyLillia）均非官方客户端，可能违反腾讯用户协议并导致 QQ 号限制/封禁；**只用小号**，不要用主号。
- **投毒/供应链**：只从上述官方 repo 的 release asset 直接下载（不经代理/网盘/二手镜像）；解压前核大小，解压后杀毒扫描；优先 OneKey/Framework 小包，Node 包体积大且来源复杂。
- **代理 MITM**：本次测试的 4 个 GitHub 代理全部不可用；即使将来可用，也不要经代理下载可执行包。
- **本机已有 QQNT**：`E:\Program Files\qq\QQ.exe` 存在，可直接用 NapCat Framework/OneKey；无需再装 NTQQ（im.qq.com 未给 Windows 直链，属预期）。

## 4 建议下一步（等人确认，未执行）

1. 下载 `NapCat.Shell.Windows.OneKey.zip`（994 KB）到 `D:\llama-mem\third_party\` → 解压 → 按 OneKey 提示选择已装 QQ（`E:\Program Files\qq\QQ.exe`）。
2. 若 OneKey 失败：`NapCat.Framework.zip`（36.7 MB）+ 手动 `NapCatWinBootMain.exe`。
3. 备选 Lagrange：`Lagrange.OneBot_win-x64_net9.0_SelfContained.zip`（35.0 MB，需 .NET 9 自包含已含运行时）。
4. 启动后按 `docs/QQ-BRIDGE.md` 配 OneBot v11 反向 WS（token/端口），再用小号自测。