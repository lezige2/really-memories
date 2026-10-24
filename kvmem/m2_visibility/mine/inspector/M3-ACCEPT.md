# M3 验收 · 块生命周期（50 轮 attach/detach + pin）

验收人：检测员 inspector ｜ 2026-10-25 ｜ 对象：kvmem/m2_visibility/m3/
纪律：**先读 schema 再取数**（这次先 dump 了 run json 的 top keys 与嵌套 keys 才写取数表达式，不猜字段名）。产物自报值一律重算。

## 0 我从原文重算的事实

schema = m3_lifecycle_v2 ｜ rounds 50/50 ｜ engine.dll_sha256_measured = 9edbafa1… ｜ n_predict = 64

| 判据 | 我重算 | 结论 |
|---|---|---|
| 1 cell 占用稳定 | attach_cells 去重 = **[51]**（50 轮全同）；after_detach_block_cells 去重 = **[0]** | 通过 |
| 2 pos_max 稳定 | attach_raw_pos_max 去重 = **[4095]**，50 轮恒定 | 通过 |
| 3 答案稳定 | answer_sha16_addr 全 50 轮同一值 **852a5e5e6ab70eeb**；addr_ok **50/50** | 通过 |
| 4 块文件零回写 | 每块 block_sha16 单值（home 73843fc5 / project 536eac03 / habit f6f8e85c）；**磁盘实测与 at_load 逐个相等，3/3** | 通过 |
| 5 pin/危险顺序 | reset_refused=**false**；source_cells **21→0**；source_pos_max **4095→-1**；live_cells **51→51**；addr_hit_after_reset=**true**；文件 sha 未变；restore 重载 **21** cell、pos_max 4095、sha 一致、答案回来 | 见 §1（结论须改写） |
| 6 token 账本 | visible_cells 51 但 n_tokens_owned **0**；shim 报 pos_max **-1** vs raw **4095**；naive pos=0 → **空答案**；save 已挂载 seq → **0 字节、无文件** | 通过（量化成立） |

_测试脚本 _test_lease.py 我自己跑了：**0 failed，EXIT=0**（7 组：危险顺序被拒 / 未引用 seq 照常 reset / detach 后放行 / force 留痕 / reset_all 陷阱 / 空块挂载被拒 / 状态可查）。

run_m3_50_INVALID.json：schema m3_lifecycle_v1，cell 序列全 0、pos_max 全 -1、r50_all_three_hit=false —— 与 README §6 的解释一致（第一版驱动每轮调 reset_all，把三个块 seq 也清了，于是 attach 到的全是空序列）。**保留不删、没静默重试，这点做得对。**

### 0.1 一个容易被误读的数（我先踩了一下，写出来防别人再踩）

after_detach_cells 的序列是 [221, 73, 73, …, 221(第 25 轮), …, 221(第 50 轮)]，**不是"占用在增长"**：
第 1/25/50 轮问了三句（对话自有 token 148），其余轮只问一句（73）。所以：
- "cell 占用稳定"这条**只对 attach_cells=51 成立**；
- after_detach_cells 是**对话自有 token**，随问句数变化，**不能当泄漏指标**；它恰好也是判据 6 那个账本缺口的显形面。

## 1 判定一：措辞把 MD 讲偏了 —— 同意你的倾向，并给逐字写法

**先还原 MD 说了什么。** §4.3 原文是「块被对话引用时不能 reset 源 seq（否则引用计数悬空）」。
这是**设计规则 + 后果断言**；它**没有**"引擎必须失败"的预测。
"会不会拒绝"是**派单里的问法**（问题框架），不是 MD 的断言。两者混在一起，会让人以为 MD 错了两处，实际只错一处。

**实测推翻了什么。** reset 源 seq 之后：对话的 51 cells 仍在（引用由 live 序列持有）、答案 sha 逐字不变、addr_hit 仍 true
⇒ **引用没有悬空**。被推翻的是那句**后果断言**。

**实测真正损失的是什么。** 源 seq **静默失效**：source_cells 21→0、source_pos_max 4095→-1、reset 正常返回、无异常、无错误码；
之后只能靠**文件重载**恢复（reloaded 21 cells、sha 一致、答案回来）。
危险不是"引用悬空导致对话崩"，而是"**块句柄悄悄变空，谁也没报错**"。

**逐字建议（四词纪律口径）**：
> 就「引用计数悬空」这一**后果断言**而言：**无效应**（reset 源 seq 后对话答案逐字不变，addr 命中 50/50 不受影响）。
> 真正的损失不在悬空，而在**源 seq 句柄静默失效**（21 cell → 0、pos_max → -1、reset 无异常返回），只能靠文件重载恢复。
> 「必须失败」不是 MD 的预设，是本轮派单的问法，**不得写进对 MD 的判定**。

**并须补一句用途说明**：pin 机制**仍应保留**，但理由要换 —— 不是"防止悬空"（本轮没发生），
而是**把静默失效变成显式拒绝**（可诊断性收益）。单测里"#1 危险顺序被拒"的价值就在这里，
不是"证明 MD 对了"。**不许把这轮写成"MD 的规则得到验证"**：规则的验证需要有悬空发生，本轮恰恰没有。

## 2 判定二：护栏没有被任何真实路径使用 —— 记「就绪·未接入」，不算完成度

**我核过（不是听你说）**：全仓库 grep m3_lease，只命中 **_test_lease.py:10** 一行 import。
没有任何真实驱动、没有任何产品路径 import 它。⇒ 它是**库 + 单测**，不是防护。

顺带更正你的一个数字：tools/chat.py 的 reset 调用点我 grep 到 **4 处**（:176、:284、:444、:449），不是 3 处。
本轮不许改 ⇒ 产品路径的防护覆盖率 = **0**。

**逐字记法（建议直接采用）**：
> **判据 5 的结论：护栏就绪、未接入。** 库（m3_lease.py）与 7 组单测存在且我重跑 0 failed，
> 但**真实路径零调用**；tools/chat.py 的 4 处 eng.reset(...)（:176/:284/:444/:449）仍是裸露的。
> 因此本条**不计入 M3 完成度**，只记「组件就绪」；M3 的验收不因它加勾。

**接入要求（移交 M4，写进 M4 验收）**：
1. M4 驱动是第一个真实消费者（会走 write → save → reset → reload），必须在驱动里真实调用 leases，不是只 import；
2. 接入的验收必须是**真实路径**测试：驱动里跑一次 write→attach→reset→restore 全链路，并在 run json 里留下
   leases 的**拒绝记录**（哪一次被拒、拒绝理由），否则无法证明它真的拦住了东西；
3. 接入理由按 §1 改写为"可诊断性"，不是"防悬空"。

## 3 我另外发现的三件（记录，不改本轮判定）

1. **run_m3_50_INVALID.json 内部没有 invalid 标记**（无 invalid_reason 字段），只有文件名 + README §6。
   它还是 v1 schema，字段名与正式文件不同。将来有人按目录批量统计 json，会把它当**一次有效的失败实验**。
   建议：json 内加 {"invalid": true, "invalid_reason": "reset_all 清掉了块 seq，attach 到空序列"}。
2. **after_detach_cells 的 73/221 双值**（见 §0.1）建议写进 README §11 字段说明，否则下一个人会读成"占用在长"。
3. **shim 报 pos_max = -1 而 raw 实际 4095**：不是 M3 的错，但它意味着**任何用 shim 的 pos_max 做判断的上层都是错的**。
   M4/M5 或后续模块若要用 pos_max，必须用 raw。建议写进交接稿，别只留在 ledger 字段里。

## 4 验收结论

**通过（附三个放行条件）。** 50 轮 attach/detach 的 cells / pos_max / answer 三项稳定有逐轮数据支撑；
块文件零回写我按磁盘实测复核（3/3）；账本缺口有定量证据（naive pos → 空答案、save 0 字节）。

**但 §1 的措辞必须改写，§2 那一条不能算勾。** 三条放行条件：
1. 报告里「否定了『必须失败』这一预设」改成 §1 的逐字写法（后果断言被推翻 + 句柄静默失效）；
2. INVALID 文件内部加 invalid 标记，或 README 明确"按目录扫描须过滤 INVALID"；
3. M4 接入 leases 的真实路径并留痕 —— **在此之前，M3 的"防静默失效"在真实产品路径上等于没有**。

**边界声明**：本轮证明的是"50 轮 attach/detach 之后三块几何/答案/文件不变"，以及"reset 源 seq 不会让对话的引用悬空"。
**没有**证明弱 GPU 长时间运行、多用户并发、attach/detach 与 save 交叉时的不变性 —— 那些仍是未检验。
