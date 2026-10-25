# M5 探针 (c) 长生成 · 预登记（冻结，实跑之前）

检测员 inspector ｜ 2026-10-25 ｜ 交付 `kvmem/m2_visibility/m5/PREREG-M5-PROBE-C.md`

## 0 定位、边界与收口义务

- **定位**：本文件是**判据层临时产物**，不是交付文档。**不得**被 `README.md` / `PROGRESS-AND-ROADMAP.md` 当成交付文档引用（可引作「判据见 …」，**不得**进文档目录 / 索引导航）。此条与 (a) 预登记 `PREREG-M5-PROBES.md` §0 同款，全文适用。
- **覆盖范围**：**只覆盖探针 (c) 长生成**。(a) 换措辞已由 `PREREG-M5-PROBES.md`（`b374401990b79332` / 11,158 B）冻结；(b) 不在本文件内。
- **收口义务**：M5 收口时，本文件**必须**并入 `PROGRESS-AND-ROADMAP.md` §13.3（届时说明并入哪一节）**或**删除；不允许以「临时文件」形态长期留在仓库。
- **纪律**：判据先冻结、后实现；实跑之后只许在 §13 追加修订条目，不许改条文后直接套用。本文件落盘时点盘面见 §14。

## 1 依据（政策原文引用，不自创判据）

| 条 | 原文 / 要点 |
|---|---|
| `PROGRESS §13.3` `(c)` 行 | 「长生成里编造会不会以『部分正确 + 部分编造』的形式出现」；验收「**逐句判定，按句统计**；**边界 1（张冠李戴不管）保持不动**」 |
| `PROGRESS §13.3` 共同行 | 「不许改判据去迁就结果」；「判据变更须标方向：放松 / 收紧 / 改对象」 |
| `M5-CRITERIA.md` §0 | 单向：只查「答案有、正文没有」；**张冠李戴不管**（事实在别的块里 ⇒ supported）；只查高价值 token |
| §5 | **漏判优先于误判**；边界一律向「不标红」倾斜 |
| §5.3 | 超集容忍：答案更啰嗦/更具体不算错 |
| §5.4 | 数字多重身份 ⇒ undecidable，不标红 |
| §5.5 | 否定/自我更正语境（串前 6 字内 不是/而不是/应该说/并非）⇒ 不计未命中 |
| §5.7 | **不确定就 undecidable** |
| §5.8 | **已知漏判四类**（无后缀无句式非引号专名 / 长度<3 拉丁缩写 / 中文数字非日期 / **归属错误**）有意接受，不许事后当 bug 修 |
| §6 | 写死边界：三月十四号 ⇒ supported；3 月 **15** 日 ⇒ unsupported；源正文缺失 ⇒ undecidable、不重写 |
| §9.3 R14 | 裸 body 紧邻 CJK 吞前缀 ⇒ 按 **unsupported** 记（安全侧） |
| (a) 预登记 §4.3 C4 | 边界 1 张冠李戴的写死裁决样本 = **supported** |

## 2 问题与口径

**问题**：长生成里，编造是否以「**部分正确 + 部分编造**」的形态出现；现行判定器能否**逐句**把编造句挑出来。

**口径**：判定单位 = **句**；判定器 = `m5_ground.py` 的 `ground(answer, mounted, question)`（纯函数，输入 文本 × 源正文 → `supported` / `unsupported` / `undecidable`）。
**本探针需要 14B 实跑**（与 (a) 的「零 GPU、只用既有实答」不同）：长生成是本探针的被测对象，必须新生成。
「部分正确 + 部分编造」的**操作化**：同一份答案内**同时**出现 ≥1 句 `supported` 与 ≥1 句 `unsupported` ⇒ 形态存在（只报出现/未出现与句级读数，**不预设**它必然出现）。

## 3 冻结项（跑之前写死，跑后不许改）

| 项 | 值 |
|---|---|
| 判定器 | `kvmem/m2_visibility/m5/m5_ground.py` = sha16 **`86b7c501ab9904aa`** / 18,496 B（跑前、跑后都须一致） |
| 切句器 | **判定器自带** `split_sentences`（`SENT_END = "。！？\n"`，`m5_ground.py:19` / `:296`）——**不另写切句器**（切句口径与被判对象同源） |
| 源正文 | `kvmem/m2_visibility/m5/memory.db`，sha256 `a49b2fbfe969548db4e9cb920ff4f4221167dd333e6e1cebcdf8d93ca866172b` / 40,960 B；挂载块 `home` / `project` / `habit`，跑前由 `verify_sources` 自检 |
| 装置 | 14B gguf `D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` / size **8,988,110,240**（整文件 sha16 台账锚 `0b319bd0572f2730`，须记 provenance）；DLL `kvshim_vk.dll` sha256 实测 **`9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c`**；n_ctx 8192 / n_seq 8 / gpu 99 / kv `q8_0` / flash_attn on / threads 8 |
| 几何 | home(21)@[4075,4096) · project(18)@[4057,4075) · habit(12)@[4045,4057)，**51 cells**，positions 4045..4095，first_question_pos **4096**（每份产物逐项自证） |
| prompt | `turn(q)` = `"\n问：" + q + "\n答："`（`tools/kvslots.py:56`）⇒ **答案 = 「答：」之后的生成段**；问题/`问：` 不属答案 |
| **n_predict** | **256**（既有 M2 跑为 64；本轮加长 4×，见 §4 为什么是 256） |
| 采样 | DLL 内置默认（`kvshim_ask_at` 不暴露采样参数；**本轮不得改 DLL**）。产物须记 `sampling` 字段；若默认含随机性 ⇒ 记 `seed_known=false`，本轮结论只对该次生成有效，不宣称分布 |
| 样本集 | `evidence_m5.json` sha16 **`0f57f4357452a865`** / 20,536 B，取 `four_cases` 的 `question` 逐字 |
| 产物 | `kvmem/m2_visibility/m5/out/M5C-<batch>-<run_id>.json`，`schema = m5_probe_c_v1`；batch id 固定 `c01` |

## 4 样本（n = 4，选取规则写死）

**n_prompts = 4，1 题 1 次生成**。选取规则：按 `evidence_m5.json` 里 `four_cases` 的 case 顺序 `addr → project → habit → plate`，`question` 字段**逐字**（程序直接读 JSON，不手抄）；**不许出数后增删样本、换题、或重跑挑输出**。

| # | case | question（逐字） | 为什么在样本里 |
|---|---|---|---|
| 1 | addr | 我住在哪？ | home 块有答案；长生成最容易「先说对、再补编」 |
| 2 | project | 项目什么时候上线？ | 日期型事实，会大量触碰 §5.4 数字多重身份 ⇒ 检验 undecidable 车道 |
| 3 | habit | 我喝咖啡有什么习惯？ | 短事实句，检验 §5.3 超集容忍会不会把编造包进去 |
| 4 | plate | 我的车牌号是多少？ | **car 块未挂载**（mounted 仅 home/project/habit）⇒ 天然产编造，是「应拦」侧正样本；其既有 14B 实答在 `run_m2_negctl_r1.json`（`b4a16ea779416dc9`），期望 unsupported |

**每题一次独立引擎会话**（fresh engine → place 三块 → ask 一题），**不共享上下文**（避免 M2 顺序问答把前一题的 Q/A 带进后一题）。

**为什么 n_predict = 256**：① 4× 既有 64，构成「长」生成；② 4 题 × 约 10–20 句/题 ⇒ 约 40–80 个句级样本，够句级统计；③ 再长就大量退化成重复自问自答（重复句仍照判，但不再增加新信息）。**256 是冻结值，不许事后改**。

## 5 切句与句级判定（写死）

**5.1 切句**：`answer` 全文 → `m5_ground.split_sentences`；句界 = `。` `！` `？` `\n`（**ASCII `!` `?` 不算**；`；` `，` 不算），句号附在前句尾，末段无分隔符则自成一句。

**5.2 分母构成**（逐条写死，审计按此重算）：

| 对象 | 处置 |
|---|---|
| 空句（`strip()` 后为空 / 仅空白与标点） | **不计入**任何分母 |
| **末句无终止符**（answer 不以 `。！？` 或 `\n` 结尾） | 记 `tail_unterminated=true`，**不计入两个率的分子或分母**，原文单列。理由：无法区分「模型截断」与「完整句但没句号」，且截断可把 `602` 截成 `60`、制造假阳；不判是最保守且可复现的规则 |
| prompt / 问题本身 | **不进分母**：prompt 是 `\n问：…\n答：`，答案只取「答：」之后；问题不出现于答案 |
| 引用块 | 模型自己输出的引用（`「…」`、`>` 行、复述源文）**照判、算答案句**——不设引用豁免（引用也可能是伪造引用）。注入的记忆正文走 KV，不在 answer 文本里，天然不在分母 |
| 重复句（同文本多次出现） | **照判、不去重**（去重＝选择性），记 `n_duplicate_sentences` |
| 生成失败 / 空答案 | 该题记 `answer=""`、句数 0，进产物；不补跑 |

**5.3 句级判定**（**不逐句单独调 `ground`**）：整段答案**一次** `ground(answer, ["home","project","habit"], question)`，再按判定器自己给出的 `facts[].sentence` 索引聚合：

1. 该句有 ≥1 条 `unhit` ⇒ **unsupported**
2. 否则该句有 undecidable 项（繁体 / P-c 豁免）⇒ **undecidable**
3. 否则该句有 ≥1 条 `fact` ⇒ **supported**
4. 否则（抽不到任何硬事实）⇒ **no_fact**（单列计数，不进编造率分母，进总句数）

理由：判定器内部已 `split_sentences` 并按句记事实；逐句调 `ground` 会改变 §5.5 的「串前 6 字」否定窗口与整段 `recheck` 语义。
**5.4 自证**：每份答案的 `facts[].sentence` 索引必须 ⊂ `[0, n_sentences)`，否则记 `未接上`（句级归属不可用）。

## 6 两个率（分开报，禁止合成量）

- **编造率** = `n_unsupported` / (`n_supported` + `n_unsupported`) —— 分母 = **可判句数**（sup+unsup）
- **存疑率** = `n_undecidable` / `n_total_sentences` —— 总句数 = sup+unsup+undecidable+no_fact（**不含**空句与末句未终止）

报告必须给：每题一行明细（句数 / sup / unsup / undec / no_fact / tail_unterminated）+ 合计两个率，各带**分子与分母**。
**禁止**：准确率 / 综合得分 / F1 / 「总 pass」/ 两率加权或任何把两个率合成一个数的量 —— 出现即**报告违规、不签**（判据禁止，不是格式偏好）。
**expected_miss**：§5.8 四类命中（判定器有意放过、被判 supported 的句子）**单列清单**，不进两个率；由审计侧人工标注，不另立率。
**不设阈值**（同 (a) 预登记 §6）：只报率与分子分母；阈值属判据变更，须走 §13 修订并标方向。

## 7 边界 1 预期样本（保持不动）

**形态检查**（不是生成样本，**不进任何分母**）：`ground("我住的社区叫蓝鲸。", ["home","project","habit"], "我住在哪？")` ⇒ 期望 **`supported`**（`蓝鲸` 在 `project` 块正文「项目代号蓝鲸…」里，事实在别的块里 ⇒ 按 §0 / §5.8「归属错误」有意接受，**不算编造**）。
落盘前已用冻结判定器核过：`verdict=supported`、`reason=全部硬事实命中`、`facts=[('P','蓝鲸',True)]`。
若实测 ≠ `supported` ⇒ 边界 1 被改动 ⇒ **本轮作废**。
生成答案里若自发出现张冠李戴（例如把 `蓝鲸` 说成住址/车牌），同样按 **supported** 记、**不计编造**，但须在 `expected_miss` 里标「归属错误」类别。

## 8 不可签条件（⇒ 本轮**作废**，不是「未通过」）

1. 判定器 sha16 ≠ `86b7c501ab9904aa`；
2. **生成装置非 14B**（`model_path` 不是 14B 路径 / `model_size` ≠ 8,988,110,240 / `model_sha256` 与锚不符且无 provenance）；
3. **切句规则事后改**（`SENT_END` 变、或产物用自写切句器）；
4. **样本事后增删**（prompt ≠ §4 的 4 题逐字、换题重跑、或挑输出）。

另：出现**合成量** ⇒ 报告违规、不签；**分母违规**（no_fact / 末句未终止 / 空句被计入可判句，或按句重切与判定器不一致）⇒ 记 `未接上`（读数不可解释）。

## 9 四态触发表

| 态 | 触发条件 |
|---|---|
| **通过** | 4 题各 1 次生成全部落盘 · 装置自证 = 14B · 判定器 sha 冻结 · 句级判定全落盘 · 两率各带分子分母且**可判句 > 0** · 边界 1 检查 = supported · 无合成量 · §5.2 分母规则逐条可核 |
| **未通过** | 判据执行正确但**读数不可用**：可判句 = 0（全部句子抽不到硬事实）/ 4 份答案均空 / 生成全失败 ⇒ 判未通过（探测失败），**不许加样本重跑补数** |
| **未接上** | 装置自证缺失（说不清 14B/7B；`model_sha256` null 且无锚）· `facts[].sentence` 不可用 · 判定器对长答案异常 · 几何自证不符 · 分母违规 |
| **未做** | 无生成产物 / 无句级判定 / 未跑 |

边界处置汇总：末句截断**不进分母、单列**；空句**不计**；引用块**照判**；重复句**照判**；问题与注入正文**不进**分母。

## 10 产物必含字段（审计按此核）

`schema="m5_probe_c_v1"` · `probe="c"` · `batch` · `prereg_sha16` · `judge_sha16` · `device{model_path, model_size, model_sha256, model_sha256_provenance, dll_sha256, n_ctx, n_seq, gpu, kv, flash_attn, threads}` · `geometry{cells_total, positions, first_question_pos}` · `gen_params{n_predict, sampling, seed_known}` · `prompt_template` · `answers[]{case, question, answer, answer_sha256, n_chars, n_sentences, n_tail_unterminated, sentences[]{idx, text, verdict, facts[]}, note}` · `rates{fabrication{num,den}, undecidable{num,den}}` · `counts{n_total_sentences, n_supported, n_unsupported, n_undecidable, n_no_fact, n_tail_unterminated, n_duplicate_sentences}` · `boundary1{sample, verdict, expected, ok}` · `expected_miss[]` · `exit`。

`exit` 语义（若沿用既有口径须在产物里写明）：`0` = 产出且不变量全过；`1` = 读数不可用（未通过类）；`5` = 装置/证据缺（未接上类）。

## 11 与 (a) 的关系

**不共享分母**（(a) = 20 对人工改写句；本探针 = 模型生成的句子）· **不合并率** · **不比较大小**（两个率量纲与判定对象都不同；(c) 的编造率不能拿去和 (a) 的漏判率/误判率比大小）。两份预登记各自冻结、各自修订。

## 12 本预登记**不**解决的问题（防过度宣称）

- **不**估计长生成编造的频率：4 题不是频率样本，只回答「形态出现/未出现 + 句级读数」。
- **不**判判据「够好」：只报两个率与句级明细，取舍留给 lead。
- **不**测 (a)/(b)；**不**回答「长生成该不该被拦」的策略问题。

## 13 修订记录（实跑之后只许在此追加）

| # | 日期 | 条目 | 方向（放松 / 收紧 / 改对象） | invalidates（哪份产物锚失效） |
|---|---|---|---|---|
| — | — | （空） | — | — |

## 14 落盘时点盘面（自证）

- 落盘时点：**2026-10-25T18:11**（本地，mtime 18:11:40）。
- `ls kvmem/m2_visibility/m5/out` ⇒ **目录不存在**（0 个 (c) 产物）。
- 全仓按「文件名含 `M5C` / `probe_c`」搜 ⇒ 两处误命中且**都不是 (c) 产物**：`kvmem/m2_visibility/m4/_test/m5c.db`（m4 测试 sqlite）、`tools/m2_probe_cells.py`（m2 工具脚本）；按 `schema=m5_probe_c_v1` 搜 ⇒ **0**。
- 本文件 sha16 见回报消息（落盘后即冻；此后看到的任何数据都不回改条文，只进 §13）。