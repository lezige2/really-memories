# Stage 1b 验收 · 层 1 结构化 + 摘录行 + M5 闸门

验收人：inspector ｜ 2026-10-25 ｜ 依据：SRC-CRITERIA.md（I1-I7、C4-f~k、R15-a~g）
纪律：不采信二级汇总；每条都给了我自己跑出来的返回值或 SQL 原值。

## 1 逐条裁决

| 条件 | 裁决 | 我的实测证据 |
|---|---|---|
| C4-f 层 1 text_kind 合法 | **通过** | 10 行：human_memory ×9（profile/project + 7 摘录）、conversation ×1（conv，contains_model_turns=1）|
| C4-g 闸门 conv 抛错 / profile 通过 | **通过（TODO 期口径）** | `conv → SourceNotAllowed`（消息含 text_kind 与 contains_model_turns）；`profile/project/conv#L5 → 返回 dict` |
| C4-h resolve_origin 含 text_kind | **通过（超出要求）** | 返回 `{registry_source_id:3, name, sha256, sha16, text_kind:"conversation", contains_model_turns:1}` |
| C4-i 负向两条 | **通过** | `Stale` ×2（origin sha 不符；层 1 哈希漂移）+ `ForeignText`（注入一行"我昨天买了一架私人飞机。"被点名拒）|
| C4-j 摘录三件套 | **通过** | 7 行 is_excerpt=1、derived_from=conv_2026-10-25@d8c094c1f5fcb8f1、逐字节命中行号 1/3/4/5/7/8/9，**不匹配数 0** |
| C4-k 调用点/无旁路 | **条件满足（TODO 期）**；生产路径调用点 = **0** | 定义 `m4_layer2_link.py:201`；唯一调用 `:604` 在验收脚本 `if a.check_m5_source:` 分支内；`m5_bridge.py:85-86` 是 TODO 注释；另有静态扫描器 `registry/check_m5_gate.py`（对 m5/m4/tools 里读源的模式要求"有闸门或带 TODO 标记"）|
| R15-d① 五元组入数据 | **通过** | `chat.db::memory_source_excerpt` 7 行，列正是 `(container_id, container_name, container_sha256, line_index, excerpt_source_id, line_sha256, line_len, role, roles_declared, decl_source)`，container_sha256 全串 = d8c094c1… |
| R15-d② 声明可审 | **通过** | `roles_declared=1`、`decl_source="lead ruling D1/R15-b (2026-10-25)"`；`EXCERPTS` 里另有 `roles_declared/declared_by/user_lines/assistant_lines` 四件 |
| R15-d③ 确定性 | **通过（读层）** | 声明是字面常量、摘要按行号升序；`assert_excerpts` 两次输出一致；存储行 sha 与重算一致 |
| 五元组 | **通过** | 它们的 `coverage()` 与我独立计数一致：`(user 7, assistant 2, 层1摘录 7, 层2覆盖 4, 可检索事实 4)`；覆盖行号 `[3,4,5,9]`，未覆盖 `L1/L7/L8`，并带 `not covered = NOT SEARCHABLE` 说明 |
| 容器版本锚 | **通过** | conv `d8c094c1f5fcb8f1` / 127 字符 / 9 行 |

## 2 一处**必修**：默认值仍朝不安全方向（这是它自己抓到的缺陷 1 的根因，没被修掉）

实测 schema：`text_kind TEXT NOT NULL DEFAULT 'human_memory'`，且**没有 CHECK 约束**。
它这次之所以没出事，是因为 `migrate_layer1` 被调到 `promote` **之前**（顺序修），不是默认值修。
⇒ 任何**将来**忘记写 text_kind 的 INSERT 会静默变成 `human_memory` ⇒ 可在 M5 源侧被放行。
这正是 lead 说的那一类：**默认值朝不安全方向，且没有任何字节层报错**。

**必修（判据 I8）**：保护性字段的默认值必须等于**拒绝态** —— `DEFAULT 'conversation'` + `CHECK (text_kind IN ('human_memory','conversation'))`。
可判形式：一条**只用老列**的 INSERT（不写 text_kind）⇒ 读回必须是 `conversation`。给出该测试的实测输出即可关闭本条。
（实现方式由执行者定：SQLite 加 CHECK 需重建表；重建与替代方案我都不预设，只看那条测试。）

## 3 关于 `_m5db` 两个哈希 —— `876deaa3` 我无法复算，不得作锚

我试了 7 种序列化（全列/核心列 × 插入序/排序 × json/repr/拼接、block_id+cells+sha 拼接、source_text 拼接）：
得到 `33877e4d` / `522165da` / `0d3bddf8` / `307a3645` / `c31c6048` / `1efc1252`，**没有一个等于 876deaa3**。
⇒ 该值**定义未知、不可复算**，按锚规则不得作为锚使用。可复算的锚只有：文件 `ef5fdfb65640d2fa`、块文件 `81127d24fd64b96b` / `e3bfec41d1f059e7`、块数 91/79。
**附带纪律（第 N 次同族）**：任何哈希值必须附定义（对什么序列化、哪些列、什么顺序），否则不可复算 = 不可验收。

## 4 锚点重算（我自己算的）

- `chat.db` = **a699fd1e5aaa9adf**（与 lead 同值）；三行 text 字节未变：61/`d3e57f11838e6bf8`、45/`aa9769adb3cb4493`、127/`d8c094c1f5fcb8f1`。
- `m4_memory.db` = **fd244c80c0cc974d**（已变 ⇒ 上轮 M4 锚作废）⇒ 我重验：`run_m4_verify.json` = **857f13c514ad233e**，**16 键全 true** ⇒ **M4「通过」重新锚定于 (a699fd1e / fd244c80 / 857f13c5)**。
- `run_m5_grounded.json` = **d97cdfdcbd6c6d3d**（未变）；`_m5db` 文件 = ef5fdfb65640d2fa（变），但 block 内容 sha（81127d24 / e3bfec41）、cells（91/79）、size 未变，且该 json **不内嵌 text_origin**（我 grep 过：既无旧值也无新值）⇒ **M5「通过」维持**，Stage 3 重跑后重锚。
- `m5_ground.py` = 86b7c501ab9904aa（未动，Stage 3 尚未开始，符合预期）。

## 5 两个自作缺陷的记录（我认可其上报方式）

- **缺陷 1（提升前迁移）**：已导出为判据 I8（见 §2）。**它被自己的"conv 应抛 SourceNotAllowed"断言抓住** —— 这条断言值得保留为回归项。
- **缺陷 2（层 2 id 与注册表 id 两个命名空间）**：I7 第 4 行的第一次真实兑现。现 `_m5db.text_origin` = `registry:conv_2026-10-25@d8c094c1f5fcb8f1`，`declared_synthetic:blk_conv_noplate_2026-10-25_01@93332bde804698bc`，两者均按 D2 字面形态可 grep。

## 6 结论

**1b：通过（附一条必修）** —— C4-f~k、R15-d、五元组、容器锚全部满足；唯一未闭的是 §2 的**默认值方向**。
该条不阻塞 Stage 2（chat.py 改读库），但**必须在 Stage 3 接闸门之前关闭**：否则 Stage 3 一旦有真实的选源分支，忘记写 text_kind 的行就会被放行，而那就是我们在防的"用自己的产出当接地依据"。