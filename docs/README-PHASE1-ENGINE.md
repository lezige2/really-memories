# llama-mem — 把长期记忆做进模型底层

目标：**不用"对话 + 把记忆拼进 prompt"来维持记忆**，而是改推理引擎本身，
让长期记忆以 KV 张量形式常驻在 attention 里，上下文由引擎自己读，
淘汰"应用层拼字符串"的老路。

## 目录

| 路径 | 用途 |
|---|---|
| `README-HANDOFF.md` | 引擎交接（行号、改动位置、坑清单、构建） |
| `README-HANDOFF-2.md` | **第二轮交接**：shift 实测、训练成本、文献地图、下一步三选一 |
| `llama.cpp-upstream/` | 上游 llama.cpp 纯净克隆（只读参考基线，HEAD `8e5a58d`） |
| `llama.cpp/` | **我们的 fork**，分支 `persistent-memory`（从 upstream 本地 clone，8e5a58d 起） |
| `bin/llama-vulkan/` | 预编译 Vulkan 版 llama-server（性能基线 + 出问题时的回退） |
| `build-cpu/` | 自建 CPU 构建产物（333 个 target） |
| `build-vulkan/` | 自建 Vulkan 构建产物（657 个 target，含全部着色器变体） |
| `vulkan-sdk/` | Vulkan SDK 1.4.363.0（项目内自包含，不进系统 PATH） |
| `tools/kvmem_probe.cpp` | **KV 记忆探针**（M1 机制验证，已跑通） |
| `tools/kvmem_persist.cpp` | **跨进程持久化探针**（write / query / control / shift，已跑通） |
| `tools/test_persist.ps1` | 三进程验收脚本（CPU/GPU × f16/q8_0） |
| `tools/test_shift.ps1` | context-shift 现状实验（变 `n_keep`，五种情况） |
| `tools/build_tools.ps1` | 一条命令重建探针（`-Gpu` 出 `_vk` 版） |
| `tools/kvmem_test.py` | 服务端 slot save/restore 路线验证（已证否，见下） |
| `tools/kv_budget.py` | 从 GGUF 元数据算 KV 记忆预算 |
| `legacy/biomem-legacy.zip` | 旧外挂记忆项目留档（写入门控/遗忘曲线/人格快照，M2 从这里取） |
| `policy/` | *（待建）* 记忆策略层（写什么/合并什么/忘什么） |

## 已验证结论（重要）

### 1. 记忆可以只存在于 KV 中 —— 已实证

`tools/kvmem_probe.cpp` 用**一个 context、两个 sequence**，全程只用 upstream 公开 API：

```
[1] 对照组：全新上下文，prompt 只有问题        → "______。"（答不出）
[2] 记忆文本以 seq 0 解码，占据位置 0..68
[3] llama_memory_seq_cp(mem, 0, 1, 0, -1)      → seq1 pos_max = 68（只加引用，零拷贝）
[4] prompt 里【只有问题】，位置从 69 开始        → "用户陈默的车牌尾号是7302。" ✅
```

结论：**答案只能来自 KV 张量，prompt 中没有任何该信息。**
因果掩码 `p0 <= p1` 天然让会话 token 看见记忆位置，**不需要改权重、不需要重训**。

### 2. 服务端 slot save/restore 路线走不通（已证否）

`tools/kvmem_test.py` 实测：llama-server 的 slot KV 是**和产生它的 prompt 文本绑定**的
（`test_slot_save.py` 里 restore 后 `prompt_n == 6`，靠前缀匹配复用）。
只要新 prompt 不是恢复内容的字面前缀，server 就会丢弃恢复的 KV 重新 prefill。

→ **这正是"必须在引擎层做记忆、而不是靠 server 现成接口"的直接证据。**
记忆区必须从 server 的 prompt 前缀匹配 / 擦除逻辑里独立出来。

### 3. `seq_cp` 是零成本的可见性通道

cell 归属是引用计数，`seq_cp` 不复制 K/V 数据。所以「一份记忆、N 个会话共享」
在数据结构上是免费的 —— 剩下的只是策略与生命周期管理。

### 4. 记忆能跨进程存活 —— 已实证（2026-10-24）

`tools/kvmem_persist.cpp`：进程 A 把记忆 seq 的 KV 用 `llama_state_seq_get_data` 写盘（3.77 MiB）→
**进程退出** → 进程 B 用 `llama_state_seq_set_data` 载回 → `seq_cp 0→1` → prompt 里只有问题 → 答对 7302。

- 对照组（不载入）答不出，证明答案只能来自载回的 KV。
- `CPU-f16 / CPU-q8_0 / Vulkan-f16 / Vulkan-q8_0` 四组合全部通过。
- 恢复会保留 cell 的 `pos` 与索取权，记忆长度不用额外记账。

### 5. context-shift 会静默吃掉记忆 —— 已实测（2026-10-24）

`tools/test_shift.ps1` 照 `server-context.cpp:3698-3699` 做 shift，只变 `n_keep`：

| n_keep | n_discard | 结果 |
|---|---|---|
| 69（记忆长度） | 300 | 答对，记忆仍在 0..68 |
| 0（server 默认） | 300 | 答错，记忆对对话序列的归属被删 |
| 0 | 1 | **仍答对，但记忆被静默下移 1 位、掉了头一个 token** |

shift 的两步是 `seq_rm(id, n_keep, n_keep+n_discard)` + `seq_add(...)`；记忆靠 `seq_cp`
挂在对话 seq 上的 0..68，`n_keep=0` 时第一步就把它删了。默认 `n_discard = n_left/2`，
900 token 的对话一次 shift 丢 300，正好抹平整段记忆。

→ 集成时必须 `n_keep >= mem_len`；但越界不报错，所以还需要引擎侧 pinned 兜底。

### 6. KV 记忆在 5k 上等价于全塞上下文，但 8k 距离外召回直接归零 —— 已实测（2026-10-24）

`tools/kvmem_quality.cpp`：20 条植入事实 / 20 问，三臂对照。

| 臂 | 结果 |
|---|---|
| 全塞上下文 f16 / q8_0 | 17/20 (85%) / 17/20 (85%) |
| **KV 记忆** f16 / q8_0 | **17/20 (85%) / 17/20 (85%)** |
| 无记忆（控制组） | 1/20 (5%，常识蒙对) |

- `kv` 与 `full` 是**同一条 token 序列、同一批位置**，所以逐题同错同对 —— 这是"复用 KV 免费"的
  最强证据（也意味着两臂不一致就是 bug）。
- `q8_0` 在 5k 规模零代价。速度：20 问，全塞上下文 740 s（每题重预填）vs KV 记忆 62 s → **约 24×**。
- 答错的 3 题全是"世界常识压过文档"（青岛→上海、琥珀书店→图书馆、三点半→星巴克），
  控制组给出同一个错答 —— 这是**模型先验**问题，压缩/训练都改不了。

**规模曲线（召回率 vs 事实离问题多远）才是关键数字：**

| 距离 | 0-1k | 1-2k | 2-4k | 4-8k | 8-16k | >16k |
|---|---|---|---|---|---|---|
| 召回 | 56% | 71% | 72% | 64% | **0%** | **0%** |

19,597 token 的记忆只答对 4/20，命中全部落在距离 ≤ 4.5k 的尾部。

→ **"常驻区 pos 0..64k 平铺"的设计不成立**：可见性（§4.1 的 `p0 <= p1`）只保证"看得见"，
不保证"够得着"。加召回门控也没用 —— 屏蔽无关块不会把相关块变近。长记忆只能靠
**压缩（L2b，把内容喂在问题前几十~几百个位置）** 或 **分页 + 按位置差重旋转 K**。
复现：`tools\run_quality.ps1 -Gpu`，曲线用 `python tools\recall_curve.py`。

### 7. 分页投放能完全恢复召回 —— 已实测（2026-10-24）

`tools/kvmem_page.cpp`：把 20k 文档切成 20 段（每段 ~1k token，各自从 pos 0 独立编码），
按索引把对应段灌进窗口再提问。

| 同一份 20k 文档、同样 20 题 | 命中 |
|---|---|
| 全常驻、平铺 | 4/20 (20%) |
| **按 oracle 索引取对块 → 灌窗** | **17/20 (85%)** |
| **按真实索引取块（字符 BM25）** | **16/20 (80%)** |
| 取错块（对照） | 1/20 (5%) |

错块组与"无记忆"基线一致 → **涨分全部来自索引，不来自"上下文变小"**。
索引本身只要 95% 的 retrieval@1（零依赖 BM25 即可，`tools/retrieval_baseline.py`），
端到端代价 5 个点。块加载 0.01 s（page cache），引擎一行未改。

→ 结论：**瓶颈是位置投放，不是显存容量**。项目风险从"模型/训练"转到"索引"，
而索引是本机就能建和调的数据结构 —— 训练（租卡）不在关键路径上。
索引 schema 见 `README-HANDOFF-2.md` §6.3（多方向指针 + 一致度排序）。

## 构建方法（可复现，已验收）

工具链（全部用户级，除 Vulkan SDK 需一次 UAC）：

| 组件 | 版本 / 位置 |
|---|---|
| CMake | 4.4.4（`pip install cmake` → `%LOCALAPPDATA%\Programs\Python\Python314\Scripts\cmake.exe`） |
| Ninja | 1.13.2（`pip install ninja`，同上目录） |
| 编译器 | clang 23.1.0 / llvm-mingw 20260826 msvcrt x86_64（winget `MartinStorsjo.LLVM-MinGW.MSVCRT`） |
| Vulkan SDK | 1.4.363.0 → `D:\llama-mem\vulkan-sdk`（`glslc` / `vulkan.h` / `vulkan-1.lib` 齐全） |

关键坑：**必须加 `-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00`**，否则
`vendor/cpp-httplib` 的 `CreateFile2` 在 MinGW 下没有声明，构建中断。

```powershell
$env:VULKAN_SDK = 'D:\llama-mem\vulkan-sdk'
cmake -S D:\llama-mem\llama.cpp -B D:\llama-mem\build-vulkan -G Ninja `
  -DCMAKE_BUILD_TYPE=Release `
  -DCMAKE_C_COMPILER=<clang.exe> -DCMAKE_CXX_COMPILER=<clang++.exe> `
  -DCMAKE_C_FLAGS="-static -D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00" `
  -DCMAKE_CXX_FLAGS="-static -D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00" `
  -DGGML_VULKAN=ON -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=ON
ninja -C D:\llama-mem\build-vulkan -j 8
```

### 探针重建与第 1 步验收

```powershell
powershell -File D:\llama-mem\tools\build_tools.ps1          # CPU 版探针
powershell -File D:\llama-mem\tools\build_tools.ps1 -Gpu     # Vulkan 版（*_vk.exe）
powershell -File D:\llama-mem\tools\test_persist.ps1 -Kv q8_0
# GPU + 生产 KV 类型：
powershell -File D:\llama-mem\tools\test_persist.ps1 -ExeName kvmem_persist_vk.exe -Gpu 99 -Kv q8_0
```

### 验收结果：与预编译版性能持平（RX 6750 GRE 10GB，Vulkan）

| 构建 | pp256 (t/s) | tg64 (t/s) |
|---|---|---|
| **自建 Vulkan** | **655.88 ± 1.02** | **61.99 ± 0.02** |
| 预编译基线 | 655.03 ± 0.04 | 61.88 ± 0.08 |
| 差异 | +0.13% | +0.18% |

CPU 构建同样通过（`-ngl 0`，6 线程）：prompt 24.1 t/s / 生成 7.1 t/s，输出内容正确。

## 计划中的改动位置（已核对上游源码）

- `src/llama-memory.h` — `llama_memory_i` 接口；上游已有 kv_cache / recurrent /
  hybrid / dsa / msa 五个实现，新增 persistent 实现属于正规扩展
- `src/llama-kv-cache.cpp` 的 `set_input_kq_mask_impl`（约 1650-1715 行）—
  可见性判定 = `cells.seq_has(j, seq_id) && p0 <= p1`（+SWA）
- `src/llama-kv-cells.h` — cell 元数据加 `block_id` / 常驻标志
- `state_write` / `state_read` — 记忆块落盘通道上游已有（`llama_state_seq_get_data/set_data`）
- `tools/server/server.cpp` + `server-context.cpp` — 记忆区从 slot 前缀匹配逻辑中独立；
  暴露 `/memory/write|recall|forget` 给策略层

## 设计要点（2026-10-24 按实测修正）

原设计是"常驻区 pos 0..64k 平铺、对话跑在高位置"。**该设计已废弃**：结论 6 实测出
位置距离 >8k 召回为 0，平铺多少 token 都读不到。改为**分页窗口**：

```
每轮：索引选出 1~2 个块 → 块的 KV 灌进 pos 0..W-1（W ≈ 1~4k）→ 对话接在后面
```

```
┌──── 窗口 pos 0..W（本轮相关的块，随时替换） ────┐┌──── 对话区 pos W.. ────┐
└─────────────────────────────────────────────────┘└────────────────────────┘
   磁盘：剩下的块以 .kvmem 存着，按索引取用（冷读 29 MiB ≈ 0.1–0.3 s）
```

- **每块写入时就从 pos 0 开始编码**，所以任何块都能占据同一个窗口槽 ——
  换块不需要重算 RoPE、不需要改引擎（`seq_rm` + `llama_state_seq_set_data` 即可），
  实测块加载 0.01 s（page cache 命中）。
- **索引是数据结构，不是权重**：只放指针与元数据（时间/地点/参与者/事件/实体），
  内容永远是磁盘上的 KV。可重建、可丢弃，也不受"不许换模型"的红线约束。
- 因果掩码 `p0 <= p1` 仍然成立，但它只保证**看得见**，不保证**够得着** ——
  位置距离才是硬约束。这也是为什么 L2a 必须是"分页"而不是"屏蔽"。

## 关键数字（qwen2 架构，DeepSeek-R1-Distill-Qwen-7B）

- 每 token KV（实测）：**57,344 B (fp16) / 30,464 B (q8_0)** — 28 层 × 4 KV 头 × 128 维；
  q8_0 的 block 里每 32 个值带 2 字节 scale，所以是 `28,672 × 34/32`，不是整整 28 KiB
- 100k tokens 记忆 = **5.34 GiB (fp16) / 2.84 GiB (q8_0)** → q8_0 与 7B Q4 权重(4.36GB)共存于 10GB 显存
- 500k tokens = **14.2 GiB (q8_0) / 26.7 GiB (fp16)**（需落盘分页）；1M tokens = 28.4 / 53.4 GiB（纯磁盘）

## 当前阶段

| 里程碑 | 状态 |
|---|---|
| **M0** 工具链 + 复现构建 | ✅ **完成**（Vulkan 657 target，性能 +0.18%） |
| **M1** 记忆成为一等公民 | 🔄 **机制 + 跨进程持久化已实证**（1/5 项完成），工程化进行中 |
| **M2** 策略层（写入门控/遗忘/人格） | ⏳ 待开始，复用 `legacy/` 里的 Python |
| **M3** 学习式召回门控 | ⏳ 需租卡，本地不做 |

### M1 还差什么（诚实清单）

机制验证 ≠ 产品可用。真正跑起来还需要：

1. ~~**跨进程持久化** —— 把 seq 的 KV 用 `llama_state_seq_get_data` 落盘，新进程
   `set_data` 载回~~ ✅ **已完成**（`tools/kvmem_persist.cpp`，四组合实测通过）
2. **免驱逐保护** —— 记忆 cell 不能被 context-shift / `seq_rm` / SWA 挤掉
   ← 现状已实测（`n_keep=0` 会静默抹掉，见"已验证结论 5"），**下一步做 pinned**
3. **与 server 集成** —— 记忆区独立于 slot 的前缀匹配与擦除（见"已验证结论 2"）
4. **并发共享** —— 一份记忆 KV 供多 slot 复用（`seq_cp` 已有，需接进调度）
5. **容量管理** —— 超出显存时按块分页到磁盘 / 冷热分层

## 基线服务器启动命令

```powershell
Start-Process 'D:\llama-mem\bin\llama-vulkan\llama-server.exe' -ArgumentList `
  '-m','D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf',`
  '-ngl','99','-c','8192','--host','127.0.0.1','--port','8080',`
  '-fa','on','--cache-type-k','q8_0','--cache-type-v','q8_0',`
  '--no-webui','--parallel','1'
```

自建版把 `bin/llama-vulkan/llama-server.exe` 换成 `build-vulkan\bin\llama-server.exe` 即可。

## 模型

GGUF 在 `D:\models\`：`DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf`（4.36GB，主用）。

旧的 ollama 栈（含 deepseek-r1:7b / qwen2.5:7b / qwen3:8b 三份重复拷贝）已整体卸载，
qwen3-8b.gguf 备测模型也已删除 —— 如需异构模型验证，重新下载即可。