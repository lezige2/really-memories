# HANDOFF — llama-mem：把长期记忆做进推理引擎

> 给下一位开发 AI 的交接文档。
> 作者已完成 M0（工具链/构建）与 M1 机制验证。**下面的"已验收事实"不要重做。**
> 文档版本：2026-10-24 · 代码基线 `llama.cpp` @ `8e5a58d`
> 更新：第 1 步（跨进程持久化）已完成并四组合实测通过 —— 见 §2.4；GPU 链接组合也已实测（§7）。
> **本轮之后还有第二份交接：[`README-HANDOFF-2.md`](README-HANDOFF-2.md)** ——
> 里面有 context-shift 实验的实测结论（§2.5 的完整版）、训练成本账、文献地图和下一步三选一。
> 读引擎细节看本文；读"要不要训练、钱花在哪"看那份。

---

## 0. 一句话目标

让长期记忆**以 KV 张量的形式常驻在 attention 里**，由引擎自己决定"看见什么"，
彻底淘汰应用层的「把记忆拼成字符串塞进 prompt」方案。

判断标准（贯穿全程）：**问一个答案只存在于记忆中的问题，prompt 里没有任何该信息，
模型仍能答对。** 这个标准已经达成过一次（见 §2.2）。

---

## 1. 设计约束（不要回退到应用层方案）

以下几条是用户明确的要求，任何实现方案都不得违反：

1. **不许靠 prompt 拼接维持记忆。** 记忆不能每轮被序列化成文本重新喂进去。
2. **不许换模型/重训才能生效。** 现成 7B GGUF 直接可用，这是产品的可行性前提。
3. **记忆必须能被"读到"而不是"被查询到"。** 召回发生在 attention 内部，不是先检索文本块再拼装。
4. **必须有遗忘与合并能力。** 无限增长等于没有记忆（M2 策略层）。

技术上的关键洞察（已实证，见 §2.2）：
KV cache 的因果掩码判定是 `p0 <= p1`，**只要记忆占用低位置、对话跑在高位置，
对话 token 就自动看得见全部记忆**。这件事不需要改权重、不需要重训。

---

## 2. 已经验收的事实（不要重做）

### 2.1 M0：工具链与可复现构建 —— 完成

| 项 | 结果 |
|---|---|
| CPU 构建 | 333 target 全绿，`build-cpu/bin/` 30+ 可执行文件 |
| Vulkan 构建 | 657 target 全绿（含全部着色器变体），`build-vulkan/bin/llama-server.exe` |
| **性能对齐** | 自建 pp256 **655.88** t/s / tg64 **61.99** t/s；预编译基线 655.03 / 61.88 → **+0.13% / +0.18%** |
| 设备 | AMD RX 6750 GRE 10GB，Vulkan，`int dot: 1`，`matrix cores: none` |

构建命令见 §7。**已踩平的坑：MinGW 必须加 `-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00`，
否则 `vendor/cpp-httplib` 的 `CreateFile2` 无声明，构建中断在 86/333。**

### 2.2 M1 机制：记忆只存在于 KV —— 已实证

`tools/kvmem_probe.cpp`（可直接运行，是回归测试）：

```
[1] 对照组：全新上下文，prompt 只有问题          → "______。"（答不出，符合预期）
[2] 记忆文本以 seq 0 解码，占据位置 0..68
[3] llama_memory_seq_cp(mem, 0, 1, 0, -1)        → seq1 pos_max = 68（引用计数，零数据拷贝）
[4] prompt 里【只有问题】，位置从 69 开始          → "用户陈默的车牌尾号是7302。" ✅
```

**这道实验证明了三件事：**

- 答案只能来自 KV 张量，prompt 中无此信息；
- `seq_cp` 是零成本的可见性通道（cell 归属是引用计数，不复制数据），
  所以「一份记忆、N 个会话共享」在数据结构上是**免费**的；
- 全程**未改动任何引擎代码**，纯 upstream 公开 API。

> 复现命令：`tools\kvmem_probe.exe -m D:\models\<模型>.gguf --gpu 0 --n 24`
> 注意 `n_seq_max` 必须 ≥ 2，默认是 1，否则报 `invalid seq_id`。

### 2.3 已证否：server 的 slot save/restore 路线

`tools/kvmem_test.py` 实测结论：**llama-server 的 slot KV 绑死在产生它的 prompt 文本上。**

证据在 `tools/server/tests/unit/test_slot_save.py`：restore 之后发新请求，`prompt_n == 6`
（只处理差异部分）——它靠 `slot.prompt.tokens.get_common_prefix()` 做前缀匹配复用。
新 prompt 只要不是那段文字的字面前缀，`n_past` 就被归零，恢复的 KV 被丢弃。

**这条结论直接决定了要改哪里**：不要去造"把 KV 存盘再读回"的 API 绕路，
**必须把记忆区从 server 的前缀匹配 / 擦除逻辑里独立出来**（见 §4.5）。

---

### 2.4 M1 第 1 步（跨进程持久化）—— 完成（2026-10-24 补测）

`tools/kvmem_persist.cpp` 把 §5 第 1 步连成闭环，三个子命令**各跑一个进程**：

| 阶段 | 做什么 | 结果 |
|---|---|---|
| `control` | 全新上下文，prompt 只有问题 | `______。` 答不出（符合预期） |
| `write` | 记忆解码进 seq 0（69 token，pos 0..68），`llama_state_seq_get_data` 落盘 | 3.77 MiB，进程退出 |
| `query` | 新进程 `llama_state_seq_set_data` 载回，`seq_cp 0→1`，prompt 仍只有问题 | `车牌尾号是7302。` ✅ |

实测矩阵（**四种组合全部通过**）：CPU-f16 / CPU-q8_0 / Vulkan-f16 / Vulkan-q8_0。

```powershell
# CPU
powershell -File D:\llama-mem\tools\test_persist.ps1              # f16
powershell -File D:\llama-mem\tools\test_persist.ps1 -Kv q8_0    # 生产配置
# GPU（先跑 build_tools 生成 _vk 版，见 §7）
powershell -File D:\llama-mem\tools\test_persist.ps1 -ExeName kvmem_persist_vk.exe -Gpu 99 [-Kv q8_0]
```

两个实现细节（下一位会踩）：

- 载入端的 `n_seq_max` 必须与写盘时一致：`n_stream = unified ? 1 : n_seq_max`，
  不一致时 `state_read` 抛 `n_stream mismatch`，文件读不进去。
- 恢复会**保留每个 cell 的 `pos` 与索取权**，所以记忆长度不用额外记账，
  直接 `llama_memory_seq_pos_max(mem, 0)` 就能拿到（文件头里的 `n_pos_max` 只做交叉校验）。

---

### 2.5 第 2 步现状实验：context-shift 会不会毁掉记忆 —— 已实测（2026-10-24）

`tools/test_shift.ps1`（`kvmem_persist shift` 子命令）把对话区填到 900 token，
然后**完全照 `server-context.cpp:3698-3699`** 做一次 shift，只变 `n_keep`：

| n_keep | n_discard | 结果 |
|---|---|---|
| 69（= 记忆长度） | 0 | 答对（填充本身无害） |
| 69 | 300 | 答对，记忆仍在 0..68，对话 pos_max 968→668 |
| **0（server 默认）** | 300 | `____。` **答错** |
| 0 | 69 | 答错（整个记忆被丢） |
| 0 | 1 | **仍答对，但记忆已被静默下移 1 位、并掉了第一个 token** |

**机理**：server 的 shift 分两步，`n_keep` 默认 0，于是丢弃区间从 pos 0 开始：

```
seq_rm (id, n_keep, n_keep + n_discard);                 // 第一步就删"归属"
seq_add(id, n_keep + n_discard, pos_next, -n_discard);   // 其余整体左移
```

而记忆正是通过 `seq_cp` 挂在对话序列上的 0..68 —— 第一步就把"对话看得见记忆"删掉了。
`n_discard = n_left/2` 是 server 的默认值，900 token 的对话一次 shift 就丢 300，
**正好把整段记忆抹平**。

**对第 2/3 步的直接结论**：

1. **一行就能止血**：server 集成时把 `n_keep` 下界钉在记忆长度上
   （`n_keep = max(user_n_keep, mem_len)`），shift 就不再碰记忆。
2. **但不能只靠这个约定**：`n_discard=1` 那行证明越界不会报错，只会**静默移位/截断** ——
   答案碰巧还在就"看起来正常"。所以 §4.6 的 `pinned` 标志值得做：
   它把"记忆 cell 不进任何可丢弃区间"变成数据结构里的不变量，而不是调用方纪律。
3. **`seq_pos_min == 0` 不能用来判断记忆是否还在**：shift 会把闲聊 cell 搬到 0..，
   这个指标会假阳性。唯一可靠判据是问答结果（探针就是这么判的）。

**顺带确认的两个容量事实**：

- 非 unified 模式下 `n_ctx_seq = n_ctx / n_seq_max`（再 pad 到 256 的倍数）。
  `n_seq_max=8` + `n_ctx=1024` 时每条 seq 只有 128 个 cell，900 token 根本填不进去
  （报 `failed to find a memory slot`）。记忆系统的 `n_ctx` 要按 **每 seq 容量 × seq 数** 算。
- `--unified`（`cparams.kv_unified = true`）下 `n_ctx_seq = n_ctx`，所有 seq 共享一个池，
  保存/恢复/seq_cp/shift 行为与上表**完全一致**。做 100k 记忆时应该用 unified，
  否则容量会被 `n_seq_max` 除一遍。

---

## 3. 分层方案：训练到底能做到哪一层

先纠正一个常见误判：**"10GB 显存训不了 7B"是错的**。
全参微调 7B 需要 ~15GB（bf16 权重 + 优化器状态）确实不行；
但 **QLoRA（4-bit 冻结底座 + 低秩适配器）在 10GB 上完全可行**（约 6-8GB）。

真正的限制不是显存，是**软件栈**：gfx1031（RX 6750 GRE）在 Windows 上
没有官方 ROCm（AMD 的 Windows ROCm 只覆盖部分 gfx11xx），DirectML 训练算子覆盖与性能都勉强，
ZLUDA 属实验性。**结论：要真训练，租一张 24GB 卡几小时是最省事的路，不要在本机硬磕。**

| 层 | 做什么 | 需要训练？ | 本地可行性 | 价值 |
|---|---|---|---|---|
| **L0 引擎层** | KV 布局、mask 可见性、免驱逐、落盘、server 集成 | ❌ 零训练 | ✅ **完全可行，已验证** | ★★★★★ 核心目标 |
| **L1 接口层** | 记忆块的位置分配、块边界、注意力偏置（手工/常数） | ❌ 零训练 | ✅ 可行 | ★★★★ |
| **L2a 召回门控** | 学一个打分器决定"这次该让哪些记忆块可见" | ✅ 小模型 | ✅ 10GB 足够（甚至 CPU/DirectML） | ★★★★ 性价比最高 |
| **L2b 记忆编码器** | 把文档编码成 N 个 KV 槽（gist tokens / memorizing encoder） | ✅ 需反传穿 7B | ⚠️ 10GB 勉强，租 24GB 舒服 | ★★★★★ 质量跃升 |
| **L3 架构层** | 新增记忆交叉注意力层 + 继续预训练 | ✅ 大规模 | ❌ 7B 需多卡；单卡只能做 ≤1B 玩具 | ★★ 研究向，非产品 |

### 最佳方案（推荐顺序）

**L0 + L1 先做完 → L2a 顺手加上 → L2b 视质量需求决定 → L3 不做（除非要发论文）。**

理由：L0 已经把"记忆在 attention 里"这个根本目标免费拿到了。
L2a 用一个**不需要动 7B** 的小模型解决"记忆变多后注意力被稀释/太贵"的问题，投入产出比最高。
L2b 是真正能提升"记忆利用率"的技术（让一段文字被压缩成几百个 KV 槽而不是几千 token），
但需要租卡。L3 在单卡上只能做出没有实用价值的玩具，明确不建议。

> 关于 L2b 的参考方向（下一位可以直接查论文）：Gist Tokens、Memorizing Transformers、
> ICAE (In-Context Autoencoder)、AutoCompressors、prefix-tuning。核心都是"冻结主模型 + 训一个编码器"。

---

## 4. 改动位置（全部已核对到行）

> 基线：`D:\llama-mem\llama.cpp`，分支 `persistent-memory`。
> 行号对 `8e5a58d` 有效；上游 rebase 后需重新定位（用函数名搜，不要信行号）。

### 4.1 可见性判定 —— 记忆能不能被看见，就看这里

`src/llama-kv-cache.cpp:1575` `set_input_kq_mask_impl<T, causal, swa, is_2d, alibi>()`

核心循环（1655-1719）：

```cpp
1664:  if (cells.is_empty(j))            goto skip;   // 空格 → 屏蔽
1669:  if (!cells.seq_has(j, seq_id))    goto skip;   // 不属于本序列 → 屏蔽
1673:  p0 = cells.pos_get(j);
1686:  if (causal && p0 > p1)            goto skip;   // 未来 token → 屏蔽
1706:  if (swa && is_masked_swa(...))    goto skip;   // SWA 窗口外 → 屏蔽
1714:  data[idst + j] = mask_keep;                    // ← 可见
1718:skip: data[idst + j] = mask_drop;
```

**结论：只要记忆 cell 的 `seq_has(j, seq_id)` 成立且 `p0 <= p1`，就自动可见。**
所以 L0 的改动重点**不是**改这个循环，而是：
- 保证记忆 cell 永不被 `seq_rm` / context-shift 删掉（§4.5、§4.6）；
- 保证新会话能拿到这些 cell 的归属（`seq_cp`，已验证）。
- 若要做 L2a 门控，**唯一需要动的就是这里**：在 1714 之前加一个
  「该块是否被本次召回门控选中」的判断（`if (!gate->visible(block_id(j), this_query)) goto skip;`）。

### 4.2 记忆抽象接口

`src/llama-memory.h:73` `struct llama_memory_i`
上游已有 kv_cache / recurrent / hybrid / iswa / dsa / msa 六个实现，
新增一个 `persistent` 实现属于**正规扩展**，不是 hack。
需要实现的纯虚函数：`init_batch / init_full / init_update / get_can_shift /
clear / seq_rm / seq_cp / seq_keep / seq_add / seq_div / seq_pos_min / seq_pos_max /
memory_breakdown / state_write / state_read`。

### 4.3 记忆对象构造工厂

`src/llama-context.cpp:486` — `llama_memory_params params_mem = { ... }`
在这里按 `ctx_type` 分派到新的 persistent 实现。

### 4.4 记忆落盘通道（已有，未接成闭环）

`src/llama-context.cpp:4570` `llama_state_seq_get_data()`
`src/llama-context.cpp:4582` `llama_state_seq_get_data_ext()`
`include/llama.h:890/900` 成对的 `get_data` / `set_data`，以及 `:941/948` 的 `_ext` 变体。

M1 待办第一项就是把它连成闭环：**把某个 seq 的 KV 写盘 → 杀掉进程 → 新进程读回 → 记忆仍生效。**

### 4.5 ★ 最关键：记忆区必须独立于 slot 的前缀匹配

`tools/server/server-context.cpp`

| 行 | 代码 | 为什么重要 |
|---|---|---|
| **3995** | `n_past = slot.prompt.tokens.get_common_prefix(input_tokens);` | **记忆被丢弃的元凶**：`n_past` 由 prompt 文本前缀长度决定，新文本一旦不匹配就归零 |
| 4074 | `n_past = 0;` | 兜底归零，同样会抹掉恢复的 KV |
| 4077 | `pos_next = slot.prompt.tokens.pos_next(n_past);` | 位置分配；记忆区要求对话从 `mem_len` 起算 |
| 4217 | `slot.prompt.tokens.keep_first(n_past);` | 截断 prompt 记录 |
| 4923 | `slot.mem.seq_rm(slot.id, slot.prompt.tokens.pos_next(), -1);` | 按序列清理，记忆序列不能被波及 |
| 1815 | `tokens.get_common_prefix(task.tokens)` | 另一处前缀匹配（多轮/续写路径） |

**改法**：把"记忆序列"（比如 `seq_id = 0` 或专用 id）从 slot 的
`prompt.tokens` 记账中彻底剥离 —— 它不参与前缀匹配、不被 `keep_first` 截断、
不被 `seq_rm` 删除。对话依旧从 `pos = mem_len` 开始编号。

### 4.6 免驱逐保护（context shift）

`tools/server/server-context.cpp:3699`
`slot.mem.seq_add(slot.id, n_keep + n_discard, slot.prompt.tokens.pos_next(), -n_discard);`
——上下文超长时的滑动窗口会整体左移位置。记忆区**必须**在 `p0` 下界之外，
否则会被 shift 挤掉或位置错乱。同理 `src/llama-kv-cache.cpp` 里的
`seq_add/seq_div` 路径要拒绝作用于记忆序列。

### 4.7 HTTP 路由

`tools/server/server.cpp:323`
`ctx_http.post("/slots/:id_slot", ex_wrapper(routes.post_slots));`
在 `server-context.cpp:5723` 的 `post_slots` 旁边照葫芦画瓢加
`/memory/write`（写入一段文本→变成常驻 KV）、`/memory/forget`（按块删）、
`/memory/list`。**注意 `/slots` 的 save/restore 已有实现但语义不对（见 §2.3），不要复用它的语义。**

---

## 5. 实施步骤与验收标准

### 第 1 步：跨进程持久化 —— ✅ **已完成**（见 §2.4，`tools/kvmem_persist.cpp`）

- 用 `llama_state_seq_get_data` 把记忆 seq 的 KV 写盘
- 新进程 `set_data` 载回，且**不改 prompt**
- **验收**：进程 A 写入记忆 → 进程 A 退出 → 进程 B 启动 → 只问问题 → 答对。
  复用 `tools/kvmem_probe.cpp` 的结构，改成两段式（write / query）。

### 第 2 步：免驱逐 + 位置管理 —— ⚠️ 现状已实测（§2.5），实现待做

- 现状：记忆会不会被 shift 挤掉，**完全取决于调用方的 `n_keep`**；`n_keep=0`（server 默认）
  一次 shift 就抹平，且不报错。
- 要做：
  - 记忆 cell 加 `pinned` 标志（`src/llama-kv-cells.h`）
  - `seq_rm` / `seq_add` / `seq_div` / context-shift 全部跳过 pinned cell
  - 集成侧同时把 `n_keep` 下界钉在 `mem_len`（双保险，且 pinned 负责兜住调用方算错的情况）
- **验收**：`test_shift.ps1` 的 "server default" 那行（`n_keep=0`）从 FAIL 翻成 PASS。

### 第 3 步：接入 server（这才是产品形态）

- 记忆序列与 slot 记账解耦（§4.5）
- `/memory/*` 接口
- **验收**：起 server → `POST /memory/write` 写入一段档案 → **重启 server** →
  新的对话（prompt 里只有问题）答对。且 `GET /slots` 显示记忆不占对话上下文配额。

### 第 4 步：M2 策略层（复用旧代码）

- 从 `legacy/biomem-legacy.zip`（56 个源文件）取：写入门控、遗忘曲线、人格快照、记忆合并
- 它从"拼 prompt 的组装器"改造成"调用 /memory/* 的控制器"——**逻辑复用，角色改变**
- **验收**：连续对话 50 轮后，记忆块数量有增有减（有合并、有淘汰），不单调膨胀。

### 第 5 步：L2a 召回门控（可选，性价比高）

- 训练一个**独立小模型**（bi-encoder，50-200M）给 (query, memory_block) 打分
- 训练数据可全合成，**不需要 7B 参与**，10GB 显卡甚至 CPU 都能训
- 推理时在 §4.1 的 1714 之前插入 `goto skip`
- **验收**：记忆扩到 200 块后，单次生成延迟不随块数线性增长，且问答准确率不降。

---

## 6. 训练方案（若要做 L2b）

**只训编码器，冻结 7B。** 目标：把一篇文档映射成 N 个 KV 槽（如 N=256），
让冻结的 7B 在这些槽上做 attention 时能"读懂"原文。

- 方法：4-bit 冻结 7B + 可训练编码器（几层 transformer），交叉熵损失，梯度只回传到编码器
- 显存：编码器 + 4bit 底座 + 激活（seq 2-4k，梯度检查点）→ **10GB 很紧，24GB 舒服**
- 数据：长文档 + 针对文档的 QA（可用合成 + 开源长文本 QA）
- **验收**：同一段 8k token 的文档，用 256 个 KV 槽编码后回答问题的准确率，
  不低于把 8k token 全塞进上下文的 90%

**如果只能在本机做**：先把编码器规模降到 ~50M、序列降到 1k，用 DirectML 试通管线，
验证"训练→产出→冻结模型可用"的闭环，再上租卡放大。**不要在本机硬训 7B。**

---

## 7. 环境与构建（可复现）

| 组件 | 版本 / 路径 |
|---|---|
| CMake | 4.4.4 · `%LOCALAPPDATA%\Programs\Python\Python314\Scripts\cmake.exe` |
| Ninja | 1.13.2 · 同目录 |
| 编译器 | clang 23.1.0 / llvm-mingw 20260826 **msvcrt** x86_64（winget `MartinStorsjo.LLVM-MinGW.MSVCRT`） |
| Vulkan SDK | 1.4.363.0 · `D:\llama-mem\vulkan-sdk` |
| 模型 | `D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf`（4.36GB） |
| Python | 3.14.5 · `%LOCALAPPDATA%\Programs\Python\Python314\python.exe` |

```powershell
$env:VULKAN_SDK = 'D:\llama-mem\vulkan-sdk'
$clang = 'C:\Users\lezige\AppData\Local\Microsoft\WinGet\Packages\MartinStorsjo.LLVM-MinGW.MSVCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\llvm-mingw-20260826-msvcrt-x86_64\bin'
cmake -S D:\llama-mem\llama.cpp -B D:\llama-mem\build-vulkan -G Ninja `
  -DCMAKE_BUILD_TYPE=Release `
  -DCMAKE_C_COMPILER="$clang\clang.exe" -DCMAKE_CXX_COMPILER="$clang\clang++.exe" `
  -DCMAKE_C_FLAGS="-static -D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00" `
  -DCMAKE_CXX_FLAGS="-static -D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00" `
  -DGGML_VULKAN=ON -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=ON
ninja -C D:\llama-mem\build-vulkan -j 8
```

探针编译（改完引擎后跑这个做回归。**下面这条是实测通过的 CPU 路线**）：

```powershell
& "$clang\clang++.exe" -std=c++17 -O2 -static -D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00 `
  -I D:\llama-mem\llama.cpp\include -I D:\llama-mem\llama.cpp\ggml\include `
  D:\llama-mem\tools\kvmem_probe.cpp -o D:\llama-mem\tools\kvmem_probe.exe `
  D:\llama-mem\build-cpu\src\libllama.a D:\llama-mem\build-cpu\ggml\src\ggml.a `
  D:\llama-mem\build-cpu\ggml\src\ggml-cpu.a D:\llama-mem\build-cpu\ggml\src\ggml-base.a `
  -pthread "<mingw>\x86_64-w64-mingw32\lib\libomp.dll.a" -lpthread -lkernel32 -luser32 -lgdi32 `
  -lwinspool -lshell32 -lole32 -loleaut32 -luuid -lcomdlg32 -ladvapi32
```

> **想跑 GPU 版探针**（更快，`--gpu 99`）：把上面 4 个 `.a` 换成 `build-vulkan\` 下的同名文件，
> 并**额外**加上 `build-vulkan\ggml\src\ggml-vulkan\ggml-vulkan.a`（42MB）和
> `D:\llama-mem\vulkan-sdk\Lib\vulkan-1.lib`。
>
> ✅ **这条组合已实测通过（2026-10-24 补测）**：llvm-mingw 的 `ld` 能直接吃 MSVC 的 `vulkan-1.lib`，
> 无需 `llvm-dlltool` 转换；产物 `tools\kvmem_persist_vk.exe`（约 50MB）可正常 `--gpu 99` 跑通。
> 链接顺序：`libllama.a ggml.a ggml-cpu.a ggml-vulkan.a ggml-base.a vulkan-1.lib`。
> 一条命令重建：`powershell -File tools\build_tools.ps1 -Gpu`（脚本里已封装两套链接参数）。

---

## 8. 坑清单（血泪，逐条踩过）

1. **`-D_WIN32_WINNT=0x0A00` 必须加**，否则 cpp-httplib 的 `CreateFile2` 无声明。
2. **`cparams.n_seq_max` 默认 1**，用多 sequence 前必须调大，否则 `invalid seq_id`。
3. **llama-server 的 slot KV 是 prompt 文本绑定的**（§2.3）。别指望 save/restore 抄近路。
4. **Vulkan SDK 安装器是 Qt Installer Framework，`asInvoker` 但仍会在装 VC_redist 时要求提权**，
   命令行模式下直接报 `Cannot elevate access rights while running from command line` 并回滚。
   必须 `Start-Process -Verb RunAs`（一次 UAC）。headless 语法：**选项在前，命令在后** ——
   `installer.exe --root <dir> --accept-licenses --confirm-command --default-answer install`。
5. **`curl` 访问 github 报 `CRYPT_E_NO_REVOCATION_CHECK`** —— 是吊销列表查不到，不是墙。
   加 `--ssl-no-revoke` 即可（实测 200）。`git` 协议本来就正常。
6. **`sdk.lunar.org` 是拼错的**，正确域名 `sdk.lunarg.com`。
7. **PowerShell 5.1 解析含中文字面量的脚本会出错** —— 脚本保持 ASCII，或改用 write 工具写 UTF-8 文件。
8. **本机 7z 在 AMD 软件包里**：`C:\Program Files\AMD\AMDInstallManager\7z.exe`（7-Zip 25.01 全功能版）。
9. **`llama-cli` 没有 `-no-cnv`**，单轮用 `-st / --single-turn`。
10. **`p0 <= p1` 是可见性判定**，`p1` 是 query 的位置，`p0` 是 key 的位置。位置 >= 记忆长度即可见。
11. **多 sequence 共享 cell 是引用计数**，`seq_rm` 删掉自己那份不会影响其他序列的视图。
12. **q8_0 的"28 KiB/token"是理想值**：block 里每 32 个值带 2 字节 scale，实际
    `28,672 × 34/32 = 30,464 B`（29.75 KiB）。实测 30,487 B/token（多出的 23 B 是文件头）。
    → 100k token 记忆是 **2.84 GiB**，不是 2.67 GiB（见 §10）。
13. **KV 状态文件的 `n_stream` 必须与载入端 `n_seq_max` 一致**（`n_stream = unified ? 1 : n_seq_max`），
    否则 `state_read` 直接抛 `n_stream mismatch`，不是静默失败。
14. **非 unified 时每条 seq 只有 `n_ctx / n_seq_max` 个 cell**（还会 pad 到 256 的倍数）。
    `n_ctx=1024` + `n_seq_max=8` → 每 seq 128，塞 900 token 直接报
    `failed to find a memory slot`。记忆系统用 `--unified`，容量才不被 seq 数除。
15. **context-shift 的 `n_keep` 默认 0**，会从 pos 0 开始丢，正好切进记忆区（§2.5）。
    集成时 `n_keep` 必须 ≥ 记忆长度；而且越界不报错，只会静默移位/截断。

---

## 9. 文件清单

| 路径 | 说明 |
|---|---|
| `llama.cpp/` | 工作 fork，分支 `persistent-memory` |
| `llama.cpp-upstream/` | 纯净上游，用于 diff / rebase，**不要改** |
| `build-cpu/` · `build-vulkan/` | 两套构建产物 |
| `bin/llama-vulkan/` | 预编译基线（性能对照 + 回退） |
| `tools/kvmem_probe.cpp` | **机制探针 + 回归测试**（§2.2） |
| `tools/kvmem_persist.cpp` | **跨进程持久化探针**（§2.4）：write / query / control / shift 四个子命令 |
| `tools/test_persist.ps1` | 第 1 步验收脚本（三进程，CPU/GPU、f16/q8_0 通用） |
| `tools/test_shift.ps1` | 第 2 步现状实验（§2.5）：变 `n_keep` 看 shift 是否吃掉记忆 |
| `tools/build_tools.ps1` | 一条命令重建探针（`-Gpu` 出 `_vk` 版） |
| `tools/kvmem_test.py` | 已证否的 server 路线（§2.3），留作证据 |
| `tools/kv_budget.py` | GGUF → KV 预算计算 |
| `vulkan-sdk/` | 项目内自包含 SDK |
| `legacy/biomem-legacy.zip` | 56 个源文件的旧策略层，M2 的素材 |
| `README.md` | 技术日志（构建数据、设计图） |

---

## 10. 硬约束

- **显存 10GB**（RX 6750 GRE / gfx1031）：7B Q4（4.36GB）+ KV + 计算缓冲 ≈ 8GB。
  每 token KV（**实测**）：fp16 **57,344 B**（56 KiB）/ q8_0 **30,464 B**（29.75 KiB）。
  → 100k token 记忆 = **5.34 GiB (f16) / 2.84 GiB (q8_0)**，q8_0 与 7B Q4 共存刚好塞得下；
  再大必须分页落盘。**旧文档写的 2.67 GiB 是忽略了 q8_0 block scale 的乐观值，差 6.25%。**
- **内存 16GB DDR4**：注意别把模型和 KV 同时放大内存。
- **磁盘**：D: 约 86GB 可用，C: 约 82GB。
- **无 ROCm**：任何 PyTorch 训练走 DirectML / ZLUDA 都是实验性质，正经训练租卡。

---

## 11. 下一步第一件事

第 1 步（§2.4）与第 2 步现状实验（§2.5）都已完成，**不要重做**。现在的结论很具体：

**`n_keep=0` 一次 shift 就会静默吃掉记忆；`n_keep >= 记忆长度` 则毫发无损。**
所以第 2 步只剩一件事：让"记忆不被驱逐"变成引擎保证，而不是调用方纪律。

1. `src/llama-kv-cells.h` 加 `pinned`（或直接复用 mem 的 seq 归属判断：记忆 seq 的 cell 一律 pinned）。
2. `llama_kv_cache::seq_rm` / `seq_add` / `seq_div` 跳过 pinned cell；
   `find_slot` / defrag 不得回收 pinned cell。
3. 用 `test_shift.ps1` 做回归：**"server default" 那行必须从 FAIL 翻成 PASS**，
   另外四行保持不变（尤其 `n_discard=1` 那行不能从"静默移位"变成"报错"）。

做完再进第 3 步（server 集成，§4.5）：`n_keep = max(n_keep, mem_len)` + `/memory/*` 路由。