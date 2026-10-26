# llama-mem

> **把长期记忆做进推理引擎的 KV 张量里，而不是拼进 prompt 字符串。**
> **as-of 2026-10-26** ｜ 本地工作树 `D:\llama-mem` ｜ llama.cpp fork（分支 `persistent-memory`）
> **发布口径**：GitHub 上**只发布本 README**。其余状态、判决、证据文档仅存本地（`docs/` 只在 `full` 分支，不随 `main` 发布）；下文提到这些路径时都是**本地线索，不承诺可点**。

## 一句话

这个项目不改 prompt，改引擎：把一段记忆编码成 **KV 张量块**（`.kvmem`）常驻在 attention 里，在它紧贴其后提问 —— **删掉对话历史，记忆依然可被读出**。所以「内存里多了几个块」不是卖点，**「prompt 里一个字都没有也能答对」**才是。

**当前状态一句话**：引擎层与 M2 / M2 规划器 / M2 完整 / M3 / M4 **已验收**；**M5 `(a)` 接地弃答（36 层）已验收**；**M5 `(c)` 长生成按四态分记：装置可用 / 判据作废 / 模型行为读数有效**；**新判据的预登记已冻结，未实现、未验收**；**K1 真实 kill 臂 `未接上（环境冻结）`**；产品层仍无服务端。

## 1 这是什么

| 项 | 内容 |
|---|---|
| 定位 | **把长期记忆做进推理引擎的 KV 张量里，而不是拼进 prompt 字符串。** |
| 关键差别 | 记忆不在 prompt 文本里，在 KV cache 里；**删掉对话历史，记忆依然可被读出**。 |
| 补丁规模 | **6 文件 / 600 insertions / 0 deletions**（`patches/persistent-memory.patch`，32,337 B，sha16 `db32faae83bec9fc`） |
| 四层成分 | C++ 引擎补丁 + C++ shim（探针挂载） + Python 工具链 + 实验产物树 `kvmem/` |

### 1.1 血统：前身 biomem

前身是 **biomem** —— 应用层记忆的聊天智能体：SQLite「海马体」 + 多路轻量索引 + 有限工作记忆 + 巩固 / 遗忘曲线，16 GB 内存 / 10 GB 显存可跑（7B 大脑）。它把记忆**拼装进上下文**；本项目是它「**改引擎**」的继任者：同一产品直觉，换掉实现层 —— 所以起点不是「更好的 prompt」，而是 `src/llama-kv-cache.cpp`。

### 1.2 「kvmem」的两种含义（别混）

| 写法 | 含义 |
|---|---|
| `kvmem/`（目录） | **实验产物树**：实验产物、夹具、预登记（PREREG）、验收（ACCEPT）、判据（CRITERIA）、台账 |
| `*.kvmem`（文件后缀） | **记忆块二进制本体**：K/V 张量 + 元数据，被 `.gitignore` 排除，clone 后拿不到 |

## 2 为什么改引擎

主流的「长期记忆」是应用层的：检索文本 → 拼进 prompt → 模型读。三个绕不开的问题：

1. **prompt 变贵**：成本随 token 线性增长，每次对话都要为**全部**历史付费，而绝大部分与当前问题无关；还会和上下文窗口抢位置。
2. **记忆没有结构优先级**：prompt 里的记忆是一段**扁平文本**，模型无法区分「三个月前随口说的」和「昨天强调的」，也无法按访问频次、置信度、来源权威性淘汰。
3. **不可审计**：事后无法回答「这次回答用了哪几条记忆？来自哪个文件？删掉它会怎样？」—— 记忆已变成自然语言的一部分，与幻觉、复述、改写混在一起。

对应的三个产品要求：**成本可控 / 有结构优先级 / 可审计**。这三条后来落成红线（§9.3）与 Memory Contract。

## 3 做法与三层现状

### 3.1 记忆在 KV cache 里，不在 prompt 里

一段记忆被编码一次，产出 `.kvmem` 块文件（K/V 张量 + 元数据）。挂载时：

1. 把块的 K/V 写进对话序列占据的 **position 区间**（例如 `[4005,4096)`）；
2. 用 `seq_cp` 把块的序列**引用**给对话序列（refcount，零拷贝）；
3. 对话在**紧贴块尾**的位置继续生成 —— 注意力自然覆盖这块记忆，而 prompt 里一个字都没有。

### 3.2 三层现状总表

| 层 | 状态 | 一句话 |
|---|---|---|
| **引擎层** | **真的** | 引用挂载、局部重旋转、Hadamard 三明治都在代码里（25 条判定见 §3.4） |
| **记忆读取能力** | **半真的** | 3 块同会话可读、4 块读不全（7B 代现场，14B 不复现 ⇒ §9.5 墓碑） |
| **产品层** | **有骨架，仍无服务端** | M3 生命周期、M4 写入固化、M5 接地弃答已落地；但全部是**单会话 / 单进程 / 夹具驱动**，服务器侧从未改造 |

### 3.3 里程碑账本（只列已验收与未闭口）

| 里程碑 | 四态 | 一句读数（本地产物坐标） |
|---|---|---|
| M0 工具链 | 完成 | Vulkan 构建 + 7B Q4 跑通，解码约 35–40 tok/s |
| M1 机制 | 完成 | 跨进程持久化**四组合**实测通过 |
| M1.7 检索层 | 完成（**但只证文本检索，不证 KV 记忆**） | recall@1 **0.762** / @3 **0.952** / MRR **0.921** |
| M1.8 judge 冲突 | **已验收** | 4 处真冲突定位并落地，A1–A17 **17/17** |
| M2（14B） | **已验收** | 3 块同会话依次答出；问位 4096 → 4169 → 4242；**三跑逐字节相同** |
| M2 规划器 / M2 完整 | **已验收** | 判决件 `M2-ACCEPT-lead.md`（已签 `6f26bce0`；现场 `21ec668df2171350`）/ `M2-FULL-FINAL-lead.md`（`84ec4e3f9b493cf7`） |
| M3 生命周期 | **通过** | **50 轮**全有效；块占恒 **51 cell**、`raw_pos_max` 恒 **4095**；住址 **50/50** 命中 |
| M3 接租约 | 已接入 | `eng.reset(` 归零，`leases.reset(` **4** 处；三份 session 剔除 `saved_at` 后 sha 全等 |
| M4 写入固化 | **已验收** | 端到端 **17/17**；9 轮对话 / 10 句判定 / 6 条 keep → 1 块 **91 cells** 独占 position 0 |
| M5 `(a)` 36 层 | **已验收** | 规则臂 leak **0/5**、false **0/13**；模型臂 leak **0/5**、false **0/11** |
| M5 `(c)` 36 层 | **装置可用 / 判据作废 / 读数有效** | 漏判 **17/18 = 94.44%**、误判 **3/61 = 4.92%**（§5.2） |
| M6b（引擎不变量） | **未接上**（整体） | 文件层 SIGKILL 原子 **6/6**、模糊 **20+20 third=0**；B1 见 §5.5 |
| K1 真实 kill 臂 | **未接上（环境冻结）** | `l1_runs=0`、`kill_attempts=0`（§5.3） |

### 3.4 引擎层 25 条判定摘要

| 判定档 | 条数 | 条目 |
|---|---|---|
| 【代码证实】 | **9** | E1 · E2 · E4 · E5 · S2 · P3 · P4 · P5 · P8 |
| 【部分落地】 | **7** | E3 · E6 · E9 · P1 · P2 · P6 · P7 |
| 【明确未做·查无】 | **7** | E7 · S1 · S3 · X1 · X2 · X3 · X4 |
| 【仅文档宣称】 | **1** | E8（`layout_guard`） |
| 【已定位·生成侧】 | **1** | E10（14B 不复现 ⇒ §9.5） |

【代码证实】= 有 `file:line` 锚；【部分落地】= 有实现无对应断言；【查无】= grep 命中 0。**这张表按文件算，里程碑状态按跑批产物算，两者不可互查代写** —— 例如 X3（接地）在写表时「查无」，后来由 M5 部分落地，但表本身不回改。

## 4 核心机制

### 4.1 记忆序列以 KV 张量常驻（`seq_cp` 引用计数挂载）

记忆块有自己的 seq id。挂载不是「把文本贴进去」，而是 `seq_cp`：**refcount only, zero copy** —— 同一块可被多个对话序列同时引用，cell 只存一份。

### 4.2 位置重排：`seq_repos_local` 只旋转被移动的 cell

块要挪位置时**不能**把整段 K 反量化再量化（有磨损：约 **10 次**往返内安全，25 次答案就坏）。`seq_repos_local` 只对**位移区间内**的 cell 做 CPU 上 dequant → rope → requantize。

### 4.3 Hadamard 三明治（`H → rope → H`）

K 存在 Walsh–Hadamard 基里，**RoPE 与 H 不对易**。所以旋转必须走 `逆H → RoPE → 正H` 三明治，顺序写错就**静默损坏**。该结论对 Qwen2 类模型成立（不触发 `rope_freqs` 分支），**不能外推到任意模型**。

### 4.4 `kv_unified=true` 下靠 position 区间区分

共享单一 KV 池时，不同记忆块**只靠 position 区间区分**；同一 position 的写入会**复用 cell** 并互相覆盖 —— 这是「块必须独占 position 0」硬约束的由来（M4）。

### 4.5 补丁形态：为什么存 patch 而不是子目录

`llama.cpp/` 是**嵌套 git 仓库**，纳入父仓只会存一个 gitlink 指针，历史与 diff 全丢。所以改动统一导出为 `patches/persistent-memory.patch` + `patches/MANIFEST.txt`（sha256 / numstat），规模 **6 文件 / 600 insertions / 0 deletions**；500 行归档版另存，仅作历史基线，**不是现行补丁**。

## 5 验收状态与四态账本

### 5.1 四态与证据档位

四态 = **通过 / 未通过 / 未接上 / 未做**，不可互相代写：**`未接上`（装置或环境没接上）既不是 `未通过`，也不是已通过**；**`判据作废` 也不是 `未通过`**。证据同样分档：**E1/FS**（静态不变量 + 文件层真 SIGKILL）、**E3**（真引擎 kill；GPU 子臂按裁定不做）。**只覆盖文件系统层的东西，永远不许写成 E3，也不许暗示替代 GPU 层。**

### 5.2 `(c)`：装置可用，判据作废（不是「未通过」）

- 装置读数：8 场景 **281.575 s**；显存峰值 **7.3379 → 7.4340 GiB**（未过 8.0、未熔断、无降档）；S8 续跑 `pos_saved=4232=pos_after_load`、`n_tokens 137=137`、`load_return=137`；`reboot` 后无新 minidump。
- 失效在**判据侧**：17 条漏判里 **16 条**是「**句内部分 token 命中即整句 supported**」（`2 十单元`×4、`在杭州`×5、`地下停车场第 2 层`×7），**1 条**是目标句抽 0 fact 被判 `no_fact`。
- **现行判据在 36 层长生成的样本外暴露出系统性失效**（漏判 94.44%，机制为「句内部分 token 命中即整句判 supported」）⇒ **现行判据作废**，须另立新判据。**新版判据的设计已冻结为内部预登记（未实现、未验收）**；由于设计时已知该批结果，**该批对新判据属样本内**，新判据的有效性验收必须在**新的样本外集**上进行。
- 预登记细节位于 `docs/_work/`（**不随 `main` 发布**，见 §7 分支规矩）。因此 `(c)` **不得整体写「通过」**，也**不是**「未通过」；模型行为读数本身**有效**（附和 5 句、编造车牌 `苏A12345`、楼层编造 7 句、数字退化 4 句），但那是行为观察，**不是判据结论**。

### 5.3 K1 真实 kill 臂：`未接上（环境冻结）`

- 现象：**进程建过并销毁过 Vulkan 设备后**，首次大文件写会在 save 开始后 **0.25–0.45 s** 处**整进程冻结**（200 ms 心跳同时静默 ⇒ 不是单条 syscall 慢），与载荷大小、park 后等待、fsync 频率**均无关**。
- 对照：`vk=off` 5 周期 **5.299 s 正常完成**；纯文件微基准稳态 0.529 s、最慢 chunk **8.003 ms**、`>1 s` chunk = 0 ⇒ **不把冻结归因给 save 路径**。
- 已试 prewarm / 4 KiB settle / 卸后等 5 s / fsync 每 8 块 / 每块 fsync —— **均未阻止冻结**；唯一跑完的几组是**逐边界 trace + fsync**，属改时序干扰，**不能当正式证据**。故 `l1_runs=0`、`kill_attempts=0`、正式阶段杀 **0** ⇒ **`crash-safe save` 的真实 kill 证据仍缺**；现有支撑只有 CPU 真引擎 kill（M7-E3-CPU）、文件层 SIGKILL（定点 6/6、模糊 20+20）与静态不变量。
- **crash-safe 边界写死**：**仅进程级非正常终止**（SIGKILL / TerminateProcess / 崩溃）；**不覆盖内核崩溃、BSOD、电源掉电** —— 后者的措辞与依据见外部工程师意见（本地 `PROGRESS §13.22`：`write(tmp)+fsync+os.replace` 对进程级崩溃已充分，Windows 目录 flush 既不可用也不必要）。

### 5.4 K2 / K3：已裁剪
原因：命中窗口只有几十到几百 ms，用户态**无法观测内核 IRP**，退化成极低命中率黑盒概率测试；且人为制造 BSOD 会硬重置主机、打断并行长测。并入 **`Known Environmental Risk`**；**重新激活条件**：向 AMD 报驱动 bug，或 OS / 驱动重大版本变更时做专项系统级测试。

### 5.5 M6b 引擎不变量：整体 `未接上`

- 文件层可签（**E1/FS**）：产品 session 目标非原子写 = 0（仅两处 `os.replace`）；文件层真 SIGKILL 原子臂 **6/6** 只可能是 `before|after`、红臂 **6/6** 全 `third`；随机时点模糊 **20+20**：原子臂 third=0、红臂 **20/20** third。
- **但 B1 整体仍 `未接上`**：C++ `kvshim_load`（`tools/kvshim.cpp:588-605`）仍是**先 reset 后 load**，受「不重建 DLL」限制未改。
- 持久化已加固：manifest 写 tmp 后 **flush → fsync → 写透 rename**（`MOVEFILE_WRITE_THROUGH`）；**目录 flush 不是缺口**（Windows 无该原语、NTFS 日志已覆盖 rename 元数据）。仍开缺口（非阻塞）：SIGKILL 后 **stale tmp 无启动清理**（残留约 **19.7 MB/文件**）、`Incompatible` 分支无实测（只有读码证据）。

### 5.6 口径禁令

`(c)` **不得整体写「通过」**；**不得**把 K1 读成「GPU 侧 kill 已通过」；**不得**把 `未接上` 代写成 `未通过`；**不得**把 B1 写成已修状态；**不得**写「crash-safe 已覆盖内核崩溃」。

## 6 怎么跑

### 6.1 一键复算：`bash verify.sh`

```bash
cd /d/llama-mem        # Git Bash / MSYS2
bash verify.sh         # 期望最后一行 ALL PASS，退出码 0
```

脚本现为 **124 行 / 12 项关系断言**（sha16 `c7c8b264f960daea`）：4 项补丁关系断言（实时 == MANIFEST == 补丁快照，归档 500 另立基线）、2 项报告哈希边车一致性、4 项门禁臂（rc 6/6/0/0）、2 项可证伪（缺 `worker_counts` → rc=7；日志删 10 行 → rc=6）。

### 6.2 退出码陷阱（不许犯）

```bash
# 错：取到的是 tail 的退出码，不是被测命令的
python some_check.py | tail -3; echo $?

# 对：先落文件，再取 rc
python some_check.py > out.txt; echo rc=$?; tail -3 out.txt
```

`verify.sh` 自身用 `set -o pipefail`（`:6-7`）；凡写进文档的「我核过 rc」，都必须是被测命令自己的退出码。

### 6.3 最小用法

| 目标 | 命令 |
|---|---|
| 造块 / 建索引 | `python -X utf8 tools/chat.py build` |
| 挂块提问（内置问题集） | `python -X utf8 tools/chat.py chat`；不挂块对照加 `--control` |
| 跨进程保存 / 恢复 | `python -X utf8 tools/chat.py save` / `python -X utf8 tools/chat.py load` |
| cell 级读写 | `tools/kvslots.py:179 write_at(...)`、`:255 save(...)` |
| 引擎二进制 / shim | **本地** `bin/llama-vulkan/`（53 个文件）、`tools/kvshim_vk.dll` —— 均不入库，需本地构建 |

`tools/chat.py` 的子命令只有 `build / chat / save / load / m1 / two`（`:1428`），问题集写死在 `tools/chat.py:62` 的 `QUESTIONS` 里。

## 7 仓库结构与目录

### 7.1 分支规矩

| 分支 | 内容 | 发布 |
|---|---|---|
| `main` | 根 `README.md` + `kvmem/`（证据）+ `patches/` + `tools/` + `legacy/` + `verify.sh` | **GitHub 对外** |
| `full` | `main` 的全部 + `docs/`（全部本地文档：索引、锚、进度、判决、审计） | 不发布（`docs/` 只在 `full`） |

**规矩**：所有 `.md` 状态文档都在 `full`；`main` 上**唯一的文档就是本 README**。

### 7.2 顶层目录

| 路径 | 是什么 | 在 `main` |
|---|---|---|
| `README.md` | 本文（唯一对外文档） | ✅ |
| `kvmem/` | 实验产物树：块、夹具、预登记、验收、判据、租约日志、会话库 | ✅（证据） |
| `patches/` | `persistent-memory.patch` + `MANIFEST.txt`（sha256 / numstat） | ✅ |
| `tools/` | Python 工具链 + C++ shim 源（`chat.py`、`kvslots.py`、`kvshim.cpp` …） | ✅ |
| `legacy/` | 前身 biomem 的遗留源码（史料） | ✅ |
| `verify.sh` | 一键 12 项关系断言 | ✅ |
| `docs/` | 本地文档库：索引 `INDEX.md`、现行锚 `ANCHORS-CURRENT.md`、进度 `PROGRESS-AND-ROADMAP.md`、判决 / 审计 | ❌（仅 `full`） |
| `bin/`、`llama.cpp/`、`llama.cpp-upstream/` | 构建产物、我们的 fork（嵌套 git 仓库）、上游只读克隆 | ❌（本地） |

### 7.3 `kvmem/` 是证据，不是文档

这些 md / json 是**实验当场凭据**（预登记、验收、判据、逐轮表、盲写清单、租约日志），不是教程；读它们只为**复算一个结论**或**判断一条旧说法是否已作废**。本 README 不维护会漂移的计数（「有多少份 md」一律以本地台账为唯一来源）。

### 7.4 不入库的内容

`*.gguf`（模型）/ `*.kvmem`（块）/ `build*/` / `bin/` / `*.db` / `runs_*/*.json`（跑批原始产物）/ `.env`。后果很重要：**clone 之后原始 run json 与块文件都拿不到**，所以证据目录里存的是**逐字节副本 + 原样命令行**，否则「证据不存在」。

### 7.5 锚的两类

| 类型 | 定义 | 用法 |
|---|---|---|
| **仓库内可复算** | 文件在库里，任何人按 §6.4 即可复现前 16 位 | 可直接引用，例如 `kvmem/m2_visibility/ISOLATION-REPORT.md` = `cb11df4453756882` / 19,043 B |
| **只在本地** | 产物被 `.gitignore` 排除（`*.kvmem` / DLL / `*.db`） | 引用时必须注明「只在本地」，他人无法复算 |

判据：问一句「**这个文件在正常流程里会不会被重写？**」—— 管线**输入**只被读 ⇒ 跑一百遍不变 ⇒ **可作锚**；管线**产物**每次重灌 ⇒ 只能作观测值。复算命令：`python -c "import hashlib,sys;b=open(sys.argv[1],'rb').read();print(hashlib.sha256(b).hexdigest()[:16],len(b))" <文件>`（**Windows 的 Git Bash 没有 `sha256sum` / `stat`**，别照抄 Linux 写法）。

## 8 模块地图

### 8.1 引擎层（C++，补丁 6 个文件；路径相对 `llama.cpp/` 树）

| 文件 | 职责 |
|---|---|
| `src/llama-kv-cache.cpp` | `seq_cp` 引用挂载、`seq_repos_local` 局部重旋转、Hadamard 三明治、连续区段批量搬运、preflight 守卫 |
| `src/llama-kv-cache.h` / `src/llama-kv-cells.h` | cell 池、seq 位图（`std::bitset<LLAMA_MAX_SEQ>`）、`pos_move` / `has_shift` 语义 |
| `src/llama-context.cpp` / `src/llama-memory.h` / `include/llama.h` | 对外接口与持久化钩子 |

### 8.2 工具层（C++ shim，1 个）

`tools/kvshim.cpp` → `kvshim_vk.dll`：把引擎能力暴露成可脚本调用的接口（`kvshim_load` / `kvshim_ask_at` / `kvshim_score_at` …）。**返回值是字节数，不是 rc** —— 把字节数当 rc 过判据会让整批验收永不可能通过。

### 8.3 Python 层（`tools/`）

| 模块 | 职责 |
|---|---|
| `chat.py` | 端到端：`build` / `chat` / `save` / `load`；四站租约（放置 / 放置 slots / 卸下 / 装上） |
| `kvslots.py` | cell 级读写 + `durable_replace`（tmp → fsync → `MoveFileExW(write_through)`） |
| `chat_lease.py` | 把租约接进 `chat.py` 的四处 reset 站点 |
| `memory_source.py` | 源文本权威副本：幂等 `put_source`、`SourceConflict`、append-only |
| `facet_index.py` / `facet_budget.py` | BM25 + facet 检索与两层闸门 |
| `freeze_check.py` / `evidence.py` / `kvdrift.py` | 冻结检查 / 三态证据 / 漂移曲线 |

### 8.4 数据层

| 存储 | 内容 | 权威性 |
|---|---|---|
| `chat.db` :: `memory_source` | **源文本正文** | **权威副本**（不可变、永不进 prompt） |
| `kvmem/sessions/*.json` + `*.chat.kvmem` | 会话两层 manifest（layout 契约 + placement 渲染） | 可审计，恢复时 fail closed |
| `*.kvmem` 块文件 | K/V 张量 + 元数据 | **派生层 = 缓存**，可删可重建 |

**「块文件不是权威，是缓存」**有实测支撑：块有损且会磨损（约 10 次 requantization 后开始崩），且绑定某模型 / rope / kv 类型。把块当唯一起源 ⇒ 模型升级或块磨损就永久丢记忆。

## 9 依赖、明确未做、红线、免责

### 9.1 依赖

| 项 | 要求 |
|---|---|
| 引擎 | 本项目 fork 的 llama.cpp（分支 `persistent-memory`），改动以 `patches/persistent-memory.patch` 提供 |
| 构建 | **本地**：Vulkan 构建产物在 `bin/llama-vulkan/`，shim `tools/kvshim_vk.dll`（均不入库） |
| Python | Python 3 + 标准库（`hashlib` / `sqlite3` / `json`），**无第三方训练栈** |
| 模型 | 14B，KV `q8_0`，`-ngl 99 -c 8192`，`n_seq 8`，`n_predict 64`，位置锚 `4096`；约需 ≥10 GB 显存。`*.gguf` 与 `*.kvmem` **均不入库** |

### 9.2 明确未做（不要把本文读成「已完成」）

1. **无服务端**：仓库里没有 `tools/server`；无序列池、无 slot 改造、无 pin 落地。现有能力全部是**单会话 / 单进程 / 夹具驱动**。
2. **未训练**：无 `torch`、无 `train/`。记忆不是「学」出来的，是**编码 + 挂载**。
3. **真并发未验**：只验过同一 `n_ctx` 下两段**顺序**会话，两路同时 decode 未做。
4. **新判据未实现、未验收**：设计已冻结为内部预登记，尚无实现；**新的样本外集未建立**。
5. **`(c)` 的判据作废**：其读数只能作模型行为观察，不能作能力结论（§5.2）。
6. **K1 真实 kill 未做**：`未接上（环境冻结）` ⇒ crash-safe 的真实 kill 证据仍缺；K2 / K3 **已裁剪**。
7. **M6b 未做完**：B1 整体 `未接上`；B2b-prefix 未接上、B2b-tail 部分覆盖；B3 不排期；stale tmp 无启动清理；`Incompatible` 分支无实测。
8. **跨布局对照臂未做**；产品侧 pin / 驱逐策略未接主路径。
9. **GPU kill 子臂永久 `未做（主机不安全）`**：用户裁定不做，替代覆盖只到文件层，**不替代 GPU 层**。

### 9.3 红线（硬约束，不可回退）

1. **不做 prompt 拼接。** 记忆文本永远不进 prompt；进 attention 的只有 K。
2. **索引只存指针，不存正文。** 库里只有 `path / n_tokens / label`，没有正文。
3. **产物可删除而不影响产品。** 删掉块文件与 `chat.db`，`chat.py build` 能重建；不依赖任何训练产物。
4. **ggml 不动。** 需要新算子时先问「能不能在 memory 层解决」。
5. **源文本是唯一权威**（`memory_source`），块是缓存；重建只要求 **token 数与答案一致**，不要求字节一致。
6. **文件只读，永不回写。** 块一旦被旋转，磁盘文件就不再等于内存；要回 0 位就从文件重新加载。
7. **写循环开始之后禁止退回 `seq_add`。** 只能从 pristine 重载或从 source 重建。

### 9.4 免责

研究原型：**无 SLA、无安全审计、无多租户隔离**。块与库都是**可重建的派生层**，删掉不影响产品成立；但**不要让不受信任的输入直接驱动 `chat.py build/chat`**（当前没有输入净化层）。

### 9.5 历史墓碑：E10（7B 代，已销号，不是现行阻塞）
E10（4 段共享区间下的可见性）症状**在 14B 上不复现**，M2.5 已销号（本地 `PROGRESS-AND-ROADMAP.md` §13.11）；本节只是 7B 代现场记录，**不是现行阻塞**。

### 9.6 作者与许可

- 分工：**lead**（预登记 / 派单 / 裁决）、**inspector**（判据冻结 / 验收 / 闸门自检）、**executor**（跑批 / 实现 / 自证）。
- 引擎改动基于 **llama.cpp**（MIT）；本仓库 `LICENSE` 亦为 MIT（Copyright (c) 2026 lezige2），vendored 两树各自保留上游许可。引用结论时请连带引用锚（`sha256` 前 16 位 + 字节数）。
