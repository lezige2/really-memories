# llama-mem

> 把长期记忆做进推理引擎的 **KV 张量**里，而不是拼进 prompt 字符串。

**一句话定位**（引自 [`PROJECT-STATE.md`](PROJECT-STATE.md)）：
**引擎层是真的；记忆读取能力是半真的；产品层是空的。**

---

## 这是什么

主流"记忆"方案在应用层把历史拼进 prompt —— 那本质上是**上下文工程**，不是记忆。
本项目改的是推理引擎本身：长期记忆以 KV 张量常驻 attention 层，由引擎自己读取。

**关键差别**：记忆不在 prompt 文本里，它在 KV cache 里。删掉对话历史，记忆依然可被读出。

核心机制（均在 `patches/persistent-memory.patch`）：

- 记忆序列以 **KV 张量**形式常驻池中（`seq_cp` 引用计数挂载，不是文本）
- 位置被挤占时做**局部重旋转**（`seq_repos_local`：CPU 上 dequant → rope → requantize）
- **Hadamard 三明治**（`H → rope → H`）用于量化友好基底 —— 注意 RoPE 与 H 不对易
- `kv_unified=true` 下共享单一 KV 池，各记忆块**仅靠 position 区间区分**

---

## 当前状态

| 层 | 状态 |
|---|---|
| 引擎层 | **已落地**。补丁 6 文件 / **500 insertions / 0 deletions** |
| 记忆读取 | **半真**。3 个块挂上去能读；4 个块挂上去读不全 |
| 产品层 | **有骨架，仍无服务端**。逐格见 [FEATURES.md](FEATURES.md) |

产品层这条变了，说明变的是哪几格：

```
M2 规划器      几何已冻结（habit 12 / project 18 / home 21 @ [4045,4096)，gap 0，51 cells）
               驱逐策略 / 多会话容量 / 位置租约 —— 未做
M3 块生命周期  attach / detach / pin / 只读 已实现并验收（50 轮）
               锚 run_m3_lifecycle_50_v4.json = ef3d1e8859add5b0（82,784 B，50/50 valid）
M4 写入固化    部分。输出层过滤已绿：锚 run_m4_verify_a4.json = 59edbd82d4b9ae44
               车牌句消融：三轮均 inconclusive，原因已定位到驱动（见 FEATURES.md）
               leases 在真实产品路径上尚未被断言约束 —— 这是 M4 最大的未闭项
M5 接地校验    未开工（判据已冻结：mine/inspector/M5-CRITERIA.md）
```

**为什么 M5 必须排在 M4 之后**：M5 校验 M4 产出的答案与块正文。
M4 的答案此前仍带 `</think`，块正文也还没做过接地消融 ——
**在一个被污染的数据上建校验器，它会先学会接受污染。**

### 已定位的缺陷：E10

4 段共享区间下的可见性问题 —— **已定位，未修复**：

> **非存储缺陷、非可见性缺陷。失败发生在生成侧**——模型没有采用眼前可见的记忆内容。

- **cell 层**：失败布局下 home 块 21/21 覆盖，无重叠
- **掩码层**：两臂各 100 条块行，`masked > 0` 的 **0 条**
- **生成侧**：同块、同位置、同掩码，一个布局复述正确事实，另一个输出「住在\_\_\_\_\_\_。A. 杭州市拱墅区 B. …」

排查中 **七条假设阵亡**（位置跨度 / 段数 / car 唯一性 / habit 自身缺陷 / 总 cell off-by-one / cell 归属 / 掩码层）。
三种候选解释均标【推断·未验证】。

**结论：已定位 ≠ 已修复。引擎代码为此未改一行。**

---

## 文档地图 —— 哪个是真的

> 判据层级：**代码 > 运行产物 > 旧文档（仅史料）**

**只有三份是需要读的入口文档，其余全部是证据。**

| 文档 | 读它的理由 |
|---|---|
| **[README.md](README.md)**（本文件） | 项目是什么、怎么跑、怎么复算 |
| **[HANDOFF.md](HANDOFF.md)** | **换会话/交接前必读**：八个锚、已确立事实与强度、顺序与未闭项 |
| **[FEATURES.md](FEATURES.md)** | **功能台账**：已实现 / 部分实现 / 未实现 / 可能需要，每行带锚与强度 |
| [PROJECT-STATE.md](PROJECT-STATE.md) | 引擎层判定总表（25 条，E1–E10 / S1–S3 / P1–P8）。**FEATURES 的引擎层附册** |
| `kvmem/**/*.md`（73 份） | **证据目录，不是文档**：预登记 / 验收 / 判据 / 台账，由 [INDEX.md](kvmem/m2_visibility/INDEX.md) 导航 |
| [kvmem/m2_visibility/ISOLATION-REPORT.md](kvmem/m2_visibility/ISOLATION-REPORT.md) | E10 的完整实验报告与排除过程（**定稿·可引用**）|
| [docs/legacy-2026-10-24/](docs/legacy-2026-10-24/) | **史料·勿引用**：早期交接文档多处与代码不符 |

> **为什么把 73 份 md 叫「证据」而不是「文档」**：它们是某次跑、某份判据、某次验收的当场凭据。
> 读它们的前提是「你要核某一条结论」。把证据当文档读，会读到互相矛盾的中间态。

旧文档里的 `508ms → 42ms`、`SQLite 不存正文`、若干 `x/y` 通过数等断言，**在代码中查无依据**，已在 PROJECT-STATE.md 中逐条标注。

---

## 仓库结构

```
PROJECT-STATE.md          唯一权威状态
patches/                  引擎补丁 + MANIFEST（sha256 / numstat）
  persistent-memory.patch   6 文件，500 insertions，0 deletions
kvmem/                    实验产物与夹具
  m2_visibility/            E10 实验（ISOLATION-REPORT.md 在此）
tools/                    探针、评测、诊断脚本
docs/                     文档（含 legacy-2026-10-24/ 归档）
llama.cpp/                我们的 fork，分支 persistent-memory（嵌套 git 仓库）
llama.cpp-upstream/       上游纯净克隆，只读基线
build-cpu/ build-vulkan/  自建构建产物
```

**补丁为什么存成文件而不是子目录**：`llama.cpp/` 本身是一个 git 仓库。
若直接纳入父仓库，git 只会存一个 gitlink 指针，**那 500 行代码一行都进不了备份**。
所以补丁以 `patches/persistent-memory.patch` 单独受版本控制，附 `MANIFEST.txt` 记录 sha256 与 numstat。

---

## 不入库的内容

见 [`.gitignore`](.gitignore)：模型权重（`*.gguf`）、记忆块（`*.kvmem`）、
编译产物（`build*/`、`bin/`）、实验运行产物（`runs_*/`）、日志、数据库（`*.db`）、
配置与密钥（`.env`、`config.json`）。

---

## 一键复算

本项目不要求你相信任何结论。

```bash
bash verify.sh
```

它跑七项断言：引擎补丁仍为 500/0、门禁五支的退出码（含两条反证：删 `worker_counts` 应得 rc=7、
删 10 行日志应得 rc=6），最后一行打印 `ALL PASS (7 项)` 并以 0 退出。
任何一项不符 → 非零退出，并指出是哪一支。

> 一个从没红过的门禁，和没有门禁是一样的。`verify.sh` 里有两支是**故意造红**的。

**脚本自身也已反证过**：把 `ISOLATION-REPORT.md.sha256` 写成错值 → `rc=1`、`FAIL: 2/9 项未通过`；改回即 `rc=0`。
校验逻辑内嵌 Python `hashlib`（不依赖 `sha256sum`，本机没有该命令），且**退出码不经过任何管道**——
写成 `cmd | tail; echo $?` 取到的是 `tail` 的退出码，会得到一个漂亮的假绿。

---

## 工作方式：十条规定

本项目在排查 E10 的过程中，**每一次错都留下了一条规矩**，全部来自真实的失败：

1. 先 grep 已有产物，再开工
2. 凡数量，附**能算出这个数量**的命令（`grep -c`，不是 `grep -m1`）
3. 判读规则先用已知结果反推；标明它是**外部锚点**还是**内部一致性检查**
4. 验收带 sha256 + numstat + 重算命令；备份须与当前文件哈希不等
5. **内部一致性不得用于判定因果**
6. **主语与量词的辖域必须显式**（"两臂各 100 条" ≠ "两臂共 100 条"）
7. 措辞修改成批提交；判据是「判对错要不要跑命令」，不是「结论变不变」
8. 引一次运行，引 run json 自己的键**并写出取值**
9. **专有名词必须 grep 得到** —— grep 不到即为错，与措辞无关
10. **判据本身按五格验收**（类名 / 现状红 / 修后绿 / 每个数的命令 / 跨几类），
    且**判据的可信度标准高于文档**

> 一个从没红过的门禁，和没有门禁是一样的。

---

## 作者

| 角色 | |
|---|---|
| 设计 · 决策 · 取舍 | **lezige2** |
| 实现 · 实验 · 复核 · 文档 | **AI 多智能体协作**（队长 / 检测员 / 执行者） |

人类作者定方向与验收标准，AI 承担代码、实验、交叉复核与文档定稿。
本仓库的每一处技术断言都要求**可被第三方用一条命令复算** —— 这条规矩由双方共同遵守。

---

## 许可

**MIT**，见 [LICENSE](LICENSE)。Copyright (c) 2026 lezige2。

引擎补丁基于 [llama.cpp](https://github.com/ggml-org/llama.cpp)（亦为 MIT）。
