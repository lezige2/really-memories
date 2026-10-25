# llama-mem

> **as-of**：本文是 2026-10-25 快照。**现行入口**：本地 `docs/_work/ANCHORS-CURRENT.md`（坐标以该文件内容为准，**banner 不钉 sha**）。
> 本文中的哈希是**签署时坐标**，不代表现值；引任何 sha 前先查 ANCHORS-CURRENT 的两列四态。
> **权威口径（2026-10-25 收敛；与 `PROGRESS §0.1` 头、`docs/_work/INDEX.md` 逐字一致）**：**里程碑状态以 `PROGRESS-AND-ROADMAP.md` §13 各收口节为准；§2.1/§2.2 只是索引/摘要（§1883 行自述"本表是摘要，不是权威"）；§0.1 只记录 80 份档案回填公告；坐标/sha 以 `docs/_work/ANCHORS-CURRENT.md` 两列四态为准。**
> **发布口径**：**本仓库只发布本 README 一份文档**。完整状态 / 判决 / 证据文档仅存于本地工作区（`docs/_work/`，含索引 `INDEX.md`、现行锚 `ANCHORS-CURRENT.md`；状态文档 `PROGRESS-AND-ROADMAP.md`、能力账 `FEATURES.md` 亦仅本地）。下文出现的这些路径**都是本地线索，不承诺可点**。

> **把长期记忆做进推理引擎的 KV 张量里，而不是拼进 prompt 字符串。**
> 本地工作树 `D:\llama-mem` ｜ llama.cpp fork ｜ 分支 `persistent-memory` ｜ 基线 commit `8e5a58d`

---

## 一句话

这个项目不改 prompt，改引擎：把一段记忆编码成 **KV 张量块**（`.kvmem`）常驻在 attention 里，
在它紧贴其后提问 —— **删掉对话历史，记忆依然可被读出**。
证据与未闭项见本地 `PROGRESS-AND-ROADMAP.md`（不随本仓库发布）。

---

## 1 这是什么

### 1.1 定位

| 项 | 内容 |
|---|---|
| 项目名 | **llama-mem**（工作树 `D:\llama-mem`） |
| 一句话定位 | **把长期记忆做进推理引擎的 KV 张量里，而不是拼进 prompt 字符串。** |
| 关键差别 | 记忆不在 prompt 文本里，它在 KV cache 里；**删掉对话历史，记忆依然可被读出**。 |
| 补丁规模 | **6 文件 / 实时 600 insertions / 0 deletions**（归档版 500） |
| 四层成分 | C++ 引擎补丁 + C++ shim（探针挂载） + Python 工具链 + 实验产物树 `kvmem/` |

### 1.2 路线来源：前身项目 biomem

前身是 **biomem** —— 一个应用层记忆的聊天智能体：SQLite「海马体」 + 多路轻量索引 + 有限工作记忆
+ 巩固 / 遗忘曲线，16 GB 内存 / 10 GB 显存可跑（7B 大脑）。
它把记忆**拼装进上下文**；本项目是它「**改引擎**」的继任者 —— 同一个产品直觉，换掉实现层。
这就是为什么本仓库的起点不是「更好的 prompt」，而是 `llama-kv-cache.cpp`。

### 1.3 「kvmem」的两种含义（别混）

| 写法 | 含义 |
|---|---|
| `kvmem/`（目录） | **实验产物树**：放实验产物、夹具、预登记（PREREG）、验收（ACCEPT）、判据（CRITERIA）、台账 |
| `*.kvmem`（文件后缀） | **记忆块二进制本体**：被 `.gitignore` 排除，clone 后拿不到 |

---

## 2 为什么改引擎：主流「记忆」方案的三个绕不开的问题

### 2.1 prompt 变贵

长上下文是把记忆塞进 context 的直接办法，但成本随 token 线性增长：每次对话都要为**全部**历史付费，
而其中绝大部分与当前问题无关。上下文越长，首 token 延迟与显存占用越难看。

### 2.2 记忆没有结构优先级

prompt 里的记忆是一段**扁平文本**：模型无法区分「这是用户三个月前随口说的」和「这是用户昨天强调的」，
也无法按访问频次、置信度、来源权威性做淘汰。文本层面没有「这一条是一等公民、那一条是缓存」的位置。

### 2.3 不可审计

一段被拼进 prompt 的记忆，事后无法回答：「这次回答用了哪几条记忆？它来自哪个文件？删掉它会怎样？」
—— 因为记忆已经变成自然语言的一部分，与幻觉、复述、改写混在一起，无法分离取证。

### 2.4 结论：淘汰应用层拼字符串

> **动机段（原文照录，出处 `docs/legacy-2026-10-24/README.md` §1；原件位于本地备份快照 `D:/llama-mem-backup-2026-10-25/` 同相对路径，不随仓库发布）**：
>
> > 主流"长期记忆"方案是应用层的：检索出文本 → 拼进 prompt → 模型读。它有三个绕不开的问题：
> >
> > - 记忆越长，prompt 越贵，且和上下文窗口抢位置；
> > - 记忆对模型而言只是普通 token，没有任何结构上的优先级；
> > - 记忆的"存在"体现在应用日志里，不在模型状态里，无法审计、无法复现。
>
> 这三条就是上一节的三问题；本项目的主张与它当年的表述一致：**prompt 里只有问题，一个字的记忆都不注入。**

三条问题对应的三个产品要求：**成本可控 / 有结构优先级 / 可审计**。
这三条后来在工程上落成红线（见 §11）与 `Memory Contract`（见本地进度文档 **§10.9**）。

---

## 3 本项目的做法与三层现状

### 3.1 记忆在 KV cache 里，不在 prompt 里

一段记忆被编码一次，产出 `.kvmem` 块文件（K/V 张量 + 元数据）。挂载时：

1. 把块的 K/V 写进对话序列占据的 **position 区间**（例如 `[4005,4096)`）；
2. 用 `seq_cp` 把块的序列**引用**给对话序列（refcount，零拷贝）；
3. 对话在**紧贴块尾**的位置继续生成 —— 注意力自然覆盖这块记忆，而 prompt 里一个字都没有。

### 3.2 三层现状总表

| 层 | 状态 | 一句话 |
|---|---|---|
| **引擎层** | **真的** | `seq_cp` 引用挂载、`seq_repos_local` 局部重旋转、Hadamard 三明治都在代码里，有验证脚本 |
| **记忆读取能力** | **半真的** | 3 个块挂上去能读（B 臂 15/15）；4 个块挂上去读不全（A 臂 2/4、C 臂 1/4）；n=5 重复性检验已做、结果逐字节稳定（**7B 代读数**；14B 上该症状不复现，见 §5 收敛注） |
| **产品层** | **有骨架，仍无服务端** | 无序列池、无服务端 slot 改造、无 pin 落地；可跑通单会话端到端 + 跨进程恢复 |

> 第三层旧版文档写作「产品层是空的」（`PROJECT-STATE.md:31` 口径）。**现行口径是「有骨架，仍无服务端」**：
> M3 生命周期、M4 写入固化、M5 接地弃答已经落地并验收（详见本地进度文档 §2 里程碑表），
> 但这些都是**单会话、单进程、夹具驱动**的；服务器侧（`tools/server`）从未改造。
> **注意**：`PROJECT-STATE.md:31` 那句「M3/M4/M5 零代码」在 2026-10-25 之后已过期，
> 本文与进度文档一律不沿用该说法。

### 3.3 逐格状态指路

不要把上表当成「有 3 个布尔」。逐格（每个里程碑、每个探针）的状态、强度、锚都在
本地 `PROGRESS-AND-ROADMAP.md` §2 的 21 行里程碑表里，每一格都带证据路径与复算命令
（该文件不随本仓库发布）。

---

## 4 核心机制

### 4.1 记忆序列以 KV 张量常驻（`seq_cp` 引用计数挂载）

记忆块有自己的 seq id。挂载不是「把文本贴进去」，而是 `seq_cp`：**refcount only, zero copy**。
因此同一块可以被多个对话序列同时引用，而 cell 只存一份。
（接口锚：`tools/chat.py:208-212` → `eng.share` → `llama_memory_seq_cp`。）

### 4.2 位置重排：`seq_repos_local` 只旋转被移动的 cell

块要挪位置时，**不能**把整段 K 重新反量化再量化（那会磨损，见 L3b：约 10 次往返内安全）。
`seq_repos_local` 只对**位移区间内**的 cell 做 CPU 上 dequant → rope → requantize。
（`llama-kv-cache.cpp:675` 新增块。）

### 4.3 Hadamard 三明治（`H → rope → H`）

K 存在 Walsh–Hadamard 基里，**RoPE 与 H 不对易**。所以旋转必须走 `逆H → RoPE → 正H` 三明治，
顺序写错就静默损坏（`llama-kv-cache.cpp:612-634,820,857-866` 新增块）。

### 4.4 `kv_unified=true` 下靠 position 区间区分

共享单一 KV 池时，不同记忆块**只靠 position 区间区分**；同一 position 的写入会**复用 cell** 并互相覆盖 ——
这是「块必须独占 position 0」这条硬约束的由来（见 M4）。

### 4.5 补丁形态（为什么存成 patch 文件而不是子目录）

`llama.cpp/` 是**嵌套 git 仓库**，把它纳入父仓库只会存一个 gitlink 指针，历史与 diff 全部丢失。
所以改动统一导出为 `patches/persistent-memory.patch` + `patches/MANIFEST.txt`（sha256 / numstat）。
**规模：6 文件 / 600 insertions / 0 deletions**（归档版 500，差值 100 行是当前唯一红项，见 §6.2）。

---

## 5 当前状态与阻塞：E10（4 段共享区间下的可见性）

> **2026-10-25 收敛注**：E10 的症状在 14B 上**不复现**，M2.5（可见性收口）已**销号**（本地 `PROGRESS-AND-ROADMAP.md` §2.2 / §13.11）。本节保留为 **7B 代现场记录** —— 读它是为了知道"当时为什么这么判"，**不是现行阻塞**。现行一句话：**M2 规划器 / M2 完整 / M4 / M5 均已验收**（同上 §13）。

### 5.1 一句话

**E10 = 已定位，未修复。** 它不是存储缺陷，也不是可见性缺陷 —— 记忆**确实写进去了、也确实可见**
（cell 层 `home` 21/21 覆盖、无重叠），**失败发生在生成侧**：挂到第 4 个块后，模型拿到的信息
无法稳定约束答案。引擎代码为此**未改一行**。

### 5.2 遍历表（ISOLATION-REPORT §2，冻结哈希 `cb11df4453756882`，267 行）

| 臂 | 配置 | 可读块 / 总数 |
|---|---|---|
| A | `home` 单块 | **0/5** |
| A | `project` 单块 | 5/5 |
| A | `habit` 单块 | **0/5** |
| A | `car`（无关块） | 5/5 |
| B | 3 块（`home+project+habit`） | **15/15** |
| C | 4 块 | **5/20**（C 恒 1/4，只有 `habit` 过） |

读法：单块能读不等于「块有效」；**3 块比 1 块更容易全对，4 块比 3 块难得多** —— 变量是「块之间的关系与总负载」，
不是「块本身在不在」。

### 5.3 七条被逐一排除的假设（ISOLATION-REPORT §3）

掩码层、存储层、cell 覆盖、位置重叠、量化、token 预算、注意力窗口 —— 七条各自用一对可判实验排除，
**没有一条能解释 3 块通过、4 块失败**。剩下唯一自洽的写法见 §5.4。

### 5.4 掩码四格表落位「②己」

掩码层两臂各 100 条块行，`masked > 0` 的 **0 条** —— 也就是说「被 mask 掉的记忆」这个解释不成立：
四格表里 E10 落在「**②己：信息在场且可达**」这一格，即问题不在「块看不见」，
而在「看见了却用不对」。掩码偏置探针进一步证明：**信息在场且可达，只差半个对数单位**。

### 5.5 下一步不是再测一条布局

这是本项目最容易走错的一步：E10 的下一步**不是**再测一条布局、再换一个 spacing，而是
**改引擎**（装注意力仪表 / 改路由 / 必要时整体编码），见本地进度文档 §13.6。
判据：布局空间的可判实验基本做完了（2×2 四格 + 第 5 点已把「格数」「副本 vs 改写」两个量分离掉）。

---

## 6 怎么跑

### 6.1 `bash verify.sh` —— 12 项关系断言（一键复算）

```bash
cd /d/llama-mem        # Git Bash / MSYS2
bash verify.sh
```

当前实测：**12 项断言，ALL PASS（rc 0）**（2026-10-25 尺子统一后；见 §6.2）。

### 6.2 补丁规模：实时 600 / 归档 500（关系断言，不再写死数字）

`verify.sh` 的第 1–4 项现在是**关系断言**而不是字面量：`实时 diff == MANIFEST 声明 == 600/0`、
`归档基线 == MANIFEST 的 archive 声明 == 500/0`、且 `归档基线 != 实时`（500 确实不是现行补丁）。
所以「实时比归档多 100 行」是**已登记的历史事实**（`MANIFEST` 记 600 版、500 版标 archive），**不再是红项**；
写死 `500/0` 会让合法演进直接打红，故改成关系式。差值全部落在 `src/llama-kv-cache.cpp`。

### 6.3 退出码陷阱（不许犯）

```bash
# 错：取到的是 tail 的退出码，不是 python 的
python some_check.py | tail -3; echo $?

# 对：
python some_check.py > /tmp/out.txt; echo rc=$?; tail -3 /tmp/out.txt
```

经管道取退出码，取到的是**管道末端命令**的码。这条曾让「我核过 rc」的陈述失效过一次。

### 6.4 `tools/` 与 `bin/` 的最小用法

| 目标 | 命令 |
|---|---|
| 造块 / 挂块 / 提问 | `python tools/chat.py build` → `python tools/chat.py ask "<问题>"` |
| 跨进程保存 / 恢复 | `python tools/chat.py save` / `python tools/chat.py load` |
| 查看/写入 KV cell | `tools/kvslots.py:146 write_at(seq, text, pos, add_bos=True)`、`:222 save(seq, path)` |
| 引擎二进制 | `bin/llama-vulkan/`（Vulkan 构建）；`tools/kvshim_vk.dll`（shim） |
| 全项目加载参数串 | `-ngl 99 -c 8192`，KV `q8_0`，`n_seq 8`，`n_predict 64`，位置锚 `4096`（14B 线） |

复算命令的完整四段（hashlib / `check_m3_prereg_consistency` / `check_m3_injection` / `check_ablate_run`）
见本地进度文档 §15.3（不随仓库发布）。

---

## 7 仓库结构与目录

### 7.1 顶层目录表

| 路径 | 是什么 |
|---|---|
| `README.md` | **唯一对外文档**（本文；GitHub 只发布这一份文档） |
| `PROGRESS-AND-ROADMAP.md` | 进度与未来开发的唯一长篇文档（里程碑细节 / 判据原文 / 未闭项 / 纪律） |
| `PROJECT-STATE.md` | 引擎层判定总表（E1–E10 / S1–S3 / P1–P8）。**内容已并入本地 `PROGRESS-AND-ROADMAP.md` §3/§17；工作区副本已于 2026-10-25 20:20 按字节回填（史料，不随仓库发布）**。位于仓库根，不在 `docs/` |
| `docs/` | `_work/`（**本地文档库**：索引 `INDEX.md` + 现行锚 + 判决/复核 + 合并台账；不随仓库发布）、`README-PHASE1-ENGINE.md`（已并入本文，原件保留）、`legacy-2026-10-24/`（史料；不随仓库发布） |
| `patches/` | `persistent-memory.patch` + `MANIFEST.txt`（sha256 / numstat） |
| `kvmem/` | 实验产物树：块、夹具、预登记、验收、判据、租约日志、会话库 |
| `tools/` | Python 工具链 + C++ shim 源：`chat.py`、`kvslots.py`、`m3_lease.py`、`chat_lease.py`、`memory_source.py`、`facet_index.py`、`freeze_check.py` … |
| `bin/llama-vulkan/` | Vulkan 构建产物（`llama-connect.exe` 等） |
| `llama.cpp/` | 我们的 fork（分支 `persistent-memory`，**嵌套 git 仓库**）—— **原样未动** |
| `llama.cpp-upstream/` | 上游纯净克隆（只读基线 `8e5a58d`）—— **原样未动** |
| ~~备份快照~~ | **已搬出仓库**：85 份被合并 md 的完整副本在 **`D:\llama-mem-backup-2026-10-25\`**（仓库外、同盘符、保留相对路径），本表不含它 |

> 历史漂移已修：旧 README 的结构表写 `docs/PROJECT-STATE.md`，**实际在仓库根**。
> 引用一律用根路径 `PROJECT-STATE.md`。

### 7.2 `kvmem/` 是证据，不是文档

**整合前实测口径（唯一计数来源 = 合并台账 §1）**：

| 维度 | 数 |
|---|---|
| 项目自有 md | **85 份 / 1,707,063 B**（≈ 1.63 MiB） |
| vendored 两树 md | **258 份**（`llama.cpp` 129 + `llama.cpp-upstream` 129），**未动** |
| 合计 | **343 份** |

这些 md 是**实验当场凭据**（预登记、验收、判据、逐轮表、盲写清单、租约日志），不是教程。
读它们的目的只有两个：**复算一个结论**，或**判断一条旧说法是否已作废**。
本 README 与进度文档**不再维护「kvmem 下有多少份 md」这类会漂移的计数** —— 计数一律以台账为唯一来源。

### 7.3 不入库的内容

`*.gguf`（模型） / `*.kvmem`（块） / `build*/` / `bin/` / `*.db` / `runs_*/*.json`（跑批原始产物） / `.env`。
后果很重要：**clone 之后原始 run json 与块文件都拿不到**，所以证据目录 `kvmem/m2_7b/evidence/t0NN/`
里存的是**逐字节副本 + 原样命令行**，否则「证据不存在」。

### 7.4 锚的两类

| 类型 | 定义 | 用法 |
|---|---|---|
| **仓库内可复算锚** | 产物文件在库里，任何人 `sha256sum` 即可复现前 16 位 | 可直接引用，例如 `run_m3_lifecycle_50_v4.json = ef3d1e8859add5b0` |
| **只在本地锚** | 产物被 `.gitignore` 排除（`*.kvmem` / DLL / `m4_memory.db`） | 引用时必须注明「只在本地」，他人无法复算，只能由作者背书 |

判据（纪律 24 的操作形式）：问一句「**这个文件在正常流程里会不会被重写？**」
—— 管线**输入**只被读 ⇒ 跑一百遍不变 ⇒ 变了就是有人动了输入 ⇒ **可作锚**；
管线**产物**每次 DROP/CREATE 重灌 ⇒ 跑一遍就变 ⇒ **只能作观测值**。

---

## 8 模块地图

### 8.1 引擎层（C++，`llama.cpp/src` + `include`，6 个文件）

| 文件（新增块） | 职责 |
|---|---|
| `src/llama-kv-cache.cpp` | `seq_cp` 引用挂载、`seq_repos_local` 局部重旋转、Hadamard 三明治、连续区段批量搬运、preflight 守卫（写前全部层校验） |
| `src/llama-kv-cells.h` | cell 池、seq 位图（`std::bitset<LLAMA_MAX_SEQ>` = 256，每 cell 32 B）、`pos_move`/`has_shift` 语义 |
| `src/llama-memory*.cpp` / `kvmem_persist.cpp` | 记忆序列的持久化、`n_keep` 告警（只有告警，没有自动抬升） |
| `include/…` | 对应声明 |

### 8.2 工具层（C++ shim，1 个）

`tools/kvshim.cpp` → `tools/kvshim_vk.dll`：把引擎能力暴露成可脚本调用的接口
（`kvshim_load` / `kvshim_ask_at` / `kvshim_score_at` …）。**返回值是字节数，不是 rc** ——
`ask_native` 每轮 `ask_rc=93`，把 93 当 rc 过判据会让「50 轮全作废、验收永不可能通过」。

### 8.3 Python 层（`tools/`）

| 模块 | 职责 |
|---|---|
| `chat.py` | 端到端：`build` / `ask` / `save` / `load`；四站租约（放置 / 放置 slots / 卸下 / 装上） |
| `kvslots.py` | cell 级读写：`write_at(seq, text, pos, add_bos=True)` / `save(seq, path)` |
| `m3_lease.py` | 租约表：pin / refcount / detach-before-save 顺序（`:107-119` 是陷阱原文出处） |
| `chat_lease.py` | 把租约接进 `chat.py` 的四处 reset 站点 |
| `memory_source.py` | 源文本权威副本（缺口 #7）：幂等 `put_source`、`SourceConflict`、append-only |
| `facet_index.py` / `facet_budget.py` | BM25 + facet 检索与两层闸门（`GATE 1.30` / `COV_MIN 0.35` / `REL_CUT 0.55`） |
| `freeze_check.py` | 三阈值冻结检查（利用率门槛 **70%**） |
| `evidence.py` | 三态：`memory_hit` / `chat_only` / `no_evidence` |
| `kvdrift.py` | 量化漂移曲线 |

### 8.4 数据层

| 存储 | 内容 | 权威性 |
|---|---|---|
| `kvmem/chat.db` :: `memory_source` | **源文本正文** | **权威副本**（不可变、永不进 prompt） |
| `kvmem/sessions/*.json` + `*.chat.kvmem` | 会话两层 manifest（layout 契约 + placement 渲染） | 可审计，恢复时 fail closed |
| `kvmem/lease_events.jsonl` / `lease_refusals.jsonl` | 租约事件 / 拒绝日志 | 观测 |
| `*.kvmem` 块文件 | K/V 张量 + 元数据 | **派生层 = 缓存**，可删可重建 |

**「块文件不是权威，是缓存」** 这句话有实测支撑：块有损且会磨损（约 10 次 requantization 后开始崩），
且绑定在某模型 / rope / kv 类型上。把块当唯一起源 ⇒ 模型升级或块磨损就永久丢记忆。
详见本地进度文档 **§10.9**（Memory Contract 全文）。

---

## 9 文档索引

**发布口径：GitHub 上只发布本 README 一份文档。** 其余文档仅存于本地工作区，下表路径是**本地线索，不承诺可点**：

| 文档（本地） | 用途 |
|---|---|
| `README.md` | 本文：定位 + 机制 + 怎么跑 + 目录 + 红线（10 分钟读完）—— **唯一对外** |
| `PROGRESS-AND-ROADMAP.md` | 进度与未来：里程碑表、判据原文、25 条判定、未闭项、纪律 41 条、锚与复算；**状态权威 = §13 各收口节**（§2.1/§2.2 只是索引/摘要） |
| `FEATURES.md` | 能力账：§0 总表 + 强度 R/C/A/S |
| `docs/_work/INDEX.md` | **文档总索引**：40+ 份文档状态（current / superseded / report / archived）、权威层级、术语表、旧文档处置规则 |
| `docs/_work/ANCHORS-CURRENT.md` | **坐标唯一入口**：sha16 的「签署坐标 / 现行坐标」两列四态 |
| `docs/_work/CONSOLIDATION-LEDGER.md` | 合并台账：85 行「哪份内容去了哪一节」；**唯一计数来源** |

其余 md（`kvmem/**`、`docs/legacy-2026-10-24/**`、`PROJECT-STATE.md` 等 **84 份**）**已经被合并、并已从工作树移出（后又于 2026-10-25 20:20 按字节回填 80 份，见上「仓库内 md 现状」）**：
它们不是「还在某处可读」，而是**只在备份快照里**——`D:/llama-mem-backup-2026-10-25/` 下**同相对路径**。
引用规则仍是 **代码 > 运行产物 > 旧文档（仅史料）**；需要核对史料时按相对路径从 `D:/llama-mem-backup-2026-10-25/` 取回（取回命令见本地进度文档 §1.1）。

> **备份快照不在仓库里**：85 份被合并 md 的完整副本（`1,707,063 B`，逐份字节见台账）住在
> **`D:\llama-mem-backup-2026-10-25\`** —— **仓库外、同盘符、保留相对路径**。它不靠 `.gitignore` 挡住，
> 而是**物理上不在 `D:\llama-mem` 里**：所以「唯一 README」不只是受控语料里成立，**磁盘上也只有一份**。
> 因此**仓库内 md 的现状见本地 `PROGRESS-AND-ROADMAP.md` §0.1**（只是档案回填公告；2026-10-25 20:20 已按字节回填 80 份）。
> （`.gitignore` 的 `.trash-*/` 规则只为防将来再出现同名中间目录；`docs/_work/**` 已在同日尺子统一修复中放行，可跟踪。）

---

## 10 vendored 两树声明

| 路径 | md 数 | 状态 |
|---|---|---|
| `llama.cpp/`（我们的 fork，分支 `persistent-memory`，嵌套 git 仓库） | 129 | **原样未动（UNTOUCHED）**，保留上游 README |
| `llama.cpp-upstream/`（上游纯净克隆，只读基线 `8e5a58d`） | 129 | **原样未动（UNTOUCHED）**，保留上游 README |
| 合计 | 258 | 本轮整合**未触碰**其中任何一份 |

两树 md 数恰好对称（129 + 129），与「upstream 本地 clone 后开分支」的来源一致。
**本仓库不对 vendored 两树做任何改写、删除或再导出**；要改引擎请走 `patches/`。

---

## 11 红线（硬约束）与作者 / 许可

### 11.1 红线（不可回退，源自 STATUS-REPORT §3.2）

> **物理定律 L1–L12 全文见本地 `PROGRESS-AND-ROADMAP.md` §16**（含每条的**表现 / 判据 / 实现**，以及 L3b 的
> 0/1/5/10/25/50/100 次往返实测崩坏表）。本节只是 §3.2 的 7 条红线，**不是** §3.1 的物理定律 ——
> 写引擎前先读 §16 的 L1（K 在 Walsh–Hadamard 基里，正解 `H → rope → H`）与 L2（手动旋转过必须用 `pos_move`）。

1. **不做 prompt 拼接。** 记忆文本永远不进 prompt；进 attention 的只有 K。
2. **索引只存指针，不存正文。** `chat.db` 里只有 `path / n_tokens / label`，没有正文。
3. **产物可删除而不影响产品。** 删掉 `blocks/*.kvmem` + `chat.db`，`chat.py build` 能重建；不依赖任何训练产物。
4. **ggml 不动。** 需要新算子时先问「能不能在 memory 层解决」。

补充口径（`Memory Contract` 落地后）：
5. **源文本是唯一权威**（`memory_source`），块是缓存；重建只要求 **token 数与答案一致**，不要求字节一致。
6. **文件只读，永不回写。** 块一旦被旋转，磁盘文件就不再等于内存；要回 0 位就从文件重新加载。
7. **写循环开始之后禁止退回 `seq_add`。** 只能从 pristine 重载或从 source 重建。

### 11.2 作者与许可

- 语料与判据的作者分工：**lead**（预登记 / 派单 / 交付 / 逐条裁决 / 纪律编号权威）、
  **inspector**（判据冻结 / 验收 / 盲写清单 / 闸门自检 / 规格书）、**executor**（跑批 / 实现 / 自证）。
- 引擎改动基于 **llama.cpp**（MIT）。vendored 两树各自保留其上游 README 与许可。
- 本文档集合为项目内部材料；引用外部结论时请连带引用锚（文件名 = sha256 前 16 位）。

---

## 12 依赖、一键复算与明确未做（对外读者速览）

### 12.1 依赖

| 项 | 要求 |
|---|---|
| 引擎 | 本项目 fork 的 llama.cpp（分支 `persistent-memory`）；改动以 `patches/persistent-memory.patch` 形式提供，`llama.cpp/` 是**嵌套 git 仓库、原样未动** |
| 构建 | Vulkan 构建产物在 `bin/llama-vulkan/`；shim `tools/kvshim_vk.dll`（不入库，需本地构建） |
| Python | Python 3 + 标准库（`hashlib` / `sqlite3` / `json`），**无第三方训练栈** |
| 模型 | 14B，KV `q8_0`，`-ngl 99 -c 8192`，`n_seq 8`，`n_predict 64`，位置锚 `4096`；约需 ≥10 GB 显存。模型 `*.gguf` 与记忆块 `*.kvmem` **均不入库** |
| 磁盘 | 块 ≈ 9.5 MB/块（14B，1 块 91 cells 口径见 §1.1） |

### 12.2 一键复算

```bash
git clone <this repo> && cd llama-mem
bash verify.sh          # 12 项关系断言；当前 ALL PASS（rc 0）；见 §6
```

产物级复算（`sha256sum <file> | cut -c1-16` 与字节数）与四段检查脚本的口径见本地 `PROGRESS-AND-ROADMAP.md` §15.3 —— **该文件不随仓库发布**，所以外部读者只能复算本 README 里**仓库内可复算**的那类锚（见 §7.4）。

### 12.3 明确未做（不要把本文读成「已完成」）

1. **无服务端**：`tools/server` 从未改造；无序列池、无 slot 改造、无 pin 落地机。现有能力全部是**单会话 / 单进程 / 夹具驱动**。
2. **未训练**：无 `torch`、无 `train/`。记忆不是"学"出来的，是**编码 + 挂载**。
3. **真并发未验**：M2 完整只验「同一 `n_ctx` 下两段**顺序**会话」，两路同时 decode 未做。
4. **跨布局对照臂未做**；**引擎不变量 fail-closed（M6a/M6b）另立**（状态见本地 `PROGRESS-AND-ROADMAP.md` §13.4.1）。
5. **产品侧 pin / 驱逐策略**：`DEFAULT_POLICY="off"`，pinned 驱逐只在规划器层验过，未接主路径。

### 12.4 免责

研究原型：**无 SLA、无安全审计、无多租户隔离**。`*.kvmem` 块与 `chat.db` 都是**可重建的派生层**（源文本在 `memory_source`，见 §11 红线 5），删掉不影响产品成立；但**不要让不受信任的输入直接驱动 `chat.py build/ask`**（当前没有输入净化层）。
