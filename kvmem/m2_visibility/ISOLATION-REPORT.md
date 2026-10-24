# m2 可见性 · 变量隔离过程报告（ISOLATION-REPORT）

**状态：已定稿·可引用** ｜ **日期：2026-10-24** ｜ **可否引用：可以；引用须连同 §1 的冻结哈希。本版定稿；任何修订必须换哈希，并同步更新 PROJECT-STATE.md**

---

## §0 一句话

引擎把块挂上去了、cell 归属完整、**KQ 掩码窗口里这些块也没有被 -inf 屏蔽**，但 4 块布局下最顶上那块仍然读不出来。失败点已切到**掩码层之外（图/生成/权重侧）**：不是挂载层、不是 cell 归属层、不是窗口级 -inf 层。

---

## §1 冻结表（结论必须绑这四行，缺一即为"某次观察"）

| 文件 | sha256（前 16） | 作用 | 若被改动，则哪条结论作废 |
|---|---|---|---|
| `llama.cpp/src/llama-kv-cache.cpp` | `dbe52f9124f1ad29` | 引擎侧 95 行打印插桩（含 2 行 include） | §7 全部掩码读数、四格表落位 |
| `runs_mask/_mask_run.py` | `9d7d502c3563ec25` | 单进程跑一臂，落 cmdline/mask_env/asks_expected/trace_classes | §7.2 A/B 受控对照的"全同"证明 |
| `runs_mask/_assert_trace.py` | `130401439f3ee438` | 逐块自洽 + p1 行数 + 三路对账，失败非零退出 | 全部"断言通过"的结论 |
| `runs_mask/_smoke_pair.py` | `c0e568431ebca0d6` | 断言两次冒烟只差 `MASK_SEQ` 一个键 | §7.2 "受控"这一定性 |

- 运行期 DLL `tools/kvshim_vk.dll` sha256 `849e7281c74a5288afb931b8c861e8190009ffb5c5244118176c2abfa1abc02e`；插桩前备份 `runs_mask/kvshim_vk.dll.bak` = `c7ea09bbc7cb616f4c649d76d8c4839bb7c9934861a70d7999959f44d793e3b8`。
- 补丁：`runs_mask/pre.patch`（原 405 行纯新增）sha256 `3db65414…`；`post.patch` sha256 `209f6b230ad74a56…`。
- `git diff --numstat`：`20/0 include/llama.h`、`17/0 src/llama-context.cpp`、`391/0 src/llama-kv-cache.cpp`、`13/0 src/llama-kv-cache.h`、`31/0 src/llama-kv-cells.h`、`28/0 src/llama-memory.h` → **TOTAL ins=500 del=0**。
- 真实删除：`git diff | grep -c '^-[^-]'` → **0**。

**重算命令（三合一，缺一退回"看"）**：

```bash
cd /d/llama-mem/llama.cpp && git diff --numstat | awk '{i+=$1;d+=$2;print} END{print "TOTAL ins="i" del="d}'
cd /d/llama-mem/llama.cpp && git diff | grep -c '^-[^-]'      # 必须 0
cd /d/llama-mem && python -X utf8 -c "import hashlib;[print(n, hashlib.sha256(open(p,'rb').read()).hexdigest()) for n,p in [('cpp',r'llama.cpp/src/llama-kv-cache.cpp'),('mask_run',r'kvmem/m2_visibility/runs_mask/_mask_run.py'),('assert',r'kvmem/m2_visibility/runs_mask/_assert_trace.py'),('pair',r'kvmem/m2_visibility/runs_mask/_smoke_pair.py')]]"
```

**计数陷阱（固定注脚）**：`git diff | grep -c '^-'` 会数出 **6**（6 个文件的 `--- a/<path>` 头），不是删除行。必须用 `^-[^-]`。
同一个病在日志里也犯过：`grep -c MASKDBG` 把 4 行 `[MASKDBG-OK]` 数进"反向冒烟应为 0"的判据里 —— **凡计数，先问这个数跨了几个类别。**

**回滚**：

```bash
cd /d/llama-mem/llama.cpp && git checkout -- src/llama-kv-cache.cpp
cd /d/llama-mem && cp kvmem/m2_visibility/runs_mask/kvshim_vk.dll.bak tools/kvshim_vk.dll
cmake --build build-vulkan --target llama -- -j 8 && powershell -ExecutionPolicy Bypass -File tools/build_tools.ps1 -Gpu -Dll -Only kvshim
```

---

## §2 方差与确定性（n=5，`runs_var/` 35 runs）

- 7 臂 × 5 次 = 35 run，rc 全 0，控制闸 35/35，单 run 6.13–8.09 s。
- A/home **0/5**、A/project 5/5、A/habit **0/5**、A/car 5/5、B 15/15、C 5/20（C 恒 1/4，只有 habit 过）。
- 同臂 5 次答案**逐字节相同**，与 19:25 历史 `runs/` 的 11 个重叠 (臂,段) 组合 11/11 一致；解码贪心（`generate()` 取 argmax，无 temperature/top_k/top_p/seed）。
→ 失败可稳定复现，**不是采样噪声**；后续 n≥2/n≥3 即可。

---

## §3 阵亡清单（比结论更值钱）

| # | 曾被当作原因的假设 | 被哪个臂否掉 | n | 关键读数 |
|---|---|---|---|---|
| 1 | 段数=4 本身致命 | `iso_dup4`（4 段，第 4 段是 project 副本 18 cells @3886） | 3 | 四段全过 3/3（home 3/3） |
| 2 | home 自身的位置/跨度 | `iso_swap_top`（home 挪到最低位 3883–3904）、`iso_gap32` | 3 / 3 | home 在最低位仍 **0/3**；间距 32 与 256 逐段相同 |
| 3 | car 是唯一元凶 | `iso_habit_bot`（无 car，底块换 habit 副本 12 cells @3892） | 3 | home 仍 **0/3** |
| 4 | habit 块自身缺陷 | `iso_dup4` / `iso_habit_bot` | 3 / 3 | habit **3/3 过**（两者都是） |
| 5 | 总 cell 数 off-by-one（69 过 / 70 失败） | `iso_habit_bot` 63 cells | 3 | 63 失败、69 过、70 失败 → **非单调** |
| 6 | 块间干扰 = cell 归属被抢/被吞 | 六布局 `raw.coverage` | 1 每布局 | home 恒 **21/21** 覆盖、`overlaps=[]`、`cell_count == Σcells` |
| 7 | 窗口级 -inf 差异 | 本轮掩码插桩（iso_base vs dup4） | 每布局 25 个 p1 行 | home `allowed=21 masked=0`，两布局**完全无差异** → 四格表落 **②己** |

**存活项（单列，不许算阵亡）**：**car 在场 ⇒ home 失败** —— 6 个含 car 的臂（iso_base / gap32 / gap256 / orderrev / swaptop / carmid）**无反例**；**充分非必要**。

**待劈项（共线，未解）**：**car 在场 ⟺ 总 cells=70** —— 含 car 的 6 臂总 cell 都是 70，无 car 的臂都 < 70，现有数据无法分开。

---

## §4 因果开关（`runs_iso2/isoI5_*`，n=3）

| 布局 | 底块 | home | project |
|---|---|---|---|
| `iso_no_car`（3 段，51 cells） | 无 | **3/3 通过** | 3/3 |
| `iso_car_back`（= iso_base 几何，70 cells） | car 19 cells @3885 | **0/3 失败（答错，非空串）** | 3/3 |

→ 同一块、同一位置 4075–4096：删 car → 复活；加回 → 猝死。**块间干扰是观测事实。**
**pitfall**：这是"删掉一块改变另一块"，不是"home 这块本身坏"。

---

## §5 两种失效模式互斥

| 模式 | 表现 | 出现在 | 原生证据 |
|---|---|---|---|
| 甲 答错 | 有非空答案，内容不含事实 | iso_base / gap32 / gap256 / orderrev / swaptop / carmid / habitbot（home, habit） | `kvshim_ask_at` 返回 >0 字节 |
| 乙 空串 | 答案空字符串 | **只有** `iso_no_home`（唯一去掉最顶块） | `kvshim_ask_at` 返回 **-1**，`n_tokens` 保持 0 |

→ 本批数据里两种模式**不共存**；乙 的 -1 说明**提问解码本身失败**，不是"生成了空串"，不能用甲的解释套乙。

---

## §6 cell 层已否证（六布局实测）

| 布局 | Σcells | `cell_count` | positions | home covered | overlaps | home 答案 |
|---|---|---|---|---|---|---|
| iso_base | 70 | 70 | 3885–4095 | 21/21 | [] | 失败 |
| iso_no_car | 51 | 51 | 3956–4095 | 21/21 | [] | 通过 |
| iso_dup4 | 69 | 69 | 3886–4095 | 21/21 | [] | 通过 |
| iso_habit_bot | 63 | 63 | 3892–4095 | 21/21 | [] | 失败 |
| iso_car_mid | 70 | 70 | 3886–4095 | 21/21 | [] | 失败 |
| iso_no_home | 49 | 49 | 3885–4031 | — | [] | 空串 |

→ 对话序列握着完整的 home 却读不出来 → 「cell 归属被抢/被吞」**已否证**。`coverage` 用半开区间 `range(pos_lo, pos_hi)`；`positions_max=4095` 不是"缺一格"。

---

## §7 掩码层：插桩、受控冒烟、四格表落位

### 7.1 插桩形态（只加打印）

`llama-kv-cache.cpp` `set_input_kq_mask_impl` 内，`LLAMA_KV_MASK_DEBUG=1` 时才生效；其余变量：`MASK_SEQ`（默认 **0**，本探针 `LIVE=0`）、`NODEDUP`、`LAYOUT`、`Q`、`WINDOWS`（闭区间 `name:lo:hi`，**传 `pos_hi−1`**）。
比较在模板类型 `T` 内做等值（`mask_drop = llama_cast<T>(-INFINITY)`），**无任何强转**，`type=f16` 已实测（不是假设）。
窗口统计**按 position 过滤**（`cells.is_empty(j)` + `cells.pos_get(j)`），因为 `j` 是行下标不是绝对位置 —— 本轮 `n_kv=256` 而位置到 4128，若按下标算会得到 `allowed=0 masked=0` 的假读数（我们真的先踩到过这个假读数）。

### 7.2 受控冒烟（同一命令、同一 layout、同一 question；只改 `MASK_SEQ`）

| 组 | `MASK_SEQ` | SUM | SUM2 | blk | **OK** | 判定 |
|---|---|---|---|---|---|---|
| A 未导出 | null（默认 0） | 25 | 25 | 100 | **4** | 通过：`SUM==asks_expected`、`blk==4×asks` |
| B | `99`（不存在） | **0** | **0** | **0** | **4** | 通过：门控真的在起作用 |

**B 的 4 行 `[MASKDBG-OK]` 是预期保留**：那是 `ask` 之后由驱动侧打的 JOIN 行，走另一条不受 `MASK_SEQ` 约束的路径。**它不是 bug，别为了 `grep -c MASKDBG` 变 0 去改门控。**
`_smoke_pair.py` 输出：`PAIR OK -- only LLAMA_KV_MASK_SEQ differs (A=null, B=99); every other key is byte-identical`（argv 已掩掉 `--run-json` 的输出路径，因为它不是控制变量）。

### 7.3 正式两跑读数（25 个 p1 行，逐行一致）

| 布局 | home 4075–4095 | project 4014–4031 | habit 3956–3967 | 底块 | 答案 |
|---|---|---|---|---|---|
| iso_base | allowed **21** / masked **0** | 18 / 0 | 12 / 0 | car 19 / 0 | 失败（答错） |
| iso_dup4 | allowed **21** / masked **0** | 18 / 0 | 12 / 0 | project2 18 / 0 | **通过** |

同一条 SUM 行（p1=4104）：iso_base `n_kv=256 n_ub=9 idxs=30 row_allowed=79 row_masked=177`；dup4 `n_kv=256 n_ub=9 idxs=30 row_allowed=78 row_masked=178`。

**⚠ 反向误读警告（必须紧跟）**：`row_masked=177` **数的主要是空 cell**（256 − 79 = 177），**不代表记忆被屏蔽**。有意义的量是**逐块 masked**（本批全为 0）。同理 `idxs=30` 是"需要搬移的 cell 列表"，与 `row_allowed=79` **不是同类相减的关系**，不能写成"少算 49 个"。

### 7.4 四格表落位（预注册，不许事后挪）

- 实测：`M_inv`（home 窗口 masked）= **0**；`M_vis`（project 窗口 masked）= **0**。
- → 落 **②己：窗口级 -inf 无差异**。措辞只否证"窗口级 -inf 差异"，**不写**"掩码与可见性无关"。方向：转生成/图侧。

**己 的区分证据（防止"己"变成逃生口）**：
1. 逐块自洽：`allowed + masked == cells` 在**每个** p1 行、**每个**块成立（25 行 × 4 块，断言 rc=0）。
2. 交叉核对：打印的 `cells` 来自引擎 cell 表，与 run json 的 **layout manifest** `cells` 逐块相等 —— 这条比自洽高一级（自洽只能证明内部一致）。
3. 计数器是活的：同一 run 内 `row_allowed` 随 p1 单调增（79→88…），说明扫描确实在跑。
4. A/B 受控：A 有 100 条 blk 行、B 有 0 条，证明打印既非恒真也非恒假。

### 7.5 三路对账（内部一致性检查，**不是判据**）

`row_allowed == cell_count + chat − Σmasked_block`，其中 `chat = p1 − 4095`（= `p1 − 4096 + 1`）。
**废弃写法（不要再抄）**：`row_allowed == cells_total + n_ub`、`row_allowed == cell_count + n_ub` 都**不成立** —— 解码每一步都会假失败。

| 布局 | row_allowed | cell_count（探针实测） | chat | Σmasked | 等式 |
|---|---|---|---|---|---|
| iso_base | 79 | 70 | 9 | 0 | 70+9−0 = **79** ✓ |
| iso_dup4 | 78 | 69 | 9 | 0 | 69+9−0 = **78** ✓ |

**注意**：`n_ub` 是 ubatch 大小（解码期为 1），**不是该行里的 prompt token 数**；正确形式已按 `p1` 推导。本轮实测：p1 从 4104 增到 4128 时 `row_masked` 177→153（即 `row_allowed` 79→103），而 `n_ub` 恒为 1 —— 所以能对上的是 `p1−4095`，不是 `n_ub`。
**地位声明**：左 row_allowed（整行扫描）、中 cell_count（`kvshim_seq_cell_scan`）、右 Σmasked_block（窗口统计）**三条路径全部产自引擎**，只是三个时刻、三段代码数同一批 cell。它只能证明"三个计数实现彼此一致"，**不能推出"掩码是原因"**。
**隐含前提**：非空 cell 只有两类（已挂载块的 cell + 本次提问 token 的 cell）。若出现第三类（残留旧 seq、pin 住的 cell），等式会漂且方向无法解释 → **报"前提不成立、对账作废"，不许拿漂移值当发现**。

### 7.6 JOIN 示例（两段式：引擎打 mask 行，驱动在 ask 之后打 OK 行）

```
[MASKDBG]    layout=iso_base q=90a855a7 blk=home lo=4075 hi=4095 cells=21 allowed=21 masked=0 first=-1 last=-1 head=[]
[MASKDBG-OK] layout=iso_car_back q=90a855a7 blk=home cells=21 ok=0 ans_sha=e63faeff
JOIN → blk=home cells=21 allowed=21 masked=0 | ok=0 ans_sha=e63faeff | 标称 iso_base ≡ 驱动键 iso_car_back（同一几何）
```

**已知缺陷（如实记）**：`layout` 标签由环境变量手填（`iso_base`），驱动内部键是 `iso_car_back`；几何完全相同但 JOIN 键需要一条别名映射。下一轮应让驱动把键直接传给引擎。

### 7.7 反推演练（拿已知答案检验四格表本身）

```
已知：iso_base 里 home 不可见（答错）、project 可见（答对）；窗口 home 4075–4095、project 4014–4031。
代入：M_inv = 0（home masked）、M_vis = 0（project masked）→ 落 ②己。
自洽性：表本身能把 ①戊 分开——同一 run 里 row 级 row_masked 曾是 177≠0，说明 -inf 检测器会产生非零值；本批逐块 masked 全 0 是真读数，不是计数器失效。
```

→ 结论不变：**这两个布局在窗口级 -inf 上无差异**，掩码不是这条线；`己` 不是"实验无效"，也不改写成 `戊`。

---

## §8 habit 横向对照与 cells 扫描（筛查，非归因）

| 来源 | 臂 | habit cells | 结果 |
|---|---|---|---|
| m2 | iso_base / no_car / gap32 / gap256 / orderrev / swaptop / carmid | 12 | **全失败** |
| m2 | iso_dup4 | 12 | **3/3 通过** |
| m2 | iso_habit_bot | 12 + 12（副本） | **3/3 通过**（两块都过） |
| b 家族 | `runs_var` B(b3) | 20（`b_habit`，不同文件） | 5/5 通过 |
| c 家族 | `runs_var` C(micro) | 5（`c_habit`，不同文件） | 5/5 通过 |

→ 三份 habit 是**三个不同块文件**（sha256 前缀 `6c210314…` / `7c364845…` / `9d47e563…`，cells 12/20/5，文本也不同），**不可作规模比较**。定性只能写：**habit 的失败与布局相关，机制未定**。

**cells 扫描（I13 + 轴 A，n=2/3；`pos_hi` 恒 3904 ⇒ `cells` 与 `pos_lo` 结构性共线 ⇒ 只能筛查）**：

| 底块 | cells | home |
|---|---|---|
| c_project / c_home / c_habit / c_car（同几何） | 5 | **4/4 全通过** |
| habit 副本 | 12 | 0/3 失败 |
| project 副本 | 18 | 3/3 通过 |
| car | 19 | 0/3 失败 |
| b_habit | 20 | 0/2 失败 |
| b_project | 28 | 0/2 失败 |
| b_home | 31 | **2/2 通过** |

→ 5 过 / 12 败 / 18 过 / 19 败 / 20 败 / 28 败 / 31 过：**非单调，无阈值**。轴 A 四者同几何同 cells 只变内容 → 5 cells 档**内容不是判别变量**。

---

## §9 剩余嫌疑与下一步（全部【推断】）

1. **car 在场 ⇒ home 失败**（充分非必要，6 臂无反例），与总 cells=70 完全共线（待劈）。
2. `iso_car_mid`（car 挪到 slot2）：home 0/3 与底块 project **0/3** 双双失败，只有 car 3/3 —— 受害者集合随布局变化，规则未定。
3. 已排除 cell 层与窗口级 -inf 层 → 下一条线在图/生成侧：掩码复用/拷贝分支的内容、跨 seq 行共享、真正送入 Vulkan kernel 的掩码张量、logits 是否受块影响。

**下一步（等 lead/inspector 定优先级，均未开工）**：打印 allow 集合的**位置列表**（而非计数）对比两布局；打印 `prev` 标志与 `srct` 查复用分支；行为侧挂起项（测甲′、测乙、Axis B）保留授权。

**方法论（本轮真正的产出，三条可复用规则）**：
1. 新实验开工前先 grep 现有产物，看要测的量是否已在采；
2. 凡写数量，一律"行号区间 + 数量 + 可复制的自证命令"；
3. 凡写判读规则，先用已知结果反推，确认不误判再上；**且先写清它在证据链里是"外部锚点"还是"内部一致性检查"——后者不得用于判定因果**。

**本实验真正的外部锚点只有两个**：layout manifest 的 `pos_lo/pos_hi/cells`；答案文本 vs `P.FULL[block_id]["fact"]`。其余（row_allowed、cell_count、Σmasked、逐块自洽）全部是内部一致性。

---

## 附录 A 自证命令

```bash
cd /d/llama-mem && M=kvmem/m2_visibility/runs_mask
python -X utf8 $M/_assert_trace.py --log $M/mask_iso_base_home.log --run-json $M/mask_iso_base_home.json   # rc=0
python -X utf8 $M/_assert_trace.py --log $M/mask_dup4_home.log      --run-json $M/mask_dup4_home.json      # rc=0
python -X utf8 $M/_smoke_pair.py  --a $M/AB_A_default.json --b $M/AB_B_seq99.json                          # rc=0
grep -m1 "MASKDBG-SUM\] " $M/mask_iso_base_home.log   # row_allowed=79 row_masked=177 n_kv=256 idxs=30
grep -m1 "MASKDBG\] "     $M/mask_iso_base_home.log   # blk=home allowed=21 masked=0
grep -m1 "MASKDBG\] "     $M/mask_dup4_home.log       # blk=home allowed=21 masked=0
python -X utf8 -c "import json;d=json.load(open(r'kvmem/m2_visibility/runs_mask/mask_iso_base_home.json',encoding='utf-8'));print(d['trace_classes'], d['asks_expected'], d['decode_batches_expected'], d['cell_layer']['cell_count'])"
```

## 附录 B 数据目录

| 目录 | 内容 | 备注 |
|---|---|---|
| `runs/` | 7 个历史 json | 冻结，mtime 19:25–19:26，本轮未动 |
| `runs_var/` | 35（7 臂 × 5） | 方差实验 |
| `runs_iso/` | 53 | 第一轮隔离 |
| `runs_iso2/` | 41 结果 + `_failed/` 12 | `_failed/` 是 dup4 首次因 manifest 缺 `project2` 报 `KeyError` 的记录，**不计入任何统计** |
| `runs_iso3/` | I9/I10/I11/轴A/I13 补点 | 每臂 n=2 或 3 |
| `runs_head/` | `kvshim_seq_cell_scan` 校准（probe=2） | 基线 104 位置（70 记忆 + 34 对话）、缺失 0、两次一致；头洞正对照 49 = 恰好三块、无对话 cell、`pos_max 4031` |
| `runs_mask/` | 掩码 trace、脚本、pre/post.patch、dll 备份 | 本报告 §7 全部原始证据 |

## 附录 C 本轮踩到并已修正的五个自造陷阱

1. **`n_tokens` 当可见性判别式**：`seq_cp` 挂载不写 token 记账（`m2_visibility_probe.py:1085`），该值恒 0；只在"空串 run"上作生成侧旁证。
2. **`seq_id` 写死 1**：本探针 `LIVE=0`（`m2_visibility_probe.py:96`），写死 1 等于零输出；已改为 `LLAMA_KV_MASK_SEQ`（默认 0）。
3. **行下标当绝对位置**：`n_kv=256` 而位置到 4128，按下标算窗口会得到 `allowed=0 masked=0` 的假读数；已改为 `cells.pos_get(j)`。
4. **跨类计数当判据**：`grep -c MASKDBG` 把 4 行 `[MASKDBG-OK]` 数进"应为 0"的反向冒烟里；已改为按类断言（SUM/SUM2/blk/OK 各有各的期望值）。
5. **在 Python 里 `os.environ[...] = ...` 设 `LLAMA_KV_MASK_*` 无效**：DLL 静态链接 CRT，**在进程启动时快照环境**，进程内 setenv 传不进去。表现是"设了调试变量却零输出"，极易误判成"没编译进去"。必须由调用方（shell）export；驱动只**记录**继承值（写进 `mask_env`），不声称自己设置它。

—— 本版定稿；修订以换哈希为准。