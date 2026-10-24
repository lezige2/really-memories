#!/usr/bin/env bash
# 一键复算 T-006：门禁五支 + 引擎未改动
# 用法：bash verify.sh        期望最后一行 ALL PASS，退出码 0
# 任一断言失败 → 退出码非 0，并打印是哪一支
set -u
cd "$(dirname "$0")"
RM=kvmem/m2_visibility/runs_mask
PY="python -X utf8"
fail=0
n=0

say() { printf '%-46s %s\n' "$1" "$2"; }
ok()  { n=$((n+1)); say "$1" "PASS"; }
bad() { n=$((n+1)); fail=$((fail+1)); say "$1" "**FAIL**"; }

# ---------- 1. 引擎未改动 ----------
read -r ins del <<EOF
$(git -C llama.cpp diff --numstat 2>/dev/null | awk '{i+=$1;d+=$2} END{print i+0" "d+0}')
EOF
if [ "$ins" = "500" ] && [ "$del" = "0" ]; then ok "引擎补丁 ins/del = 500/0"; else bad "引擎补丁 ins/del = $ins/$del（期望 500/0）"; fi

# ---------- 2. 当前产物的哈希（信息，不作断言） ----------
echo "--- 当前驱动指纹（信息）"
( cd "$RM" && $PY -c "
import hashlib
for f in ['_mask_run.py','_gate.py','_assert_trace.py']:
    b=open(f,'rb').read()
    print('   ', f, hashlib.sha256(b).hexdigest()[:16], sum(1 for _ in open(f,encoding='utf-8')), '行')
" ) || bad "读取驱动文件失败"

# ---------- 3. 门禁五支 ----------
run_gate() { # $1=log $2=json  -> 输出退出码
  ( cd "$RM" && $PY _gate.py --log "$1" --run-json "$2" >/dev/null 2>&1; echo $? )
}

expect() { # $1=期望rc $2=实际rc $3=名称
  if [ "$1" = "$2" ]; then ok "$3 (rc=$2)"; else bad "$3 (rc=$2, 期望 $1)"; fi
}

expect 6 "$(run_gate mask_iso_base_home.log mask_iso_base_home.json)" "A1 冻结红臂 mask_iso_base_home"
expect 6 "$(run_gate AB_B_seq99.log AB_B_seq99.json)"                 "A2 整类缺失 AB_B_seq99"
expect 0 "$(run_gate mask_dup4_home.log mask_dup4_home.json)"         "B  冻结绿臂 mask_dup4_home"
expect 0 "$(run_gate gate_v3_iso_car_back.log gate_v3_iso_car_back.json)" "C  新 run（四项 AND 全绿）"

# ---------- 4. 3b 可证伪：删 worker_counts → rc=7 ----------
TMP=$(mktemp -u "$RM/_verify_nowc.XXXXXX.json")
( cd "$RM" && $PY -c "
import json,sys
d=json.load(open('gate_v3_iso_car_back.json',encoding='utf-8'))
assert 'child_env' in d, '该产物不是新 run，无法构造 rc=7'
d.pop('worker_counts',None)
json.dump(d, open(sys.argv[1],'w',encoding='utf-8'), ensure_ascii=False)
" "$(basename "$TMP")" ) || bad "构造 rc=7 用例失败"
expect 7 "$(run_gate gate_v3_iso_car_back.log "$(basename "$TMP")")" "D  新 run 缺 worker_counts → rc=7"
rm -f "$TMP"

# ---------- 5. 3b 可证伪：日志删 10 行 blk → rc=6 ----------
TMPL="$RM/_verify_trunc.log"
( cd "$RM" && awk 'BEGIN{d=0} /^\[MASKDBG\] /{d++; if(d<=10) next} {print}' gate_v3_iso_car_back.log > "$(basename "$TMPL")" ) || bad "构造截断日志失败"
expect 6 "$(run_gate "$(basename "$TMPL")" gate_v3_iso_car_back.json)" "E  日志删 10 行 blk → 3a/3b 同红"
rm -f "$TMPL"

# ---------- 汇总 ----------
echo "---"
if [ "$fail" -eq 0 ]; then echo "ALL PASS ($n 项)"; exit 0; else echo "FAIL: $fail/$n 项未通过"; exit 1; fi
