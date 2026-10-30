# S2 检索线最终结论（2026-10-30，封存）

> 判定：**S2 封存，不做 C′**。三次独立尝试（闸 v2、A query-expand、gate-free）均失败；根因指向 **subject/owner 缺失**，不是打分问题；检索线在补齐主体键前不再开新臂。

## 1 三次尝试

| 尝试 | 结果 | 失败点 |
|---|---|---|
| 闸 v2（cov<.34 & gap=0 & content<2） | 真 held-out **9/10 target、8/10 负例** | cov/gap/content 三信号无法分离；content<2 边界误杀/漏拒 |
| A query-expand（4 通用同义对） | repro 3/5、held-out 3/5（过闸）；rank 池 5/5 | 词表能提前候选，过不了 coverage 闸；第三人称“号码”不扩 |
| gate-free E2E（top4） | recall **3/10=0.30**、1 负例被作答（4821 跨题串味） | 删闸放大同族噪声（小杏/小柠一起挂） |

- top20 挂载：每次 `/ask` HTTP 500 `OSError: access violation reading 0xFFFFFFFFFFFFFFFF`，原生越界；**S1 缺陷，单列，本轮不修不测**。
- 产品保护：挂载数超上限应先断言快速失败，不许走到原生越界（待实现）。

## 2 根因

- 200 库同族多主体（猫、车牌、手机、公司），gate-free 把同族块一起挂 → 串味；
- A 的词表只能提前候选，救不了第三人称主体；
- 闸 v2 的三信号在真 held-out 上无法分离 target/负例；
- 三条都指向 **subject/owner 缺失**，与 K2 over-merge 同根。

## 3 结论与边界

- **删闸否决**：gate-free 0.30 << 有闸 0.71；
- **闸 v2 不启用**，规则回 v1 语义；A FAIL；
- **S2 封存，不做 C′**；不在补齐主体键前再开检索臂；
- 检索线归入 P0 主体键 + P1 写时冲突；现有产品默认不动（K2 off/auto、verifier v2.2 显式、event_date off）。

## 4 证据

- `S2-REPRO.md/json`、`S2-A-PREREG.md`、`S2-A-EVAL.md/json`、`S2-GATE-2X2.md/json`、`S2-GATE-SEPARATION.md/json`、`S2-GATE-HELDOUT-20.jsonl`（sha `3d04414c…`）、`S2-GATE-HELDOUT-REPORT.md/json`、`S2-GATE-FREE-E2E.md/json`；
- 规则 sha `9ff03502…`、信号脚本 `6e4e119a…`、held-out sha `77131e05…`。