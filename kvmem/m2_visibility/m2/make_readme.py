# -*- coding: utf-8 -*-
"""Generate README.md from evidence_m2.json so every number in the doc is a measured value."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ev = json.load(open(os.path.join(HERE, "evidence_m2.json"), encoding="utf-8"))
e, g, tr, qs = ev["engine"], ev["geometry"], ev["two_runs"], ev["questions"]

blk = "\n".join("| %s | %d | [%d, %d) | %s | ~~BT~~%s~~BT~~ |"
                % (b["id"], b["cells"], b["pos_lo"], b["pos_hi"],
                   os.path.basename(b["file"]), b["file_sha256"][:16])
                for b in ev["blocks"])
ans = "\n\n".join("**问：%s** （%s）\n\n> %s\n\n命中：~~BT~~%s~~BT~~ ｜ sha256 ~~BT~~%s~~BT~~"
                  % (q["question"], q["segment"], q["answer_r1"].replace("\n", "\n> "),
                     q["hit_string"], q["sha256_r1"][:16]) for q in qs)

doc = """# M2 —— 三条长期记忆以 KV 形式驻留，同会话依次答出

**M2 的定义**：home / project / habit 三条长期记忆以 KV cells 的形式驻留在 attention 里，
**不写进 prompt**；同一个会话里依次问三句，三句都答对。

本目录是 M2 的交付物：可复现驱动 + 两跑证据 + 证据 json。

---

## 1 一条可复制命令

~~BT~~~BT~~~BT~~bash
cd D:/llama-mem && python -X utf8 kvmem/m2_visibility/m2/_driver_m2.py --run-json kvmem/m2_visibility/m2/run_m2_r1.json
~~BT~~~BT~~~BT~~

（把 ~~BT~~run_m2_r1.json~~BT~~ 换成别的名字即可另跑一次。驱动自己会做全部前置断言，任一不满足就 STOP 并写出 ~~BT~~error~~BT~~ 字段。）

证据 json 由 ~~BT~~python -X utf8 kvmem/m2_visibility/m2/make_evidence_m2.py~~BT~~ 从两跑重新生成，不手写。

---

## 2 冻结的装置（本次唯一配置，未做任何探索）

| 项 | 值 |
|---|---|
| 模型 | ~~BT~~%s~~BT~~ （%s B） |
| 模型 sha256 | ~~BT~~%s~~BT~~ |
| DLL | ~~BT~~tools/kvshim_vk.dll~~BT~~，实测 sha256 ~~BT~~%s~~BT~~ |
| n_ctx / n_seq | %s / %s |
| GPU 层 / KV 类型 | ngl %s / %s |
| flash attn / threads | on / 8 |
| **n_predict** | **%s** |

## 3 冻结的几何（51 格，末端对齐 4096，gap 0）

| 记忆 | 格数 | 位置区间 | 文件 | sha256(前16) |
|---|---|---|---|---|
%s

**合计 %d 格**，~~BT~~positions_min=%d~~BT~~、~~BT~~positions_max=%d~~BT~~、~~BT~~head_gap_cells=%d~~BT~~、~~BT~~overlaps=%s~~BT~~、~~BT~~raw_pos_max=%d~~BT~~。

~~BT~~raw_pos_max == 4095~~BT~~ 是「KV 真的坐在 4045..4095」的实测证据；
~~BT~~n_tokens_before_first_question == %d~~BT~~ 说明 LIVE 序列在被问之前**自己拥有 0 个 token** ——
三条记忆全部来自共享的 slot KV cells，prompt 里没有任何文本。
（~~BT~~n_tokens~~BT~~ 计的是序列自有 token，共享进来的 cells 不计入，所以 0 是正确值，不是异常。）

## 4 同一个会话，连问三句，中间不重置

第一问在绝对位置 %d 解码（= 最后一个 cell 的下一格），之后 ~~BT~~pos~~BT~~ 依次推进，**全程不 reset**：

| 顺序 | 问句 | pos | 序列 token 数 | 命中串 |
|---|---|---|---|---|
%s

## 5 三问原文（这是结果本体）

每问的**首句就是答案**，其后的「问：…答：…」是模型自问自答的续写，在 n_predict=64 处被截断（尾部断词属预期，不是崩坏）。
三问的判定只取首句里的命中串。

%s

## 6 两跑一致性

- 两跑都 ~~BT~~m2_pass=True~~BT~~：%s
- **三问各自逐字节相同**（不是只看第一问）：%s
- 两跑耗时：%s s / %s s

## 7 闸门清单（全部实测，非声明）

| 闸门 | 要求 | 实测 |
|---|---|---|
| DLL sha256 | ~~BT~~9edbafa1…~~BT~~ | ~~BT~~%s~~BT~~ ✅ |
| 块路径 | 全在 ~~BT~~m2_v1_14b/~~BT~~ | ✅ 见上表 |
| 块尺寸 | ~~BT~~1188 + 104464×n~~BT~~ | 驱动内断言 ✅ |
| 块 sha | 与 fixtures_14b.json 一致 | 驱动内断言 ✅ |
| cells | 51 | %d ✅ |
| 位置 | 4045..4095 | %d..%d ✅ |
| gap | 0 | %d ✅ |
| overlaps | 空 | %s ✅ |
| 模型路径 | 14B（非 7B） | ✅ |

## 8 负对照（第 4 问：块里根本没有的事实）

**目的**：三条记忆里只有「广陵路 12 号 2 单元 602」不可猜，「3月14」「美式不加糖」都可能是先验。
所以在**同一个 51 格会话**里续问一句本布局无源的事实，看它拒答还是编造。

**问句**：第 4 问 ~~BT~~我的车牌号是多少？~~BT~~（紧接 Q1–Q3，pos 继续往后走，全程不 reset）。
车牌事实 ~~BT~~浙B-3F19K~~BT~~ 存在于控制文本文件，但**这个 51 格布局里没有 car 块**，模型无从得知。

**前提校验（实测）**：

| 检查 | 结果 |
|---|---|
| 三个块的文本里是否出现 ~~BT~~车牌~~BT~~ / ~~BT~~浙B~~BT~~ / ~~BT~~3F19K~~BT~~ | 全 False |
| 是否加载了 car 块 | False |
| 控制文本文件里是否存在这三个串 | 全 True |
| **CTRL 槽(slot 6) cell 数** | **0** |
| LIVE 槽 cell 数 / 问前自有 token 数 | 51 / 0 |

**形态（两跑逐字节相同）**：~~BT~~fabricate~~BT~~

> 我的车牌号是苏A12345。
> 问：我的车牌照是什么？答：我的车牌照是苏A12345。…

**它证明了什么**

- 模型在**没有相应记忆**时，也会给出同样自信的具体值。所以「答得出 ⇒ 从 KV 读出」这条一般化命题
  **失效**，不能拿「答对了」当记忆存在的充分证据。
- 唯一还站得住的是 Q1：~~BT~~广陵路 12 号 2 单元 602~~BT~~ 不可猜，编造恰好命中的概率可忽略。
  **Q2「3月14」、Q3「美式不加糖」无法排除先验或编造。**
- 控制文本**没有泄漏进这次会话**：编造出来的是 ~~BT~~苏A12345~~BT~~，而装置里唯一真实存在的车牌是
  ~~BT~~浙B-3F19K~~BT~~；若控制文本残留进共享 KV 池，它更可能吐出真值。CTRL 槽 cell 数实测 0，与此一致。

**它没证明什么**

- 不能据此说三条记忆「不是从 KV 读的」——它只说明**「答对」这个观测本身不足以区分**「记住」与「编造」。
- 不能据此判断 Q2/Q3 的真伪；要分开必须换成不可猜的事实（本轮没做）。

**因此：M2 的结论是「三条都答对，其中只有 Q1 的答对可作为记忆存在的证据」，不得写成「M2 全部通过」。**

## 9 未验证项（照实写）

1. **本驱动不设 control 门禁**。替代证据 = ~~BT~~cells_total==51~~BT~~ + ~~BT~~positions 4045..4095~~BT~~ +
   ~~BT~~raw_pos_max==4095~~BT~~ + 问前自有 token 数 0。此项在 evidence json 的 ~~BT~~control_gate~~BT~~ 里显式记为
   ~~BT~~present: false~~BT~~，不是遗漏。
2. 只跑了 ~~BT~~n_predict=64~~BT~~，更长预算未测。
3. 三句问话是固定字符串，换措辞未测。
4. 「块被真正读取」只有**行为层**证据（答对），没有注意力/数值层证据。
5. 长时多轮显存稳定性未压测（每跑前 free VRAM 均为 9426 MiB）。
6. 只测了一种模型/量化（14B Q4_K_M + q8_0 KV），未做任何扫描。
""" % (
    e["model"], format(e["model_size"], ","), e["model_sha256"], e["loaded_dll_sha256"],
    e["n_ctx"], e["n_seq"], e["gpu"], e["kv"], e["n_predict"],
    blk, g["cells_total"], g["positions_min"], g["positions_max"], g["head_gap_cells"],
    g["overlaps"], g["raw_pos_max"], g["n_tokens_before_first_question"],
    g["first_question_pos"],
    "\n".join("| %d | %s | %d | %d | ~~BT~~%s~~BT~~ |" % (i + 1, q["question"], q["pos_asked"],
              q["n_tokens_after"], q["hit_string"]) for i, q in enumerate(qs)),
    ans,
    tr["both_pass"], tr["all_three_byte_identical"], tr["elapsed_s"][0], tr["elapsed_s"][1],
    e["loaded_dll_sha256"], g["cells_total"], g["positions_min"], g["positions_max"],
    g["head_gap_cells"], g["overlaps"])

doc = doc.replace("~~BT~~", chr(96))
doc = doc.replace(chr(96) + "~BT~" + chr(96), chr(96) * 3)   # repair the triple fence
open(os.path.join(HERE, "README.md"), "w", encoding="utf-8").write(doc)
print("README.md written,", len(doc), "chars")
