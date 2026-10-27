# D 盘资产盘点与磁盘卫生候选清单（只读）

> **性质**：只读盘点，供外部专家审查。**未删除/未移动/未压缩任何文件**，未跑 GPU，未联网，未 git 提交。
> **生成时间**：2026-10-26T21:35:48+0800 ｜ **工作区**：`D:\llama-mem` ｜ **机读件**：`kvmem/m2_visibility/m5/out/D-DRIVE-INVENTORY.json`
> **口径**：体积 = 递归 `st_size` 求和（apparent size，非磁盘占用块）；sha = `sha256(原始字节)` 前缀；时间为本机 +08:00。

## 0 结论

- D: 总 **238.47 GiB**（256.06 GB 十进制），已用 **23.96 GiB**（25.73 GB）、可用 **214.51 GiB**（230.33 GB），已用率 **10.05%**。
- 4 个大头占了几乎全部：`D:\models` **12.73 GiB**、`D:\llama-mem` **8.23 GiB**、`D:\agents` **1.30 GiB**、`D:\DSH` **1.18 GiB**（合计 23.44 GiB）。
- **安全可回收 ≈ 0**（仅 8 个重复 `tmp_*` 副本 + 散落日志/空目录，约 **719.1 KiB**）。
- **条件可回收**：构建产物 **2.96 GB**（重建即可）+ 第三方可重下载 **2.21 GB**（重下载即可）⇒ 上限约 **5.26 GB**；`models` **12.73 GiB** 不可删。
- **证据类目录（本会话 20:00 后产生，46.96 MB）在外部专家复核前不得删除**：cleanroom / 链复现 / 冻结校验 / B6 复核。
- 仓库状态：main `96eeefc`（ahead origin/main 1）、full `5574253`、origin/main `8008064`；tracked 797；未跟踪 60 项。

## 1 方法与纪律

- 体积：`os.scandir` 递归求 `st_size` 和（不跟随符号链接；跳过无权限的 `System Volume Information`）。
- 哈希：`sha256(路径原始字节)`；`tmp_*` 与「git ls-files 的 797 个已入库文件」及「`docs/_work` + `out` 的 224 个 md/json」逐一比对 sha256。
- git/磁盘：`git rev-parse` / `ls-files` / `status`；`shutil.disk_usage("D:/")`。
- **禁止项已遵守**：无 Remove / Move / 压缩 / git 提交 / GPU；所有“可回收”均为估算。

## 2 磁盘总账与基线复核

- 磁盘：total **238.47 GiB** / used **23.96 GiB** / free **214.51 GiB**。
- 你给的 `25.73 GB / 230.33 GB` 是**十进制 GB**，换算后正是 23.96 GiB / 214.51 GiB —— **同一状态，无矛盾**。

| 基线项 | 你给的 | 我实测 | 判定 | 说明 |
|---|---|---|---|---|
| D: used | 25.73 GB | 23.96 GiB = 25.73 GB(十进制) | **match** | 口径不同：你给的是十进制 GB（25.73e9 B），我按 GiB 记 23.96；同一状态 |
| D: free | 230.33 GB | 214.51 GiB = 230.33 GB(十进制) | **match** | 同上，25.73+230.33=256.06 GB(十进制)=238.47 GiB，与本卷 total 一致 |
| llama-mem | 8.72 GB | 8.23 GB (8.83 GB 十进制) | **close** | 差值来自本会话新增产物（账本 json/md、session 目录等仍在写） |
| D:\models | 13.67 GB | 12.73 GB (13.67 GB 十进制) | **match** | 2 个 GGUF：14B-Q4_K_M 8571.73 MB + 7B-Q4_K_M 4466.13 MB |
| git main | 96eeefc（ahead origin/main 1） | 96eeefc（ahead 1） | **match** |  |
| git full / origin/main | 5574253 / 8008064 | 5574253 / 8008064 | **match** |  |
| tracked 文件 | 797 | 797 | **match** |  |
| docs/_work md | 96 | 102 | **diff** | 审计写入导致：+6（本盘点 md、对账账本 md 等会话产物） |
| kvmem json / py | 1294 / 369 | 1300 / 370 | **diff** | 审计写入导致：json +6 / py +1（本清单、账本、session 证据脚本；仓库外证据不计） |
| 未跟踪项 | 59 | 60（含本盘点 md 新增 1 项） | **diff** | 基线 59 为审计开始时；本盘点新增 `docs/_work/D-DRIVE-INVENTORY.md` 未跟踪项 |

> 两处 diff 的原因：审计写入本身（本盘点 md、对账账本、session 证据）改变了 `docs/_work` md 与 `kvmem` json 计数，属正常漂移，不是异常。

## 3 D: 根目录逐项

| 名称 | 类型 | 体积 | 文件数 | 最后修改 | 分类 | 归属/说明 |
|---|---|---|---|---|---|---|
| `models` | dir | 12.73 GiB | 2 | 2026-10-25T00:22 | 项目资产（模型权重） | 本项目：M5 复现所需 GGUF，必须保留 |
| `llama-mem` | dir | 8.23 GiB | 15386 | 2026-10-26T21:30 | 项目仓库（含构建产物） | 本项目主仓库 |
| `agents` | dir | 1.30 GiB | 1391 | 2026-10-24T23:10 | 第三方应用（非本项目） | Agents Anywhere 安装目录，不属于 llama-mem |
| `DSH` | dir | 1.18 GiB | 8557 | 2026-10-25T09:22 | 第三方应用（非本项目） | DeepSeek Harness 安装目录（当前会话运行时） |
| `m5c2-chain-repro-20261026-210154` | dir | 22.99 MiB | 358 | 2026-10-26T21:11 | 本会话证据（链复现） | M5C2 链复现 9 个 run + 日志 + results.json |
| `crashdumps` | dir | 21.23 MiB | 30 | 2026-10-26T07:39 | 诊断资产 | 10-26 崩溃转储（含 minidump/evtx） |
| `m5c2-freeze-verify-20261026-212752` | dir | 12.33 MiB | 269 | 2026-10-26T21:27 | 本会话证据（冻结复核） | 冻结校验副本（kvmem+docs 拷贝 + _verify_meta） |
| `rev7-cleanroom-20261026-205205` | dir | 9.41 MiB | 153 | 2026-10-26T21:05 | 本会话证据（cleanroom） | rev7 干净房复现：4 棵树 + fail-closed 测试日志 |
| `llama-mem-verify-inspector-c3b` | dir | 8.04 MiB | 595 | 2026-10-26T21:24 | 验证克隆（证据） | inspector 验证克隆，HEAD caa9760，clean |
| `llama-mem-verify-clone` | dir | 7.68 MiB | 510 | 2026-10-26T21:24 | 验证克隆（证据） | 隔离验证克隆，HEAD d7020b2，clean |
| `llama-mem-verify-inspector-2326` | dir | 7.62 MiB | 566 | 2026-10-26T21:24 | 验证克隆（证据） | inspector 验证克隆，HEAD 867cd8d，clean |
| `m5c2-chain-repro-20261026-210125` | dir | 2.17 MiB | 30 | 2026-10-26T21:01 | 本会话证据（链复现） | M5C2 链复现 E1–E9 源快照 |
| `llama-mem-backup-2026-10-25` | dir | 1.63 MiB | 85 | 2026-10-25T10:36 | 项目备份 | 本项目 10-25 备份快照（体积小，疑为部分目录备份） |
| `m3fix-tmp` | dir | 396.4 KiB | 139 | 2026-10-25T12:10 | 散落临时（历史） | 10-25 M3 修复临时脚本 |
| `compare-verify` | dir | 307.2 KiB | 57 | 2026-10-25T11:59 | 散落临时（历史） | 10-25 M3 对比验证脚本/产物 |
| `m3fix-tmp-insp` | dir | 125.9 KiB | 67 | 2026-10-25T11:46 | 散落临时（历史） | 10-25 M3 修复 inspector 临时产物 |
| `crashfix` | dir | 59.0 KiB | 6 | 2026-10-26T09:14 | 诊断资产 | 10-26 BSOD 修复脚本与报告 |
| `b6-review-20261026` | dir | 58.8 KiB | 3 | 2026-10-26T21:27 | 本会话证据（B6 复核） | B6 复核 stage1/stage2 证据与脚本 |
| `llama-mem-stage` | dir | 15.9 KiB | 22 | 2026-10-26T19:58 | 散落临时 | 本会话临时截图/文本（main*.txt 等） |
| `kvmem` | dir | 187 B | 1 | 2026-10-25T23:22 | 散落临时 | D 根误落目录：仅 lease_logs/guard_disabled.jsonl 187 B |
| `$RECYCLE.BIN` | dir | 129 B | 1 | 2026-10-26T21:20 | 系统 | 回收站 |
| `c` | dir | 0 B | 0 | 2026-10-25T21:14 | 散落临时 | 空目录 D:\c\Users（误建） |
| `tmp_audit.py` | file | 55.9 KiB | 1 | 2026-10-26T20:53 | 未知 |  |
| `tmp_audit_art.json` | file | 54.2 KiB | 1 | 2026-10-26T20:54 | 未知 |  |
| `tmp_prereg.md` | file | 5.7 KiB | 1 | 2026-10-26T20:56 | 未知 |  |
| `tmp_rev4_1.py` | file | 19.6 KiB | 1 | 2026-10-26T20:51 | 未知 |  |
| `tmp_rev5.py` | file | 17.1 KiB | 1 | 2026-10-26T20:51 | 未知 |  |
| `tmp_rev5_1.py` | file | 11.0 KiB | 1 | 2026-10-26T20:51 | 未知 |  |
| `tmp_rev7.py` | file | 43.7 KiB | 1 | 2026-10-26T20:51 | 未知 |  |
| `tmp_rev7_art.json` | file | 495.8 KiB | 1 | 2026-10-26T20:53 | 未知 |  |

> 注：根下 8 个 `tmp_*` 为文件，明细见 §5.2。

## 4 `D:\llama-mem` 内部构成

| 名称 | 类型 | 体积 | 文件数 | 最后修改 | 分类（处置属性） | 说明 |
|---|---|---|---|---|---|---|
| `build-vulkan` | dir | 2.37 GiB | 2512 | 2026-10-25T00:30 | 可再生构建产物 | Vulkan 构建目录（约 2.4 GB）；可重跑构建恢复 |
| `kvmem` | dir | 1.80 GiB | 3228 | 2026-10-26T21:30 | 项目资产 | 实验代码与全部运行产物（1.84 GB） |
| `vulkan-sdk` | dir | 1.72 GiB | 460 | 2026-10-24T12:48 | 第三方源码/SDK | Vulkan SDK 1.4.363 解压（可用 downloads 内安装包重装） |
| `tools` | dir | 952.28 MiB | 178 | 2026-10-26T21:25 | 项目资产 | GPU shim DLL 等工具（kvshim_vk.dll 50 MB + 其他） |
| `build-cpu` | dir | 576.72 MiB | 434 | 2026-10-26T02:12 | 可再生构建产物 | CPU 构建目录（约 0.58 GB） |
| `downloads` | dir | 289.10 MiB | 4 | 2026-10-24T12:47 | 第三方下载物 | vulkansdk 安装包 289 MB（可重下载） |
| `llama.cpp` | dir | 210.58 MiB | 3932 | 2026-10-26T21:22 | 第三方源码（已打补丁） | 上游代码 + persistent-memory 补丁（当前工作树，必须保留） |
| `llama.cpp-upstream` | dir | 210.56 MiB | 3930 | 2026-10-25T21:16 | 第三方源码（未打补丁镜像） | 上游干净镜像，与 llama.cpp 仅差 8 个补丁文件 + .git |
| `bin` | dir | 98.99 MiB | 53 | 2026-10-24T11:29 | 项目资产/构建产物 | llama 可执行与依赖 DLL（约 99 MB） |
| `.git` | dir | 29.80 MiB | 279 | 2026-10-26T21:23 | 仓库元数据 | git 对象库（29.8 MB） |
| `build-cpu-patched` | dir | 24.77 MiB | 219 | 2026-10-26T02:14 | 可再生构建产物 | CPU patched 构建缓存（约 25 MB） |
| `docs` | dir | 2.08 MiB | 108 | 2026-10-26T21:29 | 项目资产 | 文档与 docs/_work（含本会话账本） |
| `legacy` | dir | 373.9 KiB | 31 | 2026-10-25T20:01 | 项目资产 | 旧版本代码 |
| `PROGRESS-AND-ROADMAP.md` | file | 293.9 KiB | 1 | 1970-01-01T08:00 | 项目资产（根文档） | 进度路线图 |
| `patches` | dir | 71.4 KiB | 5 | 2026-10-25T22:39 | 项目资产 | persistent-memory.patch（32,337 B） |
| `PROJECT-STATE.md` | file | 51.0 KiB | 1 | 1970-01-01T08:00 | 项目资产（根文档） | 项目状态 |
| `README.md` | file | 25.0 KiB | 1 | 1970-01-01T08:00 | 项目资产（根文档） | 说明 |
| `FEATURES.md` | file | 16.3 KiB | 1 | 1970-01-01T08:00 | 项目资产（根文档） | 功能说明 |
| `HANDOFF.md` | file | 10.0 KiB | 1 | 1970-01-01T08:00 | 项目资产（根文档） | 交接 |
| `.gitignore` | file | 6.9 KiB | 1 | 1970-01-01T08:00 | 项目资产（根文档） | 忽略规则 |
| `_rw3.log` | file | 6.8 KiB | 1 | 1970-01-01T08:00 | 散落临时 | 运行日志残留 |
| `_rw2.log` | file | 6.8 KiB | 1 | 1970-01-01T08:00 | 散落临时 | 运行日志残留 |
| `verify.sh` | file | 6.4 KiB | 1 | 1970-01-01T08:00 | 项目资产（根文档） | 验证脚本 |
| `_fc.log` | file | 2.3 KiB | 1 | 1970-01-01T08:00 | 散落临时 | 运行日志残留 |
| `.gitattributes` | file | 1.2 KiB | 1 | 1970-01-01T08:00 | 项目资产（根文档） | 属性 |
| `LICENSE` | file | 1.1 KiB | 1 | 1970-01-01T08:00 | 项目资产（根文档） | 许可证 |
| `nul` | file | 0 B | 1 | 1970-01-01T08:00 | 散落临时 | Windows 保留名文件 |

**kvmem 子目录 top**（`kvmem` = 1.80 GiB / 3228 文件）：

| 子目录 | 体积 | 文件数 |
|---|---|---|
| `m2_visibility` | 1.57 GB | 1732 |
| `variance` | 101.31 MB | 27 |
| `m2_7b` | 73.70 MB | 759 |
| `sessions` | 23.12 MB | 11 |
| `m2_v1_14b` | 10.57 MB | 6 |
| `blocks` | 8.57 MB | 2 |
| `m4c_leases` | 4.64 MB | 451 |
| `p0_1b_blocks` | 2.91 MB | 2 |
| `p0_1a_blocks` | 2.50 MB | 2 |
| `p0_2_blocks` | 2.50 MB | 2 |

## 5 临时 / 散落项清单

### 5.1 本会话（2026-10-26 20:00 后）产生的目录 —— 全部为“证据”

| 目录 | 体积 | 文件数 | 最后修改 | 标注 | 归属 | 若删除会破坏什么 |
|---|---|---|---|---|---|---|
| `rev7-cleanroom-20261026-205205` | 9.41 MiB | 153 | 2026-10-26T21:05 | **keep_evidence** | cleanroom 执行方（本会话） | rev7 干净房复现（4 棵树 + fail-closed 日志）；删除将破坏“独立复现”证据 |
| `m5c2-chain-repro-20261026-210125` | 2.17 MiB | 30 | 2026-10-26T21:01 | **keep_evidence** | chain-repro 执行方（本会话） | M5C2 链复现源快照（_src） |
| `m5c2-chain-repro-20261026-210154` | 22.99 MiB | 358 | 2026-10-26T21:11 | **keep_evidence** | chain-repro 执行方（本会话） | M5C2 链复现 9 个 run 结果 + logs + results.json |
| `m5c2-freeze-verify-20261026-212752` | 12.33 MiB | 269 | 2026-10-26T21:27 | **keep_evidence** | freeze-verify 执行方（本会话） | 冻结校验副本（kvmem+docs 拷贝；证明“冻结后字节未变”） |
| `b6-review-20261026` | 58.8 KiB | 3 | 2026-10-26T21:27 | **keep_evidence** | B6 复核方（本会话） | B6 复核 stage1/stage2 证据 json + 脚本 |

### 5.2 D 根 8 个 `tmp_*`（sha256 与已入库/已冻结文件对照：**全部重复**）

| 文件 | 体积 | sha256 前缀 | 与哪个已存在文件同字节 | 判定 |
|---|---|---|---|---|
| `tmp_rev7_art.json` | 495.8 KiB | `1f8f44b921e575fe…` | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json` | **可删但须先确认（与已入库/已冻结文件同 sha256）** |
| `tmp_audit.py` | 55.9 KiB | `6695a4b4de403870…` | `kvmem/m2_visibility/m5/out/_rev7_audit.py` | **可删但须先确认（与已入库/已冻结文件同 sha256）** |
| `tmp_audit_art.json` | 54.2 KiB | `de80cd38a7147f0f…` | `kvmem/m2_visibility/m5/out/M5C2-REV7-AUDIT.json` | **可删但须先确认（与已入库/已冻结文件同 sha256）** |
| `tmp_rev7.py` | 43.7 KiB | `65ed60125528d5d6…` | `kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py` | **可删但须先确认（与已入库/已冻结文件同 sha256）** |
| `tmp_rev4_1.py` | 19.6 KiB | `0976b4aa4bcd7646…` | `kvmem/m2_visibility/m5/run_m5c2_rev4_1.py` | **可删但须先确认（与已入库/已冻结文件同 sha256）** |
| `tmp_rev5.py` | 17.1 KiB | `9f113de9e5e355b0…` | `kvmem/m2_visibility/m5/run_m5c2_rev5_offline.py` | **可删但须先确认（与已入库/已冻结文件同 sha256）** |
| `tmp_rev5_1.py` | 11.0 KiB | `26d81e2a2f14abd0…` | `kvmem/m2_visibility/m5/run_m5c2_rev5_1_offline.py` | **可删但须先确认（与已入库/已冻结文件同 sha256）** |
| `tmp_prereg.md` | 5.7 KiB | `32eaf82ca56600c4…` | `docs/_work/PREREG-M5-C2-REV7.md` | **可删但须先确认（与已入库/已冻结文件同 sha256）** |

> 结论：8 个 `tmp_*` 全部是“已入库/已冻结”文件的**同字节副本** ⇒ 可删，但须先确认没有报告按路径引用它们。

### 5.3 其它历史临时 / 散落项

| 名称 | 体积 | 文件数 | 最后修改 | 标注 | 说明 |
|---|---|---|---|---|---|
| `llama-mem-verify-clone` | 7.68 MiB | 510 | 2026-10-26T21:24 | **delete_after_confirm** | 验证克隆（HEAD d7020b2，clean）；复核结论已写入仓库后可删 |
| `llama-mem-verify-inspector-2326` | 7.62 MiB | 566 | 2026-10-26T21:24 | **delete_after_confirm** | inspector 验证克隆（HEAD 867cd8d，clean） |
| `llama-mem-verify-inspector-c3b` | 8.04 MiB | 595 | 2026-10-26T21:24 | **delete_after_confirm** | inspector 验证克隆（HEAD caa9760，clean） |
| `llama-mem-stage` | 15.9 KiB | 22 | 2026-10-26T19:58 | **delete_after_confirm** | 22 个 main*/full* 截图文本（本会话调试残留） |
| `llama-mem-backup-2026-10-25` | 1.63 MiB | 85 | 2026-10-25T10:36 | **delete_after_confirm** | 10-25 备份快照（仅 1.63 MB，疑为部分目录；删除前确认未含唯一副本） |
| `m3fix-tmp` | 396.4 KiB | 139 | 2026-10-25T12:10 | **delete_after_confirm** | 10-25 M3 修复临时脚本（结论应在 docs/ 有记录） |
| `m3fix-tmp-insp` | 125.9 KiB | 67 | 2026-10-25T11:46 | **delete_after_confirm** | 10-25 M3 inspector 临时产物 |
| `compare-verify` | 307.2 KiB | 57 | 2026-10-25T11:59 | **delete_after_confirm** | 10-25 M3 对比验证脚本/产物 |
| `crashfix` | 59.0 KiB | 6 | 2026-10-26T09:14 | **keep_evidence** | 10-26 BSOD 修复脚本与报告（结论文档；建议归档到 docs/ 后再删） |
| `crashdumps` | 21.23 MiB | 30 | 2026-10-26T07:39 | **delete_after_confirm** | 崩溃转储（2 个 .dmp + LiveKernelReports + evtx，21 MB；排障后无长期价值） |
| `kvmem` | 187 B | 1 | 2026-10-25T23:22 | **delete_after_confirm** | D 根误落目录：仅 lease_logs/guard_disabled.jsonl（187 B，仓库内无同名文件） |
| `c` | 0 B | 0 | 2026-10-25T21:14 | **delete_candidate** | 空目录 D:\c\Users（0 字节，误建） |
| `llama-mem/_fc.log` | 2.3 KB | 1 | — | **delete_after_confirm** | 运行日志残留（内容可由 out/ 产物重建） |
| `llama-mem/_rw2.log` | 6.8 KB | 1 | — | **delete_after_confirm** | 运行日志残留（内容可由 out/ 产物重建） |
| `llama-mem/_rw3.log` | 6.8 KB | 1 | — | **delete_after_confirm** | 运行日志残留（内容可由 out/ 产物重建） |
| `llama-mem/nul` | 34 B | 1 | — | **delete_after_confirm** | Windows 保留名文件（git 未跟踪，删除需 \\?\ 前缀） |

## 6 清理候选分级

**A 必须保留（证据/资产）**
- D:\models
- D:\llama-mem（除可回收项）
- D:\DSH
- D:\llama-mem\.git
- D:\llama-mem\kvmem
- D:\llama-mem\docs
- D:\llama-mem\tools
- D:\llama-mem\patches
- D:\llama-mem\llama.cpp
- D:\rev7-cleanroom-20261026-205205
- D:\m5c2-chain-repro-20261026-210125
- D:\m5c2-chain-repro-20261026-210154
- D:\m5c2-freeze-verify-20261026-212752
- D:\b6-review-20261026
- D:\crashfix

**B 可删但须先确认**
- D:\tmp_*.py/json/md（8 个，全部同 sha256 副本）
- D:\llama-mem-verify-clone
- D:\llama-mem-verify-inspector-2326
- D:\llama-mem-verify-inspector-c3b
- D:\llama-mem-stage
- D:\llama-mem-backup-2026-10-25
- D:\m3fix-tmp
- D:\m3fix-tmp-insp
- D:\compare-verify
- D:\crashdumps
- D:\kvmem
- D:\llama-mem\llama.cpp-upstream
- D:\llama-mem\_fc.log/_rw2.log/_rw3.log/nul

**C 可删候选（纯临时）**
- D:\c（空目录）

**D 条件回收：需重建**
- D:\llama-mem\build-vulkan
- D:\llama-mem\build-cpu
- D:\llama-mem\build-cpu-patched

**D 条件回收：需重下载**
- D:\llama-mem\vulkan-sdk
- D:\llama-mem\downloads

**E 永不删除**
- D:\models
- D:\llama-mem\.git
- D:\llama-mem\kvmem
- D:\llama-mem\docs
- D:\llama-mem\tools

## 7 Top 10 体积项 与 可回收估算

| # | 项 | 体积 | 角色 |
|---|---|---|---|
| 1 | D:\models（2 个 GGUF） | 12.73 GiB | 模型权重：复现推理必需，不可删 |
| 2 | D:\llama-mem 合计 | 8.23 GiB | 项目主仓库（含构建/第三方/产物） |
| 3 | D:\llama-mem\build-vulkan | 2.37 GiB | Vulkan 构建产物：可再生（需重建时间） |
| 4 | D:\llama-mem\kvmem | 1.80 GiB | 实验代码+全部产物：项目资产，保留 |
| 5 | D:\llama-mem\vulkan-sdk | 1.72 GiB | 第三方 SDK：可用 downloads 安装包重装 |
| 6 | D:\agents | 1.30 GiB | 第三方应用（非本项目） |
| 7 | D:\DSH | 1.18 GiB | Harness 安装（当前运行时，勿动） |
| 8 | D:\llama-mem\tools | 0.93 GiB | shim DLL 等工具资产，保留 |
| 9 | D:\llama-mem\build-cpu | 0.56 GiB | CPU 构建产物：可再生 |
| 10 | D:\llama-mem\downloads | 0.28 GiB | 第三方安装包：可重下载 |

**可回收区间（只估算，未执行）**

| 情景 | 回收量 | 代价/前提 |
|---|---|---|
| 只清纯垃圾（重复 `tmp_*` + 散落日志/空目录） | **719.1 KiB** | 需确认 `tmp_*` 无独立引用 |
| + 历史临时/克隆/备份/崩溃转储（确认后） | **47.03 MB** | 需确认验证结论已入库 |
| + 本会话证据目录 | **46.96 MB** | **不建议**：外部专家复核前会破坏可复现证据 |
| 删构建产物（build-*） | **2.96 GB** | 可重跑构建；期间无法直接复跑二进制 |
| 删第三方可重下载（vulkan-sdk/downloads/llama.cpp-upstream） | **2.21 GB** | 可重下载；失去上游原件对照 |
| **理论上限（全部）** | **5.26 GB** | 不建议；会丢构建缓存与证据 |

> 关键判断：**D 盘真正占地的是模型权重（12.73 GiB，不可删）与项目仓库（8.23 GiB）**；磁盘卫生能安全回收的只有 MB 级，GB 级回收必然以“重建/重下载/丢证据”为代价。

## 8 风险清单：清了会破坏哪些可复现证据

| 路径 | 严重度 | 若删除会怎样 | 保留到什么时候 |
|---|---|---|---|
| `D:\rev7-cleanroom-20261026-205205` | high | 删除会丢失 rev7 独立复现证据（4 棵树 + fail-closed 测试日志） | 外部专家复核完成 |
| `D:\m5c2-chain-repro-20261026-210125 / -210154` | high | 删除会丢失 M5C2 链复现的 9 个 run 与源快照（E1–E9 可复算性的对照证据） | 外部专家复核完成 |
| `D:\m5c2-freeze-verify-20261026-212752` | high | 删除会丢失“冻结后字节未变”的校验副本与 _verify_meta | 外部专家复核完成 |
| `D:\b6-review-20261026` | medium | 删除会丢失 B6 复核 stage1/stage2 证据（复核结论的依据） | B6 复核归档 |
| `D:\llama-mem-verify-clone / -verify-inspector-*` | medium | 删除会丢失隔离验证克隆（可 git clone 重建，但当时 HEAD 的验证上下文会丢） | 复核结论入库 |
| `D:\llama-mem\.git` | critical | 删除 = 丢失全部 git 历史（main 96eeefc / full 5574253 / 未推送的 ahead 1 提交） | 永久保留/先推远端 |
| `D:\llama-mem\kvmem\m2_visibility\m5\out` | critical | 删除会丢失 270.9 MB 原子产物（JUDGE/RATES/REV7/REV7.1 等）与账本 | 永久保留 |
| `D:\llama-mem\docs\_work` | critical | 删除会丢失 99 个冻结/草稿 md（含 PREREG 与账本） | 永久保留 |
| `D:\llama-mem\tools` | high | 删除会丢失 GPU shim DLL（kvshim_vk.dll 50 MB），复现依赖它 | 永久保留 |
| `D:\models` | high | 删除后无法复跑任何需要 GGUF 的推理/生成（b5/b6 尚未跑） | 项目结束 |
| `D:\llama-mem\build-cpu* / build-vulkan` | low | 删除只损失重建时间（数十分钟到数小时）；不影响证据，但删除期间无法复跑二进制 | 可删（重建即可） |
| `D:\llama-mem\llama.cpp-upstream` | medium | 与 llama.cpp 差异仅 8 个补丁文件；删除不破坏补丁（patches/ 有 patch），但失去“上游原件”对照 | 确认 patches/persistent-memory.patch 可 100% 重放后再删 |

## 9 核对与复算命令（任何人可重跑）

```bash
# 磁盘（GiB）
python -X utf8 -c "import shutil;u=shutil.disk_usage('D:/');print(u.used/2**30,u.free/2**30,u.total/2**30)"

# 任一目录的体积/文件数（apparent size）
python -X utf8 -c "import os,sys;p=sys.argv[1];t=n=0
for r,d,f in os.walk(p):
    for x in f:
        try: t+=os.path.getsize(os.path.join(r,x)); n+=1
        except OSError: pass
print(t,n)" D:/llama-mem

# 8 个 tmp_* 是重复副本的自证（示例：tmp_rev7_art.json 应等于 M5C2-REV7-OFFLINE.json）
python -X utf8 -c "import hashlib;print(hashlib.sha256(open('D:/tmp_rev7_art.json','rb').read()).hexdigest()[:16])"
python -X utf8 -c "import hashlib;print(hashlib.sha256(open('kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json','rb').read()).hexdigest()[:16])"
```

## 10 给外部专家的建议

- 先看 §8：**证据目录（cleanroom / repro / freeze / b6-review）、`.git`、`kvmem/out`、`docs/_work`、`tools`、`models` 是高价值或不可再生的**，清理应从这份清单之外开始。
- 8 个 `tmp_*` 是唯一“可删且证据已在仓库”的一批（MB 级）：删除前只须确认没有报告按路径引用它们。
- 想回收 GB 级：低风险路径只有 `build-vulkan` + `build-cpu` + `build-cpu-patched`（2.96 GB，重建即可）；其次是 `vulkan-sdk` / `downloads` / `llama.cpp-upstream`（2.21 GB，重下载即可）。
- `D:\llama-mem\_fc.log/_rw2.log/_rw3.log`、`D:\kvmem`、`D:\c` 等误落项合计 < 1 MB，可一次性清掉，但删除动作应由人执行；本盘点只做只读标记。
- “可回收”是**估算**：体积为 apparent size，实际回收可能略低（簇对齐/稀疏文件），且未考虑删除期间文件被占用。

---

*本文件由 `doc-ledger` 于 2026-10-26T21:35:48+0800 只读生成；未改动被盘点文件、未 git 提交。*
