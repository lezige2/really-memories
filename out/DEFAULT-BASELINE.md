# A 默认基线（K2 off + verifier v1）

- 8765 单监听 PID 3180；DB `kvmem/default/chat.db (daily 副本)`（daily 同源副本）；**K2 off**、**verifier v1**（未设 env）、event off、TTS off、ngl28、topk4、memories=20
- DB sha：daily `0a7eae49…`；副本跑前 `be86499b…` → 跑后 `de28202a…`（副本 sha 与 daily 不同（同 192512 B，逻辑同为 20 行）；疑为 cp 时 WAL 状态差异，服务启动即读到 20 条）

| 件 | pass | 失败 |
|---|---|---|
| 81 | **81/81** | 无 |
| extra | **18/20** | L07, L09 |
| MT20 | **11/20** | V9MT01, V9MT02, V9MT07, V9MT09, V9MT10, V9MT11, V9MT12, V9MT17, V9MT18 |

## 说明

- 三件 hermetic 终态均 20，未写 daily。
- MT20 仅 11/20：K2 off 下同族/跨族干扰未被过滤（V9MT01/02 猫串、V9MT07/09/10 工位与车牌串、V9MT11/12 公司、V9MT17/18 爱吃旧值），与 S0B（K2 auto，18/20）形成明确落差。
- extra 18/20：L07「邮箱记不清」、L09「银行卡 88888」——与 K2 auto 下同因，属答案层问题。
- 结论：默认（K2 off + v1）显著劣于候选口径，符合“K2 on + v2.2”的取舍方向。