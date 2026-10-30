# S2 2×2：A off/on × 闸开/关（n200 副本，只测量）

- 源 `D:\llama-mem\kvmem\scale40k\n200\chat.db` sha `2d84aefda3c76ece`；未改默认/阈值/代码，未写库、未起服务。
- A = 预注册的确定性同义词扩写（牌子→车牌、号码→手机号、会→会议、哪儿人→老家）；闸 = coverage 0.30 gate。

| suite | 格 | in | empty | ranks |
|---|---|---|---|---|
| repro | A_off__gate_on | 0/5 | 3 | [None, None, None, None, None] |
| repro | A_off__gate_off | 3/5 | 0 | [3, 4, 1, None, None] |
| repro | A_on__gate_on | 1/5 | 2 | [None, None, 1, None, None] |
| repro | A_on__gate_off | 3/5 | 0 | [3, 4, 1, None, None] |
| heldout | A_off__gate_on | 3/5 | 2 | [13, None, None, 1, 1] |
| heldout | A_off__gate_off | 5/5 | 0 | [13, 4, 3, 1, 1] |
| heldout | A_on__gate_on | 3/5 | 2 | [2, None, None, 1, 1] |
| heldout | A_on__gate_off | 5/5 | 0 | [2, 4, 2, 1, 1] |

| id | 扩写 | A_off·开闸 | A_off·关闸 | A_on·开闸 | A_on·关闸 |
|---|---|---|---|---|---|
| q048 | 车牌 | N/-E | Y/3 | N/-E | Y/3 |
| q052 | — | N/-E | Y/4 | N/-E | Y/4 |
| q060 | 会议 | N/-E | Y/1 | Y/1 | Y/1 |
| q062 | — | N/- | N/- | N/- | N/- |
| q063 | — | N/- | N/- | N/- | N/- |
| S2H01 | 车牌 | Y/13 | Y/13 | Y/2 | Y/2 |
| S2H02 | — | N/-E | Y/4 | N/-E | Y/4 |
| S2H03 | 会议 | N/-E | Y/3 | N/-E | Y/2 |
| S2H04 | — | Y/1 | Y/1 | Y/1 | Y/1 |
| S2H05 | — | Y/1 | Y/1 | Y/1 | Y/1 |

## 说明

- A 只在 4/10 条触发（q048/q060/S2H01/S2H03）：牌子+车、会+时间；
- 第三人称‘号码/哪儿人’不在预注册语境（需 我/他/她）→ A 不扩，q052/q062/q063/S2H02 原样；
- 闸是主损失：关闸 repro 3/5、heldout 5/5；A 仅把 q060 从空救成 rank1、S2H01 13→2。
