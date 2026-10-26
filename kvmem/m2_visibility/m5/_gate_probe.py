import json,sys,os
sys.path.insert(0,'kvmem/m2_visibility/m5')
import run_m5c2_r2 as R
with open('kvmem/m2_visibility/m5/out/_gate_probe.json','w',encoding='utf-8') as f:
    json.dump(R.host_gate(),f,ensure_ascii=False,indent=1)
    f.write('\n')
print('probe done')
