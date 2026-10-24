#!/bin/bash
cd /d/llama-mem/kvmem/m2_visibility/runs_mask || exit 9
export LLAMA_KV_MASK_NODEDUP=1
W=/c/Users/lezige/Documents/deepseek-harness/default-workspace/t030
echo "=== 行为回归（不调用新函数）：iso_dup4/home 必须 7ec1430d…22fd ==="
python -X utf8 _mask_run.py --layout iso_dup4 --target home --debug --run-json t030_reg_dup4.json > t030_reg_dup4.log 2>&1; echo "  rc=$?"
python -X utf8 -c "import json;a=json.load(open('t030_reg_dup4.json',encoding='utf-8'));ref='7ec1430d972d949e5c1d306c6d838c06335bcdd1d1dac8bebde0dbb8a04622fd';print('  sha=',a['ask']['answer_sha256'][:16],'same=',a['ask']['answer_sha256']==ref)"
echo "=== 新函数确定性：同一输入跑两次 ==="
python -X utf8 $W/topk_probe.py iso_car_back home home > $W/topk_run1.json 2>$W/topk_run1.err; echo "  run1 rc=$?"
python -X utf8 $W/topk_probe.py iso_car_back home home > $W/topk_run2.json 2>$W/topk_run2.err; echo "  run2 rc=$?"
python -X utf8 -c "
import json
a=json.load(open(r'$W/topk_run1.json',encoding='utf-8'))
b=json.load(open(r'$W/topk_run2.json',encoding='utf-8'))
print('  rc',a['rc'],'|','top5 identical:',a['top5']==b['top5'],'| answer identical:',a['answer']==b['answer'])
print('  top5:',[(t['token'],round(t['prob'],6)) for t in a['top5']])
print('  answer=%r' % (a['answer'][:60],))
"
echo T030_TOPK_ACCEPT_DONE