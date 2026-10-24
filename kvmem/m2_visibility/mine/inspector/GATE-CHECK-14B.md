# 闸门自检 GATE-CHECK-14B（机械执行 BLIND-CHECK §2.2 四层）

撰写：检测员 inspector ｜ 2026-10-25 ｜ 对象：runs_m14b/out 下 run0 / E / F / X1 / B57 的 _r1 与 _r2，共 10 个 run json

## 0 盲态解除声明

**已于 2026-10-25 00:55:08 解除盲态。** 在此之前（写 BLIND-CHECK.md 时）我没有打开过 runs_m14b/ 与 m2_v1_14b/ 下的任何文件；
盲写清单的第一版正文里连字面量 14B 数值都没有出现，可以作为盲写的旁证。

本次我实际读到的 14B 文件（全部列在这里，便于审计）：

- runs_m14b/out/：run0_r1.json、run0_r2.json、E_r1.json、E_r2.json、F_r1.json、F_r2.json、X1_r1.json、X1_r2.json、B57_r1.json、B57_r2.json
- runs_m14b/fixtures_14b.json、blocks_14b.json、control_texts_14b.json、_driver14b.py
- m2_v1_14b/home.kvmem、project.kvmem、habit.kvmem、project_paraphrase18.kvmem（只读块头）
- runs_m14b/loadD_ngl99_c8192.log（配对 V 日志，grep 层放置行）
- D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf（只算 sha256）

**我注意到 out/ 里还有 P2_r1.json 与 P2_r2.json；按派单范围，我没有评估它们**（只看过文件名列与 n_predict=24 这一项，
用于核对本批的生成预算口径）。

## 1 装置核实（不采信任何人，全部自己算/自己读）

| 项 | 值 | 我的取证方式 |
|---|---|---|
| 模型 | D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf，8,988,110,240 B，sha256 0b319bd0572f2730bfe11cc751defe82045fad5085b4e60591ac2cd2d9633181 | 我自己跑 hashlib 算完整文件（7.3 s）；与 lead 报的判据值一致 |
| DLL | tools/kvshim_vk.dll，sha256 9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c | 我自己算磁盘文件；且每个 run 的 engine.dll_sha256 == engine.loaded_dll_sha256 == engine.dll_sha256_declared，且 engine.dll_sha256_source == "measured" |
| 引擎参数 | n_ctx 8192 / n_seq 8 / kv q8_0 / gpu 99 | 每个 run 的 engine.{n_ctx,n_seq,kv,gpu} |
| 每 token KV 字节 | engine.bytes_per_token = 104,448（= 48 层 × 2 × 1088） | run json engine.bytes_per_token |
| KV 池 | engine.pool_bytes = 855,638,016（= 8192 × 104,448 = 816.00 MiB） | run json engine.pool_bytes |
| 层放置 | 48/48 层 dev = Vulkan0；KV 816.00 MiB（K 408 + V 408），n_rot_k=128 / n_rot_v=64 | runs_m14b/loadD_ngl99_c8192.log:1510 起 48 行 "llama_kv_cache: layer N: dev = Vulkan0"；:1559 "size = 816.00 MiB ( 8192 cells, 48 layers, 1/1 seqs), K (q8_0): 408.00 MiB, V (q8_0): 408.00 MiB"；:1560-1561 n_rot_k / n_rot_v |
| 每 run 的 VRAM 快照 | runner.vram_before_mib = {total 10224, free 9426} | run json runner.vram_before_mib |

三点说明：
1. 816.00 MiB 与"8192 × 104,448 B"完全相等（855,638,016 / 1,048,576 = 816.00），说明**块头推导出的每格载荷与引擎自报的 KV 池是同一组数**，两边互证。
2. 该 V 日志是同参数下的**配对 CLI 演练**（head 里是 llama_completion / llama backend init），不是这 10 次运行的日志；
   这 10 次运行的 llama 日志仍被 quiet_log 丢弃（kvshim.cpp:52-54、:631）。所以"KV 全在 GPU"是"配对实测 + 代码链"，
   不是逐 run 实测 —— 与我在规格书里的限度说法一致，但现在多了一份可核的配对日志。
3. 日志第 1560-1561 行给出的 n_rot_k=128 / n_rot_v=64，独立验证了我在规格书里"14B 仍是 128/64"的推导。

## 2 第 0 层：14B 块自证（我自己解析，不读执行者的承接）

| 块 | size | 1188+104464·n | cells | 首 token | n_layer | n_rot_k | n_rot_v | k_type/k_row | v_type/v_row | 解析完整 | sha256 前 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| home | 2,194,932 | 2,194,932 | 21 | 151646 | 48 | 128 | 64 | 8 / 1088 | 8 / 1088 | True | 73843fc55efd1ab3 |
| project | 1,881,540 | 1,881,540 | 18 | 151646 | 48 | 128 | 64 | 8 / 1088 | 8 / 1088 | True | 536eac03f288bb09 |
| habit | 1,254,756 | 1,254,756 | 12 | 151646 | 48 | 128 | 64 | 8 / 1088 | 8 / 1088 | True | f6f8e85cc55bd4b9 |
| project_paraphrase18 | 1,881,540 | 1,881,540 | 18 | 151646 | 48 | 128 | 64 | 8 / 1088 | 8 / 1088 | True | a4cf0888467a0f46 |

- 四块的 K/V 记录逐层一致（48 层全为 8/1088），解析器消费到文件末尾（consumed == size，零剩余）。
- fixtures_14b.json 里 5 个块的 sha256 与磁盘实测**全部相等**（含第 5 个 variant/g18_bos_c18，它属于 P2，不在本单判定范围）。
- 四格 run json 的 layout.segments[].file_sha16 与上表前 16 位逐块相等。
→ **第 0 层：PASS（10/10 run）**，规格书里"1188 + 104464·n"的推导被实测证实（这是本轮第一次实测确认）。

## 3 逐格逐层结果

| run | layout | L0 块自证 | L1 装置一致 | L2 几何+门禁 | L3 两跑稳定 | L4 答案 | ok | 答案 sha256 前 16 |
|---|---|---|---|---|---|---|---|---|
| run0_r1 | iso_home_only | PASS | PASS | PASS | 与 r2 同 | 过 | true | 31bff41f04341473 |
| run0_r2 | iso_home_only | PASS | PASS | PASS | 同上 | 过 | true | 31bff41f04341473 |
| E_r1 | iso_dup4 | PASS | PASS | PASS | 与 r2 同 | 过 | true | c7d4e377fdc64950 |
| E_r2 | iso_dup4 | PASS | PASS | PASS | 同上 | 过 | true | c7d4e377fdc64950 |
| F_r1 | iso_fac_pp18 | PASS | PASS | PASS | 与 r2 同 | 过 | true | c7d4e377fdc64950 |
| F_r2 | iso_fac_pp18 | PASS | PASS | PASS | 同上 | 过 | true | c7d4e377fdc64950 |
| X1_r1 | iso_x1_57copy | PASS | PASS | PASS | 与 r2 同 | 过 | true | c7d4e377fdc64950 |
| X1_r2 | iso_x1_57copy | PASS | PASS | PASS | 同上 | 过 | true | c7d4e377fdc64950 |
| B57_r1 | iso_fac_nb57 | PASS | PASS | PASS | 与 r2 同 | 过 | true | c7d4e377fdc64950 |
| B57_r2 | iso_fac_nb57 | PASS | PASS | PASS | 同上 | 过 | true | c7d4e377fdc64950 |

**没有任何一层被触发失败。10 个 run 全部通过四层闸门。**

## 4 lead 点名的六条，逐条回原文

1. **四格 engine.dll_sha256 是否同一值 / 是否 9edbafa1… / 是否 measured**
   是。10 个 run 全为 9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c；
   engine.dll_sha256_source == "measured"；且 engine.dll_sha256 == engine.loaded_dll_sha256 == engine.dll_sha256_declared。
   我另外自己算了磁盘文件的 sha256，与上值相等。→ **PASS（这是 7B 那边出现过的"跨二进制"问题的对症修补）**
2. **所有 segment.file 是否都在 m2_v1_14b/**
   是。10 个 run 的每个 layout.segments[].file 都以 D:/llama-mem/kvmem/m2_v1_14b/ 开头，没有任何 m2_v1/ 或 blocks/ 的 7B 路径。→ **PASS**
3. **每段 (id, slot, pos_lo, pos_hi, cells) 是否与 7B 同构**
   E：home@1 4075-4096 21 / project@2 4014-4032 18 / habit@3 3956-3968 12 / project2@4 3886-3904 18 → 与 7B 逐字段相同
   F：home / project / habit 同上，第 4 段 project_paraphrase18@4 3886-3904 18 → 与 7B 相同
   X1：home / project / project2@4 → 与 7B 相同
   B57：home / project / pp18@4 → 与 7B 相同
   run0：home@1 4075-4096 21 → 与"单块"定义一致
   → **PASS（位置一位没动）**
4. **raw.cell_count / positions_min / positions_max / overlaps；head_gap_cells；control_ok**
   E/F：cell_count 69、min 3886、max 4095、overlaps []；X1/B57：cell_count 57、min 3886、max 4095、overlaps []；run0：21/4075/4095/[]。
   head_gap_cells 全为 0。control_ok 全为 true（且 control.questions 四问 ok 全为 true，wrote_n=210，raw_pos_max_before_ask=4095）。
   → **PASS**
5. **每个块 size == 1188 + 104464·n、首 token 151646、n_layer 48**
   → **PASS**（见 §2；另外 n_rot_k=128、n_rot_v=64、k_row=v_row=1088 也全部相符）
6. **（我补的一条）control 门禁几何是否五格同一**
   control_texts_14b.json 的 6 个条目全部 start=3886 / target_n=210 / measured_n=210 / text_sha256=c157a8e2c1a7f444…（332 字符）；
   每个 run 的 control.text_sha256 与之一致。run0 因为 layout.start=4075，用的是 --control-start 3886 把门禁窗口
   强制成同一个 210 格窗口（runs_m14b/_driver14b.py:126-167 的 patched get_control；四格上是 no-op，脚本自己 print 断言）。
   → **PASS**，且这是比 7B 更严的取法（run0 的门禁不再随布局缩短成 21 格）。这一条记一条**装置差异**：
   run0 的门禁窗口与 7B 的 get_control 语义不同（7B 会按 layout.start 缩短），但四格完全相同，不影响四格。

## 5 关于"24 token 截断"：按规则精神判一句

**事实（原文）**：五格的生成段都停在 total 33（before 0 → after 33）；答案末尾断在半词：
run0「您住在广陵路 12 号 2 单元 602。 / 我住在广陵」、四格「我住在广陵路 12 号 2 单元 602。 / 问：我住」。
**不能机械读预算**：这 10 个 run 的 runner.n_predict 记的是 null（没传 --n-predict），实际生效的是 P.N_PREDICT 默认 24
（tools/m2_visibility_probe.py:103；runs_m14b/_driver14b.py:134-139 只在传参时才覆写）。P2 两跑记的是 24。

**判定：本批不记「未测出·欠功率」。** 依据是截断的不对称性，这一条我在这里写死，补充进 BLIND-CHECK §2.4：

- **截断只能藏住一次"过"，不能制造一次"过"**：fact_ok 要求答案里出现"广陵路"，事实串在这五格里都出现在
  截断点之前的头几个 token（"…12 号 2 单元 602。"之后就进入解释段），所以"过"是截断**前面**就已经成立的事实。
- **截断对"败"才是威胁**：如果某格在 24 token 内还没说出事实，就可能是预算不足而假败。本批**没有败格**，所以不受此威胁。
- **截断不是 14B 的新差异**：7B 四格同样是 before 0 → after 33，且尾巴同样断在半词（"解析：根据给出"）。
  两批同构 ⇒ 它不是本轮新增的差异字段。

由此定规则（今后一律照此）：**"过"在截断下照判；"败"必须由 n_predict=64 批次复核才算数。**
n_predict=64 批次仍要打戳单列（它是答案完整性复核），但不改变本批"过"的有效性。

## 6 一个必须报告的新事实（不改闸门判定，但直接决定结论能不能用）

四格（E/F/X1/B57）答案**逐字节相同**（sha256 c7d4e377fdc64950…），而且与 run0（只放 home、没有任何第 4 块）
只差第一个字（run0「您住在…」vs 四格「我住在…」）。

即：在第 4 块"精确副本 vs 改写 pp18"这个操弄上，本装置给出**零可观察差异**；连"有没有第 4 块"都只差一个代词。
这既是"四格齐一"的直接证据，也是**仪器分辨力**问题的直接证据 —— 按派单，这一条由 P2 冲突探针裁决，本单不下结论。
（按 BLIND-CHECK §3.5，也不允许把"齐一"解释成"机制是零效应"。）

## 7 按盲写表查到的结论（只是查表，不是终局）

E过 / F过 / X1过 / B57过 → 命中 BLIND-CHECK §3.3 第一行 + §3.2 第一行，字面结论是
"7B 上『69 格 + 改写 = 败』在 14B 上不复现，支持预登记的规模/分配方向"。

**但这条我按规则不给生效**，两个前置没满足：
1. 仪器分辨力未定（§6 的零差异现象）——要用 P2 排除"四格齐一属假象"；
2. 答案完整性复核（n_predict=64 批次）尚未落地 —— 它只影响"败"，本批无败格，所以这一条不阻塞，但要打戳并列。

在 P1（三块单块召回）与 P2 与 64 批次三批齐了之后，我再按 §7 的表做终局判定，并写台账。

## 8 未验证 / 边界（不许当成已知）

1. "KV 全在 GPU"是**同参数配对 CLI 日志 + 代码链**，不是这 10 次运行的日志（quiet_log 丢弃；llama_log_set 未导出）。
2. 每 run 只记了 vram_before_mib（total 10224 / free 9426），没有记运行后的 VRAM 峰值，所以"整池常驻"没有逐 run 计量。
3. 这 10 个 run 的 runner.n_predict 为 null，预算 24 是从 probe:103 的默认值 + driver14b:134-139 推出来的，不是产物字段。
4. run0 的门禁窗口经 --control-start 强制为 3886/210，与 7B 的 get_control 语义不同（§4 第 6 条）。
5. P2_r1/r2 已存在但我未评估（不在本单范围）。
6. 我没有做任何跨模型数值比较（Δ/logprob/字节数/cells），也没有对四格做机制解释。

---

（附：本次所有判定都由我自己的脚本从 run json / 块文件 / 日志原文里读出来的，脚本在 workspace 的 _gate.py、_gate2.py、_gate3.py、_ev.py；
没有采信任何转述值。）
