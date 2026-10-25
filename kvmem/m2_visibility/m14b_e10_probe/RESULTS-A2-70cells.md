# A2（70 cells，+car）三次重复 —— E10 在 14B 上不复现

## 装置指纹

| 项 | 值 |
|---|---|
| 模型 | `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` 8,988,110,240 B，**sha256 前16 `0b319bd0572f2730`** |
| n_ctx / n_seq / **n_predict** | 8192 / 8 / **64** |
| **-ngl** | 99（48/48 层 Vulkan0） |
| KV 量化 | **q8_0** |
| DLL | `kvshim_vk.dll` sha16 `9edbafa150700614`（measured=declared） |
| chat.py sha16 | `4c8d73e955c108ff` |
| cmdline | `python -X utf8 _run14b.py --layout iso_car_back --target <SEG> --n-predict 64 --run-json out/A2p_r<REP>_<SEG>.json`（每份 json 的 `runner.argv` 是原文） |
| 判定器 | `fact_ok`：期望串在答案全文中的子串命中（**主判据 `hit_full`**），并列 `hit_first_sentence` |

## 块（cells 与 sha16 来自 manifest / 块文件）

| 块 | cells | sha16 | 事实 |
|---|---:|---|---|
| home | 21 | `73843fc55efd1ab3` | 住址：广陵路 12 号 2 单元 602 |
| project | 18 | `536eac03f288bb09` | 代号蓝鲸，3 月 14 日上线 |
| habit | 12 | `f6f8e85cc55bd4b9` | 咖啡只喝美式，不加糖 |
| **car（本轮新造）** | 19 | **`096fa6361447db14`** | 车牌 浙B-3F19K，深灰色速腾 |

car 块由 `make_car_14b.py` 用 14B + q8_0 + -ngl 99 编码，文本取自 `tools/m2_visibility_probe.py` 的 `FULL["car"]["text"]`（与 7B 的 car 块同文本），9 项校验全过（cells=19 / size=1188+104464×19 / BOS / n_layer 48 / k_type=v_type=8 / k_row=v_row=1088 / 读到 EOF）。工地文件放在 `kvmem/m2_v1_14b/car.kvmem`（**只新增一个文件，未改动任何既有块**）。

## 逐条结果（3 次重复 × 4 块 = 12 次 ask，np64）

| 重复 | 块 | 块 cells | 序列 token 增量 | hit_full | hit_first_sentence | 关系 | 答案原文（截） |
|---|---|---:|---:|---|---|---|---|
| 1 | home | 21 | 73 | true | true | both | 我住在广陵路 12 号 2 单元 602。问：我的地址是哪里？… |
| 1 | project | 18 | 73 | true | **false** | tail_only | 项目预计在 3 月 14 日上线。问：项目上线后，如何使用？… |
| 1 | habit | 12 | 75 | true | true | both | 我只喝美式咖啡，不加糖，不加奶，不加任何东西。… |
| 1 | car | 19 | 74 | true | true | both | 车牌号是浙B-3F19K。问：我的车是什么颜色？答：深灰色。… |
| 2 | home | 21 | 73 | true | true | both | （与重复 1 **逐字节相同**） |
| 2 | project | 18 | 73 | true | false | tail_only | （与重复 1 逐字节相同） |
| 2 | habit | 12 | 75 | true | true | both | （与重复 1 逐字节相同） |
| 2 | car | 19 | 74 | true | true | both | （与重复 1 逐字节相同） |
| 3 | home | 21 | 73 | true | true | both | （与重复 1 逐字节相同） |
| 3 | project | 18 | 73 | true | false | tail_only | （与重复 1 逐字节相同） |
| 3 | habit | 12 | 75 | true | true | both | （与重复 1 逐字节相同） |
| 3 | car | 19 | 74 | true | true | both | （与重复 1 逐字节相同） |

**三次重复整体逐字节相同**（按 home|project|habit|car 拼接比对，3 份全等）⇒ 14B 上确定性成立。

## 位置读数（placed，逐块；`expected = cells if delta != 0 else 0`）

| 块 | slot | base | delta | moved | expected | pos_lo | pos_hi | target−base==delta |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| home | 1 | 0 | 4075 | **21** | 21 | 4075 | 4096 | ✔ |
| project | 2 | 0 | 4014 | **18** | 18 | 4014 | 4032 | ✔ |
| habit | 3 | 0 | 3956 | **12** | 12 | 3956 | 3968 | ✔ |
| car | 4 | 0 | 3885 | **19** | 19 | 3885 | 3904 | ✔ |

`moved` 来自对引擎 `repos_local` 的**调用插桩**（包装 `eng.repos_local` 记录 seq/delta/moved），不是声明；`pos_max` 独立锚仍在（`raw_pos_max_before_ask` 与 `pos_hi-1` 一致）。

## 结论

- **A2 = 70 cells（51 + car 19）在 14B 上 hit_full 12/12（3 次重复 × 4 块）** ⇒ 按预登记规则：**E10 在 14B 上不复现**，止损条件触发。
- **这是"可达性"证据，不是"问答能力"证据**：答案在答完第一句后继续自问自答、并把**别的块**的事实一起背出来（例如问 home 却答出"项目代号是蓝鲸""3 月 14 日""美式"）。四块的期望 token 互不相同，所以这种多块复述**不会制造假命中**；但它证明的是「四块内容在同一次生成里都能取到」，**不是「模型选择性地回答了被问的那一块」**。
- `hit_first_sentence=false` 的 3 条（全是 project）**不是漏读**，是判定器的空白敏感：期望串写的是 `3月14`（无空格），答案是 `3 月 14 日`（有空格）。这是**仪器artifact**，已在 `hit_relation` 里标成 `tail_only`，请勿读成"首句没读到"。
- **截断状态 = unavailable**：DLL 的导出集里没有任何 EOS/stop/finished 符号，`kvshim_ask_at` 只回字节数。表中"序列 token 增量"是 `n_tokens_after - n_tokens_before`，**包含提问 token**，不是生成长度，不能当"是否触顶"用。

## 产物命名规则（统一）

`out/A2p_r<REP>_<SEG>.json` 是 A2 的**唯一规范名**（含 placed / 两个命中布尔 / metric_note / fidelity schema）。`out/A2_r<REP>_<SEG>.json` 是补字段**之前**的同一实验（答案逐字节相同），保留作历史对照、不作引用。`probe_A2_r1_home.json` 是冒烟副本，已移入 `out/_unused/`。
`S1_home.json` / `S2_project.json` / `S3_habit.json` 已写入 `"status":"not_run"` + 原因（控制闸几何：target_n 只有 21/18/12，14B 控制前缀要 67 tokens ⇒ rc=4），避免被汇总进分母。
