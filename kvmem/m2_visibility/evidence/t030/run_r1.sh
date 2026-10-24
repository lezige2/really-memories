#!/bin/bash
set -o pipefail
cd /d/llama-mem/kvmem/m2_visibility/runs_mask || exit 9
export LLAMA_KV_MASK_NODEDUP=1
for spec in "P direct" "P rotated" "C direct" "C rotated"; do
  set -- $spec
  stem=t030_r1_$1_$2
  echo "########## $stem ##########"
  python -X utf8 _t030_r1.py --arm $1 --mode $2 --run-json $stem.json > $stem.log 2>&1
  echo "  rc=$?"
  tail -2 $stem.log | sed "s/^/  log: /"
done
echo "########## 汇总（脚本读产物） ##########"
python -X utf8 -c "
import json,glob
ref_base='e63faeffa318b72a'
for p in sorted(glob.glob('t030_r1_*.json')):
    d=json.load(open(p,encoding='utf-8'))
    pr=d['preamble']
    print('%-22s mode=%-8s cells=%s delta=%s sha=%s ok=%s len=%s' % (p[:-5], d['mode'], d.get('cells_at_ask'), pr.get('repos_delta'), d['answer_sha256'][:16], d['ok'], d['len']))
    print('    answer=%r' % (d['answer'][:60],))
"
echo T030_R1_DONE