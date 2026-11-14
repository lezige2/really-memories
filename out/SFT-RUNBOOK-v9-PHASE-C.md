# TASK-105 v9 Phase C 五臂对照命令清单（proxy，8767）

口径：全部 `temperature=0.0 / top_k=1 / n_predict=192 / stop=<|im_end|>`，`--now "2026-10-28 21:00"` **冻结且各臂一致**；
base 与 v9 的 MT20 必须用**同一个** `out/SFT-EXTRA-CASES-v9-MT20.jsonl`（sha16 140500d3ca651ce5）。
proxy≠service；MT20 的 n=20 与 193 主套件不混算。

## 0) 输入产物（已存在则复用，否则补跑）
- 主套件 193：`out/PROXY-base.json`（base 156/193）、`out/PROXY-v5.json`、`out/PROXY-v8.json`、`out/PROXY-v8b.json`
- 本次新增：`out/PROXY-v9.json`、`out/PROXY-autonomy-v9.json`、`out/PROXY-MT-base.json`、`out/PROXY-MT-v9.json`

## 1) MT20 base 臂（8767 = base 无 lora，**先跑**）
```bash
python -X utf8 out/SFT-PROXY-EVAL.py --arm base --port 8767 \
  --now "2026-10-28 21:00" --only-extra \
  --extra-cases out/SFT-EXTRA-CASES-v9-MT20.jsonl --out out/PROXY-MT-base.json
```

## 2) v9 三件（8767 = base Q4 + v9 lora）
```bash
# 主套件 193
python -X utf8 out/SFT-PROXY-PREFLIGHT.py --arm sft --port 8767 \
  --lora "D:/models/v9/qwen-sft-v9-lora.gguf" --expect-lora-sha <v9_sha16>
python -X utf8 out/SFT-PROXY-EVAL.py --arm sft --port 8767 \
  --lora "D:/models/v9/qwen-sft-v9-lora.gguf" --expect-lora-sha <v9_sha16> \
  --now "2026-10-28 21:00" --out out/PROXY-v9.json

# autonomy 37（D 空 user，dempty）
python -X utf8 out/SFT-PROXY-EVAL.py --arm sft --port 8767 \
  --lora "D:/models/v9/qwen-sft-v9-lora.gguf" --expect-lora-sha <v9_sha16> \
  --now "2026-10-28 21:00" --only-extra \
  --extra-cases out/SFT-EXTRA-CASES-v3-dempty.jsonl --out out/PROXY-autonomy-v9.json

# MT20 20（system+3-8 轮 history+最后提问；固定 history 回放）
python -X utf8 out/SFT-PROXY-EVAL.py --arm sft --port 8767 \
  --lora "D:/models/v9/qwen-sft-v9-lora.gguf" --expect-lora-sha <v9_sha16> \
  --now "2026-10-28 21:00" --only-extra \
  --extra-cases out/SFT-EXTRA-CASES-v9-MT20.jsonl --out out/PROXY-MT-v9.json
```

## 3) 对照产物
```bash
# 五臂主套件（base/v5/v8/v8b/v9，193）：out/PROXY-COMPARE-v9.json
python -X utf8 out/SFT-PROXY-COMPARE-v9.py

# MT20 两臂配对表（base vs v9，n=20）：out/PROXY-COMPARE-MT20.json
python -X utf8 out/SFT-PROXY-MT20-PAIR.py
```
- 五臂脚本只吃 193 产物；**不要**把 `PROXY-MT-*.json` 传给 5WAY（否则 n=20 混入 193，且 cases_sha.extra 会与 extra_v2 冲突）。
- MT20 配对脚本自校验：both_only_extra、same_cases_sha_extra（同一 MT20 文件）、same_now、same_harness、
  same_ids、n_20、temp0_topk1；任一不满足 exit 4。

## 4) K2 备注
K2 后 gate sha 会变；终评引用以最终 gate 产物为准，E 侧无需改动。