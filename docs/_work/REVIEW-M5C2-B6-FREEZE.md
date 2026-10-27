# REVIEW-M5C2-B6-FREEZE —— (b6) 冻结件独立复核
> 复核者：`cleanroom-auditor`（**非出题者、非 LEAD**）· 对象：`docs/_work/PREREG-M5-C2-B6.md` `ac27d47d3a3efff9` / 17,374 B + `kvmem/m2_visibility/m5/out/M5C2-B6-SENTENCES.json` `23588ec099ca9255` / 9,482 B · 复核时间：2026-10-26T21:32:26+08:00
> 边界：只读；只读 b2/b4/b5 题面（8 源文+40 题）做比对，**未读 b5 运行数据**；零 GPU/模型/联网；未改 B6、未 git 提交。
## 结论：**pass**（冻结成立）—— 实质复用 **0**、歧义 lure **0**、阻塞项 **0**；不可验证项见 C13/C14

| # | 检查 | 结论 | 关键测量（全部独立复算，不采信附录 A） |
|---|---|---|---|
| C1 | 文件身份/哈希 | pass | md `ac27d47d3a3efff9`/17,374 B；json `23588ec099ca9255`/9,482 B；`json.prereg_sha16`=md sha16 ✓ |
| C2 | json 机读格式 | pass | 字节级等于 `json.dumps(...,ensure_ascii=False,indent=2)+"\n"`；顶层 22 字段与 §7.1 完全一致 |
| C3 | md↔json 48 条 | pass | 8 源文 + 40 问逐字一致，mismatch=0 |
| C4 | 结构/计数 | pass | 8 场景 / 40 题 / 24 detail + 16 lure；每域 3+2；qid 唯一且与 `b6-s<n>-q<m>` 序列完全一致；n_facts 6,7,7,7,7,8,7,7 |
| C5 | 源文汉字 40–80 | pass | 51, 50, 45, 47, 57, 49, 43, 54；md 声明值、json 声明值、实测值三者一致；json min/max=43/57 |
| C6 | 24 域零重叠 | pass | b6 8 域 ∩ (b2 8 + b4 8 + b5 8 = 24 域) = ∅；json 字段域重叠=0 一致 |
| C7 | 4-gram | pass | 去空白/标点后共享 = **0/0/0**（b2/b4/b5）；补充口径（仅去空白）6/7/8 条全为通用串（`00元，`/`80元，`/`多少钱？`/`费多少？`/`姓什么？` 等），实质复用 = **0** |
| C8 | 16 条 lure 语义 | pass | 16/16 源文明确未给（逐条「源文哪句没有」见 JSON `lure_review`）；歧义 0（b6-s2-q4 低度可推断、仍属未给） |
| C9 | 24 条 detail 语义 | pass | 24/24 有源文依据（逐条引句见 JSON `detail_review`） |
| C10 | 无 gold/标注值/提示 | pass | 题面与 json 均无逐题标注值/答案；`gold` 0 次、`答案` 0 次；字面「期望」仅附录 A 表头 1 处；四态标签名仅 §5 协议定义 |
| C11 | 冻结留痕/哈希闭包 | pass | `frozen=true`、§8 六行齐全、无自引哈希（md 不含自身/json sha16，json 不含自身 sha）、json sha 可复算；附注 `frozen_at` 早于 mtime +35 s |
| C12 | 坐标哈希 | pass | b2/b4/b5 PREREG、rev7、rev7.1、M5B2-LEAD-RULING 六项复算全部命中 |
| C13 | 附录 A 复核 | pass(计数)+unverifiable(2) | 场景/题数/汉字/域/专名(全 0)/4-gram(0,0,0)/md-json 均复现；「引用片段数 55/49/50」与「禁用标记词 2 类」无法复算（脚本不入库、词表未披露） |
| C14 | 隔离条款 | pass(文档)+unverifiable(执行) | §9 隔离条款齐备；他方是否实际未读 b6 无法由产物验证 |
| C15 | 只读与纪律 | pass | 复核前后 B6 md/json 哈希不变；未读 b5 运行数据；零 GPU/模型/联网 |

**非阻塞附注**：① `frozen_at=21:16:03` 早于两文件 mtime `21:16:37`（约 +35 s），§8 记录只能落盘后补录，审批时刻为声明、不可由字节证明，建议注明「落盘后补录」或改时间戳；② 附录 A 的 55/49/50 与「禁用标记词」两项属临时脚本口径，无法独立复算。
完整逐条证据（16 lure 逐条缺失依据、24 detail 逐条引句、4-gram 逐条判读与上下文、六项坐标复算、标签扫描命中行）见 `kvmem/m2_visibility/m5/out/M5C2-B6-FREEZE-REVIEW.json`。
