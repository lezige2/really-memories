# S2 闸 v2 真 held-out（20 条新探针）

- 规则：`reject if no_candidate or (cov<0.34 and gap==0 and content<2)`；规则 sha `9ff0350238366447`（源 `out/S2-GATE-SEPARATION.md` sha `459b81dc263b27c1`）
- 信号实现：`out/s2_gate_2x2.py` sha `6e4e119a9c0b10a3`（cov=top1 coverage；gap=top1.score−top2.score；content=top1 命中里非全停用字的个数）
- 探针：`out/S2-GATE-HELDOUT-20.jsonl` sha `3d04414c8335a1a35ed670787887cf8d110b898dd9a4df864d1f4ae567d84486`（20 条 = 10 有 target + 10 负例；全部为新主体/新事实，target 均未出现在 Q40 的 29 个 target 中）
- 库：`kvmem/scale40k/n200/chat.db`（200 行，只读 immutable，未写库、未起服务、未改默认）

## 结果

| 项 | 实测 | 门槛 | 判定 |
|---|---|---|---|
| 目标进池 | **9/10** | 10/10（≥0.95） | ❌ |
| 负例被拒 | **8/10** | 10/10 | ❌ |

丢失目标：H03（cov 0.222/gap 0/content 1）
漏拒负例：H12「我家的Wi-Fi密码是多少？」（cov 0.250/gap 0/content 2）, H19「我的快递单号是多少？」（cov 0.250/gap 0/content 2）

## 结论

**FAIL**：规则在真 held-out 上目标 9/10、负例 8/10，两项均不达标 ⇒ 按 B 的判据「现有信号无法分离」，才开 C / 换信号。规则 v2 不得启用（不改默认、不 commit）。
