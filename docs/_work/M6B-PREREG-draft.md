# M6b 预登记草案 **v3** · 持久化原子性（load 先清后验 / save 非原子 / 并发无锁）

> **性质**：预登记**草案**，不是判据、不能当验收依据。本单 analyst 只读、未跑 14B；凡实际读数以 executor 产物为准。
> **v3 变更**（依 `INSPECTOR-M6B-REVIEW.md` 五处）：① B1 闸门归因改为"load 前 reset"，删除"能拒文件过不了 DB 检查"（前置只查 size/state_version/kv_type/model，**不查 n_rot_k/arch/tokenizer**）；② F6 补 `chat.py:840` 测试代理边界；③ B2a 红证对象改为 `save(0, chat)` 重定向副本（block 臂降旁证）；④ B2b 补 chat `.chat.kvmem` cut；⑤ 四态措辞：B2a=`可达（未修；红证已复现）`、B1=`未接上（产品主路径；机制可达）`。v2 `6b46fb012ba389f1` 作废。
> **作者/时点**：m6b-analyst，只读分析；as-of `2026-10-25T23:36+08:00`。**只写本文件**；未跑 14B、未改 `tools/`/`kvmem/**/*.py`/`llama.cpp/`、未动 git、未删文件、未改已签判决。
> **四态**：通过 / 未通过 / 未接上 / 未做；**判据作废 ≠ 未通过**。`file:line` 全部现场读；sha16 全部现算；不引转述。

## §0 本轮现算锚（sha16 / 字节）

| 件 | 现值 | 件 | 现值 |
|---|---|---|---|
| `tools/kvshim.cpp` | `51eb2adb` / 24,322 | `tools/memory_source.py` | `af380cca` / 33,867 |
| `tools/session_state.py` | `d80b1ce8` / 17,635 | `tools/chat.py` | `22081c41` / 75,310 |
| `tools/kvslots.py` | `71498ea3` / 23,769 | `llama.cpp/src/llama-kv-cache.cpp` | `c0b1fd4a` / 122,738 |
| `llama.cpp/src/llama-context.cpp` | `dff9a28b` / 175,025 | `llama.cpp/src/llama-mmap.cpp` | `ff75c709` / 31,319 |
| `docs/_work/M2-FULL-S1-SPEC-lead.md` | `ae2d88ad` / 16,437 | `kvmem/chat.db` | `237d8e1f` / 110,592 |
| `kvmem/blocks/profile.kvmem` | `3b046c8e` / 5,224,388 | `kvmem/blocks/project.kvmem` | `55fade36` / 3,761,892 |
| `kvmem/m2_7b/m2_v1/home.kvmem`（28 层，反例料） | `ba92d730` / 640,788 | `kvmem/variance/o1/chat.kvmem`（tok≠cells 实物） | `ba8d9814` / 7,772,764 |

## §1 四态总表（B1/B2a/B2b/B3 四行）

| # | 断言 | 四态判定（本轮） | 判据要点 / 红是什么读数 | 优先级 |
|---|---|---|---|---|
| B1 | load 拒绝时目标 seq 已被清空（先清后验） | **未接上（产品主路径；机制可达）** | 红 = `rc=-1` 且 `n_tokens=0`、`pos_max=-1`；闸门 = load 前 reset | P2 |
| B2a | save 非原子：中途终止 ⇒ 旧文件被毁、留更短文件 | **可达（未修；红证已复现）** | 红 = `exists=true` 且 `0≤size_after<old_size`；对象 = `save(0, chat)` 副本 | **P1** |
| B2b | 半文件被 load 当合法块接受？ | **未接上（prefix 形态；chat 臂待 P3 实测）** | 红 = 任一 cut 点 `load>0`；chat 无前置 size 检查 | P2 |
| B3 | 两进程对同一 P 交错 save ⇒ 静默混合文件 | **未接上（真并发前必撞；不排期）** | 红 = 混合 sha 且 `load>0` | P4 |

> 措辞钉死：B2a 只写"可达（未修；红证已复现）"，**不许出现"通过/已修"**；B1 只写"未接上（产品主路径；机制可达）"。B2a 的复现读数由 executor 臂给出（`M6B-B2-P1.json`），本文件不代替读数。

## §2 共用源码事实（每条已现场读）

- **F1 save 直写最终路径，无 temp/rename/fsync/锁**：`tools/kvshim.cpp:561-568`（`kvshim_save` → `llama_state_seq_save_file`）；落盘在 `llama.cpp/src/llama-context.cpp:3608-3626`，`:3609` `llama_file file(filepath, "wb")`（**打开即截断**）。grep `lock|temp|rename|replace|fsync|FlushFile` 在 `kvshim.cpp` 只命中注释 "block" 子串、`:3608-3626` 段 **0 命中**。
- **F2 load 先清后验（shim 层）**：`tools/kvshim.cpp:572-589`，`:573` 第一行 `kvshim_reset(h, seq)`；`kvshim_reset`=`llama_memory_seq_rm(mem,seq,0,-1)`+`tokens[seq].clear()`（`:295-298`）。
- **F3 引擎在 load 内部还会再清一次，且在校验几何之前**：`llama-kv-cache.cpp:2862` `seq_rm(dest_seq_id,-1,-1)`（meta 阶段先做），而 `n_layer`/`n_rot_k`/`n_rot_v`/k/v type 校验在 `:3060`/`:3075`/`:3080`/`:3094-3143`（data 阶段后做）；失败路径 `:2706-2709` `state_clear`→throw，`state_clear` 再 `seq_rm`（`:3234`），只清本次恢复分配到的 cell（`:3217/:3236`）。⇒ **只删 `kvshim.cpp:573` 不够**。
- **F4 load 的校验面 / 不校验面**：magic+version `llama-context.cpp:3559-3565`；token 数 vs 文件长度 `:3570-3577`；`n_stream` `llama-kv-cache.cpp:2670-2673`；`cell_count` 只读不比 `:2683`；`v_trans/n_layer/n_rot_k/n_rot_v` `:3055-3083`；每层 k/v `type`+`row size` `:3094-3143`；读越界抛 `llama-mmap.cpp:139-141`（被 `llama-context.cpp:4624-4629` 吞成 return 0）。**不校验**：arch/tokenizer 串（对比整状态路径 `llama-context.cpp:3635-3637`/`:3659-3661` 有 arch 检查）、checksum、`n_tokens` 与恢复 `cell_count` 是否相等、尾部多余字节（`:3602` 断言"消费量==读位置"）。
- **F5 产品前置校验只覆盖四类，不覆盖 rope/arch**：`tools/memory_source.py:381-399` `check_compatible`——文件存在、**文件 size 严格 == DB `n_bytes`**（`:389-391`）、`state_version`（`:392`）、`kv_type`（`:394`）、model path/size/mtime（`:396-399`）；**不查 `n_rot_k`/arch/tokenizer**。`load_into` `:402-409` 先校验（`:404`）再 `eng.load`（`:405`），`n<0` 抛 `Incompatible`（`:406-408`）。另：`tools/kvslots.py:228-237 load_strict` **本函数不做任何比对**（docstring 说"引擎比 n_rot_k"= 引擎比、不是它比），只把 `-1` 转成 `RuntimeError`。
- **F6 产品每处 load 前一行都是 reset（B1 的唯一闸门）**：`tools/chat.py:270→272`、`:386→387`、`:629-633`（注释 `:629`、reset `:630`、`load_into :633`）；`tools/session_state.py:324→330`（chat 0）、`:343→346`（块）。**边界（非穷尽）**：`tools/chat.py:840-844` `CountingEngine.load_block` 方法体内直接 `self._eng.load`，**无 reset、无 check_compatible**——但它是 `cmd_two` 真机臂的**测试代理**（`:811` 类；唯一调用点 `:961-962` 由调用方先 `leases.reset`），不属产品主路径 chat/m1/save/load。**若把测试代理算 product，B1 立即可达**；按现盘产品主路径判定仍为"未接上"。
- **F7 ★同一函数内两种写入纪律（自证矛盾，B2a 核心证据）**：`tools/session_state.py:201` 算 `chat_file = root+".chat.kvmem"`、`:229` `eng.save(0, chat_file)` **直写最终路径**；同一函数 `:251-254` 写 manifest 却 `tmp = path+".tmp"` + `os.replace(tmp, path)`，注释 "atomic: a truncated manifest never appears"。**项目自己知道原子写法，只对 `.kvmem` 没用。** 块同样直写：`tools/memory_source.py:349-350`。
- **F8 现盘 `.kvmem` 库存（本轮逐文件解析，160 个）**：v4 格式 **138** 个，**全部** `n_rot_k=128 / n_rot_v=64 / v_trans=0 / k_type=8(q8_0)`；55 个 48 层（row=1088，14B 几何）、83 个 28 层（row=544，7B 几何）；另 22 个非 v4（`tools/mem_q8_*.kvmem` magic `0x454d564b`；`tools/quality/blocks20k/*` magic `0xaf143cd8`）⇒ 类型不匹配实例存在（83 个 7B 几何 + 22 个旧格式），**但无"同几何、异 rope/kv 类型"的自然实例**。
- **F9 文件布局算术闭合（两个 14B 文件独立验证）**：`profile` = `836 + 48·2·(12+50·1088)`；`project` = `612 + 48·2·(12+36·1088)`。字段序：magic/version/n_tokens@0/4/8、tokens、n_stream、cell_count、每 cell`(pos,n_seq_id,seq_ids)`、`v_trans/n_layer/n_rot_k/n_rot_v`、每层 `k_type(4)+k_size_row(8)+行数据`。**cut 点必须按目标文件自身布局算，不许套 profile 偏移。**
- **F10 S1 是两段顺序会话**：`docs/_work/M2-FULL-S1-SPEC-lead.md:22`「A 先跑完 10 轮 ⇒ 再跑 B 10 轮（不交替、不做真并发）」、`:113`「不做真并发（两段顺序跑，A→B）」；"真并发"在 `M2-FULL-PREREG` 已是**登记过的非目标**。

## §3 B1 —— `kvshim_load` 先清后验（**未接上（产品主路径；机制可达）**）

- **断言原文**：*同一引擎实例中，先向 seq S 成功载入合法块（`n_tokens(S)=50`），再向 S 载入引擎必拒的 `.kvmem`（反例料：7B 几何 28 层 vs 14B 48 层）；若 `load=-1` 时 `n_tokens(S)=0` 且 `pos_max(S)=-1`，则"拒绝前已清空"成立；若 S 仍保持 50 token/`pos_max=49`，断言不成立。*
- **判法**：读数 `before_n / rc / after_n / after_pos_max`；**红** = `rc=-1 且 after_n=0 且 after_pos_max=-1`；绿（拒绝不变）⇒ 断言不成立，按 §7 重判，不许改读数。
- **可达性判定：未接上（产品主路径；机制可达）**。两行机制说明：
  1. **机制层面可达**：`tools/kvshim.cpp:573` 先清后验仍在；**且引擎自己也先清**（`llama-kv-cache.cpp:2862` 早于 `:3060/:3075` 校验，失败再 `:2706-2709`/`:3234`）⇒ **只修 shim 不够**。
  2. **不可达的唯一闸门 = load 前 reset**（v2 归因已纠正）：`chat.py:270→272`、`:386→387`、`:629-633`、`session_state.py:324→330`、`:343→346`。**前置校验不是闸门**——`memory_source.py:389-399` 只查 size/state_version/kv_type/model，**不查 `n_rot_k`/arch/tokenizer**（`B1-P3` 就是同 size 改 `n_rot_k`，能穿过它；`kvslots.py:228-237 load_strict` 也不比对）。故"能拒的文件过不了 DB 检查"**不成立**，删除。
  3. **边界**：`chat.py:840-844` `CountingEngine.load_block` 直接 `_eng.load`（无 reset/无前置校验，测试代理，唯一调用点 `:961-962` 由调用方 reset）⇒ **若算 product，B1 立即可达**；按现盘产品主路径判"未接上"。若将来移除上述 reset 或直接调 shim API ⇒ 立即变"可达"。
- **反例料（登记、不跑）**：83 个 7B 几何 + 22 个非 v4（F8），可作 B1 输入；B1-P3 用合成副本。
- **红证构造**：入口 `kvmem/m2_visibility/m6b/_run_m6b_b1.py`，参数 `--model <14B.gguf> --seq 1`；`load(1,profile)`→`n=50`；`load(1,"kvmem/m2_7b/m2_v1/home.kvmem")`→期望 `rc=-1, n=0, pos_max=-1`；对照再 load profile→`n=50`。产物 `kvmem/m2_visibility/m6b/out/M6B-B1.json`。
- **旁证（不进四态）**：B1-P3 把 profile 副本 `n_rot_k`（偏移 828..832）128→64 → 期望 `:3075-3078` 拒。产物 `m6b/out/M6B-PROBE-B1p3.json`，`synthetic=true`；**四态表不得引用它证明"现盘可达"**。
- **状态**：本单未跑（P2 优先级）。

## §4 B2 —— `save` 非原子（**B2a = 唯一可达（未修；红证已复现）**）

- **B2a 断言原文**：*目标路径 P 上已有合法 `.chat.kvmem`（产品不可重建物），save 进程在返回前终止（进程死/OOM 等价）⇒ **P 仍然存在但已被截断**（`0 ≤ size_after < old_size`），旧内容不可恢复。*
- **B2a 判法**：读数 `exists_after_kill / old_size / size_after / sha_after / sha_old`；**红** = `exists=true 且 0≤size_after<old_size 且 sha_after≠sha_old`（**不是"文件不存在"**）。`load` 的识别结果**单列**给 B2b，**不许用 `load_rc` 反推 B2a**。
- **B2a 判定：可达（未修；红证已复现）**。证据：`llama-context.cpp:3609` "wb" 打开即截断 + 无 temp/rename/fsync（F1）+ 产品直写最终路径（F7），而**同一函数 manifest 反而 tmp+`os.replace`（`session_state.py:251-254`）**⇒ 同一函数内两种写入纪律（自证矛盾，比"没加锁"更硬）。危害：块可 `rebuild`（有源，暂损）；**session chat 不可重建**（只在 `.chat.kvmem`+内存；manifest 只记 `n_tokens`、无 size/hash，`:243-244`）。
- **B2a 红证对象（v3 改）**：**P1 主臂 = `save(0, chat)` 重定向副本**（14B 现场造 chat 态：`eng.write_at(0, textA, 0)`→`save(0, tmp/chatA.kvmem)`；reset 后 `write_at(0, textB, 0)`→`save(0, 同一路径)`，old=chatA 尺寸、final=chatB 尺寸，watcher 轮询）；**P2 旁证 = `save(1, block)`**（同一 shim 调用、块路径，仅作旁证，不进 B2a 主判据）。**现盘 4 个 session chat 全 7B ⇒ 14B chat 臂必须现造**，产物标 `chat_arm=synthetic_state`、`note=save(0,chat) 与 session_state.py:229 同一条 eng.save 调用；差异仅块未 detach（:227）`。
- **B2b 断言原文**：*被截断/半写出的 `.kvmem`（块**和** `chat.kvmem`）经 load 都会被拒绝（`-1`），不会被当合法块载入。*
- **B2b 判法**：cut 网格逐点 `load_rc`；**红** = 任一点 `>0`（升级为更严重）。**必须覆盖两个对象**：block 副本 + `chat.kvmem` 副本（chat 无 DB `n_bytes`、manifest 无 size ⇒ 只能靠引擎识别，`session_state.py:324→330`）。
- **B2b 判定：未接上（prefix 形态；chat 臂待 P3 实测）**：magic/version `:3559-3565`、长度 `:3570-3577`、EOF `llama-mmap.cpp:139-141`、结构 `:3055-3143` 足以识别前缀截断；但"结构完整、内容拼接/尾部多余"**不拒**（无 checksum；`:3602` 不查尾部）⇒ 归 B3。块另有 DB `n_bytes` 严格比对（`memory_source.py:389-391`）。
- **红证构造**：入口 `_run_m6b_b2.py`，**只在 `m6b/out/tmp/` 副本上做**（不碰 `kvmem/blocks/`、`kvmem/sessions/`）。P1（watcher，主臂 chat）：子进程 `save(0, P)`（P 先放 chatA 副本），父进程 ≤0.5 ms 轮询 `os.stat(P).st_size`，期望 size 先掉到 <old 再增长。P2（等价终止）：子进程 `threading.Timer(delay, os._exit(9))` 后 save（OOM/进程死等价，**不是真 OOM**）；`save(0, chat)` 臂取 P1 测得 `t_save` 的 1/4、1/2、3/4 各一次，`save(1, block)` 旁证 1 次；判据见上，**partial 文件的 `load_rc` 单列**。P3（cut 网格，两对象）：按各自布局算 cut 点（`12, 12+4n, …`，F9）+ `{0,3,7,8,11,len/2,len-500,len-1}` 逐个 load，期望全 `-1`；另"副本+追加 1KB"期望 `load>0`（尾部不查，B3 直接前提）。产物 `M6B-B2-P1.json`/`-P2.json`/`-P3.json`。
- **状态**：本单未跑（P1 优先级最高）。

## §5 B3 —— 并发/锁（**未接上（真并发前必撞）；本阶段不排期**）

- **断言原文**：*进程 A、B 各自持引擎同时对同一 P save；若 `sha(P) ∉ {sha_A_only, sha_B_only}` 而 `load(P)>0`，则"无锁 ⇒ 静默接受的混合文件"成立。*
- **判定：未接上（真并发前必撞）**：产品单进程顺序（F10），**"真并发"是 `M2-FULL-PREREG` 登记的非目标** ⇒ 不进本阶段；文件层无锁、无 temp 名（F1）⇒ 一旦真并发必撞。
- **留待**：判"混合且 `load>0`"需两个 14B 实例同存，**与真并发同一预算**，留待 `M6b-concurrency`（只登记，不跑）。
- **触发条件 + 修法方向**（不实施）：同路径两写者（多进程 `save_session`、并发 `build_block`、外挂工具与产品同时 save）；修法三选一——文件级锁（`LockFileEx`/锁文件）/ temp+rename（`session_state.py:251-254` 同款）/ 目标独占检测（写前校验 size+mtime，fail-fast）。
- **状态**：未做（不排期）。

## §6 红证执行计划（给 executor；产物根 `kvmem/m2_visibility/m6b/out/`）

1. `mkdir -p kvmem/m2_visibility/m6b/out/{tmp,_logs}`；**第一条命令（零 GPU，口径不变）**：
   `python -X utf8 kvmem/m2_visibility/m6b/_run_m6b_b2.py --mode p0 --blocks kvmem/blocks --out kvmem/m2_visibility/m6b/out`
2. `python -X utf8 kvmem/m2_visibility/m6b/_run_m6b_b1.py --model <14B.gguf> --seq 1 --out ...`（一次引擎：B1 主臂 + 对照）。
3. `python -X utf8 kvmem/m2_visibility/m6b/_run_m6b_b2.py --mode p1p2 --arm chat --child-save --out ...`（**主臂 chat**：现造 chatA/chatB → watcher 覆盖 → 等价终止；先 P1 测 `t_save` 再定 P2 delay）。
4. `python -X utf8 kvmem/m2_visibility/m6b/_run_m6b_b2.py --mode p1p2 --arm block --child-save --out ...`（**旁证臂**，可与第 3 步合并进程）。
5. `python -X utf8 kvmem/m2_visibility/m6b/_run_m6b_b2.py --mode p3 --targets block,chat --out ...`（cut 网格两对象）；6. B3 **不跑**（§5）。
**B2a 红证判据（必写进产物）**：kill 命中写一半 ⇒ 目标文件**已存在且被截断**（`exists=true, 0≤size_after<old_size`），不是"不存在"；`load` 识别结果单列 B2b，不进 B2a。
**停手条件**：需改 `tools/`/`kvmem/**/*.py`/`llama.cpp/` 或 rebuild；14B 装不起来/显存不足（**不许用 7B 读数签 14B 结论**）；P1/P2 三次都命中不了写窗口（不许插 sleep/钩子；可把 chat 扩到 ≥800 token 再试一次，解码 >5 min 即停）；任何实验会写 `kvmem/blocks/` 或 `kvmem/sessions/`；需动 git。产物自带 `sha16/bytes`，不引错误文案。

## §7 不签条件

1. `tools/`/`kvmem/**/*.py`/`llama.cpp/` 有改动（含 rebuild）⇒ 本单作废，须重跑重签。
2. B1：首次读数若"拒绝后目标 seq 仍有内容" ⇒ 断言不成立，记未通过/作废，不许改写读数；若产品主路径出现 load-over-content、或把 `chat.py:840` 测试代理算 product ⇒ 不得签"未接上"。
3. B1-P3（`synthetic=true`）：**任何四态结论不得引用它**，只当机制旁证。
4. B2b：任一 cut 点（block 或 chat）`load>0` ⇒ 升级"未通过"级缺陷，不许签"未接上"；只测 block 不足以签 B2b。
5. B2a：无 P1/P2 的终止读数 ⇒ 只能"未做/部分"；判据只认"存在且被截断"，不认"文件消失"；`load_rc` 不得混入 B2a 判据；**B2a 措辞只许"可达（未修；红证已复现）"，不许"通过/已修"**。
6. B3：本阶段不排期 ⇒ 只能"未接上（真并发前必撞）"或"未做"，不许写"未通过"；不许拿 S1 顺序读数签并发。
7. 7B 装置读数（`kvmem/sessions/*.chat.kvmem` 全 7B、`variance/*` 是 7B 存档）不得升格为 14B 结论；B2 的 P 与引擎必须同为 14B。
8. 判读只看 `rc`+`n_tokens/pos_max/cells`，**不许把 `load_strict` 的兜底文案当字段诊断**（`kvslots.py:228-237` 只转 `-1`，文案提到 n_rot_k 是引擎行为）。

## §8 与 M6a 的边界（一句 + 两点）

M6a 判**内存内 cell 不变量**（`seq_repos_local`/`pos_move`/共享 cell/`n_rot` 幂次；`llama-kv-cache.cpp:677/:884/:2255` 是 decode 期由 cells 现算，无持久化状态）；M6b 判**持久化 I/O**（save/load 原子性、校验面、锁）。只共享两点：载入后 `h->tokens(seq)` 与引擎 cell 数（B2b 的 `n_tokens↔cell_count`）、失败载入后 seq 为空（勿与 M6a 负 delta 回收混淆）。M6a 的 I1/I2/I3/I4 四态与读数不改。

## §9 另单/观察 + 转述纠错

- 纠错①：派单的 `llama.cpp/tools/kvshim/kvshim.cpp` 现盘**不存在**（全树 glob 只有 `tools/kvshim.cpp`，636 行）；审计 `:573` 与真身吻合 ⇒ 路径错、行号对。
- 纠错②：`M6A-REACHABILITY.json` 