# 注册表不变量（Stage 1a）

**权威源已经在库里，不再新建第二张表。** 它是 `kvmem/chat.db::memory_source`：

| 列 | 用途 |
|---|---|
| `id` | 行号（历史只追加，不修改） |
| `tenant / scope / mode / name / label` | 定位与展示 |
| `text` | **原话，全系统唯一副本** |
| `source_hash` | `sha256(text)` 的全 64 位 |
| `created_at` | 写入时刻 |

缺口 #7 的真实形态是**唯一性 + 消费方全覆盖 + 可校验**，不是"没有权威副本"。
所以 Stage 1a 只做注册表侧的加固，**不新增表、不改任何消费方**。

## 1a 改了什么（只动 `tools/memory_source.py`，三处 + 一个开关）

| 函数 | 之前 | 现在 |
|---|---|---|
| `put_source` | 同名不同文本 => 静默插入新修订行（`get_source` 立刻返回新文本，旧块还指着旧行 => 两份悄悄分家） | 同名不同 hash **抛 `SourceConflict`**；要建新版本必须显式 `revise=True`（CLI `--revise`）。同 hash 仍然幂等返回原 id、不写任何东西 |
| `get_source` | 直接返回行 | 返回前重算 `sha256(text)` 与 `source_hash` 比对，不一致抛 `SourceHashMismatch`。**这是 chat.py 读源用的同一个函数**，所以篡改会在这里失败，不会顺着流程流下去 |
| `probe_text` | 直接返回文本 | 同样先校验（它也是唯一被允许把原话交出去的入口） |
| `assert_unique_texts`（新） | — | I1 断言：一份文本只能有一行；重复或 hash 不符即抛错 |
| `verify` 子命令 | 只报块与源的问题 | 先打印 `uniqueness: OK (N distinct texts, one row each)`，失败返回 1 |

空文本/纯空白**不落库**（抛 `ValueError`），空串冒充源这条路被堵死。

## 一条命令

`python -u -X utf8 kvmem/m2_visibility/registry/check_registry.py` -> `run_registry_check.json`

三个写测试（幂等、拒改、篡改）**都在 `_test/` 的库副本上做**，所以 `kvmem/chat.db` 字节不变
（json 里 `db_sha16_before == db_sha16_after` 自证）。

## 实测（原值）

两端 sha256 对照：

| id | name | 库里 source_hash[:16] | 重算 sha256[:16] | 长度 | 一致 |
|---|---|---|---|---|---|
| 1 | profile | `d3e57f11838e6bf8` | `d3e57f11838e6bf8` | 61 | ✅ |
| 2 | project | `aa9769adb3cb4493` | `aa9769adb3cb4493` | 45 | ✅ |

与 `tools/chat.py::MEMORIES` 的字面量逐字节相同（`ast.literal_eval` 读取，不 import、不执行、不喂 M5）。

篡改实测（库副本，先 `DROP TRIGGER memory_source_text_is_immutable` 再 `UPDATE text`，hash 不动）：

| 校验入口 | 结果 |
|---|---|
| `memory_source.get_source(name)`（消费方函数） | **SourceHashMismatch** |
| `memory_source.probe_text(id)` | **SourceHashMismatch** |
| `memory_source.assert_unique_texts(con)` | **SourceHashMismatch** |
| `memory_source.verify(con)` | `['profile: source_hash mismatch (text was mutated behind the trigger)']` |

四条全部 fail closed；任何一条"返回而不是抛"都会让整批 `pass=false`（见 `must_raise`：它只用来断言异常类型，不存在 catch 完继续跑的分支）。

## 验收（`run_registry_check.json::acceptance`）

| # | 判据 | 值 |
|---|---|---|
| 1 | 库内 hash 自洽 | true |
| 2 | 篡改必报错 | true |
| 3 | 缺条目返回明确缺失（`get_source` 返回 None、`probe_text` 抛 KeyError） | true |
| 4 | I1 唯一（1 文本 = 1 行） | true |
| 5 | 幂等 put（同 id、`created=False`、行数不变） | true |
| 6 | 拒绝隐式修订（抛 `SourceConflict`、行数不变、文本不变） | true |
| 7 | 拒绝空文本 | true |
| 8 | 与 chat.py 常量逐字节一致 | true |
| 9 | 权威库字节未变 | true |
| 10 | 库触发器本体在且拦得住（不 DROP 直改 => IntegrityError） | true |

## 三层防线（库触发器 -> API -> 不变量）

同一件事有三道独立的闸门，**任何一道单独失效都还有另一道**：

| 层 | 位置 | 被触发时的实测输出 |
|---|---|---|
| 物理层：库触发器 | `memory_source_text_is_immutable`（`BEFORE UPDATE OF text, source_hash`） | `IntegrityError: memory_source.text is immutable: insert a new row instead of editing history` |
| API 层：读时重算 | `memory_source.get_source` / `probe_text` 调 `_verify_row` | `SourceHashMismatch: stored source_hash ... != sha256(text) ...` |
| 不变量层：I1 | `assert_unique_texts` | `SourceHashMismatch` 或 `AssertionError: the same text is stored more than once` |

负向测试**两条都跑**（`check_registry.py`）：不 DROP TRIGGER 直接 `UPDATE` => `IntegrityError`（触发器挡下，连 API 都到不了）；
DROP TRIGGER 后再改 => 上面三条 API 校验全部抛错。绕得过一层，绕不过三层。

## 1a 真正拿到的收益（比"加了校验"更硬）

链路的权威方向现在是：

`MEMORIES 字面量 (tools/chat.py:58) --put_source--> 注册表 --get_source(校验 hash)--> build_block`

- 1a **之前**：改一行字面量 => 下次 `put_source` 静默插入新修订 => `get_source` 返回新文本 => **所有块悄悄换源，没有任何一处报错**。
- 1a **之后**：同样的动作抛 `SourceConflict`（消息里给新旧 hash 与"要新版本请显式 revise"），必须人为 `--revise`。
  => 「改一行常量就悄悄换掉所有块的源」这条路被堵住了。

**剩余缺口**：权威方向仍是 **字面量 -> 注册表**（字面量说了算）。Stage 2 要反过来：chat.py 直接读注册表文本，
并补一条负向测试 —— **把 `MEMORIES` 删掉/改坏后，chat.py 仍应正常索引**（不再依赖常量存在）。

## 边界

- **未改**：`tools/chat.py`、`tools/kvslots.py`、`kvmem/m2_visibility/m5/m5_ground.py`、`kvmem/m2_visibility/m4/m4_memory.db`（M4 三锚仍 MATCH，见 `m4/README.md §19.10`）。
- **未做**（按 lead 分工）：Stage 1b（层 2 加 `registry_source_id`/`source_hash` 两列、子串断言、`text_origin` 改写）、Stage 2（chat.py 改读库）、Stage 3（M5 改读库）、R14（省份词表）、C5 那四个平行版本。
- 层 2 现在的缺口照实记在 `run_registry_check.json::consumer_coverage`：`m4/m4_memory.db::memory_source` 只有 `id,name,label,text,fanout` —— 无 hash 无注册表 id；
  `_m5db/m5_m4_blocks.db::text_origin` 是字面量 `m4.memory_source.text`，不是 `(id, sha)`。


## Stage 1b 增量：层 1 的四种行 + M5 源闸门（R15 候选）

### 新列（幂等 ALTER，**没有重写任何一行 text 的字节**）

| 列 | 值域 | 含义 |
|---|---|---|
| `text_kind` | `human_memory` / `conversation` | 这行是什么 |
| `contains_model_turns` | 0 / 1 | 里面有没有模型产出 |
| `is_excerpt` | 0 / 1 | 是"某容器的一句话摘录"还是独立源 |
| `derived_from` | `<container>@<sha16>` / NULL | 摘录必填，指回容器 |

层 1 现在是 10 行：`profile` / `project`（human_memory,0,0）、`conv_2026-10-25`（conversation,1,0）、
`conv_2026-10-25#L1/L3/L4/L5/L7/L8/L9`（human_memory,0,1，derived_from=`conv_2026-10-25@d8c094c1f5fcb8f1`）。

### I1 精确化（`assert_unique_texts`）

1. 同一 `(text_kind, is_excerpt)` 层内：一个文本只有一行；
2. 跨层唯一允许的重复 = **摘录 ⊂ 容器**，且 `derived_from` 必须解析到**唯一**的非摘录行、sha16 前缀匹配、文本逐字子串；
3. 分层不许变成「看不见的重复」：跨层重复**必须可追溯**。

实测三个层：`conversation/is_excerpt=0`、`human_memory/is_excerpt=0`、`human_memory/is_excerpt=1`。

### R15（候选纪律，写进判据）

> `text_kind=conversation` 的源**只能**用于证明「块正文来自何处」（`text_origin` 回查），
> **绝不得作为 M5 的源侧**。M5 源侧只接受 `text_kind=human_memory`。

理由：对话记录含模型回合，若它当 M5 源，模型自己的一句「记住了」甚至一句编造都会被当成"源里有"。
**安全方向**：人类发言若未进入 M5 源，相关提问变 `undecidable`（弃答）——按「漏判优先于误判」可接受。

### 闸门调用点（C4-k）

`registry/check_m5_gate.py` 做两件机器可查的事：① 打印 `assert_m5_source_allowed` 的调用点；② 扫描「会materialize M5 源文本」的文件，
要求每个都调用闸门或带 `TODO(stage3)` 标记，否则判 BYPASS。
闸门已存在并被**验收脚本**调用（`m4_layer2_link.py:604`）；**生产路径接入点 = 0**，
`TODO(stage3)` 钉在 `m5_bridge.py:86`；**`bypass=0` 在 1b 期是空真**
（M5 尚无选源分支），Stage 3 接入后该断言才具备拦截力。

（`check_m5_gate.py` 打印的 `call_site_count` 含定义行与文档行；不要把这个数读成"生产已接入"。）

### 覆盖率五元组（源侧与可检索是两件事）

`(user 行数=7, assistant 行数=2, 层1 摘录行数=7, 被层2事实覆盖的行数=4, 可检索事实数=4)`

**L1「你好呀！」/ L7「帮我查下明天天气。」/ L8「谢谢，就这样吧。」是「不可检索」（没被抽成事实、进不了检索），
不是「不可支撑」（它们仍是层 1 的源）。**

### 角色声明与逐字节断言

枚举写死在 `m4/m4_layer2_link.py::EXCERPTS` 并落库 `memory_source_excerpt`
（`container_id/container_name/container_sha256/line_index/excerpt_source_id/line_sha256/line_len/role/roles_declared/decl_source`）。
断言：`line_text == container_text.split(换行)[line_index-1]` **逐字节相等**，不等即报错（不取最近、不跳过）。
声明变更 => `drop_stale_excerpts` 把该容器的摘录集**整体删除重建**，不许就地改 role。
role **只作准入闸门**，不得参与任何内容判断。

### 一条必须记住的观察

既有 4 条 fact 的溯源（住址_2→L3、作息_3→L4、车牌_4→L5、家庭成员_5→L9）全是用户行、全是逐字子串，
所以今天**把 L2 标成 user 也不会改变任何结果**（L2 没有事实）=> 枚举标错是**隐性**的。
显式枚举 + sha16 绑定 + 逐字节断言防的是**将来**：某条助手发言恰好含一个硬事实被静默存进层 1 的那一刻，
**没有任何字节层面的东西会报错**。

### 锚

`chat.db`：`f02763dcd8512e83` -> **`a699fd1e5aaa9adf`**（列变更 + 3 条新源 + 7 条摘录）。
`profile` / `project` 的 text 与 `source_hash` **未变**：`d3e57f11838e6bf8` / `aa9769adb3cb4493`（len 61 / 45）。


## 为什么需要断言（两个真实案例，都发生在 1b 当天）

抽象地说"要有护栏"没有说服力，下面两件事是**断言挡下来的**，不是人看出来的。

**案例 1：默认值朝不安全方向走。**
1b 第一版把 `migrate_layer1()` 放在**提升之前**执行。于是 `put_source` 新插入的
`conv_2026-10-25` 行吃了列默认值 `text_kind='human_memory'` —— 那段对话里明明有助手回合。
后果：`assert_m5_source_allowed('conv_2026-10-25')` **放行**，模型产出被当成可作源的记忆。
**没有任何字节层面的东西会报错**：hash 自洽、子串成立、I1 通过、`_m5db` 照常重建。
把它挡下来的是「conv 必须抛 `SourceNotAllowed`」这条断言（C4-g）。
修法：分类必须在提升**之后**执行，且只处理 `is_excerpt=0` 的行。

> 教训：**列默认值是一种静默决策**。默认成 `human_memory` 等于默认"这行可以当源"，
> 危险方向上的默认值必须配一条反向断言，否则它会在没人注意的时候生效。

**案例 2：两个 id 命名空间。**
`m5_bridge.origin_of()` 第一版在**层 2** 里按 `registry_source_id` 反查名字，
于是 `blk_conv_2026-10-25_01` 的 `text_origin` 变成了 `registry:fact_作息_3@…` ——
层 2 的 id=3 是 `fact_作息_3`，注册表的 id=3 是 `conv_2026-10-25`。
名字看着完全合法、sha 也对得上，**只有人会读错，字节不会报警**。
修法：名字回层 1 查，两侧 hash 比对，不一致写 `stale:` 前缀而不是装作正常。
（这是 I7 第 4 行「两处各存一半真相必须有不一致断言」的第一次真实兑现。）


## Stage 2：chat.py 改读注册表（`MEMORIES` 字面量已删除）

### 变化

| 位置 | 之前 | 现在 |
|---|---|---|
| 记忆文本 | `tools/chat.py:58` 的 `MEMORIES` 字面量 | **不存在**（`grep -c MEMORIES tools/chat.py` = 0）|
| 建块来源 | `for name,label,text in MEMORIES: put_source(...)` | `ms.indexable_sources(con)` -> 读注册表，只读不写 |
| 选源规则 | 常量决定 | `text_kind='human_memory' AND is_excerpt=0`（对话记录与摘录不建块）|
| 空库行为 | 建源 | `die("the registry has no indexable source")` 明确拒绝，不静默建索引 |

`put_source` 已不在建块路径上：**写不进来的东西，也就没法悄悄换源**。
`QUESTIONS` 保留 —— 那是问题，不是记忆文本。

### 纯重构验证（引擎实跑，不是推算）

| 项 | 结果 |
|---|---|
| 三问 `answers_sha256` | `852a5e5e6ab70eeb…` / `dacdc1a89ef08165…` / `46272e43287c5ff7…` —— **三条逐字节相同** |
| 几何 | `cells_total=51`、`positions=4045..4095`、`head_gap_cells=0`、`first_question_pos=4096`（与旧运行一致）|
| `m2_pass` / `all_hits` | `True` / `[True, True, True]` |
| 块文件字节 | `profile.kvmem 3251081d12da5678`、`project.kvmem 981a9c776c720686` —— **重建前后相同** |
| 运行证据 | 旧（冻结）：`chat_lease/run_m2_final.json`；新：`m2/run_m2_after_s2.json`（sha16 `2e1f2be9b5d51a21`）|

### 「文本不再是依赖」的证据清单（投毒那条已 retired）

| # | 证据 | 状态 |
|---|---|---|
| 1 | `grep -c MEMORIES tools/chat.py` -> **0**；`git show HEAD~1:tools/chat.py` 里是 2 处（循环 + 计数）| 有效 |
| 2 | `tools/chat.py:103` 实际调用 `ms.indexable_sources(con)`（建块路径唯一入口）| 有效 |
| 3 | 账本键 `13_no_second_copy_of_memory_text` 做源码扫描（无字面量 + 读注册表 + 建块不写源）| 有效 |
| 4 | ~~投毒 `chat.MEMORIES` 后仍能正常建块~~ | **retired** |
| 5 | 空库 => `die("the registry has no indexable source …")` | **未验**（跑它会动真库，检测员未跑）|

**为什么投毒那条 retired**：`MEMORIES` 已经不存在，**投毒一个没有代码路径读取的名字，无论结果如何都不构成证据** ——
它今天不可能失败，也就证明不了什么。它原本防的「文本被当成依赖」由第 1/2/3 条覆盖。
**为什么空库那条写"未验"**：没跑过的检查不许写成通过。

### 锚

`chat.db`：`a699fd1e5aaa9adf` -> **`6d2ff37a4861b08d`**（当前值；漂移原因见下）。

**锚漂移记录（防止下次误判成内容变更）**：本文件上一版写的是 `5909b978e31e584a`，那是 **04:31:20 之前**测的值。
`chat.db` 的 mtime 是 **04:31:20** —— 正是 `m4_layer2_link.py` / `run_layer2_link.json` 写盘那一分钟；
README 的 mtime 04:31:45 在其后 => **锚是在"另一阶段还会再写一次这个库"之前测的**。
内容层面已复核，全部一致：`memory_source` 10 行（`61/d3e57f11`、`45/aa9769ad`、`127/d8c094c1` + 7 条摘录）、
`memory_source_excerpt` 7 行、`memory_block` 2 行、`PRAGMA integrity_check` = ok、page 22 / freelist 1
=> **只有文件级漂移，没有内容漂移**。
变的只有 `memory_block` 的派生状态（`built_at` / 路径重指回 `kvmem/blocks`）；
`memory_source` **一行都没动**：10 行、`profile d3e57f11838e6bf8/61`、
`project aa9769adb3cb4493/45`、`conv_2026-10-25 d8c094c1f5fcb8f1/127`、7 条摘录。
`m4_memory.db fd244c80c0cc974d` / `run_m4_verify.json 857f13c514ad233e` 未变 => **M4 验收仍有效**。

### 残留的真实依赖（不粉饰）

`chat.py` 仍需要注册表**里有**那两行文本才能建块 —— 这是正确的依赖方向（源 -> 派生），
不是"换了个地方依赖常量"。真正的残留风险是 `indexable_sources` 的过滤条件写错，
它由 `m4_layer2_link.py` 的 `text_kind` 断言与 `check_m5_gate.py` 的选源扫描共同看住。


## I8：默认值必须朝**拒绝**方向，且闸门必须读这个列

### 冻结点

| 项 | 现在 |
|---|---|
| `text_kind` | `TEXT NOT NULL DEFAULT 'conversation'` + `CHECK (text_kind IN ('human_memory','conversation'))` |
| `contains_model_turns` | `INTEGER NOT NULL DEFAULT 1` + `CHECK (contains_model_turns IN (0,1))` |
| 唯一成立的关联约束 | `CHECK (NOT (text_kind = 'human_memory' AND contains_model_turns = 1))` |
| 闸门 | 三项并列：`text_kind=='human_memory' AND contains_model_turns==0`，且（摘录时）`derived_from` 非空 + 逐字子串成立 |

**(A) 派生、(B) 双向 CHECK 都被代码事实否掉了**：`conversation` 与「含模型回合」不是同一个谓词 ——
一份**纯人类发言**的会话记录是 `conversation` + `0` 的合法事实。从 `text_kind` 派生会把它错标成「含模型回合」。
反方向的 CHECK（`conversation ⇒ turns=1`）会**禁止一行合法数据**。所以只留 `human_memory ⇒ turns=0` 这一个方向。

### 修之前它确实是装饰性的

旧闸门：
`if kind != "human_memory": raise ...` —— `turns` 只出现在报错文案和返回值里，**没有任何一处用它做决定**。
后果：写入、展示、却从不校验。比默认值方向更严重。

### 三条可判证据（原文，`registry/run_i8.json`）

| # | 做法 | 实测 |
|---|---|---|
| (i) | 只用老列的 INSERT（不写新列）| 读回 `(11, 'conversation', 1, 0, None)`；闸门抛 `SourceNotAllowed: source 'i8_probe' (id=11) is text_kind='conversation', contains_model_turns=1` |
| (ii) | 显式 `human_memory` + `1` | `IntegrityError: CHECK constraint failed: NOT (text_kind = 'human_memory' AND contains_model_turns = 1)` |
| (iii) | **绕过 CHECK**：副本库删掉 CHECK 重建表，把 conv 改成 `human_memory`+`1`，再问闸门 | 行确实成了 `('human_memory', 1)`，闸门仍抛 `SourceNotAllowed: source 'conv_2026-10-25' (id=3) is text_kind='human_memory', contains_model_turns=1` |

**(iii) 是这一轮的关键**：它证明闸门**读了** `contains_model_turns`，而不是只读 `text_kind` 摆样子。

### 落地方式

SQLite 不能加 CHECK，所以 `registry/migrate_i8.py` 按 `tools/memory_source.py::SCHEMA`（唯一 DDL 源）**重建表**：
读数 -> 建新表 -> 拷 13 列 -> 删旧 -> 改名 -> 重建索引与不可变触发器。
`run_i8.json` 里 `row_parity_problems=none`（10 行逐列逐字节相同），`trigger_present=True`。

**`row_parity` 是一次性迁移比对，不是回归项**：它证明的是"重建表那一刻，旧表 10 行逐列逐字节等于新表"，
只在那一次迁移的运行记录里成立。之后再跑 `migrate_i8.py` 不会复现这个结论（表已是新 DDL，没有旧表可比），
**不要把它当"每次都该 true"的检查用**。

### 常驻回归项（不再是"这一轮验过"）

`check_registry.py` 有 13 个验收键，其中这三个是长期驻留：

| 键 | 断言 |
|---|---|
| `11_gate_rejects_conversation` | 每个 `text_kind='conversation'` 的行必须抛 `SourceNotAllowed`（抓出缺陷 1 的就是这条）|
| `12_undeclared_insert_fails_closed` | 副本上不写新列 INSERT => 读回 `conversation/1` 且闸门抛错 |
| `13_no_second_copy_of_memory_text` | `tools/chat.py` 无 `MEMORIES` 字面量、走 `ms.indexable_sources`、建块路径不写源 |

## 纪律：**任何哈希必须附定义**

与「计数必须附原值」并列。定义要写清四件事：**对什么序列化、哪些列、什么顺序、什么编码**。
一个「定义未知、不可复算」的哈希不是锚，是死数字。

### 现存唯一一个"派生内容哈希"及其定义

`_m5db` 的 `content_sha256 = 876deaa3a4b7ad1d4a01f49e2a451b0c577b3feb6aaf86f03920fe2e98e07edf`：

* 取 `blocks` 表的 **三列** `(block_id, sha256, source_text)`（`sha256` 是块文件磁盘哈希）；
* **按 block_id 排序**（`ORDER BY block_id`）；
* `json.dumps(rows, ensure_ascii=False)` —— Python 默认分隔符（`", "` / `": "`），元组序列化成 JSON 数组，无尾随换行；
* 编码 `UTF-8`，再取 `sha256`。

复算命令（任何人可重跑，结果必须相同）：

`python -X utf8 -c "import json,sqlite3,hashlib; con=sqlite3.connect('kvmem/m2_visibility/m4/_m5db/m5_m4_blocks.db'); rows=list(con.execute('SELECT block_id, sha256, source_text FROM blocks ORDER BY block_id')); print(hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode('utf-8')).hexdigest())"`

实测输出前 16 位 `876deaa3a4b7ad1d`，与记录一致；代码位置 `m5_bridge.py:133-137`。

## 四条并列纪律（第 4 条是今晚新增）

| # | 纪律 | 它防的是什么 |
|---|---|---|
| ① | **计数必须附原值** | "多了/少了"没有原值就无法复核 |
| ② | **代码行为必须附原文或 git diff hunk** | 转述会漂移 |
| ③ | **任何哈希必须附定义**（序列化方式 / 列集合 / 顺序 / 编码）| 定义未知的哈希不是锚，是死数字 |
| ④ | **台账每项必须能独立溯源到只属于它的判据** | 共享布尔 = 隐性项数膨胀 |

### ④ 的来历（真实事故）

`check_registry.py` 曾有 `8_fidelity` 与 `13_no_second_copy_of_memory_text` 两个键
**共用同一个布尔** `res["no_second_copy_of_memory_text"]["ok"]` —— 账本显示 13/13，**实际只有 12 个独立判据**。
检测员的判词：

> 这跟「把挡路那条删掉」是反向的同一类病：**把一条已经无意义的检查留着颜色好看。**

处置：
1. `8_fidelity` 置 **retired**（值不再参与 `pass`，输出里单列 `retired keys` 名单）；
2. 新增机器自检：用 AST 取 `res["acceptance"]` 的每个键与其判据表达式，**两两必须不同**，
   输出同时打印 `key_count` 与 `distinct_judgements`，两者不等即 FAIL。

实测三层证据（缺一层就是"不可能失败的检查"）：

| 层 | 输入 | 实测输出 |
|---|---|---|
| 真账本 | 当前文件 | `ledger: 14 keys / 14 distinct judgements`（无重复组）|
| **注入别名负向** | `{"1_a": res["x"]["ok"], "2_b": res["x"]["ok"], "3_c": res["y"]["ok"]}` | `injected alias detected => {"res['x']['ok']": ['1_a', '2_b']}`、`selfcheck_ok_when_fed_alias=False` |
| **历史重放** | `git show 31afe89^:…/check_registry.py` | `keys=13 distinct=12`，重复组 `no_second_copy_of_memory_text -> [8_fidelity, 13_…]`，自检返回 **False** |

第三层是这条自检唯一的"真数据可验"证据：**先删 8 再加自检**，真账本里已经无重复可验，
所以只用真账本跑，这条自检就是**又一条不可能失败的检查**（与刚退役的投毒测试同类）。
历史重放证明：如果当时已有这条自检，它在那次提交上**会红**。

### 两类缺陷，两种查法

> **运行验证只能抓到"被运行到"的东西。**
> `DECL_SCHEMA` / `promote_excerpts` 因为 `NameError` 当场炸，被运行挡下；
> 但 `8_fidelity` 这种「名字还在、值还在、只是指向了别人」的缺失，**运行永远不会报错** —— 它只会安静地让账本多一项。

- **会炸的**（缺函数、缺常量、签名不符）=> 运行验证 + 断言；
- **安静的**（两键共用一个布尔、检查指向了别人、退役后仍计分）=> 逐项回溯源头的布尔/字段，靠自检脚本，不靠跑。

## Stage 3 step 1：M5 的源改由层 1 的人类摘录组装

改的是「喂给 M5 的源文本」，不是 KV 内存：`kvmem/blocks/profile.kvmem` `3251081d12da5678`、
`project.kvmem` `981a9c776c720686` 与 mtime `04:25:52` **三项都未变**（基线 `baseline_blocks.json @ 0a63717933055e65`）。

### 选源点只有一处
- `m4/m5_bridge.py::select_m5_source()` —— 层 2 行有 `registry_source_id` 就回层 1：
  `conversation` 容器**永不当源**，只取 `memory_source_excerpt` 的 `role='user'` 行按 `line_index` 拼接；
  `human_memory` 容器原样使用。两条分支都在**返回准入名单之前**调用 `ms.assert_m5_source_allowed`
  （调用点：`m5_bridge.py:183`、`:194`）。
- `assert joined not in container_text` 是**守护**：跳过 L2/L6（两条 assistant 行）是**有意的**，
  "修成连续子串"等于把模型输出拉回源侧。

### 两个量必须分开记（实证，不是洁癖）

| 量 | 值 | 稳定性 |
|---|---|---|
| `_m5db` **内容哈希** | `76df01317bfaf3e7` | 四次重建同一个值 |
| `_m5db` **文件 sha16** | `022a0860` / `7d6e39ce` / `babe0b55` / `c65e77d3` | **每次重写都变** |

内容哈希定义：`sha256(json.dumps([(block_id, sha256=块文件磁盘哈希, source_text), …], ensure_ascii=False))[:16]`，
`ORDER BY block_id`、默认分隔符、无尾随换行、UTF-8（`m5_bridge.py:133-137`）。

**锚只能证明"曾经是什么"，不能保存"曾经是什么"** => 任何会覆盖已验收产物的运行，先复制到
`_before/<name>@<sha16>` 并登记 `_before/REGISTER.json`（`source_name`/`source_sha16`/`copy_time`/`copyist`/`reason`，
`reason` 一律「运行前预防」）。

### 两条 fail-open 判据（已修，证据给的是"入口"而非效果）

| 缺口 | 判据 | 修法 |
|---|---|---|
| `regcon=None` 让闸门静默失效 | 注册库不可用 => **必须拒绝** | `ensure_db:201` `if not os.path.exists(REG_DB): raise`（报错含路径与原因）+ `select_m5_source:134` `assert regcon is not None` |
| `except OperationalError` 太宽 | 豁免与否由 **schema 正面证据** 决定 | 豁免需**两个独立信号同时成立**：路径声明是消融库（`:223`）**且** `PRAGMA table_info` 真没有该列（`:135`）；两者不一致 => 抛 `SCHEMA ACCIDENT`（`:142`），**措辞不含「未链接」**（否则会把人引去跑 `link --apply`，把 schema 事故修成误链接）|

### 登记：`origin_of()` 的 `except sqlite3.OperationalError` 是防御性、**不在判定路径**

保留它是为了在消融库上照样生成 origin 字符串；它**不决定**"是否豁免"（豁免由上面两个信号决定），
且下游 D3-1 的 CHECK 绑了「前缀 ⇔ `synthetic`」，误触发会被拒。**它不是第二个豁免入口。**

### 轴：同一个字段名在两份产物里指不同的轴

| 轴 | 变化 | plate_main |
|---|---|---|
| 代码轴（`e172aca` -> 当前） | R12 修复 | unsupported -> **supported** |
| 源文本轴（`127` -> `110`，同版代码） | Stage 3 | supported -> **supported** |

`run_m5_grounded.json` 的 `before_after.verdict_before` 是**代码轴**。Stage 3 的 before 侧是
`PREREG-STAGE3-11ROWS.json`（`verdict_axis: source_text`、`product_kind: reconstruction`、
provenance `_stage3_pre.json @ 9500f1c7c59c118f`）。**跨轴比较会得出「Stage 3 让 plate_main 从不支持变支持」
—— 一个看起来像改进的假结论。**

### 11 行裁决：**R 9 / C 2 = 部分已验**（不是"11 行已验"）

| 档 | 行 |
|---|---|
| **R**（重算）| `plate_main`、`home_main`、7 条探针 |
| **C**（构造性覆盖）| `plate_ablated`、`home_ablated`（源文本 113 字符逐字节相同，结论靠"输入未变"的元数据，不是重算）|

### 一条报错只能指向一个正确动作（三条独立拒绝点 + 一条拆分）

| 构造 | 拒绝点 | 报错指向的正确动作 |
|---|---|---|
| 列缺失 + **未**声明消融 + 名字在层 1 存在 | schema 观测 | `SCHEMA ACCIDENT`（这是 schema 事故，不是链接问题）|
| 列缺失 + **已**声明消融 + 名字在层 1 存在 | 路径声明 × 层 1 存在性 | 「声明本身有误，检查 `ablate_db` 路径」——**句中不含 `m2_link`** |
| 列在、`registry_source_id` 为 NULL + 名字在层 1 存在 | 层 1 存在性 | 「未链接，跑 `m4_layer2_link.py --apply`」（这**才**是链接问题）|
| 注册库不可用 | 入口 `ensure_db` | `OriginError` 含路径与原因 |

**判据**：一条报错只能指向一个正确动作。两种情形共用一个消息，消息必然对其中一种是错的 ——
所以第 2/3 行是**两条独立错误**，不是「同一句 + 一句免责」（免责留着，动作串还在，人照样会照着跑）。
验收断言同时要求：① 必须出现新的"声明有误"错误；② 该文案里**不得出现** `m2_link --apply`。

### `:80` 的 `except sqlite3.OperationalError` 登记（两件事都要写）

① **它不决定豁免** —— 豁免由「路径声明 + schema 观测」两个独立信号共同决定，不一致即抛；
② **下游由 D3-1 的 CHECK 兜住** —— `CHECK (text_origin IS NOT NULL AND ((text_origin LIKE 'declared_synthetic:%') = (synthetic = 1)))`，
误触发会产生前缀与旗标不一致的行，落库当场被拒。**它不是第二个豁免入口。**
