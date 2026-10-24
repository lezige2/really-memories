# llama-mem

> 把长期记忆写进推理引擎的 KV 张量，而不是拼进 prompt 字符串。

**状态**：引擎层已封版 · 端到端路径已跑通 · 检索层达到 M1.7 · 放置层（M2）有 1 个阻塞缺陷
**最后更新**：2026-10-24 · **分支**：`persistent-memory` · **基线上游**：`8e5a58d`

---

## 1. 这个项目在做什么

主流"长期记忆"方案是应用层的：检索出文本 → 拼进 prompt → 模型读。它有三个绕不开的问题：

- 记忆越长，prompt 越贵，且和上下文窗口抢位置；
- 记忆对模型而言只是普通 token，没有任何结构上的优先级；
- 记忆的"存在"体现在应用日志里，不在模型状态里，无法审计、无法复现。

本项目的主张是**换一条路**：

> 长期记忆以 KV 张量常驻在 attention 的 key/value cache 中，由一个独立的记忆序列持有。
> 会话序列通过引擎级的引用复制（`seq_cp`）"看见"这些位置。
> **prompt 里只有问题，一个字的记忆都不注入。**

这不是把 RAG 做得更好，而是把记忆从"文本"变成"引擎状态"。因此它的正确性判据也变了：
不是"检索到了吗"，而是"**答案只能来自 KV 张量吗**"。

### 非协商项（改这些就等于换项目）

| # | 约束 | 含义 |
|---|---|---|
| 1 | 记忆不进 prompt | 端到端测试用字符注入计数验证，必须为 0 |
| 2 | 不重训模型 | 因果掩码 `p0 <= p1` 天然让会话 token 看见更早的记忆位置，无需改权重 |
| 3 | 引擎改动不碰 `ggml/` | 所有改动限制在 `src/` + `include/`，共 6 个文件、405 行 |
| 4 | 记忆是可删的派生缓存 | 真相在 `memory_source.text`，块与索引都可以从零重建 |

---

## 2. 当前状态（一屏快照）

| 层 | 组件 | 状态 | 证据 |
|---|---|---|---|
| 引擎 | KV 记忆序列 / 跨进程持久化 / 逐 cell 重排 | **封版** | `p0_1a` 16/16、`p0_1b` 15/15 |
| 会话 | detach-before-save + manifest | **封版** | `p0_2` 22/22 |
| 放置 | 右对齐槽位（B-right）/ 头洞不变式 | **封版** | `p0_4b_right` 9/9、`hole_matrix` 6/6 |
| 检索 | facet 索引 + BM25 + 属性闸门 | **M1.7** | `test_analysis` 76/76；holdout v3 见 §7 |
| 证据 | 三态决策（memory_hit / chat_only / no_evidence） | **封版** | `evidence.py` `POLICY_VERSION=1` |
| 端到端 | `chat.py` 全链路，0 字符注入 | **跑通** | 红线 **HOLDS (R1+R2+R3)** |
| 放置 M2 | 动态换入/换出 | **阻塞** | `m2_v1` 80/81，见 §8.1 |

一句话的进度：**"记忆被模型说出来"这件事已经成立；"该不该说"还不成立。**

---

## 3. 红线（任何改动都必须重新验证）

| 编号 | 内容 | 判定方式 |
|---|---|---|
| **R1** | 记忆内容永不进入 prompt | 端到端跑一遍，统计注入字符数，必须为 **0** |
| **R2** | 应用层固定文案允许存在，但必须计数、带版本、可审计 | `POLICY_VERSION` + `chars_injected` 字段 |
| **R3** | 引擎改动不越界（`src/` + `include/`，6 文件） | `git diff --stat` 固定 |

验证命令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\llama-mem\tools\check_redline.ps1
# 期望输出：RED LINE: HOLDS (R1 + R2 + R3)
```

> **R2 的边界**：拒答文案是应用层固定文本，不进入 `ask` 的输入。它被计数、带版本、可审计，
> 因此不算"污染"。但"往 prompt 加策略句"这个口子在 M1 阶段是关闭的。

---

## 4. 架构

### 4.1 三层数据，只有一层是真相

```
memory_source.text   <- 唯一真相。人写的原始事实，SQLite 表
        |
        +-- memory_block   <- 派生缓存。一份 .kvmem 状态文件（KV 张量 + cell 元数据）
        |                     可删除，可从 text 重建
        |
        +-- facet/term/doc <- 派生的派生。检索用的倒排索引
                              可删除，可从 text 重建；只返回 id 与分数，永不返回正文
```

**不变量**：索引层永远不能变成第二个记忆存储。任何"检索时顺手把正文塞回去"的实现都是倒退。

### 4.2 运行时数据流

```
 用户问题
    |
    v
+--------------+   id + score only   +--------------+
| retrieval.py | ------------------> | evidence.py  |
| facet + BM25 |                     | 三态决策      |
| 属性闸门      |                     +------+-------+
+--------------+                            |
                                   +--------+--------+
                                   v                 v
                            memory_hit         chat_only / no_evidence
                                   |                 |
                         选块 -> 挂载到槽位     拒答（生成前，模型不调用）
                                   |                 |
                                   v                 v
                          ask(prompt=问题)      固定拒答文案
```

### 4.3 引擎扩展点（C++，6 个文件）

| 能力 | 说明 |
|---|---|
| 记忆序列持有 | 一块记忆 = 一个独立 seq，含 KV 张量 + cell 元数据 |
| 跨进程持久化 | `state_seq_get_data` / `set_data`，恢复保留 cell 的 `pos` 与索取权 |
| **逐 cell 重排** | `seq_repos_local(seq, delta)`：只旋转会移动的 cell，支持逐个 cell 的 rope 补偿 |
| 零拷贝可见性 | `seq_cp` 仅做引用计数，一份记忆 N 个会话共享 |
| 会话快照 | detach-before-save + manifest，会话状态可存可还原 |

**没有改动的东西**：`ggml/` 一行未动。所有改动在 `src/` + `include/`：

```bash
git -C llama.cpp diff --stat HEAD
#  6 files changed, 405 insertions(+)
```

### 4.4 关键不变量

| 不变量 | 内容 |
|---|---|
| L3b 有损 | 移动一个块 = 1 次重量化。预算 **5 次往返 / 10 次重量化**（实测边界 25） |
| L4（修正版）| **致命条件只有一条：chat 头部正下方出现不可见空洞**。底部、块间、chat 内部、chat 尾部的空洞均无害 |
| 恢复确定性 | 块 K 逐字节一致；chat K/V 是**字节多重集相同的置换**——契约是内容精确，不是布局精确 |
| 头洞不变式 | `chat_head` 空缝 **FATAL**，其余五种情况只需记录 |
| 槽位 | 右对齐（B-right）：第 i 个槽的尾 = `CHAT_START - (i-1) * SLOT`，`SLOT=64` |
| 容量 | `LLAMA_MAX_SEQ=256`，按 5 个 seq/用户估算约 **51 个活跃用户** |

---

## 5. 里程碑与进度

### 已完成

| 里程碑 | 目标 | 结果 |
|---|---|---|
| **M1 机制验证** | 记忆只存在于 KV 中，模型能答出 | 一个 context、两个 seq，prompt 只有问题 -> 答对 |
| **持久化** | 记忆跨进程存活 | CPU/GPU x f16/q8_0 四组合全通过 |
| **P0-1a** Memory Contract | 三层数据 + 强制不变量 + fallback 语义 | 16/16 |
| **P0-1b** 派生层三态 | 块的三种状态可判定 | 15/15 |
| **P0-2** 会话权威 | detach-before-save + manifest | 22/22 |
| **P0-4** L4 修订 | 找到真正的致命条件 | `p0_4b_right` 9/9 |
| **M1-lite** | 用 facet 检索替换 `chat.py` 里写死的两条 SQL | 端到端 0 字符注入，红线 HOLDS |
| **M1.5** 三缺口 | 中文断词 / 属性级缺席 / chat_only | 部分：断词与缺席做了，chat_only 未达标 |
| **M1.6** 类型化取值 | 金额/计数/时长类型化 + 属性词表 + 负上下文 | 探针 8/8 |
| **M1.7** 属性表 schema | 一张 `PROPERTIES` 表（15 行）决定"该不该放" | 探针 8/8，但检索侧回落（见 §7） |
| **M2 v1** 放置 | 换入/换出、每步贴锚、按块记账 | 80/81，1 个阻塞缺陷 |

### 未开始

| 里程碑 | 内容 | 前置条件 |
|---|---|---|
| **M1.8** | 修三条裁判冲突（属性命中后词法不得否决 / 值模式按作用域收窄 / 罕见单字回退收紧） | M2 稳定后立刻开 |
| **M2 完整** | 淘汰策略、多会话容量、位置租约 | 先解决 §8.1 阻塞 |
| **M3** | 块生命周期管理器（创建/合并/遗忘） | M2 |
| **M4** | 写入固化（consolidation） | M3 |
| **M5** | 接地与弃答（产品级） | M1.8 |
| **P0-3** | 受控 L10 | -- |
| **P0-5** | 多用户容量 / 位置租约 | M2 |

---

## 6. 检索层设计（M1.7）

没有中文分词器，因此用**三层混合**而不是硬塞 jieba：

| 机制 | 做法 |
|---|---|
| 中文断词 | CJK 二元组 + 拉丁词串 + **罕见单字回退**（`u:` 前缀，`df <= max(2, n_docs//8)`） |
| 打分 | BM25 `k1=1.2, b=0.75` |
| 召回 | `GATE=1.30` 绝对门 + `COV_MIN=0.35` 覆盖率门 + `REL_CUT=0.55` 相对门 + `ABS_CUT=1.10` |
| 实体 facet | 实体名词只做**范围**，属性值做**判决**（实体有值 != 属性有值） |
| 缺席判定 | `PROPERTIES` 15 行表：属性闸门 -> 类型闸门；`GATED = {money, time_of_day, date, count, duration}` |
| 多子句 | 按分句切分，**每句单独过闸**，最后并集（不许整句放宽） |
| 类型化取值 | 金额上下文（`28k` / `1万5` / `5200/月`）、中文数字计数/时长、负上下文（卡号/工号/电话附近数字不算金额） |

**明确的边界**：`location` / `name` **永不作为闸门**，只作提示。它们在 dev 集上造成的误杀比漏放更贵。

---

## 7. 评测体系与最新数字

### 7.1 数据集层级

| 集合 | 规模 | 用途 | 状态 |
|---|---|---|---|
| dev-19 | 19 查询，facet 标注 | 调阈值 | **已污染**（阈值在此上调过，必须披露） |
| dev-30 | 30 查询 | 回归 | 降级为 dev |
| holdout v2 | 50 块 / 79 查询 | 一次性测量 | 已跑一次，冻结为历史 |
| **holdout v3** | 50 块 / 79 查询 | **M1.7 一次性测量** | 已跑一次（见下），现降级为 dev |

### 7.2 封存纪律

1. 新集写好后**封存**，不跑；
2. 代码冻结后**跑一次**；
3. miss 是**测量结果**，不是重跑的理由；
4. 看过的 miss 不能回头调参；要改就**另建新集**，旧集降级为 dev。

> 这条纪律的实际代价：M1.7 的数字很难看（见下），但它是**可信的难看**。

### 7.3 holdout v3（一次性，未调参）

```
recall@1 0.836   recall@3 0.914   recall@5 0.914   MRR 0.922   (64 查询)
multi: 三段全中 top-3       12/15
absent: 拒答 recall 0.200 (2/10)   拒答 precision 0.500
chat_only: 误拒 0/5   误挂 4/5
distractor: 5/5
```

### 7.4 验收对照

| 目标 | 结果 | |
|---|---|---|
| recall@3 >= 0.85 | **0.914** | 达标 |
| multi >= 14/15 | 12/15 | 未达 |
| abstain recall >= 0.70 | **0.200** | 未达 |
| abstain precision >= 0.95 | **0.500** | 未达 |
| chat_only 误挂 <= 1/5 | 4/5 | 未达 |
| over-refused = 0/5 | 0/5 | 达标 |
| distractor 5/5 | 5/5 | 达标 |
| 红线 / p0_2 | HOLDS / 22/22 | 达标 |

**3 项达标，4 项不达标。** 属性表把"找得到"抬了一档（0.875 -> 0.914），
但"该拒"这一侧更差了（abstain recall 0.400 -> 0.200）。

### 7.5 阈值披露

`GATE / COV_MIN / REL_CUT` 是在 **dev-19** 上调出来的。因此 dev-19 的分数不能当作泛化证据，
只能当作回归护栏。

---

## 8. 已知缺陷（诚实清单）

### 8.1 【阻塞】M2：4 段共享区间时 decode 失效

现象：把 4 个块用 `seq_cp` 挂进会话 seq 后，模型答不出任何一块的内容；3 个块正常。

**已排除**（都有测量，不是推测）：

| 假设 | 结论 |
|---|---|
| `seq_cp` 静默丢弃第 4 段 | **无罪**。raw cell 探针：4 段 70 cells，与期望一致，`pos_max_raw=4095`，每段 bit 全覆盖 |
| `n_tokens` / `kvshim_pos_max` 能判可见性 | 二者对 `seq_cp` 组装的序列恒为 0/-1，是 shim 的 token 空判断，不是内存事实 |
| 位置/间隙/顺序/reset/live seq | 全部否定：B-right 槽位、紧 8 cell 间隙、挤在 3968 以上、**完全无间隙连排**、交换顺序、fresh seq、reset 与否——全 MISS |
| 模型能力不足 | **控制实验通过**：同样 4 句以普通 token 写入同一位置，答对 |
| "区间栈溢出" | 源码已否：同 stream 的 `seq_cp` 只是 `for` 循环 + `cells.seq_add`，无区间合并、无定长栈 |

**当前定位**：失败与"cache 中存在 4 段共享区间"相关，**段数敏感、几何不敏感**，
落在 decode/attention 侧。

**下一步（唯一）**：分段问实验——4 段各问一次，用干净 chat seq。
上一轮跑过一次但**夹具不可信**（文本控制漏了 BOS 导致空输出；同一 engine 复用导致后续 arm 继承退化），
必须先修夹具再判读。**在控制实验绿之前，不从这组数据下任何结论。**

### 8.2 检索层：三条机制冲突（M1.8 的输入）

1. **属性闸门与词法闸门打架**：属性已把候选收窄到正确块，`COV_MIN/REL_CUT` 又把它拒了
   （问"电话"，块里写"手机号" -> 二元组不重叠 -> 空）。属性一旦确定块，词法覆盖率不该再当裁判。
2. **值模式过宽/过窄**：`birthday` 用通用日期模式，块里"合同 12月15日到期"被当成生日；
   `height` 要求 `cm`，块里只写"身高 176"。
3. **罕见单字回退**：`公积金` 靠单字"金"回退挂到 loan/salary。这条回退当初是为"我几点睡觉"加的。

### 8.3 端到端

- `chat_only` 路径依赖对话 transcript 做评测，**无法证明 KV 特有性**（演示脚本可以证明，评测不能）。
- `我车牌号是多少` / `我说的那家修车铺叫什么` 仍挂记忆而不走对话。

### 8.4 文档

`STATUS-REPORT.md` 中 `§10.6`、`§10.7`、`附录 A/B/C` **各出现两次**（历史插入操作失误）。
两份内容不完全相同，**不能自动去重**；修法：按行号保留高行号版本，删除低行号重复段，
**不要用字符串锚点自动去重**。此项后置到 M2 阻塞解除之后。

---

## 9. 构建与运行

### 9.1 环境

| 项 | 值 |
|---|---|
| 模型 | `D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf` |
| GPU | RX 6750 GRE 10 GB（Vulkan），`--gpu 99` |
| Python | `C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe`，必须 `-X utf8` |
| Shell | MSYS2 bash（Windows；无 `sha256sum`，用 Python `hashlib`）|

### 9.2 构建

```powershell
# 引擎库
$env:VULKAN_SDK='D:\llama-mem\vulkan-sdk'
cmake --build D:\llama-mem\build-vulkan --config Release --target llama

# shim / 工具
powershell -NoProfile -ExecutionPolicy Bypass -File D:\llama-mem\tools\build_tools.ps1 -Gpu -Dll -Only kvshim
```

### 9.3 自检（按顺序）

```powershell
python -X utf8 tools/freeze_check.py      # 选块层是否被改动（M2 期间必须 FROZEN）
python -X utf8 tools/test_analysis.py     # 76/76
python -X utf8 tools/p0_1a_check.py       # 16/16
python -X utf8 tools/p0_1b_check.py       # 15/15
python -X utf8 tools/p0_2_check.py        # 22/22
python -X utf8 tools/p0_4b_right.py       # 9/9
python -X utf8 tools/hole_matrix.py       # 6/6（chat_head FATAL）
python -X utf8 tools/m2_v1.py             # 80/81（已知阻塞）

powershell -NoProfile -ExecutionPolicy Bypass -File tools/check_redline.ps1
```

### 9.4 端到端演示

```powershell
python -X utf8 tools/chat.py m1        # 检索选块 + 挂载 + 生成
python -X utf8 tools/states_demo.py    # 三态决策演示（memory_hit / chat_only / no_evidence）
```

### 9.5 一次性评测（**不要随手重跑**）

```powershell
python -X utf8 tools/holdout_v3.py     # 已跑一次，见 §7.2 封存纪律
```

---

## 10. 目录结构

```
llama-mem/
+-- llama.cpp/              # 我们的 fork，分支 persistent-memory（引擎改动只在这里）
+-- llama.cpp-upstream/     # 上游纯净克隆，只读基线（8e5a58d）
+-- build-cpu/              # CPU 构建产物
+-- build-vulkan/           # Vulkan 构建产物
+-- vulkan-sdk/             # SDK 1.4.363.0，项目内自包含
+-- bin/llama-vulkan/       # 预编译 server（性能基线 / 回退）
+-- kvmem/                  # 块文件（.kvmem）、索引、评测报告、长期记忆库
+-- legacy/                 # 旧外挂记忆项目留档（M2/M3 从这里取）
+-- docs/
|   +-- README-PHASE1-ENGINE.md   # 早期"引擎可行性阶段"文档（已归档，仍有价值）
+-- tools/                  # 全部 Python 与 C++ 工具（见下表）
+-- STATUS-REPORT.md        # 主技术报告（含全部踩坑与实测）
+-- README-HANDOFF.md       # 引擎交接（行号、改动位置、构建）
+-- README-HANDOFF-2.md     # 第二轮交接（shift 实测、训练成本、文献地图）
```

### tools/ 关键文件

| 文件 | 作用 | 指纹 / 版本 |
|---|---|---|
| `analysis.py` | 归一化 + 类型化取值 + `PROPERTIES` 表 | `9b9368524422f352` · `ANALYSIS_VERSION=4` |
| `retrieval.py` | facet 索引 + BM25 + 闸门 | `c8e9e332ef8fd367` · `INDEX_VERSION=5` |
| `evidence.py` | 三态决策 + 固定拒答文案 | `dccf7f010eaf9c7e` · `POLICY_VERSION=1` |
| `test_analysis.py` | 分析层表驱动单测（76 条） | `cec5a83fd555e46d` |
| `freeze_check.py` | 选块层冻结的**强制执行器** | `8decec8a4715bc8b` |
| `kvslots.py` | 引擎封装（Python <-> kvshim） | -- |
| `memory_source.py` | 三层数据的真相层与派生层 | -- |
| `m2_v1.py` | M2 放置夹具（80/81） | -- |
| `m2_probe_cells.py` | raw cell 探针（证明 `seq_cp` 无罪） | -- |
| `m2_probe_segments.py` | 分段问探针（**夹具待修**） | -- |
| `holdout_v3.py` | 封存评测集（79 查询） | 已跑一次 |

---

## 11. 版本与冻结

```
INDEX_VERSION    = 5
ANALYSIS_VERSION = 4
POLICY_VERSION   = 1
```

M2 期间，`analysis.py` / `retrieval.py` / `evidence.py` 及三个阈值
（`GATE=1.30`、`COV_MIN=0.35`、`REL_CUT=0.55`）由 `freeze_check.py` 钉死：
任何一项变动 -> 退出码非零 -> **M2 的测量自动标记为"不可归因"**。

要改选块层，必须在同一提交里更新指纹，并在报告里说明原因。悄悄漂移是这个文件存在的唯一理由。

---

## 12. 路线图

```
[已完成] 引擎封版 -> 端到端 -> M1.7
                    |
                    v
[当前]   M2 放置 -- 阻塞于 §8.1（4 段共享区间 decode 失效）
                    |
                    v
[承诺]   M1.8（三条裁判冲突，一个迭代，新集封存跑一次）
         达标线：abstain precision >=0.95 / recall >=0.70 / recall@3 >=0.85 /
                 chat_only 误挂 <=1/5 / multi >=14/15 / distractor 5/5
         不达标即停，不设 M1.9，剩余缺口写进产品限制
                    |
                    v
[其后]   M2 完整（淘汰策略 / 多会话容量 / 位置租约）-> M3 -> M4 -> M5
```

---

## 13. 术语表

| 术语 | 含义 |
|---|---|
| **块 / block** | 一段独立事实对应的 KV 张量 + cell 元数据，存为 `.kvmem` |
| **槽 / slot** | 会话上下文中预留给块的位置区间，`SLOT=64` cell |
| **锚 / anchor** | `CHAT_START`，会话 token 的起始位置；顶块必须贴住它 |
| **头洞** | chat 起始位置正下方的空 cell 间隙——**唯一致命的空洞** |
| **重量化** | 移动块导致的 KV 精度损失，不可逆，按次累计 |
| **B-right** | 右对齐槽位布局：每条槽的尾对齐，块尾贴槽尾 |
| **三态** | `memory_hit` / `chat_only` / `no_evidence` |
| **封存** | 数据集写好后不跑，等代码冻结后跑一次，结果不可用于调参 |
| **误挂** | 该拒答却挂上了记忆块（abstain precision 的反面） |

---

## 14. 一句话留给下一个人

> 这个项目最难的部分不是"让模型记住"，而是**"让模型在没记住的时候闭嘴"**。
> 前者已经成立，后者还没有。所以任何提高召回率的改动，都要先问一句：
> **它是不是用"该拒的时候也挂上"换来的？**

---

*文档索引：技术细节见 `STATUS-REPORT.md`（含全部实测与踩坑）；引擎交接见
`README-HANDOFF.md` / `README-HANDOFF-2.md`；早期可行性文档见 `docs/README-PHASE1-ENGINE.md`。*
