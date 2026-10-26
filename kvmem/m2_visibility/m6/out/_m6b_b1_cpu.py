# -*- coding: utf-8 -*-
"""E3-CPU real-14B (gpu=0) B1 check: P1 corrupt-chat, P2 block rejection.
No GPU, no signals; one CPU engine; old module from backup and new module.
"""
import hashlib, importlib.util, json, os, shutil, sqlite3, sys, time
from pathlib import Path
ROOT=Path(r'D:\llama-mem');TOOLS=ROOT/'tools';sys.path.insert(0,str(TOOLS))
M6=ROOT/'kvmem/m2_visibility/m6';OUT=M6/'out';TMP=M6/'tmp/b1cpu';TMP.mkdir(parents=True,exist_ok=True)
B=ROOT/'kvmem/m2_visibility/m3/_before/M6B-B1-20261026';MODEL=r'D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf';MODEL_BYTES=8988110240
DLL=str(TOOLS/'kvshim.dll'); DB=str(ROOT/'kvmem/chat.db'); SRC=ROOT/'kvmem/m2_visibility/m7/out/tmp/e3gpu'
import kvslots, memory_source as ms
def sha16(p):
 b=Path(p).read_bytes();return hashlib.sha256(b).hexdigest()[:16]
def info(p):
 b=Path(p).read_bytes();return {'path':str(p),'sha16':hashlib.sha256(b).hexdigest()[:16],'bytes':len(b)}
def load_mod(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
old_ss=load_mod('b1_cpu_ss_old',str(B/'session_state.py'));new_ss=load_mod('b1_cpu_ss_new',str(TOOLS/'session_state.py'))
# fixtures
man=TMP/'s1.json';chat=TMP/'s1.chat.kvmem';shutil.copyfile(SRC/'s1.json',man);shutil.copyfile(SRC/'s1.chat.kvmem',chat)
bad=TMP/'bad.chat.kvmem';shutil.copyfile(chat,bad)
with open(bad,'r+b') as f: f.seek(0);f.write(b'\0'*256)
badman=TMP/'bad.json';bm=json.load(open(man,encoding='utf-8'));bm['chat']['state']='bad.chat.kvmem';json.dump(bm,open(badman,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
nonman=TMP/'s2_none.json';m=json.load(open(man,encoding='utf-8'));m['chat']={'state':None,'n_tokens':0,'start':4096,'end':4096,'bytes':None};m['placement']['chat_range']={'start':4096,'end':4096};json.dump(m,open(nonman,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
# engine
t0=time.perf_counter();eng=kvslots.KVEngine(MODEL,n_ctx=8192,n_seq=8,gpu=0,dll=DLL);load_s=round(time.perf_counter()-t0,2)
base_reset=eng.reset;calls=[]
def counted(seq):
 calls.append(int(seq));return base_reset(seq)
eng.reset=counted
def seed(seq=0):
 base_reset(0);eng.write_at(0,'a a a a a a a',0,False);return [eng.n_tokens(0),eng.pos_max(0)]
def run(mod,man_path,inject_block=False):
 calls.clear();base_reset(0);eng.write_at(0,'a a a a a a a',0,False)
 before=[eng.n_tokens(0),eng.pos_max(0)]
 con=sqlite3.connect('file:'+DB+'?mode=ro',uri=True)
 err=None;rep=None
 if inject_block:
  old_li=ms.load_into
  def fail(e,row,seq,model_path=MODEL,kv_type='q8_0'):
   raise RuntimeError('E3-CPU injected block rejection (non-Incompatible)')
  ms.load_into=fail
 try:
  rep=mod.restore_session(eng,con,str(man_path),model_path=MODEL)
 except Exception as e: err=type(e).__name__+': '+str(e)
 finally:
  if inject_block: ms.load_into=old_li
  con.close()
 return {'before':before,'after':[eng.n_tokens(0),eng.pos_max(0)],'reset_calls':calls.copy(),'error':err,'report':rep}
out={'schema':'m6b_b1_e3cpu_v1','at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'scope':'真实 14B CPU（gpu=0）；无 GPU/无信号；P1 损坏 chat 真拒绝，P2 块拒绝为注入以隔离路径',
 'prereg':{'sha16':'73779a220ab0aff5','bytes':7762},'device':{'model':MODEL,'model_bytes':MODEL_BYTES,'dll':DLL,'dll_sha16':sha16(DLL),'dll_bytes':os.path.getsize(DLL),'gpu':0,'engine_load_s':load_s,'pid':os.getpid()},
 'fixtures':{'manifest':info(man),'chat':info(chat),'corrupt_chat':info(bad),'corrupt_manifest':info(badman),'no_chat_manifest':info(nonman)},
 'P1':{'red':run(old_ss,badman),'green':run(new_ss,badman)},
 'P2':{'red':run(old_ss,nonman,True),'green':run(new_ss,nonman,True)}}
out['verdict']={'P1_red_loss':out['P1']['red']['reset_calls']!=[], 'P1_green_zero':out['P1']['green']['reset_calls']==[] and out['P1']['green']['after']==[7,6],
 'P2_red_loss':out['P2']['red']['reset_calls']!=[], 'P2_green_zero':out['P2']['green']['reset_calls']==[] and out['P2']['green']['after']==[7,6],
 'C++':'未接上（受不重建 DLL 限制）'}
try: eng.close()
except Exception: pass
p=OUT/'M6B-B1-E3CPU.json';tmp=str(p)+'.tmp';json.dump(out,open(tmp,'w',encoding='utf-8',newline='\n'),ensure_ascii=False,indent=1);os.replace(tmp,p)
print(json.dumps({'P1':out['P1'],'P2':out['P2'],'verdict':out['verdict'],'artifact':info(p)},ensure_ascii=False,indent=1))
