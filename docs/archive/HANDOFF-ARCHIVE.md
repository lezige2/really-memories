# 交接文档 · llama-mem

> **as-of**：本文是 2026-10-25 快照。**现行入口**：[`docs/_work/ANCHORS-CURRENT.md`](./docs/_work/ANCHORS-CURRENT.md)（坐标以该文件内容为准，**banner 不钉 sha**）；状态见 [`PROGRESS-AND-ROADMAP.md`](./PROGRESS-AND-ROADMAP.md) §0.1。
> 本文中的哈希是**签署时坐标**，不代表现值；未闭项清单与交接起点以现行 tracking 文档为准。
> **权威指向（2026-10-25 收敛，见 [`docs/_work/INDEX.md`](./docs/_work/INDEX.md)）**：状态权威 = `PROGRESS-AND-ROADMAP.md` §0.1；坐标权威 = `docs/_work/ANCHORS-CURRENT.md`；文档索引 = `docs/_work/INDEX.md`。
> **2026-10-26 C33 补记（as-of 指针）**：M4-C 已于 2026-10-25 17:40 结项（`3309fb25cbd057f9`）；M5 `(a)` 已验收、`(c)` 判据作废；M5C2/rev7.1、b5（已冻结、未跑）、b6（已冻结、生成/盲标未做）最新状态见 `PROGRESS-AND-ROADMAP.md` §13.33。本文其余内容仍为 2026-10-25 快照。

> **操作指令**：本文件每个 sha 都能用 §7 的命令复算。**sha 不符 ⇒ 与该产物相关的结论作废，先重跑再解释。**

---

## 0 一句话

**M3 已验收；M4 三件里 A 绿、B 已判出、C 未开；M5 有实现、两探针未办。**
下一个会话先按 §2 组队，再从 §4 的顺序接着做。

---

## 1 给下一个会话的第一段话（照抄）

```
用智能体模式。先读 D:\llama-mem\HANDOFF.md，
按它的 §2 组队（三人：lead + 检测员 + 执行者），然后从 §4 第一步接着做。
M4-C 是当前最大未闭项；不要重跑已验收的 M3。
```

---

## 2 组队与纪律

```
lead      规划、派活、复核、验收、写文档。不下场写被测代码。
检测员    冻结判据、独立重算、审验收。结论直接进执行者的输入。
执行者    实现与跑批，一次只派一个。
```

**三条硬规矩**
```
① 子代理的报告是证据，不是判决 —— lead 必须独立复核后才能引用
② 一张单只写五件事：目标 / 边界（可动哪些文件）/ 约束 / 验收标准 / 必须回报的证据
③ 长跑不阻塞等：后台起、拿 job id、用 job_output 收
```

**验收分级**
```
R 重算       自己跑出同一个数
C 构造性覆盖  有会失败的反例且它真的红过
A 锚定转录    产物里的字段 + 取值，附文件名与 sha16
S 仅自述      只有一句「通过了」
```
自报不许升成重算；脚本给自己打分的布尔最多算 S。

---

## 3 已确立的锚（引用前先复算）

| 文件 | sha256 前 16 | 字节 |
|---|---|---|
| `m3/run_m3_lifecycle_50_v4.json` ← **M3 验收依据** | `ef3d1e8859add5b0` | 82,784 |
| `m3/run_m3_criterion_declarations.json` | `69147b2d360e44ba` | 10,701 |
| `m3/run_m3_unit_falsifiers.json` | `ca752cb05b0f9f59` | 9,144 |
| `m3/run_m3_redA.json` | `b9dbb5d1a6796e96` | 64,272 |
| `m3/run_m3_redB.json` | `4b0080f0a757e45c` | 1,151 |
| `mine/inspector/M3-PREREG.md`（259 行 / LF） | `3e4f465b67eebd3c` | 18,024 |
| `m4/run_m4_verify_a4.json` ← **M4-A 依据** | `59edbd82d4b9ae44` | 17,332 |
| `m4/run_m4_ablate_plate_a7.json` ← **M4-B 依据** | `77e11a04aacd24c5` | — |
| `m4/run_m5_grounded.json` | `007cb08b8f117ec5` | 41,083 |
| `m4/blocks/blk_conv_2026-10-25_01.kvmem` | `81127d24fd64b96b` | 9,507,412 |
| `tools/kvshim_vk.dll` | `9edbafa150700614` | 50,007,552 |

块几何：**91 cells**、`delta=+4005`、落位 `[4005,4096)`、`pos_max=4095`。
加载参数：`-ngl 99 -c 8192`，KV q8_0，n_seq 8，n_predict 64，位置锚 4096，**14B**。

---

## 4 下一步顺序（为什么是这个顺序）

```
1. M4-C  leases 真实接入 + 承重自证      <- 当前最大未闭项（M3 移交项）
2. 补 M5 (a)/(c) 两探针
3. 三件绿 => 写 M4 验收定稿（带分层，不写单一数字）
4. M2 规划器 / M1.8 三处 judge 冲突
```
**为什么不能先做 M5**：M5 校验的对象是 M4 的答案与块正文。
**M5 的边界已冻结：只管「无中生有」，不管「张冠李戴」；漏判优先于误判。**

---

## 5 已确立的事实（连强度一起写）

### 5.1 M3 块生命周期 —— **通过**，但必须连这五行一起读
```
judged distinct claims 13 条（15 - 2 重名: C2 是 S3_cells 的别名; C5 复述 C1）
  端到端被验证   5 条 : C1 C4 L1 L2 L3
  仅单元被验证   8 条 : S1 S2 S3_pos S3_cells T1 T2 C3 L4
  端到端不可失败 8 条 :（同上 8 条，scope = within this driver only，不是「永远红不了」）
无效轮规则 I1..I6    端到端红过 2（I3 红控B / I4 红控A 第38轮）  仅单元红过 4（I1 I2 I5 I6）
```
- 50/50 轮有效；逐轮 32 个键里只有 `round` 与 `secs` 变（30 个标量中 28 个恒定）。
- `pos_max` −1/4095/4146、`cells` 0/91/51、四个泄漏计数器全 0。
- `check_m3_prereg_consistency.py --run run_m3_lifecycle_50_v4.json` ⇒ **rc=0 PASS**。
- **T2 的准确命题是「同输入重放 50 次逐字节恒等」（确定性）**，不是「稳定」。换输入那一类**完全没测**。
- **额外观测**：attempt 2 与 attempt 4 是两个独立进程，`answer_sha16` 都是 `806a3410a856a23a` ⇒ 跨进程同输入重放恒等。**这条不计入 13 条。**

### 5.2 M4 写入固化 —— 九项成立，三件收尾

一块 91 cells / 6 条 memory 每条 `evidence_span` 逐字存在 / save+插入 / **新进程检索与作答 pid 均不同** / 多值保留旧值 / 相对时间锚定 2026-10-28 / 去重不新增 / `position0` 扫描覆盖恰好 `[0,21)` 且拒绝路径两道 guard 都给出理由。

```
M4-A  </think 泄漏     已绿。锚 run_m4_verify_a4.json = 59edbd82d4b9ae44
                       口径: 机械次数 8（承载字段）/ 语义次数 2（不同原始串）
                       两个数都要报，禁止写单个数字

M4-B  车牌句消融       已判出。锚 run_m4_ablate_plate_a7.json = 77e11a04aacd24c5
                       verdict = memory_carried_by_that_sentence_content_not_length
                       产品块对照        91 cells [4005,4096)  -> 浙B-3F19K
                       同路径重编(同文)  91 cells [4005,4096)  -> 浙B-3F19K   块 sha 与产品块逐字节相同
                       删掉那句话        79 cells [4017,4096)  -> 苏A12345（编造，不在块正文里）
                       等长对照(换词)    91 cells [4005,4096)  -> 浙Q-00000（就是换进去的那个词）
                       => 模型答的是块里的内容，不是块的长度

M4-C  leases 真实接入  未开始。判据是「删掉它必须有断言变红」，不是「加上调用」
```

### 5.3 `</think` 的成因（支持性，非单因子）
成因已缩小到「对话式正文」这一类，但现有三例（A 对话含 assistant / B 散文 / C 对话仅 user）**三处共变**，一个变量都没分离。
且 B 的 `rc=230`（A/C 是 93）说明它的续写行为也变了，**B 不能当对照组**。
要单因子须补两例：`D` 与 A 同内容同长度只去角色标记（分离形式）；`E` 与 B 同形式加长到 ~91 token（分离长度）。

### 5.4 已冻结、不许动的
```
M3-PREREG.md（259 行）       判据冻结，阶段末一次性修订
M5-CRITERIA.md               只管无中生有，不管张冠李戴
块 blk_conv_2026-10-25_01    只读，任何实验不得写它
14B only                     7B 线已冻结，产物在 kvmem/m2_7b/
```

---

## 6 措辞口径

```
不说「T2 稳定」               -> 说「同输入重放 50 次逐字节恒等」
不说「不可失败」               -> 说「端到端不可失败（within this driver only）」
不说「32 轮按计划未到」         -> 说「32 轮未完成」
不说「S3 与 C2 都验了」         -> 说「C2 是 S3_cells 的别名，两条算一条」
不说「会话结束导致进程死」      -> 说「成因未定，两个候选未做判别实验」
不说「think 出现 6 次」         -> 说「承载字段 8 / 不同答案串 2」（两个口径不许混写）
不说「M2 全部通过」             -> 逐格写，见 FEATURES.md
不说单例是统计                  -> 说「单例，非统计」
```
**数目变了必须说明变的是哪一个。** 一个数的变化若说不出「原先是什么、现在是什么、为什么」，它就不是读数。

---

## 7 复算命令（不需要引擎）

```bash
cd D:/llama-mem && B=kvmem/m2_visibility

# 锚
python -X utf8 -c "import hashlib;print(hashlib.sha256(open('$B/m3/run_m3_lifecycle_50_v4.json','rb').read()).hexdigest()[:16])"
# 期望 ef3d1e8859add5b0

# M3 声明一致性（期望 rc=0 与 PREREG-CONSISTENCY: PASS）
python -X utf8 $B/mine/inspector/check_m3_prereg_consistency.py --run $B/m3/run_m3_lifecycle_50_v4.json

# 分层普查（期望 rc=0 + INJECTION/CENSUS: PASS）
python -X utf8 $B/mine/inspector/check_m3_injection.py --mode census \\
  --run $B/m3/run_m3_lifecycle_50_v4.json \\
  --declarations $B/m3/run_m3_criterion_declarations.json \\
  --unit-falsifiers $B/m3/run_m3_unit_falsifiers.json

# M4-B 外部核对（null 记 SKIP，不当通过）
python -X utf8 $B/m4/check_ablate_run.py $B/m4/run_m4_ablate_plate_a7.json
```

---

## 8 工作环境注意

```
shell       MSYS bash；`timeout` 会撞到 Windows 的 TIMEOUT.EXE，不要用
退出码      绝不写 cmd|tail; echo $? —— 那是 tail 的码。写 cmd > f; echo rc=$?
换行        文件统一 LF；CRLF 会让 $ 锚点静默失配
产物命名     每次尝试一个新文件名（含尝试号），绝不覆盖
长跑        后台起 + job_output 收；不要 sleep 轮询
```

---

## 9 未闭项清单

```
F-M3-1  声明 §7 陷阱① 描述错（「含块的安全重置」）—— 冻结期内不改，阶段末一次性修订
F-M3-2  S3 的修法未过其 §11.4 自检 —— 已由单元注入救回，记录在案
F-M3-3  I5/I6 端到端未覆盖 —— 判 U
F-M3-4  falsified_by 混两种类型（20 个 case id + 5 条散文）；flipped 列只装 judged 判据
F-M3-5  attempt 1 停在第 32 轮 —— 「未完成」，副本在 m3/_interrupted_32of50/
F-M4-1  n_predict：引擎不暴露该属性（记 null），声明 24 与实际不一致，无证据判定哪个生效
F-M4-3  M4-C 未开始 —— M4 当前最大未闭项
F-M5-1  M5 的 (a)/(c) 两探针未办
F-PS-1  补丁工作区比归档多 100 行（src/llama-kv-cache.cpp +391 -> +491），来源与授权未判定
未测    换输入那一类的稳定性 / 引擎内部池状态 / S3 的端到端可失败性 / 判据的第三份副本
```
