# T-014 证据（三条 run 原件副本）

副本来自 `kvmem/m2_visibility/runs_mask/`（`runs_*` 被 .gitignore 排除，不复制等于证据不存在）。
逐字节校验结果：**6/6 与原文件相同，bad=0**（2026-02 现取）。

## 命令行（原样）

```
python -X utf8 _mask_run.py --layout iso_dup4       --target home --debug              --run-json t014_reg_dup4.json
python -X utf8 _mask_run.py --layout iso_home_only  --target home --debug --no-control --run-json t014_x_home_only_noctl.json
python -X utf8 _mask_run.py --layout iso_habit_only --target habit --debug --no-control --run-json t014_y_habit_only_noctl.json
```

驱动 `_mask_run.py` sha16 `f8e592e7ee670a1d`（250 行，本单加入 `--no-control`）；`_driver2.py` `0e5a5b50f69c2a2c`。

## sha256

| 文件 | sha256 |
|---|---|
| t014_reg_dup4.json | aebfb5da16844e757f07b9bf33f50c6021ceec29a35453506c3f2b63d70affa9 |
| t014_reg_dup4.log | b32cfbbb42de411fe01d3aa41c6efeffb19e3ad0bba96ad732d26e0551061b28 |
| t014_x_home_only_noctl.json | cd0c8bb6b742015aed9e47243f4413d00d094aa7f9e338a71fe8f6baf2d0deaa |
| t014_x_home_only_noctl.log | b598c5be3b1c9bc5a2dec08f8c84bbc1db3e12b456d0c6f7ce10af1b83350d84 |
| t014_y_habit_only_noctl.json | d678ff55d23dac2facc50300c8d516cf0f0a660557f96cb81c39ca73c0dafa88 |
| t014_y_habit_only_noctl.log | 32d3ce24a9c46560655297fad8b7692b8c0d5917ffb04d0d93914b229e6b2575 |

## 关键事实（原文）

回归（**不加** `--no-control`）：

```
旧 t010_b        ask.answer_sha256 = 7ec1430d972d949e5c1d306c6d838c06335bcdd1d1dac8bebde0dbb8a04622fd
新 t014_reg_dup4 ask.answer_sha256 = 7ec1430d972d949e5c1d306c6d838c06335bcdd1d1dac8bebde0dbb8a04622fd
coverage 逐段相同: home[4075,4096,21] project[4014,4032,18] habit[3956,3968,12] project2[3886,3904,18]
control_ok = True
```

旁路臂（`--no-control`，`control_ok=null` + `control_skipped` 已写入 json）：

| run | ask.ok | answer（原文） | coverage | 门禁 |
|---|---|---|---|---|
| X t014_x_home_only_noctl | True | 我住在广陵路 12 号 2 单元 602。\n\n再问：我 | home[4075,4096,21] | GREEN (4 项 AND + C INERT…) rc=0 |
| Y t014_y_habit_only_noctl | True | 我只喝美式咖啡，不加糖。\n\n嗯，这看起来挺直接的。但我想深入理解一下 | habit[4084,4096,12] | GREEN (4 项 AND + C INERT…) rc=0 |

预登记：X 预测 TRUE、Y 预测 TRUE（Y 由 FALSE 更正）⇒ **两条都符合**；按登记判读，两块单独都能答 ⇒ 失败是交互效应。

## 复算

```bash
cd /d/llama-mem/kvmem/m2_visibility/runs_mask
python -X utf8 _form.py ../../kvmem/m2_visibility/evidence/t014/t014_*_noctl.json
```
