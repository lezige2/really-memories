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

### 负向测试：注释/常量已经不是依赖

1. `grep -c MEMORIES tools/chat.py` -> **0**；`git show HEAD~1:tools/chat.py` 里是 2 处（循环 + 计数）。
2. 把删掉的常量**投毒**回去再建块（`chat.MEMORIES = [("poison","坏","这句话永远不该被索引。")]`）：
   实测输出 `indexed 2 sources + 2 blocks`、块目录只有 `profile.kvmem` / `project.kvmem`、
   `rows named poison: 0`、`indexable` 仍是 `[profile, project]`。
   => 常量即使存在也**没有任何代码路径读它**。
3. 空库：`indexable_sources` 为空时 `die(...)` 退出，不会建出空索引冒充成功。

### 锚

`chat.db`：`a699fd1e5aaa9adf` -> **`5909b978e31e584a`**。
变的只有 `memory_block` 的派生状态（`built_at` / 路径重指回 `kvmem/blocks`）；
`memory_source` **一行都没动**：10 行、`profile d3e57f11838e6bf8/61`、
`project aa9769adb3cb4493/45`、`conv_2026-10-25 d8c094c1f5fcb8f1/127`、7 条摘录。
`m4_memory.db fd244c80c0cc974d` / `run_m4_verify.json 857f13c514ad233e` 未变 => **M4 验收仍有效**。

### 残留的真实依赖（不粉饰）

`chat.py` 仍需要注册表**里有**那两行文本才能建块 —— 这是正确的依赖方向（源 -> 派生），
不是"换了个地方依赖常量"。真正的残留风险是 `indexable_sources` 的过滤条件写错，
它由 `m4_layer2_link.py` 的 `text_kind` 断言与 `check_m5_gate.py` 的选源扫描共同看住。
