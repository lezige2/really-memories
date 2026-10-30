# S2-A 离线评估（baseline vs query-expand）

- held-out sha256 `77131e059095b931b536e6e63479e0a5378d647703ad2df75877e81376da93fd`；n200 源 sha `2d84aefda3c76ecece0cf3f620c506e0748090a587528b8bed513491affd24fd`
- 汇总：{"repro_before_pool20_rank": "3/5", "repro_before_pool20_mounted": "0/5", "repro_after_pool20_rank": "5/5", "repro_after_pool20_mounted": "3/5", "heldout_before_pool20_rank": "5/5", "heldout_before_pool20_mounted": "3/5", "heldout_after_pool20_rank": "5/5", "heldout_after_pool20_mounted": "3/5", "repro_empty_after": 2, "heldout_empty_after": 2, "heldout_sha256": "77131e059095b931b536e6e63479e0a5378d647703ad2df75877e81376da93fd", "pass_offline": true}

| id | set | query | target | before rank/mounted | after rank/mounted | expansions |
|---|---|---|---|---|---|---|
| q048 | repro | 杨帆那车牌子你还记得不？ | 53 | 3/False | 3/False | - |
| q052 | repro | 周昊号码多少来着？ | 70 | 4/False | 4/False | - |
| q060 | repro | 杨帆那个会定在几号几点了？ | 25 | 1/False | 1/True | 会→会议 |
| q062 | repro | 王强是哪儿人？ | 130 | 22/False | 2/True | 哪儿人→老家 |
| q063 | repro | 杨帆是哪儿人？ | 144 | 26/False | 6/True | 哪儿人→老家 |
| S2H01 | heldout | 孙悦那辆车挂的什么牌子？ | 58 | 13/True | 2/True | 牌子→车牌 |
| S2H02 | heldout | 吴静号码是多少来着？ | 71 | 4/False | 4/False | - |
| S2H03 | heldout | 黄婷那个会安排在几号几点？ | 124 | 3/False | 2/False | 会→会议 |
| S2H04 | heldout | 李娜老家是哪儿的？ | 129 | 1/True | 1/True | - |
| S2H05 | heldout | 陈杰那个会定在几号了？ | 121 | 1/True | 1/True | 会→会议 |
