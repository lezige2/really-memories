# M4 验收定稿（lead · 2026-10-25 19:05 本地）

> 承接：`PROGRESS §6.3` 九项 acceptance（L855-872）、`§6.6` M4-C、`§6.7` 未闭项（2 个编号 + 1 条口径注记）；判据原文 `kvmem/m2_visibility/mine/inspector/M4-ACCEPT.md`（**`2616b4daaf7becc5`** / 28,751 B；原文 `c4186107246dd35d` + §11 修订，§11 首版为中间版 `14275e378450a9d4`）。
> 复算：`kvmem/m2_visibility/m4/run_m4_accept_recompute.json` = **`0b865a97ac2a0a99`**（只读、零 GPU、零新锚）。
> 独立复核：`docs/_work/INSPECTOR-M4-ACCEPT.md` = **`96bc3fc64ddff139`**（初版 `cc029fc23dabd488`；§8 追加两条自我更正：G8 撤回、放行条件 1 降为部分覆盖）。
> 前置：M4-C 已于 17:40 结项（`docs/_work/M4C-CLOSURE-lead.md` `3309fb25cbd057f9`）⇒ 九项的挂起条件消失。

---

## 0 一句话

**M4 端到端链路成立：锚里 `acceptance` 17/17 全 true，我逐项落回字段/文件，两翼（复算 + 独立复核）同结论。**
但**"九项字面全真"不可签**——九项里 **7/9 字面通过**，剩下两项（第 7、8）不是缺证据，是**台账数错/措辞压缩**：`memory_source` 实为 **5 行**（fanout 和才是 7）、"新进程检索作答 9/9"实为 **2/2 问答**（"9/9"原意是"九项验收全过"）。这两条已落进 `M4-ACCEPT.md §11`：第 7 项 **改对象**（读数定义：行数 → 行数 + fanout 和，落在 §13.3 三选一内）；第 8 项是**误读更正、非判据变更**（读数对象没变）。原文 §0–§10 一字未改。
⇒ **M4 验收定稿 = 通过**（附 §5 的不能签清单）。

## 1 身份

| 项 | 值 |
|---|---|
| 验收锚 | `run_m4_verify_a4.json` = **`59edbd82d4b9ae44`** / 17,332 B |
| 产品块 | `blocks/blk_conv_2026-10-25_01.kvmem` = **`81127d24fd64b96b`** / **9,507,412 B**（尺寸公式 ⇒ 91 cells，自洽） |
| 记忆库 | `m4_memory.db` = `fd244c80c0cc974d` / 86,016 B · 写入锚 `run_m4_write.json` = `6408d8e2ecdf6ee5` / 13,402 B |
| 复算产物 | `run_m4_accept_recompute.json` = `0b865a97ac2a0a99` / 21,644 B / exit 0 / 九项 7/9 / `readonly{gpu:false,model:false,new_anchor:false}` |
| 独立复核 | `INSPECTOR-M4-ACCEPT.md` = **`96bc3fc64ddff139`** / 18,226 B（§1–§7 未改，§8 追加两条自我更正；初版 `cc029fc23dabd488` / 15,722 B） |
| 判据原文 | `M4-ACCEPT.md` 收回工作区：原件 `c4186107246dd35d`（25,038 B）+ §11 修订（§11 首版 `14275e378450a9d4` / 27,988 B 为中间版）⇒ 现 **`2616b4daaf7becc5`** / 28,751 B；`m4/README.md` 亦收回 `3ed45808788c745e` |
| 旁证 | `run_m4_ablate_plate_a7.json` `77e11a04aacd24c5`（四臂 91/91/79/91）· `run_m4_outfilter_selftest.json` `a85ec0df2bfa3cd3` / 3,856 B（S2 关 filter ⇒ 红） |

## 2 九项复算（两翼独立，结论一致）

| # | 断言 | 期望 | 复算 | 独立复核 | 判 |
|---:|---|---|---|---|---|
| 1 | 真实对话轮数 | 9 | 9（`judge.sample` 9 / block_text 9 行 / turn max 9） | 9 | ✅ |
| 2 | 判定句数 | 10 | 10（`per_sentence` 10，keep/drop 无留白） | 10 | ✅ |
| 3 | keep 条数 | 6 | 6（`judge.keeps`=6、DB memory=6；`dedupe.keeps=7` 是插入尝试数，不是 keep） | 6 | ✅ |
| 4 | 块数 / cells | 1 / 91 | 1 / 91（a4 + DB + 字节公式三源） | 同 | ✅ |
| 5 | 落位 / `pos_max` | `[4005,4096)` / 4095 | 同（attach 侧重放位置；块文件内仍是 0/90） | 同 | ✅ |
| 6 | memory 行数 | 6（含 `2026-10-28`） | 6；anchored 仅 1 行（「计划」） | 同 | ✅ |
| 7 | `memory_source` 行数 | **7** | **5**（fanout `[1,1,2,1,2]`，和 = 7） | **5** | ❌（口径过时，已改 R1） |
| 8 | 新进程检索作答 | **9/9** | **2/2 检索 + 2/2 作答**；`acceptance` **17/17** 全 true | **2/2** | ❌（措辞误读，已改 R2） |
| 9 | 锚 | `59edbd82d4b9ae44` | 同 + 块 sha/bytes 同 | 同 | ✅ |

**第 7 项定性**：7 是 **R9 去重前**的行数（1 段级 + 6 条单元）；放行条件 3 落地后 `memory_source` 加 `UNIQUE(text)`+`fanout`，unit3=unit4、unit6=unit7 合并 ⇒ 5 行；"7" 仍存在，变成了 **fanout 和**。**不是回退，是口径变了**。
**第 8 项定性**：`m4_verify.py: QUESTIONS` 恒为 2 问 ⇒ 锚里只有 2 问 2 答；README 原句「新进程检索到该块、另两个新进程逐字答出住址与车牌。**9/9 验收项全过**」——"9/9" 指九项验收，不是 9 个问答。**字面 9/9 无原件**。

## 3 放行条件三条 + `F-M4-1` + 遗留缺口（均不阻塞九项成立性）

| 项 | 现状 | 判 |
|---|---|---|
| O1 放行条件 1（`</think` + 重复句） | 标签侧**已闭**（白名单、块正文 REFUSE、`delivered_has_tag=0`、计数进 json、会红的断言 S2 关 filter ⇒ `ControlTagLeft`、块正文 raw 不动）；**重复句处置未做**（`answer_display` 仍同句两遍、`content_warnings=[]`、`first_sentence_only()` 在而 `derive(first_sentence=False)` 未启用、未计数） | **部分覆盖** |
| O2 放行条件 2（改"支持性观察"+车牌对照） | a7 四臂 **91/91/79/91** → 浙B-3F19K / 浙B-3F19K / 苏A12345(编造) / 浙Q-00000；`same_position/same_question/encoding_path_controlled=true`；版本链 a5（3 臂）在 | **已被覆盖**（`length_confound_note` 仍须同引，未静默升级为 A/B 证实） |
| O3 放行条件 3（R9 去重 + fanout + `type/resolved`） | `memory_source` 5 行 / `unique_units=4` / `fanout_sum=6`；`memory.type` 全有值；a4 `9_units_deduped_by_text`/`10_type_and_resolved` = true | **已被覆盖**（也是第 7 项 7→5 的原因） |
| `F-M4-1`（`n_predict`） | **仍未闭**：`write`/`a4` 无该字段；a7 只有"声明 64 / `engine_reports_n_predict=null` / `consistent=null`" | **未闭，不阻塞 M4 验收**（九项读数不依赖生成长度），但**阻塞任何"n_predict 生效"断言** |
| G-anchored | `anchored_time` 不在检索单元文本里（4 条单元均不含 `2026-10-28`）⇒ 问"2026-10-28 有什么安排"命中不了 | **仍缺**（M4-ACCEPT §3-① 建议未落地；不影响九项） |

## 4 判据口径（必须随读数一起引）

1. **键数 16 → 17**：a4 `acceptance` 是 **17 键**（多 `output_layer_clean`）；16 键版是 `run_m4_verify.json` `857f13c5`。`§6.3`/`§6.7` 两处一并改。
2. **第 5 项标签**：`[4005,4096)` / 4095 是 **ask 前重放位置**；save 后块在 `[0,90]`（DB `pos_lo/pos_hi`、`position0_owner='seq1'`）。两处不同源，引用必须点名。
3. **"九项" ≠ 9 个独立性质**：③↔⑥ 按构造相等、④↔⑤ 同源、⑧与 B 套 4/5 是同一动作、⑨ 是锚 ⇒ **独立性质约 6 族**。可写"九项字段全真（6 族独立性质）"，**不可写"9 个独立性质全真"**。
4. **`dedupe.keeps=7` ≠ `judge.keeps=6`**：前者是去重测试第二轮插入尝试数，不是矛盾。
5. **B 套 pid 是版本内瞬时值**：只能断言"新进程 / `child_of` 关系"，不许沿用具体 pid。

## 5 四态

| 项 | 判 | 依据 |
|---|---|---|
| M4 验收定稿 | **通过** | 锚 `acceptance` 17/17 全 true；九项 7/9 字面 + 2 项台账修正（R1/R2 已落）；未闭项（`F-M4-1` 未闭等，见 §3）均不阻塞 |
| "九项字面全真" | **不可签** | 第 7、8 项字面为 7 / 9-9，实测 5 / 2-2；改数后可签 |
| "9 个独立性质全真" | **不可签** | 独立性质约 6 族（§4.3） |
| "未闭项清零" | **不可签** | `F-M4-1` 未闭、G-anchored 仍缺、O1 重复句处置仍缺 |

## 6 缺陷 / 缺口

- **G8 撤回**（审计初版判断有误，见 `INSPECTOR-M4-ACCEPT.md §8 C1`）：`after_len` 是「标签删除后、空行**未**折叠」的中间量（`outfilter.py:80-99`，注释原文 "the display layer also collapses blank runs -- keep those two apart"），`display_len` 是 stage-2 折叠后（`m4_display.py:55-67`）；45 vs 44 之差 = 标签 8 + 空行合并 1 = 9，与 `removed_chars/delta` 自洽，`assert_diff_explained` 明确允许连续空行合并 ⇒ **不是矛盾，不作缺陷**。**禁止**据此把 `after_len` 改成 44/23（会改坏正确中间量）；若在意，只可记「字段未带 stage 标签」的可读性注记。
- **G-anchor**：`anchors_history.json` 缺 `bdf392e8` 条目（全仓 grep = 0）；`chat.db` 末条 `5909b978` ≠ 现 `237d8e1f` ⇒ 已在 `M4-ACCEPT.md §11 R4` 长期注记。
- **G-doc**：`M4-ACCEPT.md` 与 `m4/README.md` 此前**只存在于备份目录**，工作区没有 ⇒ 已收回（原 sha `c4186107` / `3ed45808`）。同类风险：`mine/inspector/` 其余 accept 文档也在备份，**未收**（记待办，不阻塞）。
- **O1 残留**：重复句处置未做、未计数。

## 7 下一步

1. PROGRESS 同步（本节同批）：§6.3 表（第 7 项 5+fanout、第 8 项 2/2、17 键、状态改「已验收」）、§6.6/§6.7、§12.1 M4 行与 F-M4-1 行、§13.1 四项动作、§13.2 标题、L147 表项。
2. `F-M4-1` 单独立项（引擎 `n_predict` 是否暴露），`G-anchored` 归 M4 遗留。
3. 按 §13.1：**M2 规划器 / M1.8 三处 judge 冲突**。

## 8 签署

| 项 | 内容 |
|---|---|
| 签署人 | lead |
| 签署 | **M4 = 已验收**（2026-10-25）；端到端链路成立（17/17）；九项字面 7/9 + 2 项台账修正（R1 **改对象** / R2 **误读更正·非判据变更**） |
| 未签 | "九项字面全真" · "9 个独立性质全真" · "未闭项清零" · 任何"n_predict 生效" · 放行条件 1「全闭」 |
| 可复算 | 九项 ⇐ `run_m4_accept_recompute.json` `0b865a97ac2a0a99`；独立复核 ⇐ `INSPECTOR-M4-ACCEPT.md` `96bc3fc64ddff139`；判据 ⇐ `M4-ACCEPT.md` **`2616b4daaf7becc5`**（原文 `c4186107246dd35d` + §11） |