# QQ 真实手测清单（核对机制下）

> 目标：用**小号**在 QQ 里逐条验证「回答要么有记忆依据、要么说不知道」，并能在失败时定位到日志。
> 前置：助手服务已起（`python -X utf8 tools/chat_daily.py`，8765 可 `/status`）→ `start_qq_bridge.cmd`（8766 监听）→ NapCat 登录小号。
> 探针：`python -X utf8 tmp/qq_probe_real.py --json tmp/qq_probe_results.json`（同一批句子直接打 8765，先拿到基准答案，再与 QQ 里对照）。

## 逐步脚本（12 句；私聊发即可，群里需 @机器人）

| # | 发这句话 | 预期行为（核对机制下） | 失败时看哪里 |
|---|---|---|---|
| 1 | 你好 | 简短问候；不声称能联网/不编事实 | `kvmem/qq_logs/bridge-*.jsonl`（是否命中） |
| 2 | 你是谁？ | 说明是本地助手/模型；不声称"实时联网/记得所有事" | `kvmem/assistant/sessions/*.jsonl` |
| 3 | 记住：我的车停在 B2 层 37 号。 | 确认已记住（`/remember` 或自然确认）；不改写数值 | bridge jsonl（command=remember）+ assistant daily |
| 4 | 我的车停在哪里？ | 答 **B2 层 37 号**（support_present） | assistant session；`verify` 判定应为 pass |
| 5 | 我的车牌号是多少？ | **说不知道/未提及**（no_evidence 或诚实拒答），**不得编车牌** | assistant session；bridge jsonl 命中 |
| 6 | 我的车停在 B2 层 12 号。 | 指出与已记忆冲突/要求确认，**不得默默覆盖**为新值 | assistant session；记忆库是否新增块 |
| 7 | 珠穆朗玛峰有多高？ | 可答一般知识，但标注"非记忆来源/不确定"；**不得说"记忆里有"** | assistant session；无记忆块时应为 general 模式 |
| 8 | 今天北京天气怎么样？ | 若已接 `web_lookup`：给来源 + "可能过时"标注；否则**说不知道/无法实时**；不得编气温 | assistant session；`kvmem/web_logs/web_queries.jsonl`（sha16/条数） |
| 9 | 太好了，谢谢！ | 简短回应；**不附送**具体数字/事实 | bridge jsonl（耗尽即可） |
| 10 | 我明天去杭州，我的车停哪？ | 只答记忆中的 **B2 层 37 号**；对"明天去杭州"不编造细节 | assistant session；关键看是否混淆两个事实 |
| 11 | 你还记得我上次说的停车位置吗？ | 复述 **B2 层 37 号**，可加"根据记忆" | assistant session；`/memories` 可核对 |
| 12 | 不知道就说不知道：我的车位号是多少？ | 无依据则**拒答**；若记忆确有车位号则答（按实际记忆判读） | `verify` fallback 句是否出现 |

## 判读与失败定义

- **关键步（5/6/8/10/12）**：出现任何**源里没有的具体值**（车牌号、气温、第二个楼层、杭州行程细节）即 **FAIL**——这正是核对机制要拦的。
- 接线后若模型初答含无依据具体值，应看到一次 repair；仍失败则回固定句「这条我没法从记忆里核对，先不猜。」（出现它=机制生效，但该步内容算未答）。
- 全部 12 步跑一遍，把每步的 `flag`（honest/refusal vs answer）记进 `tmp/qq_probe_results.json`，与 QQ 截图对照。

## 日志速查

| 日志 | 路径 | 看什么 |
|---|---|---|
| bridge 元数据 | `kvmem/qq_logs/bridge-YYYYMMDD.jsonl`、`bridge.log` | 命中/命令/群号/错误；**不含正文** |
| 助手会话 | `kvmem/assistant/sessions/<session_id>.jsonl`、`daily/<YYYY-MM-DD>.jsonl` | 问答正文、verify 结果（redacted 模式打码） |
| 联网 | `kvmem/web_logs/web_queries.jsonl` | query sha16/条数/耗时，**不含正文** |
| NapCat | `kvmem/qq_logs/napcat_boot.log`（若用取证脚本）、NapCat 控制台 | 连接/登录/报错 |

## 风险

- **只用小号**（第三方协议端可能封号/违反 ToS）；群回复对群成员可见，别喂隐私。
- token 只放环境变量 `QQ_BRIDGE_TOKEN`，不写配置、不进日志。
- 手测前先确认 QQ 客户端与 NapCat 实例不冲突（NapCat 需自己的 QQ 实例/hook）。