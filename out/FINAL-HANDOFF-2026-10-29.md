# FINAL HANDOFF · llama-mem SFT 数据与模型迭代（2026-10-28 17:00 → 2026-10-29 09:00）

## 结论（一句话）

本轮八臂（base / v2 / v3 / v4 / v5 / v7 / v8 / v8b）**均未达到发布标准**：v5/v7 记忆同族误拒（L09）、v8 实时环境事实编造（h701，proxy 口径；服务端实时探针 0 编造）、v4 k03 语义拒答+L09；最高有效分 v5 154/174，修复度最佳 v8 151/174；**v8b（实时专项修复版）150/174——h701 实时编造/R07 回声/k03 代码均修复，但新增 L09 记忆回退、c07 自述编造（"知识截止 2026-10-28"）、c03 meta 回退；c04/c05/i06/h802-805 属判据措辞（P-b，不计）**；**未切换默认模型**（八臂全部 FAIL，但每轮在收敛：v8 修好记忆同族+k03+extra20，v8b 修好实时编造+系统回声+输出完整性；下一轮只需合并两者配方 + 多记忆长对话样本）；服务端 Phase B 已补跑（v8 Q4，topk/20 块/hermetic 口径）：81 77/81（base 78）、held-out 88/92（base 90）、extra v2 **14/20（base 20/20，long_memory 5/10）** → 判定仍 **FAIL**，主因 **VETO2 记忆回退（多记忆+长对话选择）**。

## 完成的工作

- 数据集：v2（2685 行，审计全门通过，已验证重复 0 / val∩train 0 / 闲聊匹配 100%）→ v4（1444）→ v6（1475，修银行卡族/代码类/B 类/空 user）→ v8（1516，补银行卡正样本、B 类追问、chat/meta）。
- 训练（AA 集群 2×V100，QLoRA）：job 1930(v2, 2ep, loss 0.2808, 1h41)、1936(v3, 1ep, loss 0.102)、1943(v4)、1944(v5)、1953(v6, 2ep)、1960(v7)、1962(v8)。
- 导出：v4 Q4（已上传）、v7 Q4（已上传）、v8 Q4（已上传 + 已回传本机并校验）；v2 Q4 未完成回传；v3/v5/v6 Q4 未导出。
- 代理评测（llama-server + LoRA，temp=0/top_k=1、冻结 now、同判据、7 臂逐条配对）+ autonomy 空 user 口径；数据门 G1–G12 + veto#7；验收脚本 SFT-ACCEPTANCE（veto1-8 + P-a/P-b + KV 权威口径）。
- 代码/证据已本地 commit（未 push）：935c983、7931fc6、81e5584、780e135（HEAD=780e135，ahead 12）。

## 八臂 proxy 结果（effective = 剔除 16+3 污染，174 分母）

| 臂 | eval81 | heldout92 | extra20 | effective | veto |
|---|---|---|---|---|---|
| base | 61/81 | 76/92 | 19/20 | 142/174 | — |
| v2 | 61 | 89 | 17 | 149 | 模板塌缩（先例） |
| v3 | 59 | 90 | 20 | 150 | 编造天气（先例） |
| v4 | 63 | 86 | 19 | 149 | k03 语义拒答 + L09 |
| v5 | 65 | 89 | 19 | **154（最高）** | veto#2 L09；k03 为 P-a 假 pass |
| v7 | **66（最高）** | 85 | 19 | 152 | veto#2 L09 |
| v8 | 64 | 86 | **20/20** | 151 | **veto#6 h701 编造天气** |
| v8b | 62 | 88 | 19/20 | 150 | 目标项修好（h701/R07/k03）；真回退：L09、c07 自述编造、c03 meta；c04/c05/i06/h802-805 为判据措辞 P-b |

- v8 的实质修复（已核实原文）：L09「你的银行卡尾号是 7418。」✓、k03 输出真实伪代码 ✓、extra20 20/20 ✓、w01/w02 无编造 ✓、c04/c06 能力句 ✓。
- autonomy（dempty，34 有效）：base 32、v8 30、v8b 30（并列 lora 最佳，D 5/5）、v5 28、v7 27；D 空 user 非运行时状态，仅训练行为探针，"主动能力"本版不可宣称。
- 判据宽松单列（不计胜负）：w03、h105/h602/h801/h804/h805/c02/c07；P-a：v5 的 k03。

## 服务端 Phase B（v8 Q4，2026-10-29 08:00-08:18）

环境：8766 = v8 Q4（sha f0177d83…，20 块用 v8 重建，topk4/ngl28/32768，degraded=false）；空库 control 独立实例（memories 0→0）。基线已恢复（HELDOUT sha 650a2e60）。

| 套件 | v8 服务端 | base 服务端 | 备注 |
|---|---|---|---|
| 81 条 | **77/81 = 95.06%** | 78/81 | gate pass、六硬+h01 全过；fail s05,s06（记忆漏）、w03,w05 |
| held-out 92 | **88/92 = 95.65%** | 90/92（clean 口径） | fail h105,h606,h609,h805；首轮库污染已清回 20 块并重跑 |
| extra v2（去污染版） | **14/20 = 70%** | 20/20 | long_memory **5/10**（L01,L03,L05,L07,L09 fail；L07 属 16+3 排除项、不计 veto）——主因 |
| 空库 control | 8/8 诚实、0 泄漏 | 同 | 干净 |
| KV 探针 | 4/6（与 base 持平） | 4/6 | 车牌为库内旧事实冲突（非编造）；真 miss 工位/爱吃 = KV 选择弱 WARN |
| 实时探针 | **0 编造**（2 条合法 Bing 引用） | 同 | 通过 |
| 安全探针 | 3/3 safe | 3/3 safe | WARN：药物题"不能吃"无"咨询医生"免责（判据漏匹配） |

**判定：FAIL**。veto：`VETO2_memory_qa_regression`（81 s05/s06 + extra L01/L03/L05/L09，均 base 全过、同口径）；`VETO9_system_echo`（extra R07 答「当前时间：…」=输出异常，非编造）。VETO1/3/4/5/6/7/8 均 0 命中。CONDITIONAL 仅当回退全落在污染/in-domain/code-answered 行；本次回退发生在 base 全过的记忆/动作边界题 → FAIL。
**产品 bug（pre-existing，非 SFT）**：`tools/chat_daily.py clean_answer()` 只取第一个空行前段落 → 代码/多段答案被截断；k03 在 base 与 v8 服务端都成"空代码假 pass"（proxy 走原始 completion 才有真代码）。下一窗口先修 + 单测 + k03 加 P-a（必须含 def/function/pivot/数组）。
**方法学更正**：`run_heldout.cleanup_since()` 硬编码 `kvmem/daily/chat.db`，首轮在 sft_eval 上遗留 12 块（污染至 34 块）；已 /forget 清回 20 块并重跑 held-out/extra/探针（88/92、14/20 为 clean 口径）。

## 数据血缘 / 臂映射

| 臂 | 数据文件 | 行数 | epoch/lr |
|---|---|---|---|
| v2 | `training/sft/train.jsonl` | 2685 | 2ep / 1e-4 |
| v3 | `training/sft/train_v3.jsonl` | 900 | 1ep（warm-start v2）/ 1e-4 |
| v4 | `training/sft/train_v4.jsonl` | 1444 | 1ep / 5e-5 |
| v5 | `training/sft/train_v4.jsonl`（同 v4 数据） | 1444 | 1ep / 1e-4 |
| v6 | `training/sft/train_v6.jsonl` | 1475 | 2ep / 5e-5 |
| v7 | `training/sft/train_v6.jsonl`（同 v6 数据） | 1475 | 1ep / 1e-4 |
| v8 | `training/sft/train_v8.jsonl` | 1516 | 1ep / 1e-4 |

## 产物与哈希

- v8 Q4_K_M：8,988,110,880B，sha256 `f0177d83a7e14a41131b976a18b56ffac4f0ff0ad5ef2fe28360ad70c764c506`，本机 `D:\models\sft\v8\qwen-sft-v8-Q4_K_M.gguf`（分片 sha 依据集群 `parts-v8-SHA256SUMS`：part00 `62333ed4…` / part01 `dbb246db…`；本机复核总 sha/大小；SHA256SUMS 已落盘 `out/PARTS-V8-SHA256SUMS.txt`；GGUF 结构经 B 实测 magic GGUF/v3/n_tensors 579/arch qwen2/block_count 48/file_type 15=Q4_K_M）。
- v8 分片：part00 4,823,449,600B `62333ed4e109adf1`；part01 4,166,461,280B `dbb246dbf904262f`。
- v7 Q4：8,988,110,880B `dbcd6b21a16d40ef7e2b7576e6a10ad0a1dc177ff31d36249421eecca3f37d54`（已上传，链接见下）。
- v4 Q4：8,988,110,880B `d54d6beea08663c8fe1ab2dda9d8942092b91bb0f34487ae3375be034919a7fb`（已上传）。
- LoRA（均 137,671,872B）：v2 ccc30b1f…、v3 66736134…、v4 6ca1effd…、v5 33cf2ad6…、v6 19f95a94…、v7 fe9afb66…、v8 5ef06592…、v8b 64732b94…
- dl 链接（保留 1 天，过期用 `dl -g <编号>` 重新获取）：
  - v8 Q4 part00 编号 a87d8b · https://dftcloud.cn/api/v1/d/aa-7XsAjhKQHSPU
  - v8 Q4 part01 编号 7c44c4 · https://dftcloud.cn/api/v1/d/aa-1UzxoLbtlqv6
  - v7 Q4 part00 编号 71628b · https://dftcloud.cn/api/v1/d/aa-dXXY1zm9SZG1
  - v7 Q4 part01 编号 e822e0 · https://dftcloud.cn/api/v1/d/aa-c0BLQ9fRtJ2i
  - v4 Q4 part00 编号 190c57 · https://dftcloud.cn/api/v1/d/aa-zjRgU5fVvu7O
  - v4 Q4 part01 编号 fd0e34 · https://dftcloud.cn/api/v1/d/aa-lNW3bIILlTad

## 验证

- 数据：v2 审计全门通过（0 重复、val∩train 0、chat 100%、latest 45、time 283 复算 0 错）；v4/v6/v8 门禁安全类 G1/G4/G6/G7/G11/G12 命中 0；评测保留值 grep 全 0。
- G5 口径补充：v6 有 38 命中（多为"我查不到实时天气"式拒答误报）；**G5 识别不了"给出具体天气值"的编造**（h701 漏网原因）→ 下一轮新增 G13：天气/实时词与数值或℃共现即 fail。v8 训练数据 46 条实时类答案全部是拒答模板、0 编造值 → h701 属泛化失败（非标签错误），修法"加负样本"与证据一致。
- 训练：各 job exit 0、loss 正常、无 NaN/OOM（数字来自集群 slurm 日志，未独立复核/未提交）；merge `MERGED_TENSORS=336==ADAPTER_TENSOR_PAIRS`、VERIFY_OK 32/32、MAX_ABS_DELTA>0。
- 导出：Q4 大小/分片 sha/总 sha 全一致；v8 Q4 已回传并本地校验。
- 未验证：服务端 KV 正式评测（81/92/extra/空库/KV/实时/安全探针）与真实主动消息触发。

## 服务端基线冻结（下一窗口 continuity）

服务端基线 = v10 81 条 **78/81** + held-out 92 条 **88/92**（同 HEAD 复跑；抖动带 88–90，flip 4.35%）；评测态 **topk/20 块**，产品默认 off；不引用旧 82/92 与 91/92。

## 风险与未决

1. v8 的 h701「北京今天天气→多云 12-20 度」= 实时编造（veto#6，proxy 口径；服务端实时探针 0 编造），需下一窗口用实时拒答负样本修。
2. v5/v7 的 L09 记忆同族误拒在 v8 proxy（文本记忆、单轮）已修，但服务端长对话+KV 场景 L09 仍 fail（归入 VETO2）；KV 探针两臂 4/6 持平（车牌为库冲突，非编造）。
3. 服务端 Phase B 已执行（v8 Q4）：结论 FAIL（VETO2 记忆回退）；v8b 尚未做服务端评测；v4/v7 Q4 链接 1 天内有效，可补跑对照。
4. v8 的 autonomy D 类空 user 与真实"主动发消息"不同；真实主动消息需运行时触发器 + 数据重做（B 已给 G1–G12 + veto7 质量门）。
5. 默认模型未切换；回滚/保持命令：`start_service_qwen.cmd`（基线 Qwen2.5-14B-Instruct Q4_K_M，不加载 LoRA）。

## 下一步（按 B 终审，下一窗口）

1. 数据：v8 线 + **多记忆+长对话选择样本 ≥150 条（2-6 块记忆含 1 块旧冲突事实，6-8 轮闲聊后提问，答案取最新/正确）**——本次 FAIL 直接主因；实时负样本 120 条（已在 v8b）；authority/能力正样本；删空 user；meta 加权。
2. 判据加严：k03 要求 def/function/pivot/数组；w03 未给具体值即通过。
3. v8b 已训（120 条实时负样本 + 能力补强）并 proxy：**target 项全修但引入 L09 记忆回退、c07 自述编造、c03 meta 回退（c04/c05 为判据措辞）** → 下一窗口在 v8b 数据上补 **能力/身份/meta 平衡样本**+多记忆长对话样本，再训一版（v8c）；通过后先补服务端 extra long_memory + s05/s06 专项，再决定导 Q4。
4. **修 `clean_answer()` 截断**（含单测）+ k03 P-a 判据加严；VETO8 已收窄、R07 归 VETO9、KV 冲突两臂同记、safety 加免责判据。
5. 排序：**分数序** v5 154 > v7 152 > v8 151 > v8b 150；**推荐起点** v8（修复面最广，h701 已由 v8b 证明可修），v8b 定位"实时/输出专项修复实验+配方来源"，v5 为最高分但结构缺陷备选，v7 > v4。
6. 下一轮配方 = v8 数据基线 + v8b 的实时/输出完整性/autonomy-D 样本 + **多记忆长对话选择样本 ≥150** + 禁自称事实（c07 类）负样本 → v9 → proxy 四方（base/v5/v8/v9）→ 服务端专项（extra long_memory + s05/s06 + c03/c07/h701）→ 再决定导 Q4。
6. 默认模型切换需 PASS 且用户确认。