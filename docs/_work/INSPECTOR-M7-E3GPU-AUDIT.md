# M7 E3-GPU (a) 独立复核（只读；零 GPU/不跑模型/不 git）

**对象（现场实算）**：`M7-E3-GPU.json = 36c5bf21/14,400`；`LANDED-m7-e3-gpu.json = 09e767fe/4,662`；`PREREG = e75a425b/8,833`；`_e3gpu_llama.log = 634805eb/508,547`；`_e3gpu_run.py = cf152370/35,684`；`sampler = 522b0c60/881`；`_e3gpu_stop.flag = 55f5b8ff/13`；`_e3gpu_peak.txt = 64dc11d7/10`。
**范围**：只审 `(a) 无 SIGKILL`；kill 子臂仍 `未做（主机不安全）`，本件不碰。

## 0. 一句话结论

**不可签（发布件）**：四场景读数本身站得住，但 `host_safety` 写 3≠现场 5、`minidump` 字段无 runner 生成链、S1 raw log 被删；**修完 B1–B3 后可签 E3-GPU (a) 的四场景结构读数**。**无论是否修，都不可签为 kill 臂或完整 E3。**

## 1. 装置自证

- **`offloaded 36/49` 真在原始日志**：`_e3gpu_llama.log:1482` 原文 **`load_tensors: offloaded 36/49 layers to GPU`**；同段 `:1481` 为 `offloading 35 repeating layers`、`:1480` 为 `offloading output layer`。**成立。**
- **但该日志只保留最后一个 child（S4）**：`_e3gpu_run.py:507` 每个 `run_child` 开始先 `unlink(_e3gpu_llama.log)`。S1/S2/S3 的**原始日志已被删**；S1 的 `E3META` 只存在于主产物 `S1-save.meta`（child stdout），不能回到 S1 的 raw log 复核。**G1（不阻塞读数，阻塞“原生日志全覆盖”措辞）。**
- **`n_gpu_layers_readback` 不是输入回显**：`meta_from_log()`（`_e3gpu_run.py:268`）从 DLL log callback 的 `_LOG_LINES` 正则取 `offloaded (\d+)/(\d+)`；取不到时为 `None`，不会填 `36`。**成立。**
- **`vulkan_imported` 不是 shim 返回值，也不是硬写**：`_e3gpu_run.py:97-98` 在 child 里调用 `GetModuleHandleW("vulkan-1.dll")`；**实际进程模块检查**，与 PREREG §1 写的检查一致，但不是 shim API 返回。**成立（证据等级：进程级，不是 shim 级）。**
- `device.dll = 9edbafa1/50,007,552`、model `8,988,110,240 B`、`n_gpu_layers=36/n_ctx=8192/n_seq=8/kv=q8_0/CHAT_START=4096` 均与 PREREG 对得上；`vram_peak_max=7.3553 GiB ≤8.6`。

## 2. S1 正常往返

- **不同进程成立**：save `child_pid=5376`，load `6332`；父进程每场景 `Popen` 独立 child。**成立。**
- **load 没有先 prefill**：`child("s1_load")` 只做 `ss.restore_session(...)`，没有 `write_at/build_chat_189`；`load_s=4.236`。**成立。**
- **读回三者**：save `n_tokens=189/pos_max=4284`，load `n_tokens=189/pos_max=4284`；`chat_bytes=19,744,884` 两侧一致。**引擎侧 n_tokens/pos_max 是真实读回，成立。**
- **但 `chat_sha16` 两侧都是文件字节 `sha16(chat)`**（`_e3gpu_run.py:322/346`），**不是加载后引擎内容的哈希**；S1 也没有 decode/输出对比。**能证明“文件未被改写 + 结构计数一致”，不能证明 KV 语义内容一致。G3（不阻塞结构往返，阻塞“内容往返”措辞）。**
- **原子写形态是实测不是推断**：父 watcher `time.sleep(0.02)`（`_e3gpu_run.py:514-521`）轮询 `*.tmp-*`；`tmp_seen=true`、`tmp_pattern=s1.chat.kvmem.tmp-5376-3b8cef37`、`tmp_cleaned_after=true` 均由该 watcher/事后 glob 得出；`target_existed_before=false` 在 child 启动前实测。**成立；20 ms 属实。**

## 3. S2 tail 注入

- **差 1,024 B 成立**：`s2_tail.chat.kvmem` 实测 `19,745,908`，manifest `chat.bytes=19,744,884`，差恰好 1,024；文件为 `s1` 副本尾部追加 `b"\x00"*1024`（`_e3gpu_run.py` s2 分支）。**成立。**
- **`LayoutMismatch` 在 reset 之前**：`session_state.py:359-389` 先 `os.stat` 比较 bytes，不等即 `raise LayoutMismatch(... refusing before reset)`，之后才 `eng.reset(0)`；`run.py` 在 restore 前后包装 `reset/load/load_strict` 计数，`reset_calls=0/load_calls=0`。**异常类型/顺序真实。**
- **哨兵 7/6 是引擎真实状态**：`eng.reset(0); sent_n=eng.write_at(0,"a a a a a a a",0)` 后读 `eng.n_tokens/pos_max`；before/after 都是真实 API 读数，不是常量。**成立。**
- 唯一弱点：`S2` 的 `pass` 只要求异常名含 `LayoutMismatch`、reset=0、before/after 相等；**没有单独校验异常文本的 “before reset”**，但异常原文已记录且与源码一致。**G4（轻微，不阻塞）。**

## 4. S3 老格式 / S4 fixture

- **S3 恰 1 条**：`s3_old.json` 实测无 `chat.bytes`（`1,177 B`）；restore 走 `session_state.py:363-378` 的 `_emit_unvalidated`，`events=1`、`event_lines[0].event="chat_unvalidated"`、`reason="missing_chat_bytes"`、`actual_bytes=19,744,884`、`expected_bytes=null`；**原件 `s1.json`（有 bytes）同引擎再 load：`original_load_ok=true`、`original_events=0`。成立。**
- **S4 带 bytes 且 verified**：`s4.json` 实测 `chat.bytes=19,744,884`，`s4.chat.kvmem` 与 `s1` 同 sha `6a2508d4`；`restore` 返回 `chat_bytes_verified=true`、`events=0`。**成立。**
- **但 S4 是 `s1` 的副本改名**（`run.py` s1_save 分支 `shutil.copyfile` 后改 `chat.state`），不是独立构造的新 14B fixture。**它仍验证“带 bytes 的正常 load”，但没有独立分母。G5（不阻塞，需改 wording）。**

## 5. 主机侧 / 越界 / 重写 / 残留

- **boot id 与现场一致**：实测 `LastBootUpTime=2026-10-26T03:24:52.5+08:00`，与 `boot_id_before/after` 完全相同，`voided_by_reboot=false`。**成立。**
- **Minidump 与现场一致**：`C:\Windows\Minidump` 实测 **5 份**，最新 `03:24:55.769`；与 `minidump_existing_count=5 / latest=03:24:55` 一致，`minidump_new=false` 当前为真。**成立。**
- **`host_safety.bsod_incidents` 写 3，实际今晚 5 次**：**事实错误（少记）**；Minidump 5 份也与“5 次”吻合。**B1（发布前必修，非读数阻塞）。**
- **`minidump_new`/`minidump_existing_count` 不是 `_e3gpu_run.py` 算的**：该脚本只在 `:636` 初始化 `"minidump_new": None`，全文没有任何 Minidump 检查/赋值。主产物中的 5/03:24:55/false 是**后补字段**；我现场复核为真，但**生成链缺环**。**B2（发布前必修：补 host_check 命令与时间）。**
- **没有把 (a) 写成 kill 臂**：`kill_arm="未做（主机不安全）"`、`scope="只覆盖无 kill 子臂"`、无 kill 通过字样；也没有 GPU 通用性能结论（只有 VRAM 峰值）。**成立。**
- **scope 重写**：当前主产物 `36c5bf21/14,400`、台账 `09e767fe/4,662`；较上一版 `14,371/4,633` 各 +29 B。当前 `scope` 与任务原文一致；**没有发现读数变化**（四场景读数、PIDs、哈希、峰值均与当前文件/日志/现场一致）。旧字节未保留，无法做逐字节 diff；按 lead 口径记**不阻塞重写项**。
- **`_e3gpu_stop.flag` 仍残留**：实测内容 `scenario_done`（13 B）。`run_child` 在**每次正常 child 启动前** `STOP.unlink()`（`:502`），下一轮父进程不会误读；但直接启动 child 会看到残留。**G6（不阻塞，建议 run 结束清理）。**

## 6. 失败尝试 / attempts

- 主产物与台账均**无 `attempts[]`**；`run.py` 是单次顺序执行，没有 retry/backoff。executor 自报“前一版守护器 argtypes bug 失败后修正重跑”，当前产物只有最终版本，failed attempt 的日志/产物已被覆盖。
- **未发现失败尝试读数混入最终四场景**：最终 `S1-S4` 的 child PID、`at` 时间、`s1.json` 保存时间（08:05:50）、最终日志 mtime（08:06:13）同一轮；main `at=08:05:44` 为 run 起点。**G7（不阻塞，但缺 `attempts[]` 透明度）。**

## 7. 缺口分级

**发布前必须修（不改读数）**
- **B1**：`host_safety.bsod_incidents=3` → **5**（事实错误，少记）。
- **B2**：`minidump_new/existing_count/latest_mtime` 无 runner 生成链；补 `host_check` 命令、执行时间、原始输出，或把字段移到 `host_checks` 并标 `post_run_manual`。
- **B3**：S1/S2/S3 的 raw log 被 `:507` 删除；**保留每个 child 的独立日志**，或至少保留 S1 的 `offloaded` 原始行 + sha，不得只用 `E3META` 回填。

**不阻塞，但应改措辞/留痕**
- **G1**：raw log 仅 S4；S1 `E3META` 为 child stdout，非 raw log 留存。
- **G3**：S1 `chat_sha16` 是文件哈希，不是引擎内容；S1 只证明结构往返，不是 KV 语义往返。
- **G5**：S4 是 S1 副本，不是独立 fixture。
- **G6**：`_e3gpu_stop.flag` 残留 `scenario_done`；建议父进程结束 `unlink`。
- **G7**：无 `attempts[]`；补失败尝试时间/错误/是否产生产物。
- **G8**：S1 `vram_peak=7.3553` 的 raw `_e3gpu_peak.txt` 已被 S2 覆盖，只剩最终 `7.3165`；建议每场景单独 peak 文件。
- **G9**：`vulkan_imported` 是 harness `GetModuleHandleW`，不是 shim 返回；建议产物字段名写 `vulkan_module_loaded`。
- **G10**：scope 重写 +29 B；建议记录旧版 sha/变化说明。

## 8. 签字句与最小修正

> **不可签（发布件）：四场景读数本身站得住，但 B1–B3 未修（host_safety 3≠5、minidump 无生成链、S1 raw log 被删）。修 B1–B3 后可签 E3-GPU (a) 的无 kill 四场景结构读数；仍不可签 kill 臂、完整 E3、或“KV 语义内容往返”。**
> **不需要重跑 GPU**；修正只涉及主机字段、日志留存和 attempts 留痕。

**最小修正动作**：把 `bsod_incidents` 改 5；补 `host_check` 的 Minidump/boot 命令与时间；每 child 保留独立 `_e3gpu_llama.log`（或至少保留 S1 的 `offloaded` 行）；在 `LANDED` 增加 `attempts[]`（failed argtypes attempt，无产物进入最终读数）；清理 `_e3gpu_stop.flag`；S1 的 `chat_sha` 标注“file_hash_only”，S4 标注“copy_of_s1_fixture”。