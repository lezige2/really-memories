# 14B 四格重跑规格书（E / F / X1 / B57）

撰写：检测员 inspector ｜ 2026-10-25 ｜ 只读分析产物，未跑实验、未改代码
读者：执行者 executor ｜ 前置：14B GGUF 已落到 D:/models/ 并且能打开
本文所有 Windows 路径用正斜杠书写（正斜杠与反斜杠写法指向同一路径，Python 与 ctypes 在本仓库都按正斜杠工作）。
每一处数值/接口都附出处（文件+行号 或 我本次命令的输出）；没有出处的数值不存在。

---

## 0 你的第一步（照做，不要先想别的）

1. 确认 14B 就绪：D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf 存在且不是 .dl。
   我 2026-10-25 看到的现状：只有 DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf.dl，8,988,110,240 B
   （命令：ls -la /d/models）。这一条由你正在做的那一单收尾。
2. 不改下列任何文件：tools/m2_visibility_probe.py、tools/kvslots.py、kvmem/m2_visibility/runs_iso2/_driver2.py、
   runs_t033/_driver4.py、runs_t033/_driver7.py、kvmem/m2_visibility/fixtures.json、kvmem/m2_visibility/blocks/、
   kvmem/m2_v1/*.kvmem、_gate.py、E10-NEXT2.md。
   理由：fixtures.json 的 engine.model/model_size 与每块 sha256 是 7B 结果的 provenance，且被 _driver2.py:150-152 逐块校验。
3. 新建且只写这一个目录：kvmem/m2_visibility/runs_14b/（下含 out/）；块文件写 kvmem/m2_v1_14b/。
4. 顺序：造 4 块 → 断言 → 写 fixtures_14b.json → 跑 E → F → X1 → B57，每格 2 跑（共 8 次运行）。见 §8。

---

## 1 四格的确切配方

### 1.1 一句话表

| 格 | 7B layout key | 驱动入口（7B 原始） | slot→块 | 总格数 | 7B 结局 | 7B 答案 sha256 前 16 |
|---|---|---|---|---|---|---|
| E  | iso_dup4 | runs_iso2/_driver2.py（layout 内建） | 1=home 2=project 3=habit 4=project 副本 | 69 | 过 | 7ec1430d972d949e |
| F  | iso_fac_pp18 | runs_iso2/_driver2.py（layout 内建） | 1=home 2=project 3=habit 4=project_paraphrase18 | 69 | 败 | 11e20d78a1f18a98 |
| X1 | iso_x1_57copy | runs_t033/_driver7.py（注入 layout） | 1=home 2=project 4=project 副本 | 57 | 过 | 14dc3f98202c7023 |
| B57 | iso_fac_nb57 | runs_t033/_driver4.py（注入 layout） | 1=home 2=project 4=project_paraphrase18 | 57 | 过 | e5cc43c360ead6cc |

layout 出处（我逐个打开确认，不转述交接稿）：
- E：kvmem/m2_visibility/runs_iso2/_driver2.py:32-33（iso_dup4 = (1,home,home),(2,project,project),(3,habit,habit),(4,project2,project)）
- F：runs_iso2/_driver2.py:55-56（iso_fac_pp18 第4段 = (4, project_paraphrase18, project_paraphrase18, "variant")）
- X1：runs_t033/_driver7.py:10-11（D2.LAYOUTS["iso_x1_57copy"] = (1,home,home),(2,project,project),(4,project2,project)）
- B57：runs_t033/_driver4.py:72-75（D2.LAYOUTS["iso_fac_nb57"] = (1,home,home),(2,project,project),(4,pp18,project_paraphrase18,"variant")）

四格的 target 都是 home（提问点），四格的第 4 段都是被操弄量。

### 1.2 位置（由 cells 算出，不是硬编码）

公式在 runs_iso2/_driver2.py:74：
    lo = P.CHAT - (slot - 1) * spacing - n
其中 P.CHAT = 4096（tools/m2_visibility_probe.py:94），spacing = 64（_driver2.py 每个 layout 的 "spacing": 64）。

| 段 | slot | cells | pos_lo | pos_hi |
|---|---|---|---|---|
| home | 1 | 21 | 4096-0-21 = 4075 | 4096 |
| project | 2 | 18 | 4096-64-18 = 4014 | 4032 |
| habit | 3 | 12 | 4096-128-12 = 3956 | 3968 |
| 第4块（副本或 pp18） | 4 | 18 | 4096-192-18 = 3886 | 3904 |

X1/B57 不建 slot 3，[3956,3968) 空着，其余段位置不动（公式只依赖 slot 与 cells）。
提问位置 = P.CHAT = 4096（_driver2.py:188 传 pos=P.CHAT）。gap 计算在 _driver2.py:171：
    head_gap_cells = (CHAT - 1) - (span_hi - 1)
home 段 span_hi = 4096 ⇒ 4095 - 4095 = 0。
实测四个 run json 的 layout.head_gap_cells 全为 0：runs_t031/t031_e_dup4_samedriver_r1.json、
runs_t031/t031_f_pp18_r1.json、runs_t033/x1_r1.json、runs_t033/b57_r1.json。

### 1.3 块

- home = kvmem/m2_v1/home.kvmem（21 格）
- project = kvmem/m2_v1/project.kvmem（18 格）
- habit = kvmem/m2_v1/habit.kvmem（12 格）
- "project 副本" = 同一个 kvmem/m2_v1/project.kvmem 文件第二次 load 到 slot 4（E、X1），不是另一个文件。
  证据：段 (4,"project2","project") 的 block_id 是 "project"，family 缺省为 "m2"（_driver2.py:70-71），
  path 取 manifest.blocks.m2.project.path（fixtures.json），即 kvmem/m2_v1/project.kvmem。
- "project 改写" = kvmem/m2_visibility/blocks/project_paraphrase18.kvmem（18 格，family "variant"）

### 1.4 提问文本

- 问句 = P.FULL["home"]["q"] = "我住在哪？"（tools/m2_visibility_probe.py:108；取值处 _driver2.py:182-183）
- 期望事实 = P.FULL["home"]["fact"] = "广陵路"（tools/m2_visibility_probe.py:108）
- 送进引擎的不是裸问句，而是 kvslots.turn(q)（tools/kvslots.py:53,56-58）：
      ASK_SUFFIX 是一个换行 + "答："；turn(q) = 换行 + "问：" + q + ASK_SUFFIX
  _driver2.py:116 调用 P.K.turn(question)。四格完全相同（target 都是 home）。
- 生成预算 n_predict = P.N_PREDICT = 24（tools/m2_visibility_probe.py:103；_driver2.py:188）
- 请求位置 pos = 4096（绝对位置）

### 1.5 每个 run 里发生的事（顺序固定，_driver2.py:126-218）

1. 打开引擎（P.open_engine()，参数见 §5.1）
2. 逐块校验 manifest.blocks.m2 的 sha256 与磁盘一致（_driver2.py:150-152）
3. 控制门禁 run_control（_driver2.py:154-162）：把 4 条 FULL 陈述拼成一段连续文本，
   write_at(CTRL=6, text, start=3886, add_bos=True)，要求
   - 写入 token 数 == target_n == 4096-3886 == 210
   - raw_pos_max == 4095
   - 依次在 pos=4096 问 home/project/habit/car，四问都必须 fact_ok
   （实现 tools/m2_visibility_probe.py:498-538；顺序 CONTROL_ORDER = ["home","project","habit","car"]，_driver2.py:17）
   任一问不过 ⇒ control_ok = False ⇒ 该 run 记 "CONTROL GATE FAILED -- not interpreted" 并 return 3（_driver2.py:159-162）。
   四格 7B 的 control_ok 全为 true（四个 run json 的 control_ok 字段）。
4. reset_all → load_and_place（逐块 load_strict 到 slot，再 repos_local 平移到 pos_lo，校验 pos_max == pos_hi-1）：probe:437-466
5. share_layout：把每个 slot 的 [pos_lo,pos_hi) 挂到 LIVE=0（probe:469-473）
6. cell_scan 核对覆盖：cell_count 必须是 69（E/F）或 57（X1/B57），positions_min/max = 3886/4095
7. eng.reset(LIVE) → 再 share_layout → 快照 n_tokens → kvshim_ask_at(LIVE, turn(q), pos=4096, n_predict=24)
8. ok = P.fact_ok(fact, answer)，fact_ok 定义在 probe:160-167（去空白后子串包含）

### 1.6 判据脚本到底是谁（三处不能混）

- 门禁 + 每格 ok：都在 driver 内部，即 §1.5 第 3 步与第 8 步（P.run_control probe:498-538；P.fact_ok probe:164-167）。
  这是唯一决定"过/败"的东西。
- 失败形态 failure_form 的 7 步顺序在 kvmem/m2_visibility/runs_t033/_judge_t033.py:4-11 与 :29-44：
      0 fact_ok（该文件硬编码 FACT = "广陵路12号2单元602"，:15）→ none
      1 norm 后空串 → 空串
      2 norm(question) 出现在 norm(answer) 里 → 复述提问
      3 三个下划线起 / "填空" / "选项" / 行首 A-D 加点或顿号 → 改写成模板
      4 不知道 / 无法 / 不能确定 / 没有相关信息 → 拒答
      5 有数字或地址类字（路|街|道|号|单元|室|楼|巷|村|区）→ 编造具体值
      6 其他
  注意：_judge_t033.py 的 fact_ok 与 driver 的 fact_ok 不是同一判据（前者要全串"广陵路12号2单元602"，后者只要"广陵路"）。
  ⇒ 它只当"失败形态描述"用；"过/败"一律以 run json 的 answers[0].ok 为准；两者不一致就照实报两条，不许反用。
  该脚本自带自检（_judge_t033.py:59-73），读 evidence/t030/curve_E_r1.json 与 runs_t032/t032_f_r1.json（两文件都存在，我核过）。
- kvmem/m2_visibility/_strict_label.py 不是新跑的判据：它对"已存在的产物"做 recount（form 三分 empty/quiz/plain，
  strict = raw_ok 且 form == "plain"），依赖 runs_mask/_form.py:43-55。本轮四格不产出 form 维度，别用它顶替 fact_ok。
- kvmem/m2_visibility/score_at_gate.py 与四格判定无关：它是 kvshim_score_at 那个 Δ 指标的"有效性门禁"
  （阈值写死在该文件 :14-20 与主判据 :37-39），而 Δ 指标已作废（NIGHT-REPORT.md:18、HANDOFF.md §4）。
  ⇒ 本轮不跑 score_at_gate.py，也不需要为它准备任何东西。

---

## 2 14B 造块规格

### 2.1 结论先行：块是模型专属的，块头会自证，加载器会拒绝（不是静默误读）

块头字段（我逐字节解析 5 个 7B 块；解析器完整消费到文件末尾、零剩余，见附录 A）：

| 偏移 | 字段 | 7B 实测 | 14B 预期（推导） | 谁写 / 谁校验 |
|---|---|---|---|---|
| 0..3 | magic 0x67677371 | 同 | 同 | llama-context.cpp:3611 |
| 4..7 | version = 4 | 4 | 4 | llama-context.cpp:3612 |
| 8..11 | n_tokens (int32) | 21 / 18 / 12 | 必须实测 | llama-context.cpp:3615 |
| 12..12+4n | token ids | 首 = 151646 | 必须实测 | 同上 |
| 12+4n | n_stream | 1（因为 kv_unified=true） | 1 | llama-kv-cache.cpp:2577 |
| 后 4B | cell_count | 等于 n_tokens | 必须相等 | llama-kv-cache.cpp:2627 |
| 之后每格 12 B | pos(4) + n_seq_id(4) + seq_id(4) | n_seq_id = 1 | 同 | llama-kv-cache.cpp:2717-2747 |
| 之后 16 B | v_trans, n_layer, n_rot_k, n_rot_v | 0, 28, 128, 64 | 0, 48, 128, 64 | llama-kv-cache.cpp:2756-2759 |
| 之后每层 12 B（K 段） | k_type(4) + k_size_row(8) | 8(q8_0), 544 | 8, 1088 | llama-kv-cache.cpp:2771-2776 |
| 之后每层 12 B（V 段） | v_type(4) + v_size_row(8) | 8, 544 | 8, 1088 | llama-kv-cache.cpp:2776 之后同段循环 |
| 载荷 | 每格 n_layer x (k_row + v_row) | 30,464 B | 104,448 B | llama-kv-cache.cpp:2763-2800 |

加载侧逐项校验（不是"无从比对"）：
- n_layer：llama-kv-cache.cpp:3060-3063（不匹配 → LLAMA_LOG_ERROR "mismatched layer count" → return false）
- v_trans：3070-3073；n_rot_k：3075-3078；n_rot_v：3080-3083
- 每层 k_type：3097-3100；k_size_row：3106-3109；v 侧（含 v_trans 分支的 el size 与 GQA 维）：3131-3143 / 3174-3185
- 失败后：llama-kv-cache.cpp:2706-2709 先 state_clear(...) 再 throw std::runtime_error("failed to restore kv cache")
- 这个 throw 穿过 llama_context::state_seq_read_data（llama-context.cpp:3682-3688；它只返回 io.n_bytes()，
  不看 memory->state_read 的返回值）和 state_seq_load_file（llama-context.cpp:3554-3606），
  进入 tools/kvshim.cpp:572-589 的 kvshim_load（没有 try/catch），跨过 C ABI 进入 ctypes。
  ⇒ 把 7B 块喂给 14B 引擎：拿不到 -1，得到的是 C++ 异常无处理导致的进程中断，没有 traceback；
     而且 llama 日志被 quiet_log 丢弃（tools/kvshim.cpp:52-54 与 :631），连 "mismatched layer count" 都看不到。
  ⇒ tools/kvslots.py:228-238 load_strict 的注释（"引擎会返回负值，因为 n_rot_k 不同"）在这条路径上不成立。

结论（回答"块头/加载器是否把维度写死"）：
- 加载器没有把维度常量写死；它拿"活模型"的 hparams 去比对块头。
- 块头携带足够的模型指纹（n_layer、n_rot_k、n_rot_v、每层 k/v 的 type 与 row size）来拒绝跨模型块。
- 只有前景完全相同的两个模型才可能静默通过；7B(28 层/row 544) 与 14B(48 层/row 1088) 不属于这种。
- 708 / 30,480 是 7B 专属常数，14B 必须重算（§2.2）。零引擎工具 tools/block_info.py 把它们写死
  （block_info.py:16-18：BOS=151646, HEADER=708, STRIDE=30480），拿它核 14B 块会把 cells_from_size 算错并打印
  "STRUCTURE MISMATCH"（block_info.py:53-54）。它可以继续读 cells 与首 token，但不能做尺寸自检。

### 2.2 14B 的字节数（推导，必须被实测确认）

7B 的实测分解（E10-NEXT2.md:2529 与我本次逐字节解析一致）：
    size  = 708 + 30,480 * n
    708   = 12(magic+ver+n_tokens) + 4(n_stream) + 4(cell_count) + 16(v_trans,n_layer,n_rot_k,n_rot_v) + 28 层 x 24
    30,480 = 4(token id) + 12(每格 meta) + 28 层 x 2 x 544(q8_0 一行 = 512/32*34)

14B（Qwen2 架构：48 层，8 kv head，head_dim 128 ⇒ n_embd_k_gqa = 1024，q8_0 一行 = 1024/32*34 = 1088）：
    固定部分 = 12 + 4 + 4 + 16 + 48*24 = 1188
    每格     = 4 + 12 + 48*2*1088 = 104,464
    断言式   = size == 1188 + 104,464 * n
    推出的三块大小：n=21 → 2,194,932 ；n=18 → 1,881,540 ；n=12 → 1,254,756
（这三条是算术推论，不是实测。造完块用附录 A 解析器把实测 size 与它对齐；不等就停下报数，不许改断言迁就。）

### 2.3 造块脚本：怎么写

现成两个脚本可以照抄流程，但都不能原样跑：
- tools/t031_habit_para.py：模型走 P.open_engine()（:210），P.MODEL 固定 7B；写块路径固定在 kvmem/m2_v1/（:26-29）；
  末尾断言 size == 708 + 30480*n（:184-188）⇒ 14B 上必然失败。
- kvmem/m2_visibility/make_t032_blocks.py：同样 P.open_engine()（:66）；BOS/HEADER/STRIDE 写死（:24-25）；
  M2V1 = kvmem/m2_v1（:26）；拒绝覆盖已存在文件（:59-60）；checks 的 size_derived_cells 用写死常量（:104）。

新建 kvmem/m2_visibility/runs_14b/make_blocks_14b.py，硬要求：
1. 模型：在 P.open_engine() 之前显式赋值
       P.MODEL = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
   依据：P.open_engine() 调用时读模块全局（tools/m2_visibility_probe.py:172-175）；probe 与 kvslots 里没有任何
   os.environ/getenv（我 grep 过，"environ" 只出现在 probe:777 的报告字段），⇒ 环境变量覆盖不存在，
   只能运行时赋属性或新写脚本。不要改 probe:85 那一行（会污染 7B provenance）。
2. 输出目录：D:/llama-mem/kvmem/m2_v1_14b/（新建）。四个文件：home.kvmem、project.kvmem、habit.kvmem、
   project_paraphrase18.kvmem。已存在就停（不许覆盖）。
3. 文本必须逐字相同（改一个字就换了对照因子）：
   - home："我住在广陵路 12 号 2 单元 602。"                    期望 21 格 = 1 BOS + 20 内容
   - project："项目代号蓝鲸，计划 3 月 14 日上线。"              期望 18 = 1 + 17
   - habit："我的咖啡只喝美式，不加糖。"                        期望 12 = 1 + 11
   - project_paraphrase18："项目代号叫蓝鲸，三月十四号正式上线。。我。我"   期望 18 = 1 + 17
   出处：前三条 = tools/m2_visibility_probe.py:107-112（FULL）；第四条 = fixtures.json 的
   blocks.variant.project_paraphrase18.text（与 make_t032_blocks.py:32-33 同一族记录）。
4. 写块措辞与既有块一致：eng.write_at(seq, text, 0, add_bos=True) 然后 eng.save(seq, path)
   （make_t032_blocks.py:77,83）。基址 0、含 BOS；驱动后面靠 base 求 delta 平移到 pos_lo（probe:450-457）。
5. 断言（缺一步就不许进入下一步）：
   a) P.measure(eng, text) == 期望格数（P.measure 用 add_bos=True，probe:205-213）
   b) 写入返回值 == 期望格数
   c) 重新 load_strict 回来 cells == 期望格数；token[0] == 首 token（与 7B 相同则 151646）；
      token[1:] == kvshim_tokenize(text)
   d) 首 token 一旦不是 151646 ⇒ 这是 BOS 口径变化，必须写进产物并列为差异字段，不许靠"补一个 BOS"强凑
   e) size == 1188 + 104464 * n
   f) 附录 A 解析器打印 n_layer / n_rot_k / n_rot_v / k_type / k_row，必须为 48 / 128 / 64 / 8 / 1088
      （n_rot_k=128 的依据：llama-kv-cache.cpp:333-346，head_dim 128 且 type_k 量化 ⇒ 64 翻倍到 128；
       n_rot_v=64 的依据：同文件 348-358，V 固定 64）
   g) 两次独立编码产生同一 sha256（t031_habit_para.py:131-145 的做法），否则"编码不确定"，停
6. 明细落盘 runs_14b/blocks_14b.json：每块记 name / path / text / cells / content_tokens / first_token / size /
   sha256 / n_layer / n_rot_k / n_rot_v / k_type / k_row / 全部断言结果（字段照 make_t032_blocks.py:114-122）。

### 2.4 造块前必须确认的一件事

14B 与 7B 是否同一套分词器：DeepSeek-R1-Distill-Qwen-14B 与 7B 同族（Qwen2，词表 151,646），
预期四块仍是 21/18/12/18 格、首 token 仍是 151646 —— 但这是预期，§2.3 的断言 a/c/d 就是把它变成实测。
若实测格数与 21/18/12/18 任一不符：停。位置由 cells 算出（§1.2），格数一变，
[4075,4096) / [4014,4032) / [3886,3904) 这套"与 7B 同几何"的前提就没了。不允许靠填充或裁剪把格数凑回去。

---

## 3 14B 运行装置

### 3.1 一份新的 manifest：kvmem/m2_visibility/runs_14b/fixtures_14b.json

顶层键照 kvmem/m2_visibility/fixtures.json（我 print 过：blocks, constants, control_texts, created_at, engine,
layouts, project_root, schema）。驱动真正用到的只有：engine.dll / engine.dll_sha256（_driver2.py:147-149 会用磁盘实测值
覆盖 dll_sha256 并保留 declared 对照）、以及 blocks 里每块的 path/cells/sha256（_driver2.py:68-71 取用，:150-152 校验）。

用脚本生成，不要手填数字：

    import json, os, hashlib
    def sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        return h.hexdigest()
    M = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
    D = "D:/llama-mem/kvmem/m2_v1_14b"
    man = {"schema": "fixtures_14b_v1",
           "engine": {"model": M, "model_size": os.path.getsize(M), "model_mtime": os.path.getmtime(M),
                      "n_ctx": 8192, "n_seq": 8, "gpu": 99, "kv": "q8_0",
                      "dll": "D:/llama-mem/tools/kvshim_vk.dll",
                      "dll_sha256": sha("D:/llama-mem/tools/kvshim_vk.dll")},
           "blocks": {"m2": {"home":    {"path": D + "/home.kvmem",    "cells": 21},
                             "project": {"path": D + "/project.kvmem", "cells": 18},
                             "habit":   {"path": D + "/habit.kvmem",   "cells": 12}},
                      "variant": {"project_paraphrase18":
                                  {"path": D + "/project_paraphrase18.kvmem", "cells": 18}}}}
    for fam in man["blocks"].values():
        for meta in fam.values():
            meta["sha256"] = sha(meta["path"])
    json.dump(man, open("D:/llama-mem/kvmem/m2_visibility/runs_14b/fixtures_14b.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

cells 必须用 §2.3 实测值填写；若实测不是 21/18/12/18，按 §2.4 停下，不要改这里的数字去凑。

### 3.2 一个包装驱动：kvmem/m2_visibility/runs_14b/_driver14b.py

必须用包装，不要改 _driver2.py。理由：MODEL 在 probe:85、MANIFEST 在 probe:90、CTRL_CACHE 在 _driver2.py:16，
三处都是模块常量，都能在 main() 之前赋值。

    # -*- coding: utf-8 -*-
    import os, sys
    HERE = os.path.dirname(os.path.abspath(__file__))
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))   # -> D:/llama-mem
    ISO2 = os.path.join(ROOT, "kvmem", "m2_visibility", "runs_iso2")
    sys.path.insert(0, ISO2)
    import _driver2 as D2
    P = D2.P
    P.MODEL = "D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf"
    P.MANIFEST = os.path.join(HERE, "fixtures_14b.json")
    D2.CTRL_CACHE = os.path.join(HERE, "control_texts_14b.json")     # 关键：不许复用 7B 缓存
    D2.LAYOUTS["iso_x1_57copy"] = {"spacing": 64, "segs": [
        (1, "home", "home"), (2, "project", "project"), (4, "project2", "project")]}
    D2.LAYOUTS["iso_fac_nb57"] = {"spacing": 64, "segs": [
        (1, "home", "home"), (2, "project", "project"),
        (4, "pp18", "project_paraphrase18", "variant")]}
    if __name__ == "__main__":
        sys.exit(D2.main())

E（iso_dup4）与 F（iso_fac_pp18）已在 _driver2.LAYOUTS 里（:32-33、:55-56），不必再注入；
X1/B57 两段 dict 逐字抄自 runs_t033/_driver7.py:10-11 与 runs_t033/_driver4.py:72-75。

为什么不复用 7B 的 control_texts.json：get_control（_driver2.py:87-110）命中缓存后仍会重测并在重建时改写该文件
（:107-109）；而 runs_iso2/control_texts.json 是 7B 分词器产物（iso_dup4 条目：start=3886, target_n=210,
text sha256 前 12 = c157a8e2c1a7，我读过该文件）。14B 一跑就会覆盖它，7B 的门禁 provenance 就没了。
⇒ 必须另给 control_texts_14b.json。14B 上 control 文本会重建为同一 start=3886、同一 target_n=210 的 210 个 14B token；
实测以 run json 里 control 的 target_n 与 text_sha256 为准。

### 3.3 四格的命令行（只换 --layout）

    cd /d/llama-mem/kvmem/m2_visibility/runs_14b
    python -X utf8 _driver14b.py --layout iso_dup4      --target home --run-json out/E_r1.json
    python -X utf8 _driver14b.py --layout iso_dup4      --target home --run-json out/E_r2.json
    python -X utf8 _driver14b.py --layout iso_fac_pp18  --target home --run-json out/F_r1.json
    python -X utf8 _driver14b.py --layout iso_fac_pp18  --target home --run-json out/F_r2.json
    python -X utf8 _driver14b.py --layout iso_x1_57copy --target home --run-json out/X1_r1.json
    python -X utf8 _driver14b.py --layout iso_x1_57copy --target home --run-json out/X1_r2.json
    python -X utf8 _driver14b.py --layout iso_fac_nb57  --target home --run-json out/B57_r1.json
    python -X utf8 _driver14b.py --layout iso_fac_nb57  --target home --run-json out/B57_r2.json

只有三个参数：--layout（choices 来自 LAYOUTS，_driver2.py:128）、--target（:129，四格都是 home）、
--run-json（:130）。spacing 与位置全由 layout + manifest 推出，没有第四个旋钮。
环境变量：不要设 LLAMA_KV_MASK_BIAS（不加偏置；b>=4 会打坏控制臂，HANDOFF.md §2）；
不要设 LLAMA_ATTN_ROT_DISABLE（E10-NEXT2.md:2020 列为混淆因子；块头 n_rot_k=128 / n_rot_v=64 就是它没被禁的证据）。

### 3.4 现成驱动与 14B 的关系（别拿错文件）

- runs_t033/_driver7.py：X1 的原始入口，:13-15 把 sys.argv 改写成固定 --layout iso_x1_57copy --target home 再调
  D2.main()。没有改 MODEL/MANIFEST 的钩子 ⇒ 14B 上不能用它，只能用 §3.2 的包装（注入的 layout 逐字相同）。
- runs_t033/_driver4.py：B57 的原始入口，:68-77 注入 iso_fac_hh12 与 iso_fac_nb57、切 CTRL_CACHE、调 seed_ctrl，
  :79 调 D2.main()，:81-115 追加 blocks 明细。同样没有 MODEL/MANIFEST 钩子 ⇒ 14B 不能用。
- runs_t032/_driver3.py：F 的另一条入口（t032_run.py --arm F_pp18 那套），14B 不用。
- kvmem/m2_visibility/runs_t032/mine/_driver5.py：不是 canonical 驱动。它链接隔离探针 DLL
  tools/kvshim_vk_t031.dll（该文件 :8-12 明写），不是 tools/kvshim_vk.dll。14B 上禁用。

---

## 4 判据（跑之前写死）

一格算"过"当且仅当：该 run 的 control_ok == true 且 answers[0].ok == true。
- answers[0].ok 来自 P.fact_ok("广陵路", answer)（probe:164-167）：只去空白，子串判定。
- 两次跑（_r1/_r2）的 answers[0].answer 的 sha256 必须逐字节相同；不同 ⇒ 记"不稳定"，不得取其一
  （预登记 mine/lead/PREREG-14B-4CELL.md:27）。
- 失败形态用 _judge_t033.py 的 failure_form 描述（§1.6），不改"过/败"。
- 不许用 Δ / logprob / rank / cells 数 / 字节数做跨模型比较（§5.2）。

预登记的结论读法（不许事后改，PREREG-14B-4CELL.md:22-25）：
- 14B 上 F（69 格 + 改写）也过 ⇒ 规模/分配假设成立。
- 14B 上 F 仍败 ⇒ 不是规模问题，回到关系结构。
- 实验无效 != 假设被否证（四词：未检验 / 实验无效 / 未测出·欠功率 / 无效应）。

---

## 5 引擎装置与跨模型可比性

### 5.1 A：7B 跑那四格时的启动参数

这四格没有命令行引擎：不启 llama-cli / llama-server，是 Python 经 ctypes 调 tools/kvshim_vk.dll。
装置全部在 tools/kvshim.cpp:142-177 的 kvshim_open 里定死，Python 侧只传 5 个数（tools/kvslots.py:114-115；
参数源 tools/m2_visibility_probe.py:172-175 与 :99-103）。

| 你问的 | 实际落点 | 值 | 出处 |
|---|---|---|---|
| -ngl | mp.n_gpu_layers | 99（= P.GPU，probe:101） | kvshim.cpp:145；kvslots.py:114 |
| -c | cp.n_ctx | 8192（= P.N_CTX，probe:100） | kvshim.cpp:158 |
| -fa | cp.flash_attn_type | ENABLED（kv_q8 != 0 强制开，即 KV=q8_0） | kvshim.cpp:163-165 |
| -t | cp.n_threads / n_threads_batch | 8 / 8 | kvshim.cpp:166-167 |
| — | cp.n_batch / n_ubatch | 512 / 512 | kvshim.cpp:159-160 |
| — | cp.n_seq_max | 8（= P.N_SEQ，probe:99） | kvshim.cpp:161 |
| — | cp.kv_unified | true（一个共享池，seq_cp 才是共享机制） | kvshim.cpp:162 |
| — | cp.type_k / type_v | Q8_0 / Q8_0（kv="q8_0"，probe:102） | kvshim.cpp:163-164 |
| — | 权重 | D:/models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf，4,683,073,504 B | fixtures.json engine.model/model_size；probe:85 |

四格逐格（从落盘 run json 读）：

| 格 | run json | engine.n_ctx | engine.n_seq | engine.kv | engine.gpu | engine.dll_sha256 |
|---|---|---|---|---|---|---|
| E | runs_t031/t031_e_dup4_samedriver_r1.json | 8192 | 8 | q8_0 | 99 | c7ea09bb… |
| F | runs_t031/t031_f_pp18_r1.json | 8192 | 8 | q8_0 | 99 | c7ea09bb… |
| X1 | runs_t033/x1_r1.json | 8192 | 8 | q8_0 | 99 | 3a726dbd…（dll_sha256_source = measured） |
| B57 | runs_t033/b57_r1.json | 8192 | 8 | q8_0 | 99 | 648e7244…（r2/r3 为 3d02c1f8…） |

KV 是否全在 GPU：
- 权重：n_gpu_layers=99 >= 7B 的 28 层 ⇒ 全部层在 Vulkan 设备上（kvshim.cpp:145；llama-context.cpp:213 拷进 cparams）。
- KV 缓存：cparams.offload_kqv 默认 true（llama-context.cpp:4028），kvshim.cpp 没有改它；它被当作 offload 参数
  传给 KV cache（llama-model.cpp:2936，注释 /* offload */ cparams.offload_kqv），KV cache 每层 buffer 类型由
  "if (offload) buft = ggml_backend_dev_buffer_type(model.dev_layer(il))" 决定（llama-kv-cache.cpp:214-223）
  ⇒ 28 层 KV 全走 GPU buffer type。
- 证据的限度（必须照实写）：llama 日志被 quiet_log 丢弃（kvshim.cpp:52-54、:631），因此任何产物里都不存在
  "offloaded N/28 layers" 或 "KV self size" 这类行。我 grep 过 runs_t033/*.log、runs_iso2/_run.log、runs_t032/*.log，零命中。
  ⇒ "KV 全在 GPU"是源码链推导，不是实测；我没有找到任何落盘 VRAM 计量，不要声称有。

### 5.2 B：14B 若被迫部分 offload，比较规则与必录字段

事实：装置里唯一控制层放置的旋钮是 P.GPU（probe:101），直通 mp.n_gpu_layers（kvshim.cpp:145）。
KV cache 的 buffer 类型按层跟 model.dev_layer(il) 走（llama-kv-cache.cpp:216-223）⇒ 只要 n_gpu_layers < 48，
就一定有若干层的 KV 落在 CPU buffer，装置本身变了。

算术（只算不测）：14B 权重 8,988,110,240 B（.dl 的字节数，作量级参考）+ KV 池 8192 x 104,464 B = 855,769,088 B
⇒ 仅这两项约 9.84e9 B，还没算计算缓冲（n_batch=n_ubatch=512）。10 GB 卡上属于"可能装不下"。

预先写死的规则：
1. 先试满 offload：P.GPU = 99。成功 ⇒ 装置与 7B 同语义（同 kv_unified、同 q8_0、同 n_ctx、同 n_seq）。
2. 若满 offload 失败（Vulkan OOM / kvshim_open 返回空 / llama_init_from_model 失败）：记下失败原文与降到的
   P.GPU 值，四格产物一律打戳 kv_placement = "partial(k/48)"。
3. 无论哪种情形，7B 与 14B 之间只允许比序数（过/败）。禁止跨模型相减或相比：Δ、logprob、rank、cells 数、
   每格字节数、答案长度、生成字节数。理由：两边差异字段至少有 模型 / 每格字节数 / 分词器 / 内容 token 数 /
   BOS 口径 / KV 放置装置 六项，>1 就不许下单因子结论（HANDOFF.md §4；PREREG-14B-4CELL.md:30-33）。
4. 若最终是 partial：把"KV 放置不同"写进结论的未排除项，不许写成"已控"。此时四格结果只能支持
   "在 14B + 部分 offload 这个装置下 F 过/不过"，不能支持"规模假设成立/不成立"。

必录字段表（跑的时候顺手抄；缺一项该跑记"未检验"）：

    A 装置
      ax  model_path / model_size / model_mtime（os.path.getsize、getmtime）
      ay  dll_file = D:/llama-mem/tools/kvshim_vk.dll 及其实测 sha256（用 §3.1 的 sha()）
      az  gpu_layers 实际值（P.GPU），是否曾因 OOM 降级，降级附失败原文
      ba  n_ctx / n_seq / kv（抄 run json 的 engine）；n_threads / n_batch / n_ubatch / kv_unified / flash_attn
          （写 kvshim.cpp:158-167 的常量值，并注明"源码常量，非产物字段"）
    B 块（每块一行）
      bb  path ｜ cells ｜ first_token ｜ content_tokens ｜ size ｜ sha256
      bc  n_layer ｜ n_rot_k ｜ n_rot_v ｜ k_type ｜ k_row（附录 A 解析器输出）
      bd  size 是否等于 1188 + 104464*n
    C 几何
      be  layout_key ｜ cells_total ｜ 每段 (id, slot, pos_lo, pos_hi) ｜ overlaps ｜ head_gap_cells ｜
          raw.cell_count ｜ raw.positions_min/positions_max
      bf  control.ok ｜ control.target_n ｜ control.text_sha256 ｜ 四问逐问的 answer 与 ok
    D 答案
      bg  question ｜ fact ｜ answer 全文 ｜ answer_sha256 ｜ ok ｜ failure_form（_judge_t033.py 输出）｜
          kvshim_ask_at 的返回字节数 ｜ kvshim_n_tokens(seq) 问前/问后
      bh  _r1 与 _r2 的 answer_sha256 是否相同
    E 语境
      bi  LLAMA_KV_MASK_BIAS / LLAMA_ATTN_ROT_DISABLE 是否设置（未设就写 empty）
      bj  同时刻是否只有一个执行者（是/否）

---

## 6 7B 基线：逐块三件套与尺寸（我本次实测，可复算）

没有 sha256sum，用 python -X utf8 + hashlib。实测结果：

| 文件 | size | cells | 首 token | 是否 BOS | 内容 token | (size-708) mod 30480 | sha256 |
|---|---|---|---|---|---|---|---|
| kvmem/m2_v1/home.kvmem | 640,788 | 21 | 151646 | 是 | 20 | 0 | ba92d73089fdcea8d35513948d6083c9b6e4170e77365fb66b215fcd5af38ba5 |
| kvmem/m2_v1/project.kvmem | 549,348 | 18 | 151646 | 是 | 17 | 0 | 48825f8d5500de9ea71d8d63c33ed0a67c071a9c22cfbbb357f99567ca63a969 |
| kvmem/m2_v1/habit.kvmem | 366,468 | 12 | 151646 | 是 | 11 | 0 | 6c2103141fa48d13450d3c76aa530bb31ea650d0ceb77caf28f7badaf0b749fc |
| kvmem/m2_visibility/blocks/project_paraphrase18.kvmem | 549,348 | 18 | 151646 | 是 | 17 | 0 | 32306e8ae0db979ffdfccfa6abc829f862875433f166bf8ec0950a1227d3a71b |
| kvmem/m2_v1/blk_G_bos_c18.kvmem（X0 用的那块） | 549,348 | 18 | 151646 | 是 | 17 | 0 | 06fb59ac3416a1ae727865d0ccdf6ba36f2fe14e62386037620a3d1a3303218e |

四块都满足 (size-708) mod 30480 == 0，且商等于块头 n_tokens。
块头四元组 (v_trans, n_layer, n_rot_k, n_rot_v) = (0, 28, 128, 64)；每层 (k_type, k_size_row, v_type, v_size_row) = (8, 544, 8, 544)。

对照：kvmem/m2_v1/G_bos_c18.kvmem 是另一个文件（18 格、549,348 B、
sha d75f27c42f4f18cddcbebf742a22cb98e8c48b863088da8f0109e78e1c463980，token 序列不同）。
HANDOFF.md §7 写的是这个路径，实际跑 X0 用的是 blk_G_bos_c18（§9 第 2 条）。

四格 7B 观测点（逐个读 run json）：

| 格 | 全部 run | ok | answer sha256 前 16 | 记录的 DLL |
|---|---|---|---|---|
| E | runs_t031/t031_e_dup4_samedriver_r1 与 _r2 | True/True | 7ec1430d972d949e（两次相同） | c7ea09bb |
| E | runs_g18/reg_dup4_home_before 与 _after | True/True | 7ec1430d972d949e | 3a726dbd |
| F | runs_t031/t031_f_pp18_r1 与 _r2 | False/False | 11e20d78a1f18a98 | c7ea09bb |
| F | runs_t032/t032_f_r1 与 _r2 | False/False | 11e20d78a1f18a98 | c7ea09bb |
| F | runs_g18/iso_fac_pp18_home_r1 与 _r2 | False/False | 11e20d78a1f18a98 | 3a726dbd |
| X1 | runs_t033/x1_r1 与 _r2 | True/True | 14dc3f98202c7023（两次相同） | 3a726dbd |
| B57 | runs_t033/b57_r1 / _r2 / _r3 | True x3 | e5cc43c360ead6cc（三次相同） | 648e7244 / 3d02c1f8 / 3d02c1f8 |
| X0（参考点） | runs_g18/iso_fac_G18_home_r1 与 _r2 | False/False | 3f69de0797a6afb3（两次相同） | 未落在该字段 |

答案原文（前 46 字符）：
- E 与 B57 措辞"我住在…"，X1 措辞"你住在…"，三者 sha 不同但都 ok。
- F 六次逐字节相同："我住在" + 6 个转义下划线 + "。要填空的选项有：A. 中国；B." ⇒ failure_form = 改写成模板。
- X0 两次逐字节相同（3f69de07…）⇒ 69 格 + 无关 18 格真事实 = 败，7B 上已跑过。

---

## 7 陷阱（每条都能让这一轮白跑）

1. 不要改 probe:85 的 MODEL。用 §3.2 的运行时赋值；改常量会让 7B 复跑变成"另一个模型"，provenance 断。
2. 不要复用 7B 的 control_texts.json（§3.2）。get_control 会覆盖它。
3. 不要覆盖 kvmem/m2_visibility/fixtures.json，另建 fixtures_14b.json（§3.1）。
4. tools/block_info.py 的 708/30480 是 7B 常量，核 14B 块会误报 STRUCTURE MISMATCH（§2.1）。核 14B 用附录 A。
5. 7B 块喂 14B 引擎不是"返回 -1"，是 C++ 异常打断进程且无日志（§2.1）。不要用"试着 load 一下"当探测。
6. 块的基址必须是 0 且含 BOS（make_t032_blocks.py:77,83；probe:450-457 靠 base 求 delta）。基址不为 0 会静默错位。
7. 提问点必须紧贴被问块末格 +1：home 末格 4095、提问 4096、gap=0（probe:498-538 的三条前置检查）。
   gap 不为 0 ⇒ rc=-1、空答、无诊断。
8. 同一时刻全场只允许一个执行者（DLL 被映射时链接失败；两个引擎同起会 Vulkan OOM；HANDOFF.md §8）。
9. B57 的 7B 基线不是当前 DLL 跑出来的：r1=648e7244、r2/r3=3d02c1f8，现役是 3a726dbd（队长实测）。
   本轮 14B 四格必须用同一份 14B DLL 跑完 8 次；跨二进制比较一律标"跨二进制"（NIGHT-REPORT.md 第 4 节第 5 条）。
10. block_info.py 只能答"12 字节前缀 + token 序列"，答不了 provenance —— 但 E10-NEXT2.md:2536 那句
    "文件里没有 model/rope/type/n_rot_k" 是错的（§9 第 6 条），不要因为台账那么写就放弃块头自证。

---

## 8 执行顺序与停止条件

1. （前置）14B GGUF 就绪；kvshim_open 能返回非空的引擎。
2. 写 runs_14b/make_blocks_14b.py（§2.3），造 4 块到 kvmem/m2_v1_14b/。
   停：断言 a-g 任一失败；格数不是 21/18/12/18；首 token 不是 151646（记差异字段并回来问，不许强凑）。
3. 用附录 A 解析器核四块：n_layer=48、k_row=1088、size == 1188 + 104464*n。
4. 生成 fixtures_14b.json（§3.1）；写 _driver14b.py（§3.2）。
5. 跑 E 的 2 次。停：control_ok=False ⇒ 装置不可用，先解决门禁，不许解释四格。
6. E 过门禁后，依次跑 F、X1、B57 各 2 次；每次跑前确认上一个 python 进程已退出。
7. 交证据：每格 run json 路径 + §5.2 必录字段全表 + 两次 answer sha256 是否相同 + 四格序数结论。

本轮不做：改 E10-NEXT2.md（等四格跑完）；加掩码偏置；换 habit 内容做对照；并发跑多个引擎。

---

## 9 文档不符清单（对 HANDOFF.md / NIGHT-REPORT.md / E10-NEXT2.md，我逐条核过）

1. HANDOFF.md:159 写 kvmem/m2_visibility/m2_visibility_probe.py:85 是 MODEL 常量位置 —— 该文件不存在。
   实际文件是 tools/m2_visibility_probe.py，MODEL 在 :85。仓库里没有环境变量覆盖 MODEL 的代码
   （probe 与 kvslots 都没有 os.environ/getenv）。
2. HANDOFF.md:181-182（§7）把 X0 当"备用（未做）"，且称用 m2_v1/G_bos_c18.kvmem：
   - 该实验跑过两次且逐字节相同、结论败：runs_g18/iso_fac_G18_home_r1/r2，ok=False，
     answer sha256 3f69de0797a6afb3（两次相同）；
   - 它用的是 m2_v1/blk_G_bos_c18.kvmem（sha 06fb59ac…，fixtures.json blocks.variant.blk_G_bos_c18，
     layout 见 _driver2.py:59-60），不是 §7 写的 G_bos_c18.kvmem（另一文件，sha d75f27c4…）。
   状态与路径两处都错。
3. HANDOFF.md:116 驱动清单里的 _driver5.py 不在 runs_t033 下；实际在 kvmem/m2_visibility/runs_t032/mine/_driver5.py，
   且链接隔离探针 DLL tools/kvshim_vk_t031.dll（该文件 :8-12），不是 canonical 的 tools/kvshim_vk.dll。
4. HANDOFF.md:37 "各点 2-4 次独立跑，答案逐字节相同"易被读成同一二进制：实际 E/F 在 c7ea09bb（另有 3a726dbd 回归）、
   X1 只在 3a726dbd、B57 在 648e7244 与 3d02c1f8 ⇒ 这张 2×2 是跨二进制拼出来的。
   按 NIGHT-REPORT.md 第 4 节第 5 条，跨 DLL 不得当受控对照，写结论时必须标"跨二进制"。
5. HANDOFF.md:84 与 :154 的"708 字节头 + 30480 字节/格"不是结构描述，只是两个凑出的常数（§2.2 有分解）。
6. NIGHT-REPORT.md:74-75 与 E10-NEXT2.md:2536 的"文件不携带 model/rope/type_k/type_v/n_rot_k"不成立：
   块头携带 n_layer / n_rot_k / n_rot_v 与每层 k_type、k_size_row、v_type、v_size_row
   （写：llama-kv-cache.cpp:2753-2776；读+校验：3050-3143）。我这 5 个 7B 块全部读成 (28, 128, 64, 8, 544)。
   ⇒ "同编码配置"可从"未证明"升级为"块头逐字段相等即已证明"。
7. tools/kvslots.py:228-238 load_strict 的注释与实现不符：跨模型块的拒绝发生在
   llama-kv-cache.cpp:3060-3063 / 3075-3083 的 return false → :2706-2709 的 throw；而 kvshim_load
   （tools/kvshim.cpp:572-589）没有 try/catch，n<0 分支收不到它（§2.1）。
8. mine/lead/PREREG-14B-4CELL.md:6-7 写"每 token = 708 字节头 + 每格字节数(N)"：正确写法是固定开销 1188 B +
   每格 104,464 B（14B）；7B 是 708 + 30,480。14B 每格 104,464 B = 102.0 KiB，与"约 102 KB"同量级，
   与 HANDOFF 的"约 104 KB"（十进制 104.5 kB）也相容 —— 两种写法都对，只要带单位。

---

## 10 标为"未验证"的项（不许在结论里当已知）

1. 14B GGUF 完整性/可加载性：队长报 sha256 已 MATCH（0b319bd0…）。但我**没有**亲自复算该 sha256，也没有看到
   一次成功的 kvshim_open；执行者加载实测出来之前，这条状态以执行者报的为准。
2. 14B 分词器是否给出与 7B 相同的 cells（21/18/12/18）与首 token 151646。§2.3 断言 a/c/d 会把它变成实测。
3. 14B 每格 104,464 B、固定 1188 B 是推导值（结构已被 5 个 7B 块逐字节验证；48 层/8 kv head/head_dim 128
   取自 GGUF 头），尚未由 14B 实测块确认。§2.3 断言 e/f 会确认或推翻它。
4. 14B 的 n_rot_k / n_rot_v 是否仍为 128 / 64（推导依据 llama-kv-cache.cpp:333-358 与 head_dim=128；未实测）。
5. "7B 四格 KV 全在 GPU"只有源码链推导（§5.1），没有落盘日志或 VRAM 计量。
6. 7B 的 B57 基线只在 648e7244 / 3d02c1f8 上跑过，现役 3a726dbd 上未复跑。
7. E10-NEXT2.md 里没有 14B 条目（我 grep "14B" 在 3194 行台账里零命中）；本轮不动台账。

---

## 附录 A：零引擎块头解析器（只读，不加载模型）

用途：不开引擎就能核 cells、首 token、n_layer、n_rot_k/n_rot_v、k/v 类型与行宽，以及 size 是否自洽。
我在 home / project / habit / project_paraphrase18 / blk_G_bos_c18 五个 7B 文件上跑过：解析正好消费到文件末尾（零剩余）。

    import struct, hashlib
    def parse(path):
        raw = open(path, "rb").read()
        magic, ver, n = struct.unpack_from("<3I", raw, 0)
        off = 12
        toks = struct.unpack_from("<%di" % n, raw, off); off += 4 * n
        n_stream, = struct.unpack_from("<I", raw, off); off += 4
        info = {"magic": hex(magic), "version": ver, "n_tokens": n, "first_token": toks[0],
                "n_stream": n_stream, "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}
        for s in range(n_stream):
            cell, = struct.unpack_from("<I", raw, off); off += 4
            info["cell_count"] = cell
            if cell == 0:
                continue
            for i in range(cell):
                pos, nseq = struct.unpack_from("<Ii", raw, off); off += 8 + 4 * nseq
            vt, nl, nrk, nrv = struct.unpack_from("<4I", raw, off); off += 16
            info.update({"v_trans": vt, "n_layer": nl, "n_rot_k": nrk, "n_rot_v": nrv})
            if vt != 0:
                raise SystemExit("v_trans != 0 的分支在 7B 块上没出现过，遇到先报告")
            for il in range(nl):
                kt, = struct.unpack_from("<i", raw, off); off += 4
                kr, = struct.unpack_from("<Q", raw, off); off += 8
                if il == 0:
                    info.update({"k_type": kt, "k_row": kr})
                off += cell * kr
            for il in range(nl):
                tv, = struct.unpack_from("<i", raw, off); off += 4
                vr, = struct.unpack_from("<Q", raw, off); off += 8
                if il == 0:
                    info.update({"v_type": tv, "v_row": vr})
                off += cell * vr
        info["consumed"] = off
        info["complete"] = (off == len(raw))
        return info

判读规则：
- 7B 块：n_layer=28、k_row=v_row=544、size == 708 + 30480*n
- 14B 块：n_layer=48、k_row=v_row=1088、size == 1188 + 104464*n
- complete 必须为 True；否则文件被截断或格式变了
- first_token 与 7B 相同（151646）才允许说"BOS 口径未变"

---

（规格书完。任何一条与实测冲突，以实测为准，并把冲突报到 lead；不许改断言迁就产物。）
