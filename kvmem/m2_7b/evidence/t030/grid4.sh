#!/bin/bash
cd /d/llama-mem/kvmem/m2_visibility/runs_mask || exit 9
export LLAMA_KV_MASK_NODEDUP=1
W=/c/Users/lezige/Documents/deepseek-harness/default-workspace/t030
echo "########## 第四格：块尾 4095（project [4078,4095]），提问点 4095 ##########"
python -X utf8 $W/curve_one.py --name grid4_tail4095_ask4095 --layout iso_car_back --blocks project --target project --ask-pos 4095 --k 5 > $W/grid4.json 2>$W/grid4.err
echo "  rc=$?"
tail -3 $W/grid4.err
python -X utf8 $W/curve_one.py --name grid1_ref_tail4095_ask4096 --layout iso_car_back --blocks project --target project --ask-pos 4096 --k 5 > $W/grid1.json 2>$W/grid1.err
echo "  grid1(基线复核) rc=$?"
echo T030_GRID_DONE