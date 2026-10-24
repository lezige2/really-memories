#!/bin/bash
cd /d/llama-mem || exit 9
W=/c/Users/lezige/Documents/deepseek-harness/default-workspace/t030
python -X utf8 $W/p_norm.py
echo "=== (a)(b)(c) 检验：同源两建（b1 vs b2，topk 时代） ==="
python -X utf8 $W/norm_pe.py $W/kvshim_vk_topk_b1.dll $W/kvshim_vk_topk_b2.dll 2>&1 | tail -6
echo "=== 行为回归（新引擎 DLL，含 MASKDBG-WIN）：iso_dup4/home ==="
cd kvmem/m2_visibility/runs_mask
export LLAMA_KV_MASK_NODEDUP=1
python -X utf8 _mask_run.py --layout iso_dup4 --target home --debug --run-json t030_reg_dup4b.json > t030_reg_dup4b.log 2>&1; echo "  rc=$?"
python -X utf8 -c "import json;a=json.load(open('t030_reg_dup4b.json',encoding='utf-8'));print('  sha',a['ask']['answer_sha256'][:16])"
echo "=== MASKDBG-WIN 探针是否生效 ==="
grep -c "MASKDBG-WIN" t030_reg_dup4b.log
grep "MASKDBG-WIN" t030_reg_dup4b.log | head -4
echo T030_FINAL_CHECK_DONE