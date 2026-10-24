# T-031 任务 1 补充：F 臂的独立交叉核对（不是我跑的，是本机另一个执行者的产物）

| 产物 | 臂 | answer sha16 | ok | 记录的 DLL |
|---|---|---|---|---|
| runs_t031/t031_f_pp18_r1.json（我） | iso_fac_pp18 / home | 11e20d78a1f18a98 | False | c7ea09bbc7cb |
| runs_t031/t031_f_pp18_r2.json（我） | 同上 | 11e20d78a1f18a98 | False | c7ea09bbc7cb |
| runs_t032/t032_f_r1.json（另一执行者） | 同上 | 11e20d78a1f18a98 | False | c7ea09bbc7cb |
| runs_t032/t032_f_r2.json（另一执行者） | 同上 | 11e20d78a1f18a98 | False | c7ea09bbc7cb |

答案全文四份一致：`我住在\_\_\_\_\_\_。\n\n要填空的选项有：A. 中国；B.`

⇒ F 臂现有 **4 个观测点**（我 2 + 另一执行者 2，不同驱动脚本 `_driver2.py` vs `t032_run.py`），
全部 MISS 且逐字符相同；"唯一失败"这一说法现在有第二个（第三个、第四个）观测点支撑。
注意：这 4 份用的是同一个二进制 c7ea09bbc7cb；二进制不同时的可比性见 runs_t032/mine/EXECUTOR_HANDOFF.md 的 binary map。
