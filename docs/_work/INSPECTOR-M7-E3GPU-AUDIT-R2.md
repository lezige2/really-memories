# M7 E3-GPU (a) 复审 R2（task-50 重跑；只读，零 GPU/不跑模型/不 git）

**旧审计**：`docs/_work/INSPECTOR-M7-E3GPU-AUDIT.md` = `e6a58bf315680610` / 9,705 B（保留不改；其结论“不可签发布件、B1–B3 必修”）。
**本轮对象（现场实算）**：`M7-E3-GPU.json = e6b03da6f75cb851 / 30,561 B`；`LANDED = cebe77646204a173 / 9,827 B`；`_e3gpu_run.py = 2c166ec71921585b / 48,970 B`；`sampler = 522b0c60/881`。
**旧→新**：主产物 `36c5bf21/14,400` → `e6b03da6/30,561`；台账 `09e767fe/4,662` → `cebe7764/9,827`；B1–B3 修复轮。kill 臂仍 `未做（主机不安全）`。

## 1. B1：5 次 + 5 份 dump —— 真修，值/枚举与现场一致

实测 `C:\Windows\Minidump` 与 `host_safety.minidump_files` **逐项一致**（名称/字节/mtime 全等）：
`102626-5187-01.dmp 2,201,077 @01:31:36.2997028`；`102626-4468-01.dmp 1,994,809 @01:38:56.5625530`；`102626-4593-01.dmp 1,063,617 @01:56:32.6758278`；`102626-4437-01.dmp 2,062,496 @03:10:17.4578327`；`102626-4671-01.dmp 2,043,758 @03:24:55.7693314`。**5 份、无多无少。**
`host_safety.bsod_incidents=5`，与 lead/现场“今晚 5 次”一致；`minidump_count=5`。
**保留意见 G1**：`bsod_incidents=5` 和 `incidents` 的 bugcheck 列表（0xA/0xA/0x44/0x144/0xA）仍是源码硬写，不是从 dump 推导；本次值对，但换主机就会错。**非阻塞。**

## 2. B2：host_check 命令/原始输出/rc/时间 —— 真修；before/after 真推导

`_e3gpu_run.py:162-220`：`_ps_raw()` 实跑 PowerShell 并保存 **`command/rc/collected_at/stdout/stderr`**；`host_check()` 分别跑 `Get-CimInstance Win32_OperatingSystem.LastBootUpTime` 与 `Get-ChildItem C:\Windows\Minidump`；产物 `host_check.before/after` 均有四件套：
- before `08:23:00`、after `08:23:48`；boot 命令 rc=0、dump 命令 rc=0；stdout 原始 JSON 均在。
- **`derive_host_state()`（:190-220）**按 `name+bytes+mtime` 做 before/after 差集：`minidump_new = bool(new)`、`voided_by_reboot = boot_before != boot_after`；`finish_host()`（:828-842）把结果写入 `reboot` 与 `host_safety`。**没有 `minidump_new`/`voided_by_reboot` 的硬写分支。**
- 实测 `LastBootUpTime=2026-10-26T03:24:52.5000000+08:00` 与 `boot_id_before/after` 完全相同；`minidump_before_count=5=after`、`minidump_new=false`、`new_files=[]` 与现场一致。**B2 成立。**

## 3. B3：五个独立日志 —— 真修

五个文件均各自含 **恰好 1 条** `load_tensors: offloaded 36/49 layers to GPU`，全部在 **第 1482 行**：
`S1-save 71f4c7cc/508,495`、`S1-load 0561baa9/508,547`、`S2 07a02d3d/508,444`、`S3 1961d4f7/508,650`、`S4 ade0e9a2/508,547`；**sha16/字节与产物 `raw_logs` 逐项一致（自己算）。**
源码 `run_child`：每场景 `log_path = _e3gpu_log_<scenario>.log`，**只 `touch(exist_ok=True)`，没有 unlink/truncate**；child logger 用 `open(log_path,"a")`（`:288-289`）。**无覆盖、无删除。**
保留：若同场景二次运行会向旧日志**追加**，可能累积两条 load；本轮是首次使用这些文件名，五份各 1 条，未混。**非阻塞。**

## 4. reproducibility：独立重跑成立

**pid 全换**：S1-save `11812`（上轮 5376）、S1-load `10180`（6332）、S2 `10192`（6512）、S3 `5900`（8072）、S4 `6468`（7100）。
**时序/峰值也换**：S1-save `elapsed 16.45 s / load_s 7.734 / vram 7.3878`（上轮 `6.73 / 4.271 / 7.3553`）；S1-load `5.43 s / 4.453`（上轮 `4.236`）。
**日志独立**：五份新日志，各含独立 load；`s1.json` 的 `saved_at` 从 `08:05:50` 变为 `08:23:22`。
`chat_bytes 19,744,884 / chat_sha16 6a2508d4df79fa57 / n_tokens 189 / pos_max 4284` 与上轮全 match —— 这是 14B GPU 推理同一几何下**字节级确定性**，不是抄旧数字：pid、时间、峰值、日志、manifest 时间戳全部为本轮新值。**可信。**

## 5. 两个新变化点

- **S1 `target_existed_before=true`**：因上一轮 `s1.json` 残留；本轮 `tmp_seen=true`、`tmp_pattern=s1.chat.kvmem.tmp-11812-0a07ddcb`、`tmp_cleaned_after=true`，`saved_at` 变新。**原子写形态结论不变**（temp+rename 覆盖旧 target 仍成立）；但它不是“从无到有”测试，上一轮 false 的创建场景本轮未重测。**非阻塞，建议注明。**
- **manifest 变化只由 `saved_at` 引起**：把本轮 `s1/s2/s3/s4` 的 `saved_at` 换回 `08:05:50` 后，sha16 分别精确回到旧值 `a50b0040/65d5507f/48545bf5/bad358e1`；本轮为 `f808aa43/f2aa84c1/a6cdf140/bfc92ffd`。**S3 `source_manifest_sha16=a6cdf140` 同理，只是时间戳；四态不受影响。**

## 6. device_prep：合规，但 `signals_sent_by_parent` 必须按 GPU child 读

- `authorized_by="user (ask_user_question option B)"`；`action=close_browsers`；方法 `CloseMainWindow→Stop-Process(msedge only)`；**14 个 pid 全留痕**（3188/4172/4632/5192/5564/6464/7364/8236/8528/9944/10032/10928/11232/11960）；before=14、graceful 后=8、force 后=0；`force_used=true`；`other_processes_touched=false` —— **命令全部只针对 `Get-Process -Name msedge`，没有碰其他进程。**
- **但**：`device.signals_sent_by_parent=false` / `LANDED.parent_signals_sent=false` 在本轮字面上不覆盖 device_prep——父进程确实对 msedge 执行了 `Stop-Process -Force`。`device_prep_note` 已限定“只描述 GPU child”，故**语义上成立**；字段名仍有歧义。**G2：建议改名 `gpu_child_signals_sent=false`。非阻塞。**

## 7. attempts / hash_semantics / stop.flag

- `attempts[]` 已落实：attempt#1 `08:04:00 failed`（argtypes OverflowError，`artifacts=[]`、`readings_used=false`）；attempt#2 `08:22:44 completed`（本轮）；最终读数只来自本轮。
- `hash_semantics` 明写 `chat_sha16` 是文件字节哈希、S1 只证结构；`s4_fixture_note` 明写 S4=S1 副本改名。**G3/G5 已按旧审计落实。**
- `_e3gpu_stop.flag` 现场**已不存在**；源码结束时 `STOP.unlink()`（`:1010`）。**G6 已清理。**
- 每场景 peak 独立文件：S1-save 7.3878、S1-load/S2/S3 7.3490、S4 7.3490；**G8 已落实。**

## 8. 缺口分级

**无阻塞（可签）**
- 以上 B1–B3 均实修；四场景读数、独立日志、主机现场、reproducibility 均站住。

**非阻塞（发布前建议补/注明）**
- **G1**：`bsod_incidents`/bugcheck 列表硬写；本次值对，建议由 `host_check` 推导或标注“人工维护”。
- **G2**：`signals_sent_by_parent=false` 仅对 GPU child 成立；实际父进程 force 关了 msedge。改字段名或加显式 scope。
- **G3**：S1 `target_existed_before=true`；原子写成立，但从无到有未重测。
- **G4**：S2/S3/S4 场景对象缺 `elapsed_s/meta/atomic_shape`（S1 有），schema 不齐；不影响判据。
- **G5**：`host_safety.incidents` 的 bugcheck 码不是 host_check 生成，来自人工记录。

## 9. 签字

> **可签：E3-GPU (a) 无 kill 子臂的四场景结构读数（B1–B3 已实修；独立重跑；kill 臂仍 未做）。**
> **不可签：kill 臂、完整 E3、KV 语义内容往返。** G1–G5 仅留痕/改字段名，不需要重跑 GPU。