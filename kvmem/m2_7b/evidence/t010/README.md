# T-010 证据（五条 mask run 原件副本）

本目录是 `kvmem/m2_visibility/runs_mask/` 下五份产物的**逐字节副本**。
`runs_*` 被 .gitignore 排除（`**/runs_*/*.json` / `*.log`），所以证据必须复制到这里才进得了库。

## 每条的命令行（原样）

```
python -X utf8 _mask_run.py --layout iso_car_back  --target car   --debug --run-json t010_a_car.json
python -X utf8 _mask_run.py --layout iso_dup4      --target home  --debug --run-json t010_b_dup4_home.json
python -X utf8 _mask_run.py --layout iso_no_car    --target home  --debug --run-json t010_c_nocar_home.json
python -X utf8 _mask_run.py --layout iso_habit_bot --target home  --debug --run-json t010_d_habitbot_home.json
python -X utf8 _mask_run.py --layout iso_car_back  --target habit --debug --run-json t010_e_carback_habit.json
```

工作目录 `kvmem/m2_visibility/runs_mask/`，环境 `LLAMA_KV_MASK_NODEDUP=1`（脚本内 export）。
驱动版：`_mask_run.py` sha16 `f91a6fd91c3bd44b` / 240 行。DLL：`849e7281c74a5288`。

## 文件 sha256（与 runs_mask/ 原件逐一相同，2026-02 现取）

| 文件 | sha256 |
|---|---|
| t010_a_car.json | 69fd83a9ac9ad7bcfb5773edbe00be808f11f7070a0d71b451ffed8a6d8195ba |
| t010_a_car.log | bd37183154cc4522ed1059ad388cd3c2b8662391ef57a7d74f3ec969111bc1c8 |
| t010_b_dup4_home.json | 9b3b9c48f4348f64650c8d734ed24bcb575e0a91449b0f4fd445b5eca553495e |
| t010_b_dup4_home.log | d12ec3f168e20b9c09cdbab7929bbe822d78159c0f9a0e61fb6d6bd12fb8fa7b |
| t010_c_nocar_home.json | 8ed215fde74fdf080191f4b53e43aaa5ebc69f6e4a0a11b63c4f403041040fb0 |
| t010_c_nocar_home.log | 2d0bf02a16abe5b7675e9b39cf5ec9316a507288e0d6dddfb43ea59b2d58abee |
| t010_d_habitbot_home.json | a491d0db7ad91a05726ef29ecc1230044b31795955a8b6d951ad09bca5679a1f |
| t010_d_habitbot_home.log | 02582141110e7a733feb83a7d6bca061c9b72118764b06e8a133c20b8e66b422 |
| t010_e_carback_habit.json | 12b0f5dbdaa9aee2752f4e2c414fc829ea5a25bfe6a6e6152ceb892f046415cf |
| t010_e_carback_habit.log | 9038cfd706be48bda72319fbae64951c6588cea965de4dda6d481a710959239d |

复算副本一致性（任一份不符即失败）：

```bash
cd /d/llama-mem/kvmem/m2_visibility
sha256sum -c SHA256SUMS      # 本目录内
```
（本机若无 `sha256sum`，用 `python -X utf8 -c ...` 逐对比；判据只认退出码。）

## 预登记预测（队长写于跑之前）vs 实测

| run | layout | target | 预测 ok | 实测 ok | 符合 |
|---|---|---|---|---|---|
| A | iso_car_back | car | TRUE | TRUE | 是 |
| B | iso_dup4 | home | TRUE | TRUE | 是 |
| C | iso_no_car | home | TRUE | TRUE | 是 |
| D | iso_habit_bot | home | FALSE | FALSE | 是 |
| E | iso_car_back | habit | FALSE | FALSE | 是 |

`ask.ok` 预登记在先：**5/5 相符**。

形态预测登记**晚于**这五条 run 的实际运行（预测是 plain×5，收到时结果已产出），
因此形态一栏**不构成预测证据**，只能算描述。

## 实测字段（原文）

| run | ok | answer_len | cell_count | 门禁 |
|---|---|---|---|---|
| A | True | 32 | 70 | GREEN (4 项 AND) rc=0 |
| B | True | 30 | 69 | GREEN (4 项 AND) rc=0 |
| C | True | 30 | 51 | GREEN (4 项 AND) rc=0 |
| D | False | 42 | 63 | GREEN (4 项 AND) rc=0 |
| E | False | 35 | 70 | GREEN (4 项 AND) rc=0 |

## 形态判定（`runs_mask/_form.py`，口径见该文件 docstring）

| run | 归一化后 form | 未归一化 form | 最长连续 _ | 字面 \_ 组数 | cloze_marker |
|---|---|---|---|---|---|
| A | plain | plain | 0 | 0 | n |
| B | plain | plain | 0 | 0 | n |
| C | plain | plain | 0 | 0 | n |
| D | quiz | quiz | 12 | 12 | Y |
| E | plain | plain | 0 | 0 | n |

D 的答案里是 12 组 `\_`（反斜杠+下划线），不是连续下划线；按"含『填空』即 quiz"两条读法都判 quiz。

## 复算

```bash
cd /d/llama-mem/kvmem/m2_visibility/runs_mask
python -X utf8 _form.py ../../kvmem/m2_visibility/evidence/t010/t010_*.json   # 注意从 runs_mask 出发用 evidence 相对路径
python -X utf8 _form.py t010_a_car.json t010_b_dup4_home.json t010_c_nocar_home.json t010_d_habitbot_home.json t010_e_carback_habit.json
```
