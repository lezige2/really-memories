# -*- coding: utf-8 -*-
"""M5 36A model arm: 30 original sentences -> 14B@Vulkan 36 layers rewrite.
One greedy call per sentence; no retry; no JUDGE/ADJ. Sampler only; no signals.
"""
import ctypes, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path
M5=Path(r'D:\llama-mem\kvmem\m2_visibility\m5'); OUT=M5/'out'
M7=Path(r'D:\llama-mem\kvmem\m2_visibility\m7'); sys.path.insert(0,str(M7/'out'))
import _e3gpu_run as E
STOP=OUT/'_m5_model_stop.flag'; PEAK=OUT/'_m5_model_peak.txt'; LOG=OUT/'_m5_model_llama.log'
SAMPLER=M7/'out'/'_e3gpu_sampler.ps1'; PREREG=Path(r'D:\llama-mem\docs\_work\PREREG-M5-PROBE.md')
RULE=OUT/'M5-36A-pairs.json'; RULE_SEALED=OUT/'M5-36A-intent-sealed.json'
PROMPT='请把下面这句话改写为同义句：只改措辞，保留全部事实、数字和专有名词，不增加也不删除任何事实，不要解释。\n原句：{orig}\n改写：'
NPRED=64
def sha16(p):
 b=Path(p).read_bytes(); return hashlib.sha256(b).hexdigest()[:16]
def info(p):
 b=Path(p).read_bytes(); return {'path':str(p),'sha16':hashlib.sha256(b).hexdigest()[:16],'bytes':len(b)}
for x in (STOP,PEAK,LOG):
 try:x.unlink()
 except FileNotFoundError:pass
host_before=E.host_check('before_m5_model')
g=E.gate_values()
g['prereg_sha16']=sha16(PREREG); g['prereg_ok']=g['prereg_sha16']=='04d7b8d644e69620'
g['dll_sha16']=E.sha16(E.VK); g['dll_ok']=g['dll_sha16']=='9edbafa150700614' and E.sz(E.VK)==50007552
g['model_ok']=E.sz(E.MODEL)==8988110240
g['free_ram_ok']=(g.get('free_ram_kb') or 0)>=8388608
g['vram_baseline_ok']=g.get('vram_baseline_gib') is not None and g['vram_baseline_gib']<=0.6
g['pnp_ok']=g.get('pnp_rndis_usb_audio')==0
g['gpu_procs_ok']=g.get('gpu_procs_gt256mb')==0
g['browsers_ok']=g.get('browser_or_code_procs')==0
gate_ok=all(g[k] for k in ('prereg_ok','dll_ok','model_ok','free_ram_ok','vram_baseline_ok','pnp_ok','gpu_procs_ok','browsers_ok'))
sampler=subprocess.Popen(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(SAMPLER),'-Flag',str(STOP),'-Out',str(PEAK)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
time.sleep(0.2); os.environ['M7_E3GPU_LOG']=str(LOG)
res={'gate':g,'gate_ok':gate_ok}
if not gate_ok:
 res['status']='未接上（装置不合格：开工硬闸）'; eng=None
else:
 t0=time.perf_counter()
 try:
  eng=E.open_engine()
  # kvshim_ask argtypes are not set by open_engine()
  L=eng.lib
  L.kvshim_ask.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_int]
  L.kvshim_ask.restype=ctypes.c_int
  res['load_s']=round(time.perf_counter()-t0,2)
  txt=LOG.read_text(encoding='utf-8',errors='replace') if LOG.exists() else ''
  m=re.search(r'offloaded (\d+)/(\d+) layers to GPU',txt)
  res.update(vulkan_imported=bool(ctypes.windll.kernel32.GetModuleHandleW('vulkan-1.dll')),
             n_gpu_layers_readback=int(m.group(1)) if m else None,
             n_gpu_layers_readback_total=int(m.group(2)) if m else None,
             offloaded_log_line=m.group(0) if m else None,
             n_ctx=E.NCTX,n_seq=E.NSEQ,kv=E.KV,chat_start=E.CHAT_START,
             engine_opened=True,model_calls=30,model_loaded=True)
  rule=json.load(open(RULE,encoding='utf-8'))
  outs=[]; accepted=[]; excluded=[]
  tgen=time.perf_counter()
  for p in rule['pairs']:
   pid=p['pair_id']; orig=p['orig']
   prompt=PROMPT.format(orig=orig)
   t=time.perf_counter()
   eng.reset(0)
   raw=eng.ask(0,prompt,n_predict=NPRED,pos=None)
   dt=round(time.perf_counter()-t,3)
   # fixed normalisation, no regeneration
   s=raw.strip()
   s=re.sub(r'^改写[：:]\s*','',s)
   s=re.sub(r'^["“”\'\s]+|["“”\'\s]+$','',s)
   reason=None
   if not s: reason='empty'
   elif len(s)<2: reason='too_short'
   elif s==orig.strip(): reason='verbatim_copy'
   elif len(s)>256: reason='too_long'
   elif any(x in s for x in ('无法','抱歉','作为AI','不能','原文','原句','改写要求','这句话的意思是','解释')):
    reason='meta_or_refusal'
   elif s.startswith('问：') or s.startswith('答：'): reason='qa_wrapper'
   rec={'pair_id':pid,'orig':orig,'raw':raw,'normalized':s,'seconds':dt,'reason':reason}
   outs.append(rec)
   if reason is None:
    accepted.append({'pair_id':pid,'orig':orig,'rewrite':s,'dim':'模型同义改写'})
   else:
    excluded.append({'pair_id':pid,'orig':orig,'raw':raw,'reason':reason})
  res['generation_s']=round(time.perf_counter()-tgen,2)
  res['accepted_count']=len(accepted); res['excluded_count']=len(excluded)
  res['excluded']=excluded; res['outputs']=outs
  eng.close() if hasattr(eng,'close') else None
  res['status']='装置自证可用；模型臂已生成' if (res['vulkan_imported'] and res['n_gpu_layers_readback']==36 and m) else '未接上（装置不合格：readback/日志）'
 except Exception as e:  # noqa: BLE001
  res['error']=type(e).__name__+': '+str(e); res['status']='未接上（装置不合格：生成失败）'
  accepted=[]; excluded=[]
STOP.write_text('model_done',encoding='utf-8')
try: sampler.communicate(timeout=30)
except subprocess.TimeoutExpired: pass
peak=float(PEAK.read_text().strip()) if PEAK.exists() else None
host_after=E.host_check('after_m5_model'); hs=E.derive_host_state(host_before,host_after)
if 'accepted' in locals():
  doc={'schema':'m5_36a_pairs_model_v1','arm':'model','role':'CAND',
       'scope':'CAND 模型臂候选冻结；不含意图标签；JUDGE 只看文本',
       'prereg':{'path':str(PREREG),'sha16':sha16(PREREG),'bytes':PREREG.stat().st_size},
       'source_pairs':info(RULE),'source_sealed':info(RULE_SEALED),
       'producer':{'method':'14B@Vulkan 36 layers greedy rewrite, one call per orig',
                   'prompt_template':PROMPT,'n_predict':NPRED,'temperature':0,
                   'temperature_note':'kvshim generate() is argmax/greedy; no temperature parameter',
                   'model_calls':30,'no_retry':True},
       'count_calls':30,'count_accepted':len(accepted),'count_excluded':len(excluded),
       'excluded':excluded,'raw_outputs':res.get('outputs',[]),'pairs':accepted}
  p=OUT/'M5-36A-pairs-model.json';tmp=str(p)+'.tmp';json.dump(doc,open(tmp,'w',encoding='utf-8',newline='\n'),ensure_ascii=False,indent=1);os.replace(tmp,p)
  psha=sha16(p); pbytes=os.path.getsize(p)
  sealed=json.load(open(RULE_SEALED,encoding='utf-8'))
  keep={x['pair_id'] for x in accepted}
  lab=[x for x in sealed['labels'] if x['pair_id'] in keep]
  sdoc={'schema':'m5_36a_intent_sealed_model_v1','arm':'model','pairs_path':str(p),
        'pairs_sha16':psha,'pairs_bytes':pbytes,'sealed_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'seal_rule':'候选冻结后封存；JUDGE/ADJ 在候选冻结前不得读取。',
        'intent_definition':sealed['intent_definition'],'count':len(lab),'labels':lab}
  sp=OUT/'M5-36A-intent-sealed-model.json';tmp=str(sp)+'.tmp';json.dump(sdoc,open(tmp,'w',encoding='utf-8',newline='\n'),ensure_ascii=False,indent=1);os.replace(tmp,sp)
  pilot={'schema':'m5_36a_pilot_model_v1','arm':'model','role':'CAND','at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
         'scope':'CAND 模型臂装置自证/冻结；JUDGE/ADJ 未接，不出 M5 质量判决',
         'prereg':{'path':str(PREREG),'sha16':sha16(PREREG),'bytes':PREREG.stat().st_size},
         'device':{k:res.get(k) for k in ('vulkan_imported','n_gpu_layers_readback','n_gpu_layers_readback_total','offloaded_log_line','load_s','n_ctx','n_seq','kv','chat_start','model_calls','engine_opened','generation_s')},
         'device_proof':{'model':E.MODEL,'model_bytes':E.sz(E.MODEL),'dll':E.VK,'dll_sha16':E.sha16(E.VK),'dll_bytes':E.sz(E.VK),'n_gpu_layers':E.NGL,'log_path':str(LOG),'log_sha16':sha16(LOG) if LOG.exists() else None,
                         'peak_gib':round(peak/(1024**3),4) if peak else None,'vram_gate_gib':8.6,'gate':g,'gate_ok':gate_ok,'host_before':host_before,'host_after':host_after,'reboot':hs},
         'artifacts':{'pairs':info(p),'intent_sealed':info(sp)},
         'judge_adj':{'status':'未接上（CAND 角色不运行 JUDGE/ADJ）','judge_sha16':'86b7c501ab9904aa'},
         'status':res.get('status'),'error':res.get('error'),
         'limitations':['模型臂输出仅候选；JUDGE/ADJ 未接','未对任何 GPU 进程发信号','未做 (c)']}
  pp=OUT/'M5-36A-pilot-model.json';tmp=str(pp)+'.tmp';json.dump(pilot,open(tmp,'w',encoding='utf-8',newline='\n'),ensure_ascii=False,indent=1);os.replace(tmp,pp)
  print('STATUS',res.get('status'),'error',res.get('error'))
  print('COUNTS',len(accepted),len(excluded),'model_calls',res.get('model_calls'))
  print('EXCLUDED',json.dumps(excluded,ensure_ascii=False))
  print('PEAK',pilot['device_proof']['peak_gib'],'READBACK',res.get('n_gpu_layers_readback'),'VULKAN',res.get('vulkan_imported'),'LINE',res.get('offloaded_log_line'))
  print('PAIRS',info(p));print('SEALED',info(sp));print('PILOT',info(pp))
