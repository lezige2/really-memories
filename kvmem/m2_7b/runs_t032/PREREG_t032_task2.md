# T-032 · 任务2 预登记（在跑之前写入，跑完不改）

臂：P_pp18_only = home(slot1) + habit(slot3) + project_paraphrase18(slot4)，**去掉 project**。
相对 F（iso_fac_pp18 = home + project + habit + pp18）：home/habit/pp18 的 slot 与绝对区间一字不改，
唯一变化是 **project 的 18 格（slot2，[4014,4032)）整体缺席**。
几何：home [4075,4096)、提问点 4096、gap_top 须为 0（cell_scan 实测，不靠公式）。
问：home 原问题「我住在哪？」。两次独立进程。

预登记（写于跑之前）：
  通过 ⇒ 失败需要"project 与它的改写同时在场" ⇒ 同事实的两种表面形式同时在场才坏。
  仍失败 ⇒ 与 project 是否在场无关 ⇒ 该解释不成立。

备注（不改判据）：去掉 project 会在 [4014,4032) 留一个空洞，填充物并没有补上；这是"缺块"而不是"换块"，
除非结果反转，否则不作为额外变量讨论。
