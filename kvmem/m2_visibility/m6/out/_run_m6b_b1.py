# -*- coding: utf-8 -*-
"""M6B-B1 unit harness: red (legacy) / green (fixed) / zero behavior.
No GPU, no real model, no signal. Fake engine counts resets; sentinel 7/6.
"""
import hashlib, importlib.util, json, os, shutil, sys, time, types
from pathlib import Path
ROOT=Path(r'D:\llama-mem'); TOOLS=ROOT/'tools'; sys.path.insert(0,str(TOOLS))
M6=ROOT/'kvmem/m2_visibility/m6'; OUT=M6/'out'; TMP=M6/'tmp/b1'; BEF=OUT/'_before'
BEF.mkdir(parents=True,exist_ok=True); TMP.mkdir(parents=True,exist_ok=True)
B=ROOT/'kvmem/m2_visibility/m3/_before/M6B-B1-20261026'
MODEL=r'D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf'
MODEL_SIZE=8988110240
MAN=str(TMP/'s1.json'); CHAT=str(TMP/'s1.chat.kvmem')
import memory_source as ms

def sha16(p):
 b=Path(p).read_bytes();return hashlib.sha256(b).hexdigest()[:16]
def info(p):
 b=Path(p).read_bytes();return {'path':str(p),'sha16':hashlib.sha256(b).hexdigest()[:16],'bytes':len(b)}

def load_mod(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
 sys.modules[name]=m;spec.loader.exec_module(m);return m
old_ss=load_mod('ss_before',str(B/'session_state.py'))
old_chat=load_mod('chat_before',str(B/'chat.py'))
new_ss=load_mod('ss_after',str(TOOLS/'session_state.py'))
new_chat=load_mod('chat_after',str(TOOLS/'chat.py'))

class FakeEng:
 def __init__(self, fail_chat=False, fail_block=False):
  self.seqs={0:[7,6],1:[7,6],2:[0,-1],3:[0,-1],4:[0,-1],5:[0,-1],6:[0,-1],7:[0,-1]}
  self.reset_calls=0;self.target_resets=[];self.load_calls=0;self.load_strict_calls=0
  self.fail_chat=fail_chat;self.fail_block=fail_block;self.closed=False
 def _n(self,s):return int(self.seqs.get(int(s),[0,-1])[0])
 def _p(self,s):return int(self.seqs.get(int(s),[0,-1])[1])
 def reset(self,seq):
  self.reset_calls+=1;self.target_resets.append(int(seq));self.seqs[int(seq)]=[0,-1]
 def load_strict(self,seq,path):
  self.load_strict_calls+=1
  if self.fail_chat: raise RuntimeError('fake chat incompatible/refused')
  # for legal fixture, load the manifest counts
  m=json.load(open(MAN,encoding='utf-8'));n=int(m['chat']['n_tokens']);end=int(m['chat']['end'])
  self.seqs[int(seq)]=[n,end-1];self.load_calls+=1;return n
 def load(self,seq,path):
  self.load_calls+=1
  if self.fail_block: raise RuntimeError('fake block refused (non-Incompatible)')
  self.seqs[int(seq)]=[50,49];return 50
 def n_tokens(self,seq):return self._n(seq)
 def pos_max(self,seq):return self._p(seq)
 def cells_of(self,seq):return self._n(seq)
 def share(self,*a,**k):return None
 def drop(self,*a,**k):return None
 def repos_local(self,seq,delta,*a,**k):
  # emulate move: keep n, shift pos by delta
  n,p=self._n(seq),self._p(seq);self.seqs[int(seq)]=[n,p+int(delta)];return n
 def close(self):self.closed=True

ROW=(1,'profile','profile','<text>','<hash>',1,'D:\\llama-mem\\kvmem\\blocks\\profile.kvmem',50,0,MODEL,MODEL_SIZE,1792858962,'q8_0',1)
def clone_manifest(no_chat=False):
 m=json.load(open(MAN,encoding='utf-8'))
 if no_chat:
  p=str(TMP/'s2.json');m['chat']={'state':None,'n_tokens':0,'start':4096,'end':4096,'bytes':None}
  m['placement']['chat_range']={'start':4096,'end':4096}
  json.dump(m,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=1);return p
 return MAN

def restore(mod,eng,man,block_ok=True):
 ms.block_rows=lambda con:[ROW]
 if block_ok:
  def li(e,row,seq,model_path=MODEL,kv_type='q8_0'):
   return e.load(seq,row[6])
 else:
  def li(e,row,seq,model_path=MODEL,kv_type='q8_0'):
   raise RuntimeError('fake block refused (non-Incompatible)')
 ms.load_into=li
 con=types.SimpleNamespace(close=lambda:None)
 before={'seq0':[eng.n_tokens(0),eng.pos_max(0)],'seq1':[eng.n_tokens(1),eng.pos_max(1)]}
 err=None;rep=None
 try: rep=mod.restore_session(eng,con,man,model_path=MODEL)
 except Exception as e: err=type(e).__name__+': '+str(e)
 return {'before':before,'after':{'seq0':[eng.n_tokens(0),eng.pos_max(0)],'seq1':[eng.n_tokens(1),eng.pos_max(1)]},
         'reset_calls':eng.reset_calls,'target_resets':eng.target_resets,'load_calls':eng.load_calls,
         'load_strict_calls':eng.load_strict_calls,'error':err,'report':rep}

def run_case(which):
 eng=FakeEng(fail_chat=(which in ('R1','G1')),fail_block=(which=='R2'))
 if which=='R1':return restore(old_ss,eng,MAN)
 if which=='R2':return restore(old_ss,eng,clone_manifest(no_chat=True),block_ok=False)
 if which=='G1':return restore(new_ss,eng,MAN)
 if which=='G2':return restore(new_ss,eng,clone_manifest(no_chat=True),block_ok=False)
 if which=='baseline':return restore(old_ss,eng,MAN)
 if which=='green':return restore(new_ss,eng,MAN)

def run_mount(which,site):
 eng=FakeEng()
 ms.block_rows=lambda con:[ROW,ROW]
 def li(e,row,seq,model_path=MODEL,kv_type='q8_0'):
  raise RuntimeError('fake mount load refused (non-Incompatible)')
 ms.load_into=li
 before=[eng.n_tokens(1),eng.pos_max(1)]
 err=None
 try:
  if site=='P3':
   mod=old_chat if which=='red' else new_chat
   mod.KVEngine=lambda *a,**k:eng
   mod.ms.connect=lambda db:types.SimpleNamespace(close=lambda:None)
   mod.ms.block_rows=lambda con:[ROW,ROW]
   mod.cmd_chat()
  elif site=='P4':
   mod=old_chat if which=='red' else new_chat
   mod._place_slots(eng,[ROW,ROW])
  elif site=='P5':
   mod=old_chat if which=='red' else new_chat
   mod.KVEngine=lambda *a,**k:eng
   mod.ms.connect=lambda db:types.SimpleNamespace(close=lambda:None)
   mod.ms.block_rows=lambda con:[ROW]
   mod._selection=lambda con,q:[{'name':'profile','score':1.0,'signals':{},'source_id':1}]
   mod.E.decide=lambda q,sel,h:{'state':'grounded','intent':'test','refuse':False,'reason':'test','reply':'','chars_injected':0,'policy_version':1}
   mod.E.BADGE={'grounded':'[test]'}
   fakeR=types.SimpleNamespace(INDEX_VERSION=1,build_index=lambda con,verbose=True:None)
   sys.modules['retrieval']=fakeR
   mod.cmd_m1()
 except Exception as e: err=type(e).__name__+': '+str(e)
 return {'site':site,'before':before,'after':[eng.n_tokens(1),eng.pos_max(1)],'reset_calls':eng.reset_calls,
         'target_resets':eng.target_resets,'error':err}

def main():
 out={'schema':'m6b_b1_unit_v1','at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
      'scope':'无 GPU 单元级；fake engine 哨兵 7/6；不改产品码（红臂用备份件）',
      'prereg':{'path':'docs/_work/PREREG-M6B-B1.md','sha16':'73779a220ab0aff5','bytes':7762},
      'backup':info(B/'session_state.py'),'new_files':{'session_state':info(TOOLS/'session_state.py'),'chat':info(TOOLS/'chat.py'),'kvslots':info(TOOLS/'kvslots.py')},
      'red':{},'green':{},'mount':{}}
 for k in ('R1','R2'):
  out['red'][k]=run_case(k)
 out['baseline']=run_case('baseline')
 out['green']['restore']=run_case('green')
 out['green']['G1']=run_case('G1')
 out['green']['G2']=run_case('G2')
 for site in ('P3','P4','P5'):
  out['mount'][site]={'red':run_mount('red',site),'green':run_mount('green',site)}
 # zero behavior compare fields
 b=out['baseline']['report'];g=out['green']['restore']['report']
 fields=['shifts','rebuilt','blocks','layout_problems','chat_end','chat_n_tokens','anchor','chat_bytes_verified','unvalidated_chat_bytes']
 out['zero']={'fields':{f:{'before':b.get(f) if b else None,'after':g.get(f) if g else None,'equal':(b or {}).get(f)==(g or {}).get(f)} for f in fields},
              'reset_calls':{'before':out['baseline']['reset_calls'],'after':out['green']['restore']['reset_calls']},
              'error':{'before':out['baseline']['error'],'after':out['green']['restore']['error']}}
 out['verdict']={'red_R1':out['red']['R1']['reset_calls']>=1 and out['red']['R1']['after']['seq0']==[0,-1],
                 'red_R2':out['red']['R2']['reset_calls']>=1 and out['red']['R2']['after']['seq1']==[0,-1],
                 'green_R1':out['green']['G1']['error'] is not None and out['green']['G1']['reset_calls']==0 and out['green']['G1']['after']['seq0']==[7,6],
                 'green_R2':out['green']['G2']['error'] is not None and out['green']['G2']['reset_calls']==0 and out['green']['G2']['after']['seq1']==[7,6],
                 'zero_equal':all(v['equal'] for v in out['zero']['fields'].values()),
                 'note':'C++ kvshim.cpp:589-592 未修，B1 总体仍 未接上（受不重建 DLL 限制）'}
 p=OUT/'M6B-B1-FIX.json';tmp=str(p)+'.tmp';json.dump(out,open(tmp,'w',encoding='utf-8',newline='\n'),ensure_ascii=False,indent=1);os.replace(tmp,p)
 print(json.dumps({'red':{k:{'reset':v['reset_calls'],'after':v['after'],'error':v['error']} for k,v in out['red'].items()},
                   'green_restore':{'error':out['green']['restore']['error'],'reset':out['green']['restore']['reset_calls'],'after':out['green']['restore']['after']},
                   'baseline':{'error':out['baseline']['error'],'report':out['baseline']['report']},
                   'mount':{s:{w:{'reset':v['reset_calls'],'after':v['after'],'error':v['error']} for w,v in out['mount'][s].items()} for s in out['mount']},
                   'zero':out['zero'],'artifact':info(p)},ensure_ascii=False,indent=1))
if __name__=='__main__':main()
