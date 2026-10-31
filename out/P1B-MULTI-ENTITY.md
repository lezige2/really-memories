# P1b 多实体族占比（只读）

- daily `D:\llama-mem\kvmem\daily\chat.db` sha `0a7eae495c4be89c`；n200 `D:\llama-mem\kvmem\scale40k\n200\chat.db` sha `2d84aefda3c76ece`
- 定义：family=单一 predicate；entity=显式 owner 或“我/我的”解析出的 self；同族 distinct 实体 >1 即多实体族。

## 汇总

| 数据集 | 族数 | 多实体族(all) | 多实体率 | 多显式 owner 族 | self 身份 |
|---|---|---|---|---|---|
| daily | 4 | **0** | 0.0% | 0 | 阿泽 |
| n200（对照） | 10 | 8 | 80.0% | 7 | self |

## daily 逐族

| family | 实体 | 实体数 | 多实体 | ids |
|---|---|---|---|---|
| cat | 阿泽 | 1 | 否 | [14] |
| meeting | 阿泽 | 1 | 否 | [1, 2, 5, 7, 8, 9, 10, 11] |
| plate | 阿泽 | 1 | 否 | [3, 12, 13] |
| travel | 阿泽 | 1 | 否 | [4, 6] |

## n200 对照（族级）

| family | 实体数 | 多实体 |
|---|---|---|
| bank | 2 | 是 |
| cat | 12 | 是 |
| color | 1 | 否 |
| company | 16 | 是 |
| dog | 1 | 否 |
| hometown | 12 | 是 |
| meeting | 13 | 是 |
| phone | 14 | 是 |
| plate | 14 | 是 |
| seat | 2 | 是 |

## 判定

- daily 多实体族：0 / 4（显式 owner 多族：0）
- **owner 线：not_applicable** → 不适用，K2/检索维持永久 off
- self 身份：daily=阿泽（候选 ['阿泽']）；n200=self。只读；未写 daily、未 commit。
