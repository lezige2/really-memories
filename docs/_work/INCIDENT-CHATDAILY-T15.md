# INCIDENT-CHATDAILY-T15（P0：chat_daily 17 个方法丢失 / 服务 500）

- 事故单：task-32 / T15（结构化槽位）
- 主责：b6-designer（本文件作者）
- 状态：`chat_daily.py` 未复原（无可用副本），按 LEAD 决定转交 rev7-impl 重建；本单不再改 `chat_daily.py`
- 现行文件：`tools/chat_daily.py` **117,037 B / sha16 `a55930d19218563b`**（22:38 起未再变化）
- 完好件：`tools/memory_service.py` **27,982 B / sha16 `7dcc62a0bae75cfc`**（12 键槽位 API 全部在）

## 1 时间线与事实

| 时间（2026-10-27） | 事件 |
|---|---|
| ~22:25–22:38 | 我在 `chat_daily.py` 做 T15 槽位接线：`daily_memory_meta.slots`（含迁移）、`_meta_get/_meta_set/_slots_of`、`_insert_memory_block` 写 slots、`_retrieval_select`/`_retrieval_keyword_fallback` 槽位过滤+加权+排序、`_ask_natural` 检索路径复用。 |
| 22:38 前（最后一次我的自检） | 文件 148,942 B / sha16 `999bddd12bbfcf0e`；12 个 CPU 测试轮跑：`test_slots_cpu` 43/0、`chat_daily` 93/0、`retrieval` 35/0、`memory_graph` 41/0、`refusal` 31/0、`rollover` 33/0、`logging` 29/0、`openai` 37/0、answer_verifier 全 0。随后按 task-32 rev3 把该 sha 发 rev7-impl，请其 review/接 `_ask_natural`。 |
| 22:38:xx（之后） | 文件被并发写入覆盖为 **117,037 B / `a55930d19218563b`**：保留了 rev7-impl 的新方法（`_canon_slots/_augment_slots/_canon_qslots/_verify_run/_chat_prompt/_ask_natural` 等），但 `_rows` 到 `_web_answer` 的旧核心方法段整体丢失（17 个 `self.xxx(` 无定义）。 |
| 22:40 | LEAD 报警：`/health`、`/ask` AttributeError；服务停。 |
| 22:40–22:51 | 尝试恢复（均未成功，见 §2）：git 全对象扫描、D 盘/备份/临时目录副本搜索、`__pycache__` pyc 检查。文件保持未变；按 LEAD 指示转交重建。 |

## 2 恢复尝试（为什么没恢复）

1. `git`：`tools/chat_daily.py` 从未入库（`??` 未跟踪），`git cat-file --batch-all-objects` 扫 blob 无 `class DailyApp`/`_local_time_reply` 内容 ⇒ 无 git blob 可回。
2. 全盘副本搜索：`D:\llama-mem`、`D:\llama-mem-backup-2026-10-25`、`D:\llama-mem-stage`、`D:\llama-mem-verify-clone`、`D:\tmp`、`D:\crashfix`、`D:\compare-verify`、`%TEMP%`、用户目录（40KB–3MB 文本文件）中**没有**含 `def _local_time_reply` 或 `class DailyApp` 的其它副本；`tools/` 下无 `.bak/.orig`。
3. `tools/__pycache__/chat_daily.cpython-314.pyc`：header `source_size=117037`，即坏版本编译产物，不含旧方法源码（Python 3.14 无可用反编译器；即使有也未保留行级源码）。
4. 结论：**没有原样副本**；继续在我这边“重写 16 个方法”既耗时又可能与 rev7-impl 正在重建的版本冲突，按 LEAD 指令停手。

## 3 根因（主责在我）

- **直接触发**：同一文件并发 read-modify-write + 最后写入基于被截断/部分合并的内容。我在 `chat_daily.py` 上做的是“`read_text()` → 字符串替换 → `open('w').write()`”，**没有**按项目纪律用 `tmp + os.replace` 原子替换，也没有写前 `.bak`；同时 rev7-impl 正在同一文件加 `_canon_slots/_augment_slots/_canon_qslots/_verify_*` 等自然模式/核对接线。两个写者交错时，最后一次落盘保留了新方法段、丢掉了旧核心方法段（117,037 B），而我在 22:38 的自检跑在**覆盖之前**的 148,942 B 版本上。
- **次级触发**：线程/任务书让我“把 sha 发 rev7-impl 请其 review/接线”，但我没有先声明文件独占/加锁，也没有告诉对方“我会再动”；对方也没有等我的完成信号就写了同文件。
- **为什么自检漏检**：
  1. `import chat_daily` 仍成功（缺失方法只在调用时 `AttributeError`）；
  2. 我只在自己编辑后跑了一次全测，之后**没有重读 sha/mtime** 复核最终状态；
  3. 测试覆盖不全：natural 模式路径没走到 `_sync_mounts/_sync_mounts/_web_answer/_explicit_search` 等；
  4. 没有做“`self.xxx(` 调用 vs `def xxx` 定义”的 AST 差集断言；
  5. 没有 fake-engine + 服务级 `/health` 冒烟；
  6. 没有保存“编辑前版本”的哈希/副本链，事故后无法回退。

## 4 改进（3 条，写死）

1. **共享文件写盘纪律**：改动前先产出 `tools/chat_daily.py.bak.<YYYYmmdd-HHMMSS>`（并记 sha16/字节）；写入一律 `tmp + os.replace`；写前/写后各打印 sha16+字节。编辑前在 team board 声明“文件独占 + 预计时长”，完成后再释放；同文件任何新写者必须先重读 sha 并回一句。
2. **交付前强制 gate（脚本化，缺一不交）**：① AST 断言 `{self.X( 调用} - {def X} == ∅`；② fake engine 冒烟 `ask("你好")`、`ask("我下周三去哪开会？")`、`/status`；③ 跑全部 CPU 测试并记录逐项 rc；④ 记录文件 sha16/字节并与上一步一致；⑤ 服务级 `/health` 冒烟由 LEAD 重启后验（我不重启服务）。
3. **并发与回滚**：任何共享文件被并发修改（mtime/sha 变化）⇒ 立即停手、不覆盖、报 LEAD；LEAD 指定唯一写者并保留 `.bak` 链；服务只由 LEAD 重启，避免坏文件直接上线。

## 5 影响面与交接

- 数据/会话：未重启 8765、未清 eval2 会话；`kvmem/` 数据未动；仅 `chat_daily.py` 代码受损。
- 可复用成果：`tools/memory_service.py` 完好（12 键槽位 API），**不需要重写**；`tools/test_slots_cpu.py` 43/0 仍可对重建后的 chat_daily 复跑。
- 交接：rev7-impl 以现有测试为规格重建 `chat_daily.py`；槽位接线片段见 `docs/_work/T15-SLOTS-SNIPPETS.md`（本文件附件），有冲突以 rev7-impl 已有 `_canon_slots/_augment_slots/_canon_qslots` 设计为准，不重复定义。