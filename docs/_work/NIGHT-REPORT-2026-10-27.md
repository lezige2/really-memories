# NIGHT-REPORT 2026-10-27（LEAD 夜间自主执行结果）

> 生成时间：2026-10-27T00:35+08:00 · 执行人：LEAD · 状态：**b5 已判、C 版验收通过、DSH provider 已配好待重启**

## 1 一句话结论

- **b5（研究）**：判 **擦边**（不是通过、不是未通过）。误判 9/72 = 12.50%（Wilson 上界 22.08% > 15%）、漏判 0/29（上界 11.70%）；三套 gold 一致。
- **C 版（产品）**：验收 **通过**，S1–S7 全过（含跨进程持久、强杀恢复、个体日志、隐私打码）。证据 `kvmem/m2_visibility/m5/out/C-V1-ACCEPT.json` = `c9f4f111c1b218d4` / 10,441 B。
- **DSH 接入**：`local14b` provider 已写进 `~/.dsh/profiles/desktop/cordis.patch.yml`（已备份），**需要重启 DSH 一次才生效**；本地服务已在 `127.0.0.1:8765` 常驻运行。

## 2 b5 结论（唯一来源 `M5C2-B5-VERDICT.json` = `fa93b38cdedea58e`/4,922 B，pin `906d9fcc0643906f`）

| 项 | 值 |
|---|---|
| 生成层 | `M5C2-B5-GEN.json` `2b63a02463994c03`/68,184 B，40/40 前向，**一次性已消耗** |
| 切句 | `M5C2-B5-SENTENCES.json` `ba92635c8ad0c410`/116,566 B，326 句 |
| gold | `M5C2-B5-GOLD.json` `54aa3da53c45da69`/64,148 B；盲标一致 319/326 = 97.85%；LEAD 裁定 7 条 |
| 抽取 | `M5C2-B5-EXTRACT.json` `93505eecc539634a`/444,613 B；326/326、elapsed 2,418.3 s、peak 8.0423 GiB、aborted=null |
| 判定 | `M5C2-B5-DECIDE.json` `59da64cb6f2464de`/741,080 B；102 supported / 206 unsupported / 17 undecidable / 1 parse_fail |
| 独立审计 | `M5C2-B5-DECIDE-AUDIT.json` `f72d267ec9b7eef1`/109,477 B；**逐 sid diff=0（326/326）** |
| 两率 | `M5C2-B5-RATES.json` `aae1b790d19dfa73`/75,582 B |
| 结论 | **擦边**：FP 9/72=12.50%（上界 22.08%）、漏判 0/29（上界 11.70%）；A-only 9/70、B-only 9/71 均擦边，三套一致 ⇒ 不降级 |

**禁写**：「b5 通过」「b5 未通过」；擦边不得事后改达标。
披露：n_leak=29 功率偏弱（b6 应 ≥40）；抽取峰值 8.0423 GiB（>8.0 目标 43 MiB、<8.6 fuse）。

## 3 C 版验收（`C-V1-ACCEPT.json` `c9f4f111c1b218d4`；pin `C-V1-ACCEPT-FREEZE.json` `25428a454bb43618`）

| 场景 | 结果 | 证据 |
|---|---|---|
| S1 记与答 | 通过 | 3/3 含具体值（云栖书店 / 120 元 / YQ-7781） |
| S2 不知道 | 通过 | 6/6 拒答（固定拒答文案） |
| S3 跨进程持久 | 通过 | quit 后重开自动恢复 3/3 |
| S4 删除生效 | 通过 | /forget 后同题拒答 |
| S5 对照 | 通过 | --control 3/3 拒答 |
| S6 资源与崩溃 | 通过 | taskkill /F 后重开记忆仍在；外部采样 peak 8.272 GiB ≤8.6 |
| S7 个体日志 | 通过 | `inspect_logs --verify` exit 0、crash_recovered 出现、redacted 打码、answer→block 可核对 |

资源：冷启动 12.99 s、回答 P50 1.17 s / P95 1.61 s（9 次短问答）、VRAM 峰 8.272 GiB（来源 powershell-gpuadaptermemory）。
**披露**：峰值 8.272 > SPEC §4 的 8.0 目标（+0.27 GiB，未超 fuse 8.6）；answer_n=9 只覆盖短问答，长回答延迟未测。

关键文件：`tools/chat_daily.py` `5f64a7c14cfa3ac8`、`tools/chat_service.py` `8479e9ee2df00022`、`tools/run_c_acceptance.py` `937ed744b26cc47a`、`tools/inspect_logs.py`、`start_chat.cmd`、`start_service.cmd`、`docs/USER-GUIDE-C.md`。

## 4 DSH 接入（已配置，等一次重启）

- 补丁位置：`C:\Users\lezige\.dsh\profiles\desktop\cordis.patch.yml`（新 sha `4e4b85ebbb169af9`/16,502 B）
- 备份：`cordis.patch.yml.bak-20261027-local14b`（`34b650ce2a8deafb`）
- 内容：`llm-pi-ai.providers.local14b` → `baseURL http://127.0.0.1:8765/v1`、`api: openai-completions`、模型 `local-14b-memory`（contextWindow 8192）、`headers.authorization: Bearer local`
- **HMR 未监听该文件（日志无 reload 事件），必须重启 DSH 才生效**
- 回滚：双击 `D:\llama-mem\rollback-dsh-local14b.cmd`（或复制备份回去），再重启 DSH
- 启动服务：双击 `D:\llama-mem\start_service.cmd`（当前已在跑，可不管）

**早上启用步骤**：
1. 确认服务在跑：浏览器打开 `http://127.0.0.1:8765/health`，看到 `"status":"ok"`；
2. 重启 DSH；
3. 模型选择器里选「本地 14B（记忆 / llama-mem）」→「本地 14B 记忆」；
4. 发一句：`记住：我每周三晚上七点有组会，地点 B 座 302`；
5. 再发：`我周几有组会？`（应回答周三/B座302）；再发 `我车牌号是多少？`（应答不知道，不编）。

**已实测（服务直连）**：remember → `已记住（id=1，34 token）`；问待办 → `交周报、周三体检、周五复盘`；问未记事实 → `长期记忆里没有这条，当前对话里也没有提到。我不想猜`。

## 5 QQ

- 适配器已交付并 CPU 测试通过：`tools/qq_bridge.py` `0ed698febc277018`、`tools/qq_bridge.example.json`、`tools/test_qq_bridge_cpu.py`（16 tests，exit 0）、`docs/QQ-BRIDGE.md`。
- **按你的决定：等 DSH 内验证可用后再装 NapCat**。届时我装、你拿小号扫码；风险（封号/违反用户协议）文档已写明。

## 6 文档与仓库

- b5 结论已同步到 `README.md`、`PROGRESS-AND-ROADMAP.md`、`PROJECT-STATE.md`、`FEATURES.md`、`docs/_work/ARTIFACTS-KEY.md`、`docs/_work/INDEX.md`（doc-ledger，未 commit）。
- **未做 git commit**（docs 在 `.gitignore` 里，需 `git add -f`；等你醒后我一次性提交到 `full` 分支，不 push）。
- 事故 IN-1（judge 脚本被截断 0 字节）已解决：拆 extract/decide 重建、判据复用 rev7.1、DECIDE↔独立审计 diff=0；台账 `M5C2-B5-ATTEMPTS.json` `06283bdbc7b33fda`/45,641 B。

## 7 明天可做（按优先级）

1. 你重启 DSH 试「本地 14B 记忆」；卡住就发我 `kvmem/daily/service.log` 尾部；
2. 用你真实的三类记忆跑一遍（个人信息 / 每周纲要 / 待办），不合适我调；
3. b6（已冻结 `ac27d47d3a3efff9`，需 GPU 串行 ~1.5 h）；
4. QQ：装 NapCat + 小号联调；
5. 文档提交（`full` 分支）+ 清理旧 tmp/克隆（需你点头）。