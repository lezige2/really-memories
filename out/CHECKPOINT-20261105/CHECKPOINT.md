# 任务检查点（2026-11-05 02:12）

## 关机
- 方式：`shutdown /s /f /t <remaining>`，目标 **2026-11-05 03:50:00**
- 2026-11-05 02:14:37 重新下发，剩余 5722 秒；系统提示“已计划系统关机(1190)”
- 取消：`shutdown /a`
- 注意：此前 Task Scheduler 任务已删除；当前是 shutdown 定时器，不是计划任务。

## 版本
- HEAD：`071d2e3 fix(p1): superseded 归档 + archive-days + 低置信 fallback`
- 全量默认代码：`116f0f3`
- ahead：**99**，0 push
- 版本：`v1.0.0-rc1`

## 服务/数据
- 服务已停：8765 无监听；最后运行 PID 16864，healthcheck PASS。
- daily：20 源/20 块；`memory_access/memory_archive` 已建；`memory_source` 无新列。
- daily DB sha：`c27952324b762239…`；备份 `out/p1-enable/chat.db` sha `f540a023…`。
- 默认 5 项 **on**：cap / access / archive / fallback / audit；archive 首次确认 **未签**。
- id14 为 `reconstructed`（原块误删、Qwen 重建；非字节等价）。

## 验收证据
- 81 81/81；extra 17/19（剔 L05；L07/L09）；MT20 5×2：全关 55/100、全开 **51/100**（−4pp，无 case 崩落）。
- 199/200/201 边界 PASS；100 行 archive/fallback/reheat PASS；6 链 action 6/6；rollback drill PASS（刚跑，sha 一致）；audit trace PASS。
- 启动/重启后 healthcheck PASS；`START.md` 唯一命令。
- 已知边界：`out/KNOWN-LIMITATIONS.md`。

## 3:30 前收尾（待执行）
1. 3:30 前不再开新测量；
2. 把 goal 置 **pause**；
3. 保留工作区（不要 `git clean`）；
4. 3:50 自动关机。

## 恢复
```powershell
cd D:\llama-mem
python -X utf8 tools/healthcheck.py
python -X utf8 tools/chat_service.py --db kvmem/daily/chat.db --blocks kvmem/daily/blocks --sessions kvmem/daily/sessions --host 127.0.0.1 --port 8765 --retrieval topk --topk 4 --n-gpu-layers 28 --model "D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"
```
首次真实归档前需用户亲自 `--confirm-first-archive`；20 条库不会触发，验证要用副本回拨 created_at。