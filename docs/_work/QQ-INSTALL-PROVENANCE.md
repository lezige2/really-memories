# QQ-INSTALL-PROVENANCE（NapCat 安装来源与完整性取证 · 摘要）

> 只读取证；未再下载/安装。机器可读件：`docs/_work/QQ-INSTALL-PROVENANCE.json`。
> 对象：NapCat v4.18.41（`NapNeko/NapCatQQ` latest，2026-10-21）+ QQNT 9.9.33-52230 + 安装壳 `third_party/_napcat_onekey/NapCat.52230.Shell/`。

## 1 官方 API ↔ 下载物比对（`https://api.github.com/repos/NapNeko/NapCatQQ/releases/latest`，200 / 9,688 B）

| asset | API size | API digest (sha256) | 本机 bytes | 本机 sha256 | 判定 |
|---|---|---|---|---|---|
| NapCat.Shell.Windows.OneKey.zip（id 661878436） | 994,134 | `46c3ec15…27f39c` | 994,134 | `46c3ec15…27f39c` | **size+digest 全等** |
| NapCat.Framework.zip（id 661878438） | 36,738,019 | `3c526f57…965822` | 36,738,019 | `3c526f57…965822` | **size+digest 全等** |
| NapCat.Shell.zip（安装器下载，id 661878437） | 35,894,640 | `6801f93e…cf96b` | 35,894,640 | `6801f93e…cf96b` | **size+digest 全等** |
| NapCat.Shell.Windows.Node.zip（未下载，仅记录） | 124,089,498 | `51fbb10e…d3f0` | — | — | 未使用 |

## 2 安装目录

- 路径：`third_party/_napcat_onekey/NapCat.52230.Shell/`；Shell 目录 **2,512 文件 / 1,260,697,292 B（≈1,202.3 MiB）**；父目录 `_napcat_onekey/` 共 2,523 文件 / 1,611,358,568 B（含安装器与腾讯 QQNT 离线包）。
- QQNT 版本：`versions/config.json` `baseVersion=curVersion=9.9.33-52230`；`resources/app/package.json` `qq-chat 9.9.33-52230` ⇒ 与目录名一致。
- NapCat 版本：`napcat.mjs` 内置 `4.18.41` 标记（`resources/app/napcat/package.json` 的 `version: 0.0.1` 是占位，不作版本证据）。
- 安装器根 `QQ.exe` = **314,581,680 B**，`FileVersion=9.9.33.52230 / Product=QQ` ⇒ 安装器从腾讯官方 CDN 下载的 QQNT 离线包（本记录不复述其网络路径，只核文件版本）。

## 3 关键文件 sha256

| 文件 | bytes | sha256 |
|---|---|---|
| `resources/app/napcat/napcat.mjs` | 3,134,858 | `7c66d0239d7effe73ab6e4920eddef732a8066fb47cd19539541c72055c5f0aa` |
| `resources/app/napcat/loadNapCat.js` | 224 | `3d272756b14175c1e603261da6d8180e69f3435cbbd73baaf0542ea52f12330f` |
| `resources/app/napcat/config/napcat.json` | 310 | `28b2416e4579cce687309bc9071df4f41acfe03b3670e0b4a1d81fe46967ff0b` |
| `NapCat.52230.Shell/NapCatWinBootMain.exe` | 32,768 | `8b860a0be0993211c8664a08097d09979fb7e3406f63247c5a3b4251dad8e744` |
| `resources/app/napcat/NapCatWinBootMain.exe` | 35,328 | `fdc3b5b3131093f627811e171425e98681f71523c0aa21693dee8c6b6b2892f7` |
| `NapCat.52230.Shell/QQ.exe`（壳内启动 stub） | 1,717,800 | `abbed71fc3dfe84fa712a2243041029c4a2e60b25595528522cb92c5758d388a` |
| `_napcat_onekey/QQ.exe`（安装器下载的 QQNT 离线包） | 314,581,680 | `b25c0d3ce9df764074a9118d0ded927e1b2d7ebf60e306112e8df18a040ec492` |
| `_napcat_onekey/NapCatInstaller.exe` | 140,288 | `c1545743f1f62c0aad892b3ad0a7b2fb40b263a841353748d303fec461a501f2` |
| `_napcat_onekey/NapCat.Shell.zip` | 35,894,640 | `6801f93e533846cea05f4f531874a0e84371ab2331c5585b57cd7e3b869cf96b` |
| `third_party/NapCat.Shell.Windows.OneKey.zip` | 994,134 | `46c3ec155aa61f12e89bbf97013a21243d00b0019b5565992a88852d7627f39c` |
| `third_party/NapCat.Framework.zip` | 36,738,019 | `3c526f5789ff6cc56d78381eb10536c8273fe394d227187b27dea94b59965822` |

## 4 传输路径声明

1. OneKey/Framework：GitHub 官方 release asset 直链 → 本机 `third_party/`（size+digest 与 API 全等）。
2. `NapCat.Shell.zip`：**安装器经 ghproxy.net 下载**。代理可见传输内容，但落盘 zip 的 sha256 = 官方 API digest `6801f93e…` ⇒ **传输路径可被代理看到，内容以官方 size/digest 校验为准**。
3. QQNT（`_napcat_onekey/QQ.exe` 314 MB）：安装器从 **Tencent 官方 CDN** 下载；`FileVersion=9.9.33.52230`，与 `versions/config.json`/目录名一致。本记录未单独固定该 314 MB 文件的官方 digest（腾讯未提供公开 digest），完整性仅由"安装器→官方 CDN + 版本一致性"支撑。

## 5 风险与结论

- 风险：NapCat 属第三方协议端，**可能违反 QQ 用户协议/封号**（只用小号）；工具链投毒面 = 官方 repo + 腾讯 CDN + ghproxy 传输；安装目录含完整 QQNT 运行时（≈1.2 GB / 2,512 文件），建议 Defender 扫描、不设开机自启。
- 不符项：**0**（mismatches=[]）。
- 结论：**`provenance_ok`** —— 两个直接下载物与 API size+digest 全等；安装器产出的 `NapCat.Shell.zip` 与官方 digest 全等；QQNT 版本三处一致（离线包 FileVersion / versions/config.json / 目录名）；NapCat 4.18.41 标记存在。