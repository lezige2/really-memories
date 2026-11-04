# 事故记录：daily 块被副本测试误删（2026-11-04）

## 1 事故摘要
- 时间：2026-11-04 17:2x；
- 对象：`kvmem/daily/blocks/mem-327723633d2d.kvmem`（source_id=14，文本「补充一个事实：我养的猫叫豆豆。」）；
- 操作：C2 用 daily 副本验证回热时，副本 `chat.db` 的 `memory_block.path` 仍是 daily 绝对路径；脚本按该路径删块，误删 daily 原块；
- 影响：daily id14 块缺失；DB `memory_block` 行仍在；服务 ask 该事实会报 incompatible / 缺块。

## 2 恢复尝试与结论
- 仓库找到 24 个同 id/同尺寸副本，sha16 `23d5d2ab…`；恢复到临时副本后服务报 **incompatible**：这些块由旧模型（DeepSeek-R1-Distill-Qwen-14B）生成，与 daily 当前 Qwen2.5 不兼容；**不能作为原块恢复**。
- 用 **Qwen2.5 真实引擎**按原文重建 id14 块；服务实测「我的猫叫什么？」→「豆豆」、`block_ids=[14]`、`verified=true`。
- 重建后 daily：20 source 行 / 20 block 行 / 0 缺失；块 sha256 `4cdd576d…`、1254756 B。
- **非字节等价**：原块不可得；只能证明同文本、同 Qwen 模型、服务可挂载。

## 3 数据状态（必须如实引用）
- daily DB sha：原 `0a7eae49…` → 现 `dcd60893…`；
- 变化原因：`memory_block` 的 built_at/model_path/model_size/model_mtime 更新（重建）；
- `memory_source` 行数仍 20；未删行、未改文本；
- 备份：`out/incident-20261104/chat.db.pre-restore`、`blocks.pre-restore/`、`mem-...rebuild-before-repair.bak`；
- 审计：`out/audit/20261104.jsonl` 记 `decision=reconstructed`，原因写明原文件不可恢复、Qwen 重建。

## 4 根因
1. 测试隔离缺陷：副本 DB 未重写 `memory_block.path`，仍指向 daily 绝对路径；
2. 删除操作无路径前缀断言；
3. 回热代码使用 `ms.build_block` 默认 `MODEL`（DeepSeek distill），与产品 Qwen 不一致；首次重建写出错误模型块；
4. 8767 出现双监听，两个服务抢 GPU，错误信息叠加，延长定位时间。

## 5 已采取纠正
- `tools/sandbox_guard.py`：`assert_under` / `rewrite_block_paths` / `verify_all_under`；
- 副本测试必须先 `rewrite_block_paths`，删除前断言前缀；
- 回热同族键收紧为 `(subject, event_or_action, place, time, object)`，组会/开会/出差不再同族；
- 回热重建必须显式传产品模型路径，不得用 `ms.MODEL` 默认；
- 双监听规则继续有效：启动前查端口/租约，异常先停旧进程。

## 6 当前可用性
- daily 服务读路径可用；id14 可挂载；其余 19 块未变。
- **该块标记 reconstructed**；此后任何涉及 id14 的逐字节比对结论自动作废，只能做内容/可挂载/问答验证。
- 回热代码仍默认 off、未接服务；本次事故不改变默认。