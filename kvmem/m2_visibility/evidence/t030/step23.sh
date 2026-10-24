#!/bin/bash
cd /d/llama-mem/kvmem/m2_visibility/runs_mask || exit 9
export LLAMA_KV_MASK_NODEDUP=1
W=/c/Users/lezige/Documents/deepseek-harness/default-workspace/t030
echo "########## 步骤 2：洞=1，提问点挪到 4095（块 [4077,4094]） ##########"
python -X utf8 $W/curve_one.py --name hole1_ask4095 --layout iso_car_back --blocks project --target project --ask-pos 4095 --k 5 > $W/hole_askat4095_a.json 2>$W/hole_askat4095_a.err; echo "  run rc=$?"
python -X utf8 -c "import json;d=json.load(open('hole_askat4095_a.json',encoding='utf-8'));print('  blocks',d['blocks'],'ask_pos',d['ask_pos'],'rc',d['rc'],'ok',d['ok']);print('  answer=%r'%(d['answer'][:60],))" 2>&1 | tail -3
echo "########## 步骤 3：曲线 A-F（问 home，首步 top-8） ##########"
run2 () {
  python -X utf8 $W/curve_one.py --name "$1" --layout "$2" --blocks "$3" --target home --k 8 --fact-token "$4" > $W/curve_$1_r1.json 2>$W/curve_$1_r1.err
  python -X utf8 $W/curve_one.py --name "$1" --layout "$2" --blocks "$3" --target home --k 8 --fact-token "$4" > $W/curve_$1_r2.json 2>$W/curve_$1_r2.err
}
run2 A iso_car_back home 35946
run2 B iso_car_back home,project 35946
run2 C iso_car_back home,project,habit 35946
run2 D iso_car_back "" 35946
run2 E iso_dup4 "" 35946
run2 F iso_fac_pp18 "" 35946
echo T030_STEP23_DONE