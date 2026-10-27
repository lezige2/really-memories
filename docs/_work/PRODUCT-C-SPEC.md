# PRODUCT-C-SPEC（C 版「14B 本地记忆助手」验收口径 · v1.0 预注册）

> 件性质：**产品验收预注册**（先于实现与验收；验收口径冻结后不得事后放宽）
> 作者：LEAD · frozen_at: 2026-10-26T23:41:00+08:00 · frozen_by: LEAD · frozen_rev: 1
> 依据：现有产品路径 `tools/chat.py`（75,031 B，KV 块即记忆，prompt 不拼接）+ `tools/chat_lease.py`（M3 租约守卫）+ `tools/kvslots.py`（引擎）+ `tools/session_state.py`（会话持久化）+ `docs/FEATURES.md` 的产品声明。
> 时点：b5 判读 / b6 未完成之前；本件**不依赖也不改动**任何 b5 冻结件。

## 0 目标

把已有研究原型收敛成**用户每天能直接打开用**的本地助手：一条命令启动、能记住用户说的事实、被问时答、不知道时说不知道、退出重开记忆还在、10 GB 显存内稳定。

## 1 硬约束（不可协商）

- 硬件：单机 Windows + 10 GB 显存；模型 `D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf`（8,988,110,240 B），dll `tools\kvshim_vk.dll`（50,007,552 B）。
- 单用户、本机、**无网络**、无多租户；不训练、不改模型权重。
- 记忆 = **KV 块**（磁盘可重建的派生层）；prompt 里**不拼接**记忆文本（沿用 chat.py 的“无 prompt 拼接”原则）。
- 引擎预算：VRAM 常态目标 ≤8.0 GiB，**fuse 8.6 GiB**；超 fuse 必须中止并给可读错误。
- 上下文：`N_CTX=8192`、`CHAT_START=4096`；记忆块总长 ≤4096 token，对话窗口 ≤4096 token。

## 2 入口与命令

- 启动器：双击 `start_chat.cmd`（内部 `python -X utf8 tools/chat_daily.py`），或直接跑该 python 命令。
- 交互：普通输入 = 提问；以下 `/` 命令：

| 命令 | 语义 |
|---|---|
| `/remember <文本>` | 把一段事实编码成 KV 块、入库、重建索引；返回块 id |
| `/memories` | 列出已存记忆（id / 首行 / 长度 / 创建时间） |
| `/forget <id>` / `/forget all` | 删除指定/全部记忆（含块文件与索引），二次确认 |
| `/ask <问题>` | 等价普通输入 |
| `/save [路径]` | 原子保存当前会话（默认 `kvmem/sessions/daily.json`） |
| `/load [路径]` | 恢复会话 |
| `/status` | 模型/dll pin、显存、记忆条数、当前会话 token 占用 |
| `/quit` | 退出前自动 save |

## 3 记忆与拒答语义

1. `remember` 后立即生效（同一进程内下一条问题即可用）。
2. 跨进程：退出后重开，未显式 `/load` 时**自动恢复**最近一次会话（`daily.json` 存在即恢复）。
3. 拒答：对**记忆中没有**的具体事实（金额/店名/型号/时间等），模型必须答“不知道/无法确认/记忆里没有”，不得编造。
4. 回答里有据时应能落到具体记忆；`/status` 或回答尾部可显示“依据块 id”（可选）。

## 4 资源与性能预算

| 项 | 预算 | 测量方式 |
|---|---|---|
| 冷启动到可提问 | ≤120 s | 计时 |
| 单次回答（记忆命中，≤200 输出 token） | P95 ≤60 s | 20 次采样 |
| 常驻 VRAM | ≤8.0 GiB（目标），硬上限 8.6 GiB | 引擎发射器峰值 |
| 异常退出 | 不丢已 remember 的记忆；会话文件原子写 | 强杀进程后重开验证 |

## 5 验收场景（S1–S6，全过才记“通过”）

- **S1 记与答**：`/remember` 3 条事实（店名/金额/型号）→ 逐一提问 → 3/3 答对且含具体值。
- **S2 不知道**：问 6 个记忆里没有的具体问题 → ≥5/6 明确拒答（不知道/无法确认），不编造具体值。
- **S3 跨进程持久**：S1 后 `/quit` → 重开进程 → 不 `/load` 自动恢复 → 再问 3 题 → 3/3 答对。
- **S4 删除生效**：`/forget <id>` → 同题再问 → 不再引用该事实（应拒答或答“已删除”）。
- **S5 对照**：同一问题在不挂记忆的对照会话（不加载块）→ 应拒答；证明“答对来自记忆而不是猜”。
- **S6 资源与崩溃**：全程 VRAM ≤8.6 GiB；回答中强杀进程（任务管理器/taskkill）→ 重开 → S1 的 3 条记忆仍在、可答。

## 6 证据产物

`kvmem/m2_visibility/m5/out/C-V1-ACCEPT.json`（indent=1 / ensure_ascii=False / 末尾换行 / 原子写）字段：
`schema, version, spec_pin, started_at, ended_at, model_pin, dll_pin, engine_meta, scenarios[]{id,name,pass,cases[],evidence}, resources{peak_gib, cold_start_s, answer_p50_s, answer_p95_s}, sessions[], logs[], verdict, caveats[]`。

`verdict ∈ {通过, 未通过, 未接上}`；任一场景 fail ⇒ 不得写通过；`未接上` 仅用于装置/环境不满足（须写明）。

## 7 非目标（明确不做）

- 不做多用户/远程访问/联网检索；不做安全审计与输入净化（沿用原型 caveat，文档必须披露）；
- 不做训练/微调/量化改造；不做“无限记忆”（容量受 4096 token 块与显存预算约束）；
- 不以本件替代 b5/b6 的研究结论：C 是**可用性交付**，H1 证据另见 b5。

## 8 变更控制

- 验收口径 v1.0 冻结后**不放宽**；实现变更记 `docs/_work/PRODUCT-C-CHANGELOG.md`。
- 若实现中发现某条口径物理不可达（例如延迟预算），只能**加严或如实记“未接上（口径不可达）”**，不得改口径凑通过。