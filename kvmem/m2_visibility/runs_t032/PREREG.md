# T-031 任务 2 预登记（写入时间：跑之前，块已落盘、布局尚未跑）

本文件在**任何** iso_fac_hp12 运行之前写成。跑完后不得修改本文件的"预登记"段落，
只能在下面的"结果"段落追加。

## 被问的问题与构型（写死）

- 构型：iso_fac_hp12 = home(21) + project(18) + habit(12) + [slot4 = habit_paraphrase(12)]
  - 几何（按 start = 4096 − 3*64 − 12 = 3892 预算）：home [4075,4096)、project [4014,4032)、
    habit [3956,3968)、habit_paraphrase [3892,3904)；span_hi = 4096 ⇒ head_gap_cells = 0；
    提问点 4096 == 块尾+1。
  - 与 F 臂唯一差别：slot4 的块是 habit 的改写（12 格）而不是 project 的改写（18 格），
    因此 start 由 3886 变为 3892（四臂里前三件完全相同）。
- 提问：home 的原问题「我住在哪？」；期望事实「广陵路」。
- 判据：ok = answers[0].ok（P.fact_ok(期望事实, 答案)），与 F 臂同一判据。
- 跑两次（r1/r2），若两次 allow 不同则如实并列。

## 预登记（先写死，再看数）

- **仍失败（MISS）** ⇒ 「近似重复」是通用杀伤，与改写的是哪一块无关：
  slot4 放哪一块的近义改写都会压掉 home 的可达性。
- **通过（OK）** ⇒ 杀伤是局部的：只有「project 的改写」才坏，habit 的改写不坏。
  （此时必须同时记：project 改写块是 18 格、habit 改写块是 12 格，因此"局部"与"格数"未分开，
   要在结论里写明这条共线，不能宣称已经定位到内容层。）

## 结果（跑完追加，不覆盖上文）
### 任务 2 结果（两次跑，2026 观测）

- 命令（workdir D:\llama-mem\kvmem\m2_visibility\runs_t032）：
  `python -X utf8 _driver3.py --layout iso_fac_hp12 --target home --run-json t032_hp12_r1.json`
  `python -X utf8 _driver3.py --layout iso_fac_hp12 --target home --run-json t032_hp12_r2.json`
- rc=0 两次；control_ok=True 两次；ok=False 两次（MISS）。
- answer 全文（两次逐字符相同，repr）：
  `'我住在\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_。\n\n根据以上对话，填空最恰当'`
  answer_len=34 / ask_at 返回 bytes=74 / n_tokens 0->33 / sha16 = **7c2fca5e43c46a3d**。
- 几何自证：coverage home 4075-4096 21/21、project 4014-4032 18/18、habit 3956-3968 12/12、
  habit_paraphrase 3892-3904 12/12；start=3892、cells_total=63、span_hi=4096、head_gap_cells=0。
- **命中预登记的第一个分支**：仍失败 ⇒ 近似重复是通用杀伤，与改写的是哪一块无关
  （F 臂 project 改写失败、本次 habit 改写也失败）。
- 附带事实（方向性，不作结论）：slot4 换块后答案文本与 F 臂**不同**
  （F: 11e20d78a1f18a98 / 本篇: 7c2fca5e43c46a3d），说明 slot4 内容对输出**不是惰性的**。
- 未分开的共线：本次 slot4 是 12 格（F 臂是 18 格），"哪一块"与"格数"仍未分离。
