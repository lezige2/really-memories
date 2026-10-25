# FEATURES — 功能台账

> **一条规矩**：状态由**产物**支持，不由文档宣称。产物说了而文档没说 → 按产物记；文档说了而产物没有 → 记「未证」。
> **强度**：`R` 重算 / `C` 构造性覆盖 / `A` 锚定转录 / `S` 仅自述。**自报不许升格成重算。**
> **锚格式**：`文件名 = sha256 前 16 位`。**产物重跑 ⇒ 结论自动过期。**

---

## §0 一页总表（17 行）

| # | 功能 | 状态 | 锚 = sha16 | 强度 |
|---|---|---|---|---|
| 1 | M1 索引 | **部分实现** | `tools/chat.py` = 4c8d73e955c108ff · `tools/facet_index.py` = e410463a40ef459f | A |
| 2 | M1.8 三处 judge 冲突 | **未开始** | 无 | 无 |
| 3 | M2 规划器 | **未实现** | 无 | — |
| 4 | M2 完整（驱逐 / 多会话 / 位置租约） | **未实现** | 无 | — |
| 5 | M3 块生命周期 | **已实现** | `run_m3_lifecycle_50_v4.json` = ef3d1e8859add5b0 | **R** |
| 6 | M3 接入 chat.py（租约） | **部分实现** | `chat_lease/run_compare.json` = fd6333a45034e662 ⚠**不在仓库** | A |
| 7 | M4 写入固化 | **已实现·未验收** | `run_m4_verify_a4.json` = 59edbd82d4b9ae44 | **R** |
| 8 | M4-A 输出层过滤 | **已实现** | `run_m4_verify_a4.json` = 59edbd82d4b9ae44 · `run_m4_outfilter_selftest.json` = a85ec0df2bfa3cd3 | **R** |
| 9 | M4-B 车牌句消融 | **未证** | `run_m4_ablate_plate_a3.json` = 06a7dac53b399174 | A |
| 10 | M4-C leases 真调用 | **未开始** | 无 | 无 |
| 11 | M5 接地校验 | **部分实现** | `run_m5_grounded.json` = 007cb08b8f117ec5 · `run_m5_fix_compare.json` = 9eab963bdf977241 | A |
| 12 | `.kvmem` 落盘 + SQLite 指针 | **部分实现** | `blk_conv_2026-10-25_01.kvmem` = 81127d24fd64b96b · `m4_memory.db` = fd244c80c0cc974d ⚠**均不在仓库** | **R** |
| 13 | BM25 + facet 检索 | **已实现** | `tools/facet_index.py` = e410463a40ef459f · `tools/facet_budget.py` = f9290bf464166ee4 | A |
| 14 | 14B 路径与块格式 | **已实现** | `blk_conv_2026-10-25_01.kvmem` = 81127d24fd64b96b ⚠**不在仓库** | **R** |
| 15 | 7B 线 | **部分实现** | 无（产物已迁出）| — |
| 16 | 重编路径字节级复现 | **已实现** | `run_m4_ablate_plate_a3.json` = 06a7dac53b399174 | **R** |
| 17 | 输出层过滤的 D/E 探针 | **未开始** | — | — |

**⚠ = 锚不在仓库**：`.gitignore` 的 `*.json` 曾把全部 run 产物挡在仓库外，现已具名放行 18 个；
但块文件（`*.kvmem`）、DLL、`m4_memory.db`、7B 产物仍是排除项 —— **clone 的人拿不到这些文件，只能读到本文里的 16 位十六进制**。

---

## §1 已实现（能跑、有锚、有失败形态）

### 1.1 M3 块生命周期 —— attach / detach / pin / 只读
```
锚  m3/run_m3_lifecycle_50_v4.json = ef3d1e8859add5b0   82,784 B   attempt 4
    50 轮全部 valid，verdict 通过，failed []，secs 273.6
    answer_sha16 = 806a3410a856a23a（另一进程 attempt 2 同值 ⇒ 跨进程确定性）
强度 R  —— 检测员逐条复核：8 个锚 8/8 逐字节一致；五行分层全成立
分层  13 distinct claims / 端到端被验证 5 / 仅单元 8 / 端到端不可失败 8
      I 规则端到端变红 2：I3 由 redB path[2] 承载、I4 由 redA round 38 承载
```
**限制（引用时必须一起引）**：
- 8 条 `not_falsifiable_e2e` 的 `scope: within this driver only` —— **不是「永远不能红」**，是被 I3/I5/I6 先占位
- 两个红控在**两条不同路径**上变红：redB（块被清 ⇒ 91→91→0）、redA（跳过 detach ⇒ cells 142 = 91+51）。只红一条不足以证明两条规则都活着
- **单元注入证伪的「单因子」不可由产物复算** —— 产物没留注入前后输入对，只能记「各自被一次单元注入打红」
- **引擎不拒绝被引用块的 reset，租约只在 Python 侧** —— 这是 M3 的边界，不是缺陷

### 1.2 M4-A 输出层过滤 —— 控制标签不许出现在交付文本里
```
锚  m4/run_m4_verify_a4.json = 59edbd82d4b9ae44
    per_tag {'think': 1} / tag_chars_removed 8 / raw_to_delivered_delta 9
    mechanical_fields_with_a_tag_hit 2 / semantic_distinct_raw_strings_carrying_a_tag 2
    acceptance.output_layer_clean = True
强度 R —— 检测员 import outfilter，用真实 raw 串在内存里重跑：过滤开出 {'think':1}/45 字无标记；过滤关 assert_clean 抛 ControlTagLeft
```
**两个数必须一起报，禁止单写一个**：机械次数 = 承载字段 8（自报的「6」是错的，不对称去重）；语义次数 = 不同原始串 2。
**为什么会有这一格**：a2 的计数器在 display 层取数，而 display 已被 `m4_display` 洗过 —— **它数的是一个已经被洗干净的输入**，永远报 `per_tag {}` / `removed 0`。同一份 raw：a2 报 0、a3 报 1。

### 1.3 重编路径字节级复现产品块
```
锚  run_m4_ablate_plate_a3.json = 06a7dac53b399174
    arms[product_block_control].block_sha256   = 81127d24fd64b96bc86751cd2789abdf40c06cc111d0a977437f596b347334e6
    arms[reencoded_with_sentence].block_sha256 = 81127d24fd64b96bc86751cd2789abdf40c06cc111d0a977437f596b347334e6
强度 R —— 同一份原文走写入路径重编，产出与产品块逐字节相同 ⇒ 「来源」这个自变量被消灭
限制   单例（一个块、一次文本），非统计
```

### 1.4 M4 写入固化（十项 acceptance 全真，但**未验收**）
```
锚  run_m4_verify_a4.json = 59edbd82d4b9ae44
```
**「已实现」与「已验收」是两件事，这里必须分开写**：
```
已实现  M4 声明的那十项 acceptance 在 a4 里全真
未验收  A 绿 / B 未证 / C 未开始 —— 三项没全绿，这一行就不能算验收通过
```
**⚠ 不要引用旧的 `m4_memory.db` sha**：本文件先前见过的 `817a66e45a4e3594` **已被后续重跑覆盖**，磁盘现值是 `fd244c80c0cc974d`。**这就是「锚随重跑失效」的实例。**

---

## §2 部分实现

### 2.1 M1 索引 —— 查询侧在，建索引的产物不在
```
锚  tools/chat.py = 4c8d73e955c108ff（仓库内）  tools/facet_index.py = e410463a40ef459f（仓库内）
出处 chat.py:385  def _selection(con, q, k=2)
     chat.py:426  sel = _selection(con, q)
强度 A
限制 索引查询已在 chat 里被调用；**建索引的产物不在仓库**
```
> 附注：`mine/lead/BRIEF-M4.md:16` 引的 `tools/chat.py:379` **是空行**，真位置是 385 / 426。该文件是历史 brief，未改；以此处为准。

### 2.2 M3 接入 chat.py（租约）
```
锚  chat_lease/run_compare.json = fd6333a45034e662   ⚠ 不在仓库
强度 A
限制 回归唯一真判据是答案逐字节；文档自标「M3 最后一项未闭合项」
```

### 2.3 M5 接地校验
```
锚  run_m5_grounded.json = 007cb08b8f117ec5（41,083 B）  run_m5_fix_compare.json = 9eab963bdf977241（15,141 B）
强度 A
acceptance 11 项：9 个布尔全真 + false_positive 0 + false_negative 0
quadrants 四案例齐：a_wrong_province_same_body（'您的车牌是苏B-3F19K。'）等
限制 (a)/(c) 两探针仍未办
```
**M5 的边界（冻结，不许扩）**：只管「无中生有」，不管「张冠李戴」；**漏判优先于误判**。

### 2.4 `.kvmem` 落盘 + SQLite 指针
```
锚  blk_conv_2026-10-25_01.kvmem = 81127d24fd64b96b  9,507,412 B   ⚠ 不在仓库
    m4_memory.db = fd244c80c0cc974d  86,016 B                       ⚠ 不在仓库
强度 R
限制 指针表在，但**正文也入库** ⇒「SQLite 只存指针」这句不成立；两个锚复算的人拿不到
```

### 2.5 7B 线
产物已迁至 `kvmem/m2_7b/`，只剩报告与 runs 目录名。**端到端不可复算 —— 7B 结论一律不许引用。**

---

## §3 未实现 / 未开始（明确没做，不是「还没验证」）

| 功能 | 状态 | 为什么没做 / 什么条件下才有意义 |
|---|---|---|
| **M4-C** `leases` 真调用 | 未开始 | **M4 最大的洞**：「import 了但没调用」与「调用了但结果没人断言」是**同一类静默失效**。判据是「删掉它必须有断言变红」，不是「加上调用」 |
| **M1.8** 三处 judge 冲突 | 未开始 | 零补丁、零产物，只在旧文档挂着三句话 |
| **M2 规划器** | 未实现 | 全仓 grep `规划器|planner` 只命中 `session_state.py` 的 `planner_version` 布局字段 —— **几何冻结 ≠ 规划器实现** |
| **M2 完整** | 未实现 | pinned 驱逐查无 / 多序列单会话写死 / 位置租约未开 |
| **D/E 探针** | 未开始 | 见 §4.1 |

### 3.1 M5 为什么必须排在 M4 之后
M5 校验 M4 产出的答案与块正文。M4 的答案此前仍带 `</think`，块正文也还没做过接地消融 ——
**在一个被污染的数据上建校验器，它会先学会接受污染。** 顺序是 STATUS-REPORT §4.6 定死的：
`M1 索引 → M2 规划器 → M3 生命周期 → M4 写入 → M5 接地`，且「**没有 M2/M4，M5 没有意义**」。

---

## §4 可能需要（未决 —— 没有判据，也没有共识）

> 与 §3 的区别：§3 是**决定要做但还没做**，§4 是**连要不要做都没定**。写在这里不表示欠账。

1. **D / E 两探针** —— 现有三例（A 对话含 assistant / B 散文 / C 对话仅 user）**三处共变**，一个变量都没分离。
   而且 B 的 `rc=230`（A/C 是 93）说明它的**续写行为都变了** —— **B 连当对照组的资格都没有**。
   要单因子必须补：`D` 与 A 同内容同长度只去角色标记（分离形式）；`E` 与 B 同形式加长到 ~91 token（分离长度）。
   **只补 D 不补 E，会把「形式 vs 长度」永久留在未分离状态。**
2. **块内位置的「声明 vs 结果」** —— `attach_range` 是算出来的期望值还是实测结果？若是期望值，它会在一切正常和一切崩掉时给出同一个值。
3. **消融是否必须跨进程** —— arm1 与 arm2 的块 sha 相同、位置相同、问题相同，却一个 96 字节一个 `-1`。
   「必须跨进程」目前只有一例证据。
4. **`raw_to_delivered_delta` 的跨层差** —— 含 `m4_display` 压掉的空行，**不可归因**；归因只能靠 `per_tag`。

---

## §5 引擎层附册

E1–E10 / S1–S3 / P1–P8 共 25 条判定在 **[PROJECT-STATE.md](PROJECT-STATE.md)**，每条挂【代码证实】【部分落地】【明确未做·查无】【仅文档宣称】。
**引擎层有冲突以 PROJECT-STATE 为准**；本文件是产品层台账。

---

## §6 这张表自己的规矩

```
① 状态由产物支持，不由文档宣称；拿不出锚的写「未证」，不写「已实现」
② 强度不许自报升格：脚本给自己打分的布尔最多算 S
③ 锚必须是「文件名 = sha256前16」；产物重跑 ⇒ 结论自动过期（见 m4_memory.db 那次）
④ 一个功能若有两个名字下的两个值，必须写清它量的是什么，或拆成两个字段
⑤ 「不可解释」与「未通过」分两格：inconclusive_control_failed 不是失败，是没做成实验
⑥ 「已实现」与「已验收」分两格：十项 acceptance 全真 ≠ 三项附加项全绿
⑦ 锚不在仓库的，必须标 ⚠ —— 复算的人拿不到文件，那句话就只能当转录（A）读，不能当重算（R）
```
