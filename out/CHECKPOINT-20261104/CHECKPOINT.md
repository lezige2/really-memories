# 任务检查点（2026-11-04 22:24）

## 关机
- 命令文件：`out/ops/shutdown-0350.cmd`
- 计划任务：`DSH-P1-Shutdown-0350`
- 下次运行：**2026-11-05 03:50:50**（本机时间）
- 动作：`shutdown /s /f /t 0`

取消：
```powershell
Unregister-ScheduledTask -TaskName "DSH-P1-Shutdown-0350" -Confirm:$false
```

## 仓库
- HEAD：`7fbf3e6 docs(p1): 开启运行手册...`
- ahead 93，**0 push**
- 工作区：**1000+ 项未提交**（P1 全量默认代码、证据、临时件）
- 本次检查点：
  - patch：`out/CHECKPOINT-20261104/p1-worktree.patch`（280,822 B）
  - stash（仅 tracked）：`f548d827a7bb1982c7b809534fa4c74a5654da1e`
  - stat：`out/CHECKPOINT-20261104/p1-worktree.stat`

> 注意：patch/stash 只保存 tracked 变更；大量 untracked 证据仍在磁盘。关机不丢盘，但**不要 git clean**。

## 当前代码/默认状态
- 工作区代码：**cap/access/archive/fallback/audit 默认全 on**（未 commit、未在服务运行）；
- **现网 daily 未切默认**：无服务；daily 仍是 20 行，默认行为由未提交代码决定，重启前需确认。
- 已备份：`out/p1-enable/chat.db`（sha `f540a023…`），daily 当前 `dcd60893…`。
- P1 技术门 6/6；四条保护已实现（soft/hard、首次确认、manifest/restore、audit 默认决策类）。
- **未完成**：全量默认上现网前的 V9MT04 双侧验证；C2 正在跑，结果未出。
- daily id14 为 `reconstructed`；逐字节比对作废。

## 3:50 前收尾（待执行）
1. 等/停 C2，保存最终结果；
2. 再生成一次 patch/stash（覆盖本文件）；
3. 把 goal 置 pause；
4. 更新 HANDOFF（P1 默认是“代码已改、未验证/未启用”还是“已回退”）；
5. 不再改码。

## 恢复方式
```bash
cd /d/llama-mem
git apply out/CHECKPOINT-20261104/p1-worktree.patch   # 若工作区已丢
# 或 git stash apply f548d827...
```
先读本文件与 `HANDOFF-2026-10-31.md` §24/§25，再决定是否继续默认验证。