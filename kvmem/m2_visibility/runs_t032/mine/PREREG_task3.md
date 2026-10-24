# T-031 任务 3 预登记（掩码偏置探针）—— 在任何阶梯运行之前写死

## 探针（引擎侧，llama.cpp/src/llama-kv-cache.cpp 的 set_input_kq_mask_impl）

- 环境变量 `LLAMA_KV_MASK_BIAS="lo:hi:b"`，未设 ⇒ 行为完全不变（解析块只在 env 非空时生效）。
- 只对**位置在 [lo,hi] 内、且值恰为 mask_keep** 的格加 b；位置取自 `cells.pos_get(j2)`（真实 cell），
  不使用行号；被 mask_drop 的格永不改动；空 cell（无位置）跳过。
- 每次 mask 构建打一行 `[MASKBIAS] lo=.. hi=.. b=.. n_cells_touched=.. type=..`，
  n_cells_touched 是该次调用内真实写入的格数（多行 ubatch 时按 (行,格) 计）。
- home 在本构型占位置 4075..4095（21 格）。

## 验收（先做，做不过就不做阶梯）

1. 不设 env：iso_dup4 问 home，answer sha16 必须 == **7ec1430d972d949e**（回归基线）。
2. `LLAMA_KV_MASK_BIAS=4075:4095:0.0`：与不设时答案**逐字节相同**（证明路径无副作用）。
3. `build-vulkan/src/libllama.a` mtime 必须变化（证明真编了）。已记录：1792855433.698493 → 需新的值。

## 阶梯（iso_car_back 问 home，home 在该构型下失败）

b = 1 / 2 / 4，各跑一次，env 固定 `4075:4095:<b>`。

## 预登记结论分支（先写死）

- **某一档开始答对（ok=True）** ⇒ 信息在场且可达，只是注意力没落上去（分配问题）。
- **全档都答错** ⇒ 问题在更上游（编码/读出），不在注意力分配。

## 已知副作用（必须写进结论，不是缺陷）

- b ≠ 0 时 Vulkan 的 mask_opt 快路径失效（该快路径只对全 0 / 全 -inf 的掩码成立），
  **变慢是预期的**，不是新发现；每条运行的 elapsed 一并记录。

## 并发污染检查（本次特有）

- 若一次 mask 构建出现**两行** [MASKBIAS]，说明源文件被第二个写者又插了一段同逻辑
  （偏置会被叠加成 2b）⇒ 该次数据作废，必须在产物里写明。
## 结果（跑完追加）

### 引擎侧改动（唯一改动的源文件：llama.cpp/src/llama-kv-cache.cpp）

- 改动点 3 处，全部在 `set_input_kq_mask_impl` 内：
  1. 函数开头解析 env（未设/格式错 ⇒ `bias_on=false`，什么都不做）；
  2. 每行掩码写完之后，按真实 cell 遍历（`cells.is_empty(j2)` 跳过、`data[idst+j2] != mask_keep` 跳过、
     `p2 = cells.pos_get(j2)` 判 `[lo,hi]`），命中则写 `llama_cast<T>(b)` 并计数；
  3. 函数末尾 `[MASKBIAS] lo=.. hi=.. b=.. n_cells_touched=.. type=..` 一行。
- 源文件 sha256 = c0b1fd4a1193384ea54e83c203c861a5d96d493cdbc8f7dc1dbc15eff164f5ec（构建前后同值；
  `LLAMA_KV_MASK_BIAS` 在文件里出现 3 次 = 1 注释 + 1 getenv + 1 错格式告警 ⇒ **只有一处解析**，不存在双写叠加）。
- 掩码类型实测 **f16**（`type=f16`）。

### 构建

1. `cd /d/llama-mem/build-vulkan && cmake --build . --target llama`（rc=0，编了 llama-kv-cache.cpp.obj 并重打 libllama.a）
   - **libllama.a mtime：1792855433.698493 → 1792856607.7611046**（验收 3 通过）
2. `powershell -NoProfile -ExecutionPolicy Bypass -File D:\llama-mem\tools\build_tools.ps1 -Gpu -Dll -Only kvshim`
   - **第一次失败**：`ld.lld: error: failed to write output 'D:\llama-mem\tools\kvshim_vk.dll': Permission denied`
     —— 另一个 agent 的探针进程正持有该 DLL（详见"并发污染"一节）。我没有 kill 它。
   - **隔离做法**：用与 build_tools.ps1 完全相同的 clang++ 命令行（同 5 个 .a + vulkan-1.lib + 同 flags）
     输出到 **tools/kvshim_vk_t031.dll**（sha256=ed91cbe09618a314cf993d168563dcd8b6c01bc2cb91a9810448b7dbe417ab27），
     探针运行器 `runs_t032/mine/_driver5.py` 用 `KVEngine(..., dll=...)` 指定它，**整条运行路径仍是 _driver2.main**。
   - **后来 DLL 空出来时已补打官方目标**：tools/kvshim_vk.dll 重建成功（rc=0），
     sha256=3a726dbd9e264facceb32205db8e2daee66c1132cc4c69605c040a86970bbf93，
     并用它跑了 `canon_dup4_noenv.json`：OK，sha16=**7ec1430d972d949e**（与基线一致）。

### 验收

| # | 要求 | 结果 |
|---|---|---|
| 1 | 不设 env，iso_dup4 问 home，sha16 == 7ec1430d972d949e | **通过**。探针 DLL：`acc1_dup4_noenv.json` OK/bytes=64/sha16=7ec1430d972d949e，`[MASKBIAS]` 行数 **0**；官方 DLL：`canon_dup4_noenv.json` 同样 sha16=7ec1430d972d949e |
| 2 | b=0.0 与不设时逐字节相同 | **通过**。`acc2_4075_4095_0.0.json` 与 `acc1_dup4_noenv.json` 的 answer **完全相同**（length 30/30，sha16 都是 7ec1430d972d949e）。另跑 `4075:4075:0.0` 与 `0:-1:0.0` 亦相同 |
| 3 | libllama.a mtime 变化 | **通过**（见上，1792855433.698493 → 1792856607.7611046） |

### 阶梯（iso_car_back 问 home；env = 4075:4095:b）

| run | env | rc | verdict | ask_at bytes | answer sha16 | 答案全文 |
|---|---|---|---|---|---|---|
| cb_UNSET | 未设 | 0 | **MISS** | 72 | e63faeffa318b72a | `住在______。  \nA. 杭州市拱墅区  \nB. 杭州市拱墅区北高峰` |
| cb_1 / cb_1_r2 | b=1 | 0 / 0 | **OK** / **OK** | 48 | 121c3c3eaf7d2e82（两次相同） | `我住在\_\_\_\_\_\_。\n\nA. 广陵路 12 号\nB.` |
| cb_2 / cb_2_r2 | b=2 | 0 / 0 | **OK** / **OK** | 70 | 1e10e8ffd360b45f（两次相同） | `住在广陵路 12 号 2 单元 602。\n\n解释：根据提供的地址` |
| cb_4 | b=4 | **3** | **未解释（门禁 RED）** | — | — | 见下 |

- **门禁失败明细（b=4）**：`control_ok=false`，四个控制问题（控制臂 = 纯文本，非记忆布局）全部退化成
  `今天天气一般。今天天气一般。…`。原因可证：偏置窗口按**位置**生效，控制文本恰好占据 3885..4095，
  其中 4075..4095 是控制文本最后 21 个 token（填充句"今天天气一般"）⇒ b=4 把控制臂的尾巴压坏了。
  因此 **b=4 这一档不产生可解释的臂结论**（driver 自己拒绝解释，return 3）。
- 只有 home 的格被碰过（实测）：cb_2 的 130 行里 `n_cells_touched` 取值只有 {0, 21, 189=9×21,
  210=10×21, 231=11×21}，**全部是 21 的整数倍** ⇒ 命中的正是 home 那 21 格，没有溢出到别的块。

### 预登记命中

**命中第一支：某一档开始答对（b=1 即已翻转，b=2 给出干净直答）⇒ 信息在场且可达，只是注意力没落上去
（注意力分配问题），不是更上游的编码/读出。**

- 支持这条的不只是 ok 标签：b=2 的答案里出现完整事实串 `广陵路 12 号 2 单元 602`，且 b=1 的答案里
  正确选项 `A. 广陵路 12 号` 排在 A 位（b=UNSET 时同一构型给出的是 `杭州市拱墅区` 这种错事实）。
- 限制（必须同时写）：
  1. b=4 档无数据，**"从哪一档开始"只能说 ≤1**；没有测 b∈(0,1)，所以"阈值"未测定。
  2. 该窗口同时作用于控制臂（见上），b≥4 时实验设计本身失效。
  3. 偏置是**加在允许格的 logit 上**，等价于把这些格的注意力权重乘 e^b；它证明"抬权即可达"，
     不等于证明"原状态下这些格权重为 0"。
- 速度：b≠0 时 mask_opt 快路径失效属预期；但本次**无法给出干净的耗时对比**——同一张卡上还有别的
  agent 的引擎在跑，实测 elapsed 在 28s（未设）到 86s（同一构型 b=0.0）之间波动，故不给结论。

### 并发污染（本次真实发生，必须连同结论一起看）

- 同 workspace 有**另一个 agent** 在做同一批任务：`kvmem/m2_visibility/t032_run.py`（臂 F_pp18/H1/H2_habitpara12，
  产物在 runs_t032/ 根下，块写成 kvmem/m2_v1/habit_para12.kvmem），其进程长时间持有 tools/kvshim_vk.dll。
- 两次运行**无输出、exit=127 的死掉**（acc2 首次、acc1 首次），复跑同命令即成功 ⇒ 归因为环境竞争，
  不是我这段代码的缺陷（同一命令 `4075:4095:0.0` 第二次跑通，130 行 [MASKBIAS]，答案与基线逐字节相同）。
- 每次运行都数了 `[MASKBIAS]` 行数：完整跑完的 env 运行都是 **130 行**（b=4 门禁中断时 105 行），
  未设 env 的运行是 **0 行**；且**每次 mask 构建只打 1 行** ⇒ 运行期不存在双写叠加。

### 产物（绝对路径）

引擎/工具：
- D:\llama-mem\llama.cpp\src\llama-kv-cache.cpp（[MASKBIAS]，3 处插入）
- D:\llama-mem\tools\t031_patch_maskbias.py（本次插入脚本，幂等性由"只替换一次"断言保证）
- D:\llama-mem\tools\kvshim_vk_t031.dll（隔离探针 DLL）
- D:\llama-mem\tools\kvshim_vk.dll（官方目标，已重建）
- D:\llama-mem\build-vulkan\src\libllama.a（已重编）

运行与证据（D:\llama-mem\kvmem\m2_visibility\runs_t032\mine\）：
- PREREG_task3.md（预登记段跑前写死 + 本节结果）、_driver5.py、control_texts.json
- acc1_dup4_noenv.json/.log、accX_zero.json/.log
- acc2_4075_4095_0.0.json/.log、acc2_4075_4075_0.0.json/.log
- canon_dup4_noenv.json/.log
- cb_UNSET.json/.log、cb_1.json/.log、cb_1_r2.json/.log、cb_2.json/.log、cb_2_r2.json/.log、cb_4.json/.log
