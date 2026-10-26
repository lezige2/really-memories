# -*- coding: utf-8 -*-
"""Audit gap B regression: preflight scratch must not equal a block target seq.
Buggy module = current fixed source with the single +2 reverted to +1.
Fake engine models kvshim_load: load(seq) clears seq before the refusal.
"""
import hashlib, importlib.util, json, os, sys, types, time
from pathlib import Path
ROOT=Path(r'D:\llama-mem');TOOLS=ROOT/'tools';sys.path.insert(0,str(TOOLS))
OUT=Path(__file__).with_name('M6B-B1-SCRATCH.json');TMP=ROOT/'kvmem/m2_visibility/m6/tmp/b1scratch';TMP.mkdir(parents=True,exist_ok=True)
MODEL=r'D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf';MODEL_SIZE=8988110240
import memory_source as ms
def sha16(p):
 b=Path(p).read_bytes();return hashlib.sha256(b).hexdigest()[:16]
def info(p):
 b=Path(p).read_bytes();return {'path':str(p),'sha16':hashlib.sha256(b).hexdigest()[:16],'bytes':len(b)}
# manifest no chat, 1 block slot0 -> target seq1
srcman=ROOT/'kvmem/m2_visibility/m7/out/tmp/e3gpu/s1.json';m=json.load(open(srcman,encoding='utf-8'))
m['chat']={'state':None,'n_tokens':0,'start':4096,'end':4096,'bytes':None};m['placement']['chat_range']={'start':4096,'end':4096}
man=TMP/'scratch_none.json';json.dump(m,open(man,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
# buggy module: exactly the old +1
fixed=TOOLS/'session_state.py';txt=fixed.read_text(encoding='utf-8')
assert 'scratch = max_slot_id + 2' in txt
bug=TMP/'session_state_plus1.py';bug.write_text(txt.replace('scratch = max_slot_id + 2','scratch = max_slot_id + 1'),encoding='utf-8',newline='\n')
def load_mod(name,path):
 spec=importlib.util.spec_from_file_location(name,str(path));mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
ss_red=load_mod('b1_scratch_plus1',bug);ss_green=load_mod('b1_scratch_fixed',fixed)
ROW=(1,'profile','profile','<text>','<hash>',1,'D:\\llama-mem\\kvmem\\blocks\\profile.kvmem',50,0,MODEL,MODEL_SIZE,1792858962,'q8_0',1)
class FakeEng:
 def __init__(self): self.seqs={0:[7,6],1:[7,6],2:[7,6]};self.n_seq=8;self.loads=[]
 def n_tokens(self,s): return int(self.seqs.get(int(s),[0,-1])[0])
 def pos_max(self,s): return int(self.seqs.get(int(s),[0,-1])[1])
 def cells_of(self,s): return self.n_tokens(s)
 def reset(self,s): self.loads.append(('reset',int(s)));self.seqs[int(s)]=[0,-1]
 def load(self,s,path):
  # kvshim_load: reset the seq FIRST, then fail
  self.loads.append(('load',int(s)));self.seqs[int(s)]=[0,-1]
  raise RuntimeError('injected preflight refusal after kvshim reset')
 def load_strict(self,s,path): raise RuntimeError('not used')
 def repos_local(self,*a,**k): return 0
 def share(self,*a,**k): pass
 def close(self): pass

def run(mod):
 eng=FakeEng();before=[eng.n_tokens(1),eng.pos_max(1)]
 ms.block_rows=lambda con:[ROW]
 def li(e,row,seq,model_path=MODEL,kv_type='q8_0'):
  return e.load(seq,row[6])
 ms.load_into=li
 err=None
 try: mod.restore_session(eng,None,str(man),model_path=MODEL)
 except Exception as e: err=type(e).__name__+': '+str(e)
 return {'before':before,'after':[eng.n_tokens(1),eng.pos_max(1)],'loads':eng.loads,'error':err}
red=run(ss_red);green=run(ss_green)
# cross-check: buggy module replaced exactly one token
out={'schema':'m6b_b1_scratch_collision_v1','at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
 'question':'P2 preflight scratch == highest block target seq ? "先清后验" : unused',
 'bug_source':{**info(bug),'diff_from_fixed':'scratch = max_slot_id + 1 (old +1)'},
 'fixed_source':info(fixed),'manifest':info(man),
 'red':red,'green':green,
 'verdict':{'red_collides':red['loads'][0][1]==1 and red['after']==[0,-1],
            'green_no_collision':green['loads'][0][1]==2 and green['after']==[7,6],
            'same_error':red['error']==green['error']}}
p=OUT;tmp=str(p)+'.tmp';json.dump(out,open(tmp,'w',encoding='utf-8',newline='\n'),ensure_ascii=False,indent=1);os.replace(tmp,p)
print(json.dumps({'red':red,'green':green,'verdict':out['verdict'],'artifact':info(p)},ensure_ascii=False,indent=1))
