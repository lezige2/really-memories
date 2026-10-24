# BRIEF · M4 写入固化（排队，M3 与 M5 放行条件之后开工）

2026-10-25 ｜ 依据 `STATUS-REPORT.md` §4.4 原文 + `mine/inspector/M4-CRITERIA.md`（判据已冻结）

## 一、Goal
让「哪些内容值得成为一块记忆」从**人写的常量**变成**自动沉淀**：
一次真实对话结束后，按冻结判据自动产出 1 块记忆并落盘，**新进程**能检索并正确回答。

## 二、已查清的接口（队长取证，直接用）
```
tools/kvslots.py:146   write_at(seq, text, pos, add_bos=True)
tools/kvslots.py:222   save(seq, path)
tools/kvslots.py:240   share(src, dst, p0=0, p1=-1)
tools/retrieval.py:115 build_index(con, verbose=True)   INDEX_VERSION = 5
tools/retrieval.py:199 search(con, query, k=3, mode="facet", explain=False)
tools/chat.py:379      _selection(con, q, k=2) -> retrieval.search(...)   # M1 索引**已接入**
tools/chat.py:57       MEMORIES = [...]   # 当前是人写常量，M4 就是要取代它
```
**更正**：MD 说「facet_budget.py 还只是实验脚本」只对那个打分脚本成立；真正检索的 `retrieval.py` 已接进 `chat.py`。
所以「新进程能检索」这一环用现成模块，不需要重建索引。

## 三、Boundary
新建 `kvmem/m2_visibility/m4/`。**不得修改** `tools/` 下任何文件（含 chat.py / kvslots.py / retrieval.py）、DLL、`kvmem/m2_v1_14b/`、`m2/`、`m5/`、`m3/`。
要复用 chat.py 的逻辑就用 import，不要复制粘贴它的代码再改。

## 四、Constraints（MD §4.4 + L6）
1. **编码时必须独占 position 0**（L6）。写入前后各做一次断言：目标 seq 在 `[0, len)` 内无其它内容；不满足则拒绝写入并报错，不许「先写了再说」。
2. 分段目标长度 ~500–1000 token；段过大受 L10 限制。
3. 判据以 `M4-CRITERIA.md` 为准：keep K1–K6 / drop D1–D7 / undecidable 五型；**属性词表封闭**，新属性报 undecidable 不许自建；
   **多值不覆盖**（旧值标 superseded，保留）；**相对时间必须锚定**（无 ts 记 undecidable，不许原样存）。
4. 取舍方向与 M5 **相反**：M4 宁多记不漏记（K1/K3/K4/K5 recall 1.0，precision ≥0.8）。**不许把两条统一。**
5. 14B + DLL `9edbafa1`；`kv q8_0` / `n_ctx 8192` / `n_predict 64`。

## 五、Acceptance Criteria
| # | 判据 |
|---|---|
| 1 | 一次对话（输入逐字给定，不许手改成「好记的」）→ 自动沉淀 **1 块** |
| 2 | 沉淀结果 = 三元组 + 证据片段，属性在封闭词表内 |
| 3 | 落盘：`write_at(seq, text, 0)` → `save` → 插入 SQLite，position 0 独占断言通过 |
| 4 | **新进程**（不是同一进程）跑 `retrieval.search` 能检索到该块 |
| 5 | **新进程**加载该块后，就该事实提问能正确回答（答案原文照抄） |
| 6 | 多值场景：同一属性第二次写入 → 旧值 superseded 且未被删除 |
| 7 | 相对时间场景：无 ts 的「下周三」→ undecidable，**不落盘**；有 ts 时按判据锚定为具体日期 |
| 8 | 寒暄/问句/assistant 发言不产生记忆（D 型逐个反例） |

## 六、Required Evidence
1. 输入对话全文（逐字）+ 分段结果 + 每个 keep/drop 判定的理由（对应 K/D 编号）；
2. position 0 独占断言的实测输出（通过/拒绝各一次）；
3. 新进程验证的完整命令与输出（必须能看到新进程的 pid 或独立的进程边界，同一进程内调用不算）；
4. 块文件路径 + sha256 + cells；
5. 第 8 项反例逐条结果；
6. 判据未覆盖、实现自己做了选择的地方，单独列一节，标注「判据空白，实现自定」。

## 七、Risks
- 最大的假验收是「同一进程里 load 一下就算新进程」——**必须真的起新进程**，证据里要能看出来；
- 判据里的「属性词表封闭」意味着实现要**拒绝**新属性，别为了方便偷偷加词；
- 不许为了通过第 5 项而把提问句改成和原文一致 —— 提问措辞由检测员另行给定。