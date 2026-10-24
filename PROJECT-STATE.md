# PROJECT-STATE — llama-mem 项目真实状态（唯一权威）

生成时间：2026-10-24（T-003 交付）　判据层级：**代码 > 运行产物 > 旧文档（仅史料）**

> 一句话定位：**引擎层是真的；记忆读取能力是半真的；产品层是空的。**
>
> 当前状态：4 段共享区间的 KV 记忆问题（E10）**已定位 —— 非存储缺陷、非可见性缺陷；失败发生在生成侧（模型未采用眼前可见的记忆内容）**。详见 §3.10 (f) 与 §7。

标注体系（每个技术断言挂且仅挂一个主标记）：

| 标记 | 含义 |
|---|---|
| 【代码证实】 | 实现锚点存在，且有可重复运行的验证锚点 |
| 【部分落地】 | 代码在，但宣称的不变量有明确缺口；或只有实现没有验证 |
| 【仅文档宣称】 | 旧文档写了，代码里查无 |
| 【明确未做·查无】 | 目录/函数/依赖不存在，附 grep 关键词与范围 |
| 【未验证】 | 有代码路径或产物，但没跑过，或只跑过单次 |
| 【推断】 | 机制猜测，附证伪方式 |
| 【史料】 | 旧文档说法，仅说明"当时怎么决定" |

行号格式（两类，见 §10.1 换算表）：

- 【甲】能换算的：`文件:工作树行（上游 N，偏移 M）`　例：`llama-kv-cache.cpp:1871（上游 1575，偏移 296）`（本文件补丁纯新增 296 行、新增块 592-887，见 §10.1 表头，正文不再重复）
- 【乙】新增块内的：`文件:工作树行（补丁新增块 a-b，无上游对应）`　例：`llama-kv-cache.cpp:675（补丁新增块 592-887，无上游对应）`
- `tools/`、`kvmem/`、`llama-cparams.h`、`llama-batch.cpp`、`llama-graph.cpp` 不在补丁范围，单写行号，无偏移。

---

## §1 一句话现状（≤200 字）

引擎层是真的：llama.cpp `persistent-memory` 分支、commit `8e5a58d`、6 文件 405 行纯新增补丁，`seq_cp` 引用挂载、`seq_repos_local` 局部重旋转、Hadamard 三明治都在代码里，有验证脚本。
记忆读取能力是半真的：3 个块挂上去能读（B 臂 15/15），4 个块挂上去读不全（A 臂 2/4、C 臂 1/4），n=5 重复性检验已做、结果逐字节稳定。
产品层是空的：无序列池、无服务端、无 pin、无 `layout_guard`、M3/M4/M5 零代码。

---

## §2 判定总表（25 条）

| 编号 | 项 | 判定 | 关键锚点 |
|---|---|---|---|
| E1 | 记忆独立序列 + `seq_cp` 引用挂载 | 【代码证实】 | `tools/kvshim.cpp:160-161,375`；`kvmem_persist.cpp:60-61` |
| E2 | `seq_repos_local` 只旋转位移 cell | 【代码证实】 | `llama-kv-cache.cpp:675`（新增块） |
| E3 | 连续区段批量搬运 | 【部分落地】 | `llama-kv-cache.cpp:715-727,838-871`（新增块）；验证仅注释自述 |
| E4 | Hadamard 逆H→RoPE→正H | 【代码证实】 | `llama-kv-cache.cpp:612-634,820,857-866`（新增块） |
| E5 | `pos_move` / `has_shift` 语义 | 【代码证实】 | `llama-kv-cache.cpp:879-882`（新增块）；`llama-kv-cells.h:482`（新增块） |
| E6 | 零字节隔离 | 【部分落地】 | 有拒绝路径断言，缺"未参与序列逐字节不变"断言 |
| E7 | pinned 免驱逐标志 | 【明确未做·查无】 | 三文件 grep `pinned\|evict\|pin_` 命中 0 |
| E8 | `layout_guard` / `retrievable` | 【仅文档宣称】 | 全仓库 grep 命中 0 |
| E9 | `n_keep` 自动抬升止血 | 【部分落地】 | 只有告警 `kvmem_persist.cpp:513-516` |
| E10 | 4 段共享区间可见性 | 【已定位·生成侧】 | 见 §3.10 (f)、§7；非存储/非可见性缺陷，未修复 |
| S1 | server slot 前缀匹配改造 | 【明确未做·查无】 | `tools/server` 不在 git 修改列表 |
| S2 | `seq_rm` / `seq_add` 生命周期 | 【代码证实】 | `kvshim.cpp:278,380,394`；`llama-kv-cells.h:244,267` |
| S3 | 多序列实际用法 | 【明确未做·查无】 | 单会话写死，见 §4 |
| P1 | `.kvmem` 落盘 + SQLite | 【部分落地】 | 指针表在，但正文也入库 |
| P2 | `chat.py` 端到端 | 【部分落地】 | SQL 已不写死；正文来源是源码常量 |
| P3 | BM25 + facet 检索 | 【代码证实】 | `facet_index.py` / `facet_budget.py:52-70` |
| P4 | `freeze_check` 三阈值 | 【代码证实】 | `freeze_check.py:26,67,72`；本次实跑 exit 0 |
| P5 | `evidence` 三态 | 【代码证实】 | `evidence.py:10-12,38,108-121` |
| P6 | `check_redline` R1/R2/R3 | 【部分落地】 | R1 已独立复现；R2 未跑 |
| P7 | `m2_v1` 放置夹具 | 【部分落地】 | 实现+运行结果；失败项为 E10 |
| P8 | `kvdrift` 漂移脚本 | 【代码证实】 | `kvdrift.py:59-60,108,151-158` |
| X1 | 训练 | 【明确未做·查无】 | 无 torch、无 `train/` |
| X2 | M4 空闲巩固 | 【明确未做·查无】 | grep `consolidat` 命中仅注释 |
| X3 | M5 接地/防幻觉 | 【明确未做·查无】 | 无生成后校验代码 |
| X4 | M3 生命周期 | 【明确未做·查无】 | LRU 只在夹具 |

---

## §3 引擎层（E1–E10）

补丁形状：`git -C llama.cpp diff --stat` = **6 files changed, 405 insertions(+)**, **0 deletions**；`src/llama-kv-cache.cpp` 只有 **1 个 hunk** `@@ -591,0 +592,296 @@`。这不是重写引擎：`set_input_kq_mask` 相关改动行数为 **0**。

### E1 记忆独立序列 + `seq_cp` 引用挂载 【代码证实】

- 实现：`tools/kvshim.cpp:160-161`（`cp.n_seq_max = n_seq`、`cp.kv_unified = true`）、`:375`（`kvshim_seq_cp`）、`:345`（`llama_state_seq_save_file`）、`:356`（`llama_state_seq_load_file`）；`kvmem_persist.cpp:60-61`（`SEQ_MEM = 0`、`SEQ_CHAT = 1`）；导出 `include/llama.h:818（补丁新增块 805-824，无上游对应）`。
- 引用语义：`llama-kv-cache.cpp:486` 注释 `no data copy is necessary`，`:509` `cells.seq_add(...)`，`:516` 说明跨流复制才需要真拷贝（`kv_unified` 恒真，故走零拷贝分支）。
- 验证：`tools/p0_1a_check.py`（16 项断言）、`tools/kvslots.py` 五步自检。**本次未运行**（需加载 4.36 GB 模型，属 GPU 任务）。

### E2 `seq_repos_local` 只旋转位移 cell 【代码证实】

- 实现：`llama-kv-cache.cpp:675（补丁新增块 592-887，无上游对应）`；选 cell 只取 `pos_in(p0,p1) && seq_has(seq)`（`:769` 同行区间，新增块）；虚函数 `llama-memory.h:129（补丁新增块 120-144，无上游对应）`、`llama-kv-cache.h:144（补丁新增块 144-153，无上游对应）`；公开出口 `llama-context.cpp:4474-4484（补丁新增块 4474-4486，无上游对应）`。
- 验证：`p0_1a_check.py:97-118`（`test_zero_side_effect`；`:52 diff_bytes`，`:101` 拒绝路径零副作用）。

### E3 连续区段批量搬运 【部分落地】

- 实现：`llama-kv-cache.cpp:715-727`（把连续 cell 合并成 runs）、`:838-871`（`MAX_CHUNK = 256` 分块 get/quantize/set），均在补丁新增块内。
- 验证：**只有实现，没有断言**。唯一独立陈述是 `llama-kv-cache.cpp:713-714`（新增块）的注释 `measured: ~500 ms for a 145-token block`，以及旧文档表格（报告自述值，无原始计时日志）。按门槛（§10.4）降为【部分落地】。

### E4 Hadamard 逆H→RoPE→正H 【代码证实】

- 实现：`llama-kv-cache.cpp:612-617` 注释明写 `RoPE does NOT commute with H, so a shift must be done as H -> rope -> H`；`:619` `llama_kv_fwht`；`:820` `use_hadamard = (n_rot_k != 0)`；`:857-866` 三明治；`:23` `ggml_gen_hadamard`（≤591，无偏移）。
- 验证：`tools/diag_place.py` 十路隔离实验（定位手段）；判别式 `LLAMA_ATTN_ROT_DISABLE=1` 时旧块加载失败。
- **不得混淆**：`prism.hadamard` 是权重/元数据侧的 Hadamard 折叠特性（元数据键 `LLM_KV_PRISM_HADAMARD_*` **共 11 个**，见 `llama-arch.cpp:468-478`；LoRA 命中该表时报错见 `llama-adapter.cpp:340`），与 KV 侧的 Walsh–Hadamard 基变换是两个特性。后者定义在 `llama-kv-cache.cpp:21-23`（`ggml_gen_hadamard`，注释 `orthonormal Walsh-Hadamard rotation matrix` / `note: res^2 == I`），实现于 `:619` `llama_kv_fwht`，应用点 `:857-866`。

### E5 `pos_move` / `has_shift` 语义区分 【代码证实】

- 实现：`llama-kv-cache.cpp:879-882`（新增块）注释 `pos_move() (not pos_add()) because the rotation is already applied - pos_add() would leave a pending K-shift and rotate twice`；对应 `cells.pos_move(i, delta)`。
- 定义：`llama-kv-cells.h:482（补丁新增块 474-504，无上游对应）` `bool pos_move(...)`；对照注释 `:428`（`pos_set`：does not modify `has_shift`）、`:446`（`pos_add`：sets `has_shift` to true），两行 ≤473，无偏移。
- 读取：`llama-kv-cache.cpp:1534（上游 1238，偏移 296）` `get_has_shift()`。

### E6 零字节隔离 【部分落地】

- 有：`p0_1a_check.py:97-118` 断言"拒绝路径不碰一个字节"（`:52 diff_bytes` 逐字节比较）。
- 缺：**没有"未参与序列的 cell 逐字节不变"的自动断言**。`kvdrift.py:151-158` 的 differ 字节是度量重量化漂移的，不能兼作隔离断言。

### E7 pinned 免驱逐标志 【明确未做·查无】

- 查了什么：`grep -rnic "pinned\|evict\|pin_" llama.cpp/src/llama-kv-cache.cpp llama.cpp/src/llama-kv-cache.h llama.cpp/src/llama-kv-cells.h` → **三文件均 0 命中**。
- 夹具侧存在：`m2_v1.py:121` `def evict(slot)`，`:26` 自述 `Deterministic eviction only (LRU). No product eviction policy in this cut.`；`kvslots.py:245` 是 save-then-reset 的 LRU。
- 结论：**夹具内的确定性 LRU，不是产品驱逐策略**。

### E8 `layout_guard` / `retrievable` 【仅文档宣称】

- 查了什么：`grep -rn "layout_guard\|retrievable" tools/*.py tools/*.cpp llama.cpp/src/*.cpp` → **0 命中**。
- 最接近的实现：`session_state.py:16/51/74/93` 的 `guard_policy` 字段（manifest 记账），不是 `layout_guard`，也不产出 `retrievable` 标志。

### E9 `n_keep` 止血 【部分落地】

- 有告警：`kvmem_persist.cpp:513` `range_covers_mem = (n_keep < mem_len)`，`:514-516` 打印 `MEMORY EXPOSED` / `memory protected`。
- **无自动止血**：`mem_len` 在 `tools/` 只出现 7 处（`:447,461,474,506,513,515,540`），全部是计算与打印，没有任何把 `n_keep` 抬到 `mem_len` 的代码。

### E10 4 段共享区间可见性 【已定位·生成侧】（历史推理见下方 (a)–(e)，收口结论见 (f)）

**(a) 补丁本身已排除**：`405 insertions / 0 deletions`，`llama-kv-cache.cpp` 仅 1 个 hunk `@@ -591,0 +592,296 @@`，掩码逻辑零改动（`git diff | grep -c set_input_kq_mask` = **0**）。

**(b) 原假设"掩码增量复用窗口"已被 C 臂几何反例正面削弱**：

- 该假设内容：块位置远低于 `seq_pos_min` 时，整行掩码走 copy 分支被跳过 → 应当"越靠上越不可见"。
- C 臂是反例：`layout=micro`，4 块共 **20 cells**，位置 **3899–4096**，整片贴在对话顶部（对话起点 4096）：home 4091-4096 · project 4027-4032 · habit 3963-3968 · car 3899-3904，各 5 cells。按该假设应当可见。
- 实测：C 臂 **n=5 全部 1/4**（仅 habit 通过，home/project/car 恒失败）。→ 不是证据不足，是被几何反例打掉一半。

**(c) A 与 B 至少三个变量同时变化，因此不得指认单一因子**：

- 段数 4 → 3；
- 每块 cell 数（块内容长度）21/18/12/19 → 31/28/20；
- 布局 key `m2_fwd` → `b3`，起点 3885 → 3948。

这三个量同时变，"是段数导致的"和"是几何导致的"两种说法都站不住。这是"不许定性"的硬理由，比"样本太小"更站得住。

**(d) 候选机制（均属【推断】，不得作为结论）**：

- ① 掩码按 seq 增量复用的 cell 窗口裁剪：`llama-kv-cache.cpp:1944-1956（上游 1648-1660，偏移 296）`。证伪方式：在拷贝分支前后打印 `idst/idst_prev/idxs.size()` 与实际 keep 的 cell 数，3 段与 4 段各跑一次，若 4 段 keep 数 < 该 seq 的 cell 数即坐实。
- ② `seq_cp` 共享区间的成员合并路径。证伪方式：插桩统计共享区间的成员枚举结果，对照 `kvshim_seq_cell_scan` 的覆盖计数。

**(e) 旧文档自列的假设已被代码检索否证**：`STATUS-REPORT.md:1296-1300`（史料）提出"`seq_cp` 合并 cell 区间时可能用固定长度区间栈/游标，第 4 段溢出后静默丢弃"。
`grep -rn "std::array<\|[4]\|[8]\|MAX_SEG\|n_segments\|segments" llama-kv-cache.cpp llama-kv-cells.h llama-batch.cpp` → **0 命中**；唯一定长数组是掩码里的 `seq_pos_min[LLAMA_MAX_SEQ]`，`llama-kv-cache.cpp:1889（上游 1593，偏移 296）`，256 个 seq，与段数无关。
→ **第 4 段不是数组溢出，该假设否证。**

**(f) T-004 收口（2026-10-24）—— 已定位·生成侧，未修复**

- **cell 层否证**：失败布局里 home **21/21** 覆盖、`overlaps` 为空（引擎 cell 表实测，非 manifest 声明）。六布局 `cell_count == Σcells`，含失败的 iso_base / iso_habit_bot / iso_car_mid。
  复算：`cd /d/llama-mem && python -X utf8 -c "import json,glob;[print(p, json.load(open(p,encoding='utf-8'))['cell_layer']['cell_count'], json.load(open(p,encoding='utf-8'))['cell_layer']['overlaps']) for p in sorted(glob.glob('kvmem/m2_visibility/runs_iso2/*.json'))[:3]]"`
- **掩码层否证**：`iso_base`（home 失败）与 `iso_dup4`（home 通过）两臂 home 均 **allowed=21 masked=0**；两臂 **各 100 条块行**（每臂 25 个解码步 × 4 块，合计 200），masked>0 的 0 条；每臂另有 4 条 [MASKDBG-OK]（ask 之后的 JOIN 行，属另一类，不计入块行）（trace 出自冻结版 `dbe52f9124f1ad29`）。
  复算（每臂应为 100 与 4；`-m1` 只能给人看一行，`-c` 才能自己算出 100 —— 口径第 2 条要的是后者）：`cd /d/llama-mem/kvmem/m2_visibility/runs_mask && grep -c "MASKDBG] " mask_iso_base_home.log; grep -c "MASKDBG-OK" mask_iso_base_home.log; grep -c "MASKDBG] " mask_dup4_home.log; grep -c "MASKDBG-OK" mask_dup4_home.log`
- **失败在生成侧**：同块、同位置、同掩码 —— `iso_dup4` 复述「你住在广陵路 12 号 2 单元 602。」，`iso_base` 输出「住在______。  A. 杭州市拱墅区  B. 杭州市拱墅区北高峰」。
- **未修复**：没有改动任何引擎逻辑（补丁仍 500 插入 / 0 删除），因此措辞只停在"已定位"这一档（不声称修好）。
- **候选解释（均属【推断】，未验证）**：① 注意力被同区其它块稀释至临界；② "另外，还有一些和问题无关的日常记录。"这类重复文本诱发"出题"模板；③ 提问在长上下文里被当成题干。三者都需要新建块文件的正反对照实验才能区分，**不在 T-004 范围内**。
- 过程报告：`kvmem/m2_visibility/ISOLATION-REPORT.md`（引用须带其冻结哈希）。

---

## §4 会话与服务层（S1–S3）

### S1 server slot 前缀匹配改造 【明确未做·查无】

`git -C llama.cpp status --porcelain` 只列 6 个 `src/` 与 `include/` 文件，**`tools/server` 不在修改列表** → 上游原样。`tools/server/server-context.cpp:3995` 的 `n_past = slot.prompt.tokens.get_common_prefix(input_tokens)` 原样存在（该文件 mtime 12:48，早于全部补丁工作）。**server 接入未做。**

### S2 `seq_rm` / `seq_add` 生命周期 【代码证实】

- 实现：`kvshim.cpp:278`（reset = `seq_rm(seq,0,-1)`）、`:380`（`seq_rm`）、`:394`（`seq_add`）；`kvmem_persist.cpp:496-497`（shift 用 rm+add）；`llama-kv-cells.h:244`（`seq_rm`）、`:267`（`seq_keep`），两行 ≤473 无偏移。
- 缺口：生命周期全靠调用方脚本编排，**无 RAII、无自动回收**。

### S3 多序列实际用法 【明确未做·查无】（四项分开写）

1. **无 `n_parallel`**：`grep -rn "n_parallel" tools/ llama.cpp/tools/server` 于本项目代码中无相关配置使用。
2. **无服务端**：`grep -rln "http.server\|Flask\|HTTPServer\|socket.bind" tools/*.py` → **0 命中**。
3. **seq 写死 8**：`kvshim.cpp:160`、`kvmem_persist.cpp:254`、`kvmem_page.cpp:331`、`kvmem_quality.cpp:279`；python 侧 `kvslots.py:64` 与 `chat.py` 五处（`:107,146,318,354,411`）。语义槽只有 `SEQ_MEM=0` / `SEQ_CHAT=1`。
4. **`kv_unified` 恒真**：`kvshim.cpp:161`、`kvmem_page.cpp:332`、`kvmem_quality.cpp:280`。

→ 结论：**单会话结构**。`n_seq_max=8` 是 8 个序列位，**不是"支持 8 路并发/8 用户"**；并发瓶颈在"单 context + seq 写死 + 无序列池 + 无服务端"，不在 `LLAMA_MAX_SEQ`（那是上游默认 256，`llama-cparams.h:8`，本文件未打补丁，本项目实际用 8）。

---

## §5 工具层（P1–P8）

### P1 `.kvmem` 落盘 + SQLite 只存指针 【部分落地】

- 指针表：`memory_source.py:82-95` `memory_block(path, n_tokens, n_bytes, built_at, model_path, model_size, model_mtime, kv_type, state_version)`。
- **但正文也入库**：`memory_source.py:60` `CREATE TABLE memory_source`，`:67` **`text TEXT NOT NULL`**，`:75-76` `BEFORE UPDATE OF text` 触发器强制不可改（提示 insert a new row）。实测 `kvmem/chat.db` 的 `memory_source` 有 2 行带正文。
- → "SQLite 只存指针不存正文"与代码不符：它正是为"派生块可重建"而存正文。

### P2 `chat.py` 端到端 【部分落地】

- 已落地部分：`grep -c "SELECT" tools/chat.py` = **0**，取块走 `memory_source.py:207` 的查询函数；流程注释在 `chat.py:125`（load → repos_local → seq_cp → generate），`:212` `attached(seq_cp)`。
- 缺口（写法见规范）：**权威副本存在**（`memory_source.text` + 不可改触发器，`memory_source.py:57-79`），但只能由源码常量灌入（`chat.py:57 MEMORIES = [...]` 硬编码正文，`:111` 用它入库、`:121` 用它统计），**没有面向用户的写入口** → M4 仍属未做。

### P3 BM25 + facet 检索 【代码证实】

- 实现：`facet_index.py`、`analysis.py`、`retrieval.py`、`eval_retrieval.py`（含 BM25 基线）、`facet_budget.py:52-70`（alpha 窄化 + 佐证闸门）、`:177` 扫描。
- 自承短板：`facet_budget.py:157-159` 原文 `the narrowing is SAFE here, which is exactly why alpha cannot be measured on this corpus ... every alpha produces the same ranking` → **alpha 在该数据集上未被真正证伪**。

### P4 `freeze_check` 三阈值 【代码证实】

- 实现：`freeze_check.py:26` `FROZEN_THRESHOLDS = {"GATE": 1.30, "COV_MIN": 0.35, "REL_CUT": 0.55}`；`:67`/`:72` 输出分支。
- 验证（本次实跑）：`python -X utf8 tools/freeze_check.py` → exit **0**，**87 ms**，输出 `SELECTION LAYER: FROZEN (3 files, 3 thresholds, versions {'INDEX_VERSION': 5, 'ANALYSIS_VERSION': 4})`。

### P5 `evidence` 三态 【代码证实】

- 实现：`evidence.py:10-12`（`memory_hit` / `chat_only` / `no_evidence`）、`:38` `POLICY_VERSION = 1`、`:108-121` 返回与 refuse 分支。
- 验证夹具：`states_demo.py`（需 GPU，**本次未跑**）。

### P6 `check_redline` R1/R2/R3 【部分落地】

- 实现：`check_redline.ps1:3-16`（R1 权重 sha256 不变 / R2 移走训练产物仍可跑 / R3 隐含于 R1；exit 0/1）。
- 验证：R1 已独立复现——`sha256` 实测 `731ece8d06dc7eda6f6572997feb9ee1258db0784827e642909d9b565641937b`，与 `tools/redline_model.sha256` **逐字符相同**（3.36 s，只读）。
- **R2 未跑**：它会调 `test_persist.ps1`（三进程）写 kvmem 状态文件并写 `tools/quality/redline_persist.log`。R3 因 `artifacts/` 目录不存在而空真。
- → **红线整条 HOLDS 未被独立验证，只验证了 R1**（见 §10.3）。

### P7 `m2_v1` 放置夹具 【部分落地】

- 实现：`m2_v1.py:181` `KVEngine(n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")`；`:273` 打印 `N/81`。
- 分数按时间序（单一现行值）：**79/81（预算两本账修好前）→ 80/81（修好后，现行）**。依据 `STATUS-REPORT.md:1301-1302`（史料原文："预算已按两本账修好……修后 `m2_v1.py` 80/81，唯一失败就是上面的可见性"）。两本账：`resident_moves`（每次从 pristine 重载清零，上限 5）与 `total_mounts` / `requant_total`（仅统计）。
- 唯一失败项就是 E10（4 块重建后可见性，`STATUS-REPORT.md:1247-1258,1289-1292` 为史料描述）；该失败项**已定位到生成侧**（非存储、非可见性缺陷，详见 §3.10 (f)）。

### P8 `kvdrift` 漂移脚本 【代码证实】

`kvdrift.py:59-60`（`--local` 切 `seq_repos_local` 与 `seq_add` 两种位移）、`:108` 模式打印、`:151-158` differing 字节统计；配套 `kv_audit.py:78` `diff_bytes`。

---

## §6 未做项（X1–X4）

| 项 | 查了什么 | 范围 | 命中 |
|---|---|---|---|
| X1 训练 | `ls -d train`；`python -c "import torch"`；`grep "import torch\|optimizer"` | 仓库根；`tools/*.py` | 目录不存在；`ModuleNotFoundError: No module named 'torch'`；0 命中 |
| X2 M4 空闲巩固 | `grep -rni "consolidat\|consolidate"` | `tools/*.py` | 仅命中 `memory_source.py:159` 注释里的 `grounding checks`，非实现 |
| X3 M5 接地/防幻觉 | 生成后校验代码检索 | `tools/*.py` | 0；`evidence.py` 只在检索侧出三态 |
| X4 M3 生命周期 | 产品侧 LRU/生命周期检索 | `llama.cpp/src`、`tools/` | 0；LRU 只在夹具 `m2_v1.py:121`、`kvslots.py:245` |

---

## §7 数据与不确定性

> **T-004（变量隔离 → 掩码层）已完成**，过程报告见 `kvmem/m2_visibility/ISOLATION-REPORT.md`（**已定稿·可引用**；引用须带其冻结哈希 **cb11df4453756882**，267 行）。
> 三句结论：
> 1. **cell 层**：失败布局里 home **21/21** 覆盖、`overlaps` 为空（引擎 cell 表实测，非 manifest 声明）。
> 2. **掩码层**：`iso_base` 与 `iso_dup4` 两臂 home 均 **allowed=21 masked=0**；两臂 **各 100 条块行**（每臂 25 个解码步 × 4 块，合计 200），masked>0 的 0 条；每臂另有 4 条 [MASKDBG-OK]（ask 之后的 JOIN 行，属另一类，不计入块行）（trace 出自冻结版 `dbe52f9124f1ad29`）。
> 3. **失败在生成侧**：同块同位置同掩码，`iso_dup4` 复述「你住在广陵路 12 号 2 单元 602。」，`iso_base` 输出「住在______。  A. 杭州市拱墅区  B. 杭州市拱墅区北高峰」。
> 冻结哈希（**产出本文所引产物的版本**，非现盘版本）：`llama-kv-cache.cpp` **dbe52f9124f1ad29**；`runs_mask/_mask_run.py` **9d7d502c3563ec25**；`runs_mask/_assert_trace.py` **130401439f3ee438**；`runs_mask/_smoke_pair.py` **c0e568431ebca0d6**（DLL `849e7281c74a5288`）。**驱动两文件与门禁已被 T-006 取代（现盘哈希见第 8 条）；重跑本文所引冻结产物须先检出上列版本。**
> **臂名口径**：本轮失败臂在 run json 中记作 experiment=iso_car_back（D2.LAYOUTS 无 iso_base 这个键），其几何与本文所称 iso_base 相同（home/project/habit/car，70 cells，span 3885–4095）。mask_iso_base_home.json 里的 mask_env.LLAMA_KV_MASK_LAYOUT=iso_base 是 shell 继承值，**trace 行内的 layout= 不是实际布局的证据**（静态 CRT 快照，见附录 C 第 5 条）；实际布局以 run json 的 layout.key 与 cell_layer.coverage 为准，二者与本轮 windows 逐段一致（21/18/12/19）。**本行仅适用于本文引用的冻结产物**；T-006 之后新 run 的 `layout=` 已是真值（见第 4 条）。
> 未修复：引擎逻辑一行未改（500 插入 / 0 删除），生成侧的三种候选解释**均未验证**。
>
> **T-006（验证工具链）已完成** —— 只改驱动与门禁，引擎未动。
> 4. **静态 CRT 坑已绕过**：驱动从"同进程调用"改为**启动器 + worker**，`Popen(env=...)` 在子进程启动前注入真实布局键；进程内 `os.environ` 无效（DLL 在进程启动时快照环境）。新 run 的 trace **154 行全部 `layout=iso_car_back`**，`iso_base` 出现 **0** 次；run json 记 `child_env` / `env_source` / `ask.n_predict` / `trace_gate`。
> 5. **四项 AND 门禁**（`runs_mask/_gate.py`）：**A** 按类标签（SUM 行 25 / 旧值 0）· **B** 集合断言（不含任何数量）· **3a** 外部锚点（`SUM==1+N_PREDICT`、`blk==len(segments)*SUM`、`OK==len(segments)`、`SUM2==SUM`）· **3b** 独立管路（启动器在 stderr 管道上 tee 计数 vs 日志实测，逐类）。3b 为三态 `{pass,fail,inert}`：新 run 缺 `worker_counts` → **rc=7**；冻结旧产物 → **INERT 不投票**，汇总行明写"3 项 AND + 3b INERT"，不得混称四项。
> 6. **3b 可证伪（已造红）**：日志删 10 行 blk → `blk 90 != 100`，3a 与 3b 同红、rc=6。**整类缺失由 A 与 3a 承担**——3b 在"整类不打印"时会退化为恒真（`AB_B_seq99`：A红 / B**绿** / 3a红 / 3b INERT 为正确排布）。
> 7. **插桩零行为影响**：答案 sha `e63faeff` 与历史失败臂逐字节相同；不传 `--debug` 时日志 0 字节、答案 `7ec1430d`。
> 8. T-006 冻结哈希：`runs_mask/_mask_run.py` **1b9a0b383554dd70**（208 行）；`runs_mask/_gate.py` **c2085a04a21c21da**（187 行）；`runs_mask/_assert_trace.py` **5df5ae7c539b377a**（92 行）；`llama.cpp` **ins=500 del=0**、cpp **dbe52f9124f1ad29**。
> 9. **T-007（锚点自证）**：run json 新增 `anchors`，把 3a 的四个期望值 SUM / SUM2 / blk / OK 连同**推导式与出处**一起写进产物（例：`blk.expect = n_segments * SUM`，`n_segments = len(layout.segments)`），另记 `trace_gate` 与 `trace_gate_cpp_sha256`。
>    **边界（不可省）**：`anchors.*.expect` 是**驱动按表达式算出的期望，不是独立读数**——`SUM`/`blk` 仍以 `llama-kv-cache.cpp:2031` 门控为前提，`OK` 依赖驱动自身打印逻辑。
>    故它**能自证推导链，不能自证前提成立**；前提以字符串形式记录，门控一旦变更 3a 会红且原因可读。**不得把它当外部锚点引用。**
>    `runs_mask/_mask_run.py` 现为 **5ea03395954d76e9**（230 行，T-007 取代 T-006 的 1b9a0b38 / 208 行；`_gate.py` 与 `_assert_trace.py` 未变）。

### 7.1 m2_visibility 三臂——**n=5 重复性检验已做**（T-003 A 段）

运行方式：`tools/m2_visibility_probe.py` 单臂进程逐个调用（`--arm X [--target Y] --run-json <新路径>`），每臂 5 次，共 **35 次**，输出至新目录 `kvmem/m2_visibility/runs_var/`。

> 历史 `runs/` 7 个 json 未被改动，依据两条：(a) 其 mtime 仍为 19:25–19:26，早于本轮运行的 19:57–19:58；(b) 与历史重叠的 11 个（臂, 段）组合，答案与本轮 `runs_var/` 对应项逐字节一致。
> 注：本轮运行前未记录 md5 基线（`_history_files_before.txt` 仅含计数 0），故不以 md5 作为证据。

| 臂 | layout | cells | 每次结果 | n=5 汇总 | ok 率 | 判定 |
|---|---|---|---|---|---|---|
| CONTROL | `m2_fwd` | 70 | 控制闸 4/4 | 35/35 次 run 的 `control.ok = true` | 1.000 | 夹具可信 |
| A/home | `m2_fwd` | 70 | 0/1 | **0/5** | 0.000 | **稳定失效** |
| A/project | `m2_fwd` | 70 | 1/1 | **5/5** | 1.000 | 该臂复现阳性 |
| A/habit | `m2_fwd` | 70 | 0/1 | **0/5** | 0.000 | **稳定失效** |
| A/car | `m2_fwd` | 70 | 1/1 | **5/5** | 1.000 | 该臂复现阳性 |
| B | `b3` | 79 | 3/3 | **15/15** | 1.000 | 该臂复现阳性 |
| C | `micro` | 20 | 1/4 | **5/20** | 0.250 | 稳定部分失效（habit 恒过，home/project/car 恒失败） |
| D_FWD / D_REV | — | — | — | **未产出**（历史 `runs/D_FWD.log` 仅 139 B 一行 `COMMAND:`，无 json）；本轮未跑 | — | — |

**重复性结论（关键）**：

1. 同一臂 5 次运行的**答案逐字节相同**（每臂答案指纹唯一，例：A_car 恒 `3f43dcac3703`、A_home 恒 `e63faeffa318`、B 恒 `c005b4f943b9`、C 恒 `9f57dc06f3ac`）。
2. 与历史 19:25–19:26 的运行答案逐字节相同（**11 个重叠 (臂, 段) 组合，11/11 identical**）→ 跨进程、跨会话确定性成立。（历史是 7 个 run 文件；A 臂在其中拆成 4 份，故可重叠对齐的是 11 个 (臂, 段) 组合。）
3. 采样参数：`kvshim_ask` → `generate` 走**贪心解码**，`kvshim.cpp` 与 `m2_visibility_probe.py` 中**无 temperature / top_k / top_p / seed 任何参数**（`grep` 命中 0），因此**不存在采样随机性**。→ 历史 n=1 的结论不是采样噪声，方差为 0。
4. 单次耗时 6.13–8.09 s，每臂 n=5 共 35 次总耗时约 4 分钟。

**由此可写死的只有"可复现性"，不是"病因"**：4 块不通是**稳定可复现**的（A_home / A_habit 各 5/5 失败），但"为什么"仍未定性（见 §3.10）。

另需钉死一句：贪心解码下 n=5 **只证明可复现性，不增加统计功效**——"方差为 0"意味着重复运行不会给出新信息，要定性病因只能靠变量隔离或插桩，不能靠加样本。

### 7.2 量化漂移曲线（按 requantization 次数记）

- 0 / 1 / 5 / 10 次往返移动（= 0 / 2 / 10 / 20 次 requantization）均答对 `A-4417`；
- 25 次往返（= **50 次 requantization**）→ 答成 `A-444417`；
- 50 次往返（= 100 次）→ `ioneerioneer`；100 次往返（= 200 次）→ `3`。
- "5 次往返"只是 n=1 观察上界，**不是安全线**。字节差不是漂移指标（1 次往返即约 6.8% 字节不同，重量化让 f16 scale 抖 1 ULP）。
- 出处：旧文档表格（报告自述值，**无原始计时日志**）。

### 7.3 尺寸与耗时（报告自述值，无原始计时日志）

每 token KV（q8_0）**29.8 KiB**（30,464 B）；8192 ctx 池 **238 MiB**；50 token 块落盘 **1489 KiB**；移动 50 token 块 **42 ms**；移动 86 cell 两块 **76 ms**；逐 cell vs 批量 **508 ms → 115 ms → 42 ms**。
实测文件：`kvmem/blocks/profile.kvmem` **1,524,708 B**、`project.kvmem` **1,097,988 B**；`kvmem/m2_v1/` 夹具块 366,468–640,788 B。即一块 ≈ 50 cell ≈ 1.45 MiB。

**口径纪律**：`508 ms → 42 ms` 是单块优化曲线，`76 ms` 是两块 86 cell 的另一次测量，**口径不同，不可接龙成一条曲线**。

### 7.4 检索数字的边界（防误导，必读）

> **README §7 的 recall@1 0.762 / recall@3 0.952 / MRR 0.921 来自文本检索链（`eval_heldout.py` / `holdout_v3.py` / `eval_retrieval.py`，三脚本 `kvshim`=0 / `KVEngine`=0 / `llama`=0；`kvmem/eval.db` 无 `memory_block` 表），证明的是文本检索层可用，不是 KV 记忆可用。**

补充实测：`holdout_v3.db` / `holdout_v2.db` / `holdout50.db` / `heldout.db` / `eval.db` 五库均**只有 `memory_source`、无 `memory_block` 表**（`sqlite3 mode=ro` 只读盘点）。

### 7.5 10G 显存能挂几块 【推断】

按 Q4_K_M 7B 权重约 4.4 GB（常识估算，仓库无实测）、池 238 MiB、单块 1.45 MiB，池内理论上限约 163 块。但硬约束是**可读距离**：距离 0–1k 召回 56%、1–2k 71%、2–4k 72%、4–8k 64%、**8–16k 0/9、>16k 0/3**（报告自述值）。未在 10G 卡上跑满实测。
证伪方式：在目标卡上跑满池 + 逐距离召回扫描，记录实际可读块数。

---

### 7.6 E10 第四轮（T-010～T-023）：**打死的不是假设，是一个判据**

> 本轮只改夹具、门禁与文档，**引擎逻辑一行未改**：`llama-kv-cache.cpp` **dbe52f9124f1ad29**（ins=500 del=0），DLL `849e7281c74a5288`。
> **`E10 = 已定位·生成侧，未修复` 不变。** 本节所有 pass/fail 数字均须与 `form` 并读（见 7.6.2）。

**7.6.1 已证实（三条，均不依赖 `ok` 标签）**

| # | 结论 | 证据 | 它不能证伪什么 |
|---|---|---|---|
| 1 | 记忆**完整存在且可见**（`coverage[*]`: home 21/21、project 18/18、habit 12/12、project2 18/18；`_assert_trace.py` 输出 `SUM=25 SUM2=25 blk=100 OK=4`） | `evidence/t010/t010_b_dup4_home.*` | 只否定"没写进去/被 mask 掉"，不涉及读取 |
| 2 | **顶部空洞 ⇒ 记忆不生效**：`head_gap>0` **空答 7/7**（8 条记录：`ask` 路径 4、`answers[]` 路径 4），**零 trace 1/7**（仅 `t018` 有 log 可查：`MASKDBG=4` 全是驱动自打，引擎 0 行） | `evidence/t018/` | 与"不贴提问点"共线未分开；只说明**没有生成**，不能说明**劣化生成**。零 trace 的验证范围仅 1/7，**不得写成 7/7** |
| 3 | **单块可答**（`iso_home_only`/home、`iso_habit_only`/habit 均 TRUE，形态 plain） | `evidence/t014/` | 两条均为 `C:inert`（跳过控制臂）产物，**不得与有控制臂的 run 混入同一计数** |

第 2 条使**第一轮 P4「project 空答」降级为夹具现象**——原先把"测试框架没铺满"当成了模型失败。
第 3 条使**"某块本身坏了"这一整类假设作废**。

**7.6.2 判据级发现：`ok` 会把"填空"记成"回忆"**

`ok` 是**对 expected 事实做子串匹配**。于是当模型退化成"填空题并把正确答案列进选项"时，只要答案里出现"广陵路"，就被记为答对。
实测（`runs_iso3/axA_c_habit_home_r1|r2.json`，记录在 `answers[]` 而非 `ask`，故 `ask.ok=None`）：
```
answer = "我住在\_\_\_\_\_\_。\n\nA. 广陵路 12 号 2 单元 602"    ok = True
```
全库 home 记录 `ok × 形态`：`ok=True` 中 45 份 plain、**2 份 quiz/cloze**；`ok=False` 中 19 quiz、5 plain、1 empty。
**在此之前所有 pass/fail 拟合（含本轮被打死的五条假设）都建在这个标签上。**

纪律（今后强制执行，零成本可在既有产物上重算）：
1. 凡报 pass/fail **必须并报 `form`**（`empty` / `quiz` / `plain`），三列并列，不许只报一个 `ok`；
2. **`ok=True 且 form=quiz` 单列"待定"，不得计入 pass**；
3. 同一 run 在 `ask` 与 `answers[]` 两条路径上结论若不一致，**必须两条路径同时报**。

**strict 重算结果（`_strict_label.py` 36466e90a305e81f / 153 行，只读产物、零 run）**：
扫 8 个 `runs*` 根、263 条记录 / 233 文件；同时带两条路径的文件为 **0**（不存在跨路径重复计数）。
`ask` 路径 55 条：raw True 27 ⇒ strict 27（**0 条被剥夺**）；`answers[]` 路径 208 条：raw True 114 ⇒ strict 112（**剥夺 2 条**）。
全库仅 2 条被剥夺，均为 `axA_c_habit_home_r1|r2`；27 个 layout 中只有 `axA_c_habit` 由 2 变 0。
**七个关键对照布局（`iso_dup4`/`iso_dup_p3`/`iso_dup_p2`/`iso_habit_bot`/`iso_dup4_s128`/`iso_car_back`/`iso_no_car`）raw 与 strict 完全同数，无一翻号。**
⇒ 判据确有脏点，但**触达面是 2 条记录，本轮没有任何结论因此改变**。
⇒ 连带影响（**此处我先前写错过一次，已按检测员的纠正改写**）：被剥夺的 2 条是 `axA_c_habit_home_r1|r2`，
它们曾是 `H_last` 与"两条件合取"的反例之一，strict 下转为"待定"。但两者各有独立反例且未被剥夺：
`H_last` —— `axA_c_home` 与 `I13_b_home31`（第四块是 slot1 副本，raw=2 / strict=2）；
两条件合取 —— `I13_b_proj28`（应 pass 实 fail）与 `axA_c_car`（应 fail 实 pass）。
⇒ **两条判死均完好。**
**另须记死**：`iso_dup4` / `iso_dup4_s128` 是 **pass 案例，支持而非判死**——不得当作反例引用（执行者曾如此误述，已纠正）。

**7.6.3 已判死（均有反例在盘，不许以"另加条款"救活）**

`car 在场 ⇒ home 失败` ｜ `第四块内容身份` ｜ `纯距离说` ｜ `纯内容说` ｜ `纯结构说` ｜
`H_last`（第四块必须是 slot2 的副本）｜ `H_neighbor`（紧邻块决定成败）｜ `H_adjacent`（副本相邻即败）｜
**两条件合取**（canonical 顺序 + 第四块是 home/project 的副本）：全库撞出 **21 命中 / 3 反例**（`I13_b_proj28`、`axA_c_car`、`axA_c_habit`）⇒ 判死。

判死口径：**有反例即死**。反例一律连 run 名与关键字段一并写出，不得只写"只剩 X 说"。

**7.6.4 实验线的天然终点（可核理由，非"累了"）**

块库里**内容与尺寸完全绑死**：`home=21`、`project=18`、`habit=12`、`car=19`；变体 `c_*=5`、`b_*=20/28/31`。
"habit 内容 + 18 cells"这类组合**不存在**，而造它需要新 `.kvmem` 张量（引擎侧编码），**不是加一个布局键**。
⇒ 剩余可分离变量全部落在"造块"这一档，本轮实验到此为天然终点。

**7.6.5 产物自证纪律（本轮新立两条）**

· **产物不得写错自己的几何**：`layout.spacing` 曾是硬编码 `64`，`iso_dup4_s128` 实为 128 却被记成 64。已修（`_mask_run.py` **b40cd8a5e942d486** / 252 行，`_driver2.py` **f5811ff0db2fe41f** / 204 行），并保留 `evidence/t020/` 作为缺陷现场。**错得"恰好正确"才最难发现。**
· **命中 ≠ 可用**：按布局名 grep 产物，必须核对命中的文件是否真的含有被判的字段。

**7.6.6 本轮冻结哈希**

`_mask_run.py` **b40cd8a5e942d486**（252 行）｜`_gate.py` **5be03f50c1ac3215**（230 行）｜`_assert_trace.py` **5df5ae7c539b377a**（92 行）｜`_driver2.py` **f5811ff0db2fe41f**（204 行）｜`_form.py` **c409fd15a90699df**（85 行）｜`E10-NEXT2.md` **8615beb2e7648a93**（549 行）；`evidence/` 七个目录 **40 条 SHA256SUMS 自校验 bad=0**。

**7.6.7 门禁输出接口（自 T-015 / T-019 起）**

`OVERALL` 行的措辞**有两种合法前缀**（`4 项 AND` / `5 项 AND`），且任一维 INERT 时会变形——**解析器不得按字面前缀匹配**。
机器请读固定两行：`VERDICT=GREEN|RED` 与 `DIMS=A:.. B:.. 3a:.. 3b:.. C:..`（键名与顺序冻结）。
控制臂维度：`control_ok=True` ⇒ pass；`None` 且有 `control_skipped` ⇒ **INERT**（不投票）；`None` 无 skipped 或缺键 ⇒ **fail**。
## §8 文档史与失真清单（防坑，价值最高）

旧四篇：`README.md`（19:31，自称入口）、`STATUS-REPORT.md`（19:05，技术全量）、`README-HANDOFF-2.md`（15:49，交接二轮）、`README-HANDOFF.md`（13:32，交接一轮）。四篇已归档至 `docs/legacy-2026-10-24/`，**仅作史料**。

| 编号 | 旧说法（带行号） | 代码/产物实际 | 判定 | 影响 |
|---|---|---|---|---|
| D1 行号失真 | HANDOFF 系列给的引擎行号（如 `set_input_kq_mask_impl` 1575、`p0 > p1` 1686） | 工作树同符号在 **1871**、**1982**（`llama-kv-cache.cpp`，上游 1575/1686，偏移 296）；工作树 1575 行现在是 `get_stream()` | 【史料】【部分落地】 | 读者按旧行号找不到代码；**且不是加常数就能修，必须按 hunk 分块** |
| D2 检索与 KV 混淆 | README §7 的头条数字被当作整体能力展示 | 三 eval 脚本零 KV 引用；五库无 `memory_block` 表 | 【史料】 | 把 0.762/0.952/0.921 误读成"KV 记忆可用" |
| D3 实验状态失真 | README:263-265「下一步（唯一）：分段问实验」；STATUS-REPORT:1335「下一个唯一实验（未做）」 | 7 个 run 已于 19:25–19:26 落盘，夹具已修（`m2_visibility_probe.py` 自述 fixes the fixture）；四个 md 对 `m2_visibility` **0 命中** | 【史料】 | 读者以为实验没做，重复安排工作 |
| D4 结论失真 | 文档「块数决定可见性、几何（位置）不影响」 | C 臂 20 cells、贴对话顶部，仍 n=5 恒 1/4；A/B 之间三变量同变 | 【史料】【推断】降级 | 错误定位方向，浪费后续排查 |
| D5 封版措辞失真 | 旧文档按"契约/已定"叙述 pin、`layout_guard`、`n_keep` 止血 | E7 / E8 代码查无；E9 只有告警无自动抬升 | 【史料】【仅文档宣称】 | 产品层能力被高估 |
| D6 分数时差未标注 | 79/81 与 80/81 并列出现 | 是同一份文档里的时间差（`STATUS-REPORT.md:1301-1302`：预算两本账修好前 79/81，修好后 80/81） | 【史料】 | 读者无法判断哪份是现行 |

共性：**乐观归因 + 时间差未标注**，不是笔误。

---

## §9 词表

| 词 | 含义 |
|---|---|
| cell | KV 缓存的最小存储单元，一个 (layer, head, position) 的 K/V 一份 |
| sequence | 序列，`seq_id` 标识；本项目只用了 0=记忆 / 1=对话 |
| `seq_cp` | 序列间引用挂载：只复制 cell 元数据、不搬数据（`kv_unified` 下零拷贝） |
| `seq_repos_local` | 只对位移 cell 重算 RoPE，其余不动（冻结前缀） |
| `kv_unified` | 多序列共享同一 cell 池 |
| requantization | 重量化：q8_0 存储 → dequant → 运算 → 再量化，每次位移必发生一次 |
| 三阶流转 | `.kvmem` 文件 → SQLite 指针 → 引擎内常驻 cell |
| 尺寸块 | 一块 ≈ 50 token ≈ 1.45 MiB 的 KV 状态文件 |
| M1–M5 | 里程碑：M1 检索/放置、M2 多块共存、M3 生命周期、M4 空闲巩固固化、M5 接地与弃答 |

---

## §10 附录

### 10.1 行号换算表（按 hunk 分块，勿用全局常数）

注：`src/llama-kv-cache.cpp` 的新增块 592–887 即**本文件补丁纯新增的 296 行**（全项目唯一一处大偏移源）；下文【甲】类括注里的"偏移 M"就是这个文件级的补丁增量，不是该行本身的属性。

| 文件 | 新增块（工作树） | 换算规则 |
|---|---|---|
| `include/llama.h` | 805–824 | ≤804 不变；≥825 → 上游 = 工作树 − 20 |
| `src/llama-context.cpp` | 495–498、4474–4486 | ≤494 不变；499–4473 → −4；≥4487 → −17 |
| `src/llama-kv-cache.cpp` | **592–887**（本项目唯一大偏移源） | ≤591 不变；≥888 → −296 |
| `src/llama-kv-cache.h` | 144–153、267–269 | ≤143 不变；154–266 → −10；≥270 → −13 |
| `src/llama-kv-cells.h` | 474–504 | ≤473 不变；≥505 → −31 |
| `src/llama-memory.h` | 12–14、120–144 | ≤11 不变；15–119 → −3；≥145 → −28 |

反例（一次讲清，省后来人踩坑）：`llama-kv-cells.h:482` 的 `pos_move` 落在新增块 474–504 内，若机械套 −31 得 451，而上游 451 是**空行**——它压根不在上游存在。

### 10.2 锚点索引（速查）

- 补丁形状：`git -C llama.cpp diff --stat` → 6 files, 405 insertions(+), 0 deletions；`llama-kv-cache.cpp` 单 hunk `@@ -591,0 +592,296 @@`。
- 掩码零改动：`git diff src/llama-kv-cache.cpp | grep -c set_input_kq_mask` = 0。
- 序列语义：`kvmem_persist.cpp:60-61`；`kvshim.cpp:160-161`。
- 重旋转：`llama-kv-cache.cpp:675`（新增块）；`llama-memory.h:129`（新增块）；`llama-context.cpp:4474-4484`（新增块）；`include/llama.h:818`（新增块）。
- Hadamard：`llama-kv-cache.cpp:612-634,820,857-866`（新增块）。
- 掩码增量复用：`llama-kv-cache.cpp:1944-1956`（上游 1648-1660）。
- 定长数组否证：`seq_pos_min[LLAMA_MAX_SEQ]`，`llama-kv-cache.cpp:1889`（上游 1593）。
- 阈值冻结：`freeze_check.py:26`；`GATE 1.30 / COV_MIN 0.35 / REL_CUT 0.55`。
- 三态：`evidence.py:10-12,38,108-121`。
- 知识落库：`memory_source.py:60,67,75-76,82-95`。
- 硬编码记忆源：`chat.py:57,111,121`。
- 探针入口：`m2_visibility_probe.py:1097-1110`（`--arm/--target/--run-json`）。

### 10.3 未验证清单（明说没跑过）

1. **红线整条 HOLDS**：只独立验证了 R1（模型 sha256）；R2（`test_persist.ps1` 三进程 + 写盘）、R3 未跑。
2. `p0_1a_check.py`（16 项）、`p0_1b_check.py`（15 项）、`p0_2_check.py`（22 项）：需加载 4.36 GB 模型 + 写状态文件。
3. `p0_4b_right.py`（3 块 9/9 路径）：需 GPU + 写盘。
4. `hole_matrix.py`（6/6）：需 GPU。
5. `m2_v1.py` 80/81：需 GPU + 写盘，本次未复跑，数字来自旧文档。
6. `states_demo.py`、`diag_place.py`、`kvdrift.py`、`kv_audit.py`、`variance_check.py`：需 GPU。

### 10.4 「已落地」门槛（本文判定依据）

判【代码证实】必须同时有 (a) 实现锚点（函数/语句级）；(b) 验证锚点（能跑的脚本 + 断言点）；(c) 验证可重复（非单次，或明确标【未验证】）。只有 (a) → 最高【部分落地】。E3、E6、P6 即因此降级。

### 10.5 【推断】清单（全文可数，共 3 条）

1. §7.5 10G 显存可挂块数外推。
2. §3.10(d)① 掩码按 seq 增量复用的 cell 窗口裁剪。
3. §3.10(d)② `seq_cp` 共享区间的成员合并路径。

以上三条均附证伪方式，**不得作为结论引用**。

---

## §11 下一步（依赖与验收线）

| 步骤 | 依赖 | 验收线 |
|---|---|---|
| M2.5 可见性收口（E10） | 无（当前阻塞） | 4 块布局下 4/4 段可读，n=5 稳定；且能在 3 段与 4 段之间解释差异（候选机制二选一定性） |
| M3 生命周期 | M2.5 解除 | 引擎层 pin 标志落地；每块 mount 计数；接近预算自动从 pristine 重载；产品侧驱逐策略（非夹具 LRU） |
| M4 写入固化 | M3 | 面向用户的写入口（当前只有 `chat.py:57` 源码常量）；新块自动沉淀并可重建 |
| M5 接地与弃答 | M4 + 检索层 | 生成后答案与权威文本比对；不可接地时弃答而不是编造 |

> **顺序不可颠倒**：没有 M2.5 就没有可靠的读取；没有 M3/M4 就没有可写权威副本，M5 的接地校验会退化成常量规则（假接地）。

---

（本文依据代码与运行产物写成；旧四篇已归档为史料。任何后续改动请同时更新 §2 总表与 §10 附录。）