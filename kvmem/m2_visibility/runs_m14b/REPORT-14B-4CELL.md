# 14B 四格 ×2 + run0 —— 交付报告（executor）

2026-10-25 ｜ 产物 runs_m14b/out/*.json、logs/*.log、evidence_4cell.json、fixtures_14b.json ｜ 主报告

## 0 一句话结论（先把最要紧的放前面）

**10 跑全部通过验收判据；但四格答案彼此逐字节相同。**
E = F = X1 = B57 = `c7d4e377fdc64950…`（同一 24 token 串），只有 run0 不同（`31bff41f…`）。
按预注册「F 也过 ⇒ 规模/分配假设成立」可以直接这么写，但**我认为现在还不能这么写** —— 理由见 §5，请你裁决。

## 1 run0（单块基线，2 跑）—— 通过

| 跑 | cells | pos | 首token | BOS | 内容数 | 答案 | sha16 | fact_ok | control_ok |
|---|---|---|---|---|---|---|---|---|---|
| r1 | 21 | 4075–4095 | 151646 | 是 | 20 | `您住在广陵路 12 号 2 单元 602。` | 31bff41f04341473 | True | True |
| r2 | 21 | 4075–4095 | 151646 | 是 | 20 | （同上，逐字节） | 31bff41f04341473 | True | True |

=> **KV 数值载荷在单块路径上可用**，2x2 有资格开跑。
run0 的控制门禁窗口被显式固定到 3886/210（与四格同一窗口）；驱动的 `iso_home_only` 自身 start=4075 只能容 21 格，
而 control 前缀要 67 token，第一次跑正是因此 `ERROR prefix already 67 tokens > target 21`。
我的处理：只把 control 文本窗口覆写到 3886，**摆放几何一格没动**（pos_lo/hi 仍 4075/4096），并把它记进 run json。

## 2 四格 ×2（8 跑）—— 验收项逐条

| 格 | layout | cells | pos_min–max | gap | control_ok | fact_ok | 答案 sha16 | 两跑同 |
|---|---|---|---|---|---|---|---|---|
| E | iso_dup4 | 69 | 3886–4095 | 0 | True | True | c7d4e377fdc64950 | **是** |
| F | iso_fac_pp18 | 69 | 3886–4095 | 0 | True | True | c7d4e377fdc64950 | **是** |
| X1 | iso_x1_57copy | 57 | 3886–4095 | 0 | True | True | c7d4e377fdc64950 | **是** |
| B57 | iso_fac_nb57 | 57 | 3886–4095 | 0 | True | True | c7d4e377fdc64950 | **是** |

- 每格两跑答案 sha256 相同（5/5 格含 run0）=> 「不稳定·不取其一」**没有触发**。
- `failure_form` = `none`（判据停在第一顺位 fact_ok；未出现空串/复述提问/填空模板/拒答/编造）。
- control 四问（home/project/habit/car）全 True，start=3886 target_n=210 text_sha256 有记录、无一次退化成复读。

## 3 每一格的段几何（含块指纹）

| 格 | slot | block | 文件 | pos_lo–hi | cells | 首token | BOS | 内容 | sha16 |
|---|---|---|---|---|---|---|---|---|---|
| E | 1 | home | home.kvmem | 4075–4096 | 21 | 151646 | 是 | 20 | 73843fc55efd1ab3 |
| E | 2 | project | project.kvmem | 4014–4032 | 18 | 151646 | 是 | 17 | 536eac03f288bb09 |
| E | 3 | habit | habit.kvmem | 3956–3968 | 12 | 151646 | 是 | 11 | f6f8e85cc55bd4b9 |
| E | 4 | project（副本） | project.kvmem | 3886–3904 | 18 | 151646 | 是 | 17 | 536eac03f288bb09 |
| F | 1–3 | 同 E | 同 E | 同 E | — | — | — | — | — |
| F | 4 | **pp18** | project_paraphrase18.kvmem | 3886–3904 | 18 | 151646 | 是 | 17 | a4cf0888467a0f46 |
| X1 | 1 | home | home.kvmem | 4075–4096 | 21 | 151646 | 是 | 20 | 73843fc55efd1ab3 |
| X1 | 2 | project | project.kvmem | 4014–4032 | 18 | 151646 | 是 | 17 | 536eac03f288bb09 |
| X1 | 4 | project（副本） | project.kvmem | 3886–3904 | 18 | 151646 | 是 | 17 | 536eac03f288bb09 |
| B57 | 1–2 | 同 X1 | 同 X1 | 同 X1 | — | — | — | — | — |
| B57 | 4 | **pp18** | project_paraphrase18.kvmem | 3886–3904 | 18 | 151646 | 是 | 17 | a4cf0888467a0f46 |
| run0 | 1 | home | home.kvmem | 4075–4096 | 21 | 151646 | 是 | 20 | 73843fc55efd1ab3 |

`load_and_place` 每段都验过 loaded cells == manifest cells 且 `pos_max == pos_hi-1`，任一不符会 raise；本次无一 raise。

## 4 装置（10 跑逐跑记录，全部相同）

| 项 | 值 |
|---|---|
| model | D:/models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf |
| model size | 8,988,110,240 |
| loaded_path | D:\llama-mem\tools\kvshim_vk.dll（每跑 ctypes `_name` 回读） |
| DLL sha256（实测，每跑重算） | 9edbafa1507006147baad99ea936808b9cbb9ade2874b68d4ab5d83f227b2e5c |
| n_ctx / n_seq / gpu / kv | 8192 / 8 / 99 / q8_0（fa on，经 shim 恒开） |
| bytes_per_token | 104448（= KV pool 每 token 步长） |
| pool_bytes | 855638016 |
| 跑前 free VRAM | 9426 MiB / 10224 MiB（10 跑全部同值，说明跑完确实释放回同一水位） |
| manifest 双重断言 | 打印 path=`…\runs_m14b\fixtures_14b.json`；`P.load_manifest()` 回读 schema=fixtures_14b_v1、sentinel=FIXTURES_14B_V1_SENTINEL_9edbafa1；四块路径全在 m2_v1_14b/ 且盘上 sha 与 manifest 一致 |
| 7B 路径扫描 | 跑前扫 manifest、跑后扫每个 run json：0 命中（禁用标记 = 7B 权重名 / m2_v1/*.kvmem / runs_iso2/control_texts.json） |

## 5 **四格齐一这件事，请你裁决**（本单最要紧的一条）

四格答案完全一样，意味着**被操纵的变量没有产生任何可观测差异**：
- slot4 由 project 副本 换成 pp18 改写 → 答案不变（E vs F）；
- 去掉 slot3 habit → 答案不变（E vs X1）；
- 两者同时换 → 答案仍不变（E vs B57）。

另一方面装置**不是全无分辨力**：run0（只有 home）与四格**不同**（`31bff41f` vs `c7d4e377`），
即「整体加上 2–4 块」会改变输出（人称从 `您住` 变 `我住`，尾部转成 `问：我住`）。
所以分辨力存在，只是在 slot3/slot4 这个方向上测不出差异。

这留下两种互斥读法，**我不代你选**：
1. **无效应**：14B 在 69 格下确实不受第 4 块内容影响 => 预注册结论「规模/分配假设成立」可以落；
2. **未测出·欠功率**：这个装置在 slot4 方向本来就没有分辨力，那么「F 也过」不构成证据 ——
   它不是「14B 扛住了改写」，而是「改写根本没被读」。

注意 7B 当年的区别不在 fact 是否出现，而在**失败形态**（F 出现填空模板改写）。14B 四格连字符串都一样，
说明那个区分 E/F 的标记在 14B 上消失了 —— 这既可以解读为「14B 更稳」，也可以解读为「装置变钝」。
只能靠一个 **slot4 的正向对照** 来分辨，而这一步我没有你的授权不会做。

### 一个不用造新块就能做的分辨实验（等你点头）
四格现有产物就够：在 **F** 里 pp18 正在 [3886,3904)，它的内容是「项目代号叫蓝鲸，三月十四号正式上线」。
若 block4 真被读到，问「项目代号叫什么？」在 **F** 应出「蓝鲸」而在 **E** 不应出（E 的 slot4 是 project 副本）。
=> 出差异 = 装置在 slot4 有分辨力，则四格齐一属「无效应」，预注册结论成立；
=> 仍无差异 = 装置在 slot4 无分辨力，四格应记「实验无效·欠功率」，**不能**记为「假设成立」。
成本 2 跑（约 2 分钟），不动任何已冻结常量、不改任何块。要我做就说一句「做 slot4 对照」。

## 6 `-v` 日志这条，我只能交到这个程度（硬限制，非偷懒）

你要 10 份 -v 日志、自己数 `dev = Vulkan0` 条数。**这条路在驱动侧走不通**，原因是代码级的：
- `kvshim_init_log()` 无条件执行 `llama_log_set(quiet_log, nullptr)`（kvshim.cpp:630-633，quiet_log 在 :52-54 丢弃全部文本），
  `KVEngine.__init__` 每次都调它（kvslots.py:114）；
- 我实测该 DLL **不导出** `llama_log_set`（只导出 KVSHIM_API 符号），所以 Python 侧**无法**抢回日志回调；
- 结论：驱动跑的这 10 次，进程内**不存在**任何 `dev = Vulkan0` 行。我不能伪造，也不会把别的日志改名充数。

我能交的替代证据：
1. 10 份 per-run 日志确实在 `runs_m14b/logs/*.log`（manifest 断言、VRAM、答案、7B 扫描都在里面），只是没有 llama 内核行；
2. **同常量**的 `-v` 实测：`runs_m14b/loadD_ngl99_c8192.log` —— `llama_kv_cache: layer N: dev = Vulkan0` 出现 **48 次**（N=0..47），
   且 Vulkan0 是全日志唯一的 dev 取值，KV buffer 816.00 MiB 单块；
3. 代码链：llama-model.cpp:2936（offload = cparams.offload_kqv，默认 true @ llama-context.cpp:4028）
   → llama-kv-cache.cpp:216-223（`buft = dev_buffer_type(model.dev_layer(il))`）；gpu=99 ≥ 48 层 => 每层 KV 都在 Vulkan0。

要拿到「每跑一份真 -v」只有一条路：改 kvshim.cpp 让 quiet_log 受环境变量控制后重编 —— 那是源码改动 + DLL sha 会变
（9edbafa1 就不再是被测对象）。**不属本单边界，等你的话。**

## 7 未验证 / 需要注意

1. §5 的分辨力问题 —— 未解，是本单唯一实质开口。
2. 每跑的真 -v 设备行不可得（§6）。
3. 单跑只有 24 token，答案尾部被截断（`问：我住` 就是截断处），更长的生成本次未测。
4. 只跑了 home 作 target；project/habit/pp18 自身的召回未逐一验证（本轮顺序只要求 home）。
5. 跑前 free VRAM 10 次都是 9426 MiB，**不代表**长时间多轮后不涨；没有做 N 小时压测。
6. 四格齐一是否由「q8_0 KV 量化把差异磨平」造成：未测（若要测需 q8_0 vs f16 对照，会引入新差异字段，未做）。