# P2 owner + coarse→rerank 实施方案（不写码）

> P1b/S2 三次失败后的结论：瓶颈是 **subject/owner 抽取能力**，不是打分/闸；本窗口不再写码。

## 1 目标

```
query → coarse topk10/20（不跑 K2/time）
      → 候选池内：subject 过滤 → time → K2（仅在池内）
      → 最终 top4
```

## 2 前置（必须先做）

1. **确定性 subject 抽取**：词表/显式标记/同句共现；不许模型抽；
2. 块侧 subject 存 **sidecar**（键=块 id，可重建，不写 daily tags）；
3. P1b 的教训：`daily_memory_meta.tags` 参与检索加权，**语义标签不能塞 tags**；
4. held-out 必须新造：多主体链、否定/离开、主体缺失、换牌 vs 新买一辆。

## 3 验收门

- pool recall@20 ≥0.95（≥38/40）；
- 200 档 recall@4 ≥0.711、direct≥0.95、误隐=0；
- P50 ≤ 当前 +20%；81/extra/MT20 不回归；
- subject 抽取准确率 ≥95%，抽不出→ambiguous，不猜。

## 4 为什么现在不做

- P1b R2 5/18：extract_miss 9、ambiguous 错判 4、否定仍漏；
- S2 闸 v2 9/10+8/10、gate-free 3/10；根因同 subject；
- 2.5h 内重写抽取+重排+验收，只会重演“边跑边调”；
- 先做确定性抽取与 sidecar，等下一窗口有完整 held-out 再开。

## 5 明确不做

- 不用模型抽 subject；
- 不放宽 pool/recall 门槛；
- 不把 tags 当语义元数据；
- 不在 K2 off 时假装 P2 有效。