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

## 边界

- **未改**：`tools/chat.py`、`tools/kvslots.py`、`kvmem/m2_visibility/m5/m5_ground.py`、`kvmem/m2_visibility/m4/m4_memory.db`（M4 三锚仍 MATCH，见 `m4/README.md §19.10`）。
- **未做**（按 lead 分工）：Stage 1b（层 2 加 `registry_source_id`/`source_hash` 两列、子串断言、`text_origin` 改写）、Stage 2（chat.py 改读库）、Stage 3（M5 改读库）、R14（省份词表）、C5 那四个平行版本。
- 层 2 现在的缺口照实记在 `run_registry_check.json::consumer_coverage`：`m4/m4_memory.db::memory_source` 只有 `id,name,label,text,fanout` —— 无 hash 无注册表 id；
  `_m5db/m5_m4_blocks.db::text_origin` 是字面量 `m4.memory_source.text`，不是 `(id, sha)`。
