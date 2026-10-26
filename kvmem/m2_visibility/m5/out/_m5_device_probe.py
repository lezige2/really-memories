# -*- coding: utf-8 -*-
"""M5 36A pilot device proof only: load 14B on Vulkan 36 layers, no generation.
Zero JUDGE/ADJ calls; no parent signal; sampler only.  Saves M5-36A-pilot.json.
"""
import ctypes, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path
M5=Path(r'D:\llama-mem\kvmem\m2_visibility\m5')
OUT=M5/'out'
M7=Path(r'D:\llama-mem\kvmem\m2_visibility\m7')
sys.path.insert(0,str(M7/'out'))
import _e3gpu_run as E
STOP=OUT/'_m5_stop.flag'; PEAK=OUT/'_m5_peak.txt'; LOG=OUT/'_m5_device_llama.log'
SAMPLER=M7/'out'/'_e3gpu_sampler.ps1'
PREREG=Path(r'D:\llama-mem\docs\_work\PREREG-M5-PROBE.md')
PAIRS=OUT/'M5-36A-pairs.json'; SEALED=OUT/'M5-36A-intent-sealed.json'
def sha16(p):
 h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()[:16]
def info(p):
 b=Path(p).read_bytes(); return {'path':str(p),'sha16':hashlib.sha256(b).hexdigest()[:16],'bytes':len(b)}
for x in (STOP,PEAK,LOG):
 try: x.unlink()
 except FileNotFoundError: pass
host_before=E.host_check('before_m5')
gates=E.gate_values()
gates['prereg_sha16']=sha16(PREREG); gates['prereg_ok']=gates['prereg_sha16']=='04d7b8d644e69620'
gates['dll_sha16']=E.sha16(E.VK); gates['dll_ok']=gates['dll_sha16']=='9edbafa150700614' and E.sz(E.VK)==50007552
gates['model_ok']=E.sz(E.MODEL)==8988110240
gates['free_ram_ok']=(gates.get('free_ram_kb') or 0)>=8388608
gates['vram_baseline_ok']=gates.get('vram_baseline_gib') is not None and gates['vram_baseline_gib']<=0.6
gates['pnp_ok']=gates.get('pnp_rndis_usb_audio')==0
gates['gpu_procs_ok']=gates.get('gpu_procs_gt256mb')==0
gates['browsers_ok']=gates.get('browser_or_code_procs')==0
gate_ok=all(gates[k] for k in ('prereg_ok','dll_ok','model_ok','free_ram_ok','vram_baseline_ok','pnp_ok','gpu_procs_ok','browsers_ok'))
sampler=subprocess.Popen(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(SAMPLER),'-Flag',str(STOP),'-Out',str(PEAK)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
time.sleep(0.2)
os.environ['M7_E3GPU_LOG']=str(LOG)
res={'gate':gates,'gate_ok':gate_ok}
if not gate_ok:
 res['status']='未接上（装置不合格：开工硬闸）'
else:
 t0=time.perf_counter()
 try:
  eng=E.open_engine()
  res['vulkan_imported']=bool(ctypes.windll.kernel32.GetModuleHandleW('vulkan-1.dll'))
  res['load_s']=round(time.perf_counter()-t0,2)
  txt=LOG.read_text(encoding='utf-8',errors='replace') if LOG.exists() else ''
  m=re.search(r'offloaded (\d+)/(\d+) layers to GPU',txt)
  res['offloaded_log_line']=m.group(0) if m else None
  res['n_gpu_layers_readback']=int(m.group(1)) if m else None
  res['n_gpu_layers_readback_total']=int(m.group(2)) if m else None
  res['n_ctx']=E.NCTX; res['n_seq']=E.NSEQ; res['kv']=E.KV; res['chat_start']=E.CHAT_START
  res['model_calls']=0
  res['engine_opened']=True
  eng.close() if hasattr(eng,'close') else None
  res['status']='装置自证可用' if (res['vulkan_imported'] and res['n_gpu_layers_readback']==36 and m) else '未接上（装置不合格：readback/日志）'
 except Exception as e:  # noqa: BLE001
  res['error']=type(e).__name__+': '+str(e)
  res['status']='未接上（装置不合格：load 失败）'
# stop sampler via flag only; no signal
STOP.write_text('device_probe_done',encoding='utf-8')
try: sampler.communicate(timeout=30)
except subprocess.TimeoutExpired: pass
peak=float(PEAK.read_text().strip()) if PEAK.exists() else None
host_after=E.host_check('after_m5')
hs=E.derive_host_state(host_before,host_after)
art={'schema':'m5_36a_pilot_v1','task':'M5 36A pilot (a) — CAND freeze + device self-proof only',
 'role':'CAND','at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
 'scope':'仅 CAND 候选冻结与 36 层装置自证；不运行 JUDGE/ADJ，不出 M5 质量判决',
 'prereg':{'path':str(PREREG),'sha16':sha16(PREREG),'bytes':PREREG.stat().st_size},
 'candidate':{'pairs':info(PAIRS),'intent_sealed':info(SEALED),
              'pairs_model_calls':0,
              'producer_explanation':'预登记 §2 只写“CAND 写对”，未规定模型改写；沿用旧 M5(a) 零模型口径，人工/规则改写，model_calls=0；不是模型生成。'},
 'judge_adj':{'status':'未接上（CAND 角色不运行 JUDGE/ADJ；待 inspector 冻结后盲标）',
              'judge_sha16':'86b7c501ab9904aa'},
 'device':{k:res.get(k) for k in ('vulkan_imported','n_gpu_layers_readback','n_gpu_layers_readback_total','offloaded_log_line','load_s','n_ctx','n_seq','kv','chat_start','model_calls','engine_opened')},
 'device_proof':{'model':E.MODEL,'model_bytes':E.sz(E.MODEL),'dll':E.VK,'dll_sha16':E.sha16(E.VK),'dll_bytes':E.sz(E.VK),
                 'n_gpu_layers':E.NGL,'log_path':str(LOG),'log_sha16':sha16(LOG) if LOG.exists() else None,
                 'peak_gib':round(peak/(1024**3),4) if peak else None,'vram_gate_gib':8.6,
                 'gate':gates,'gate_ok':gate_ok,'host_before':host_before,'host_after':host_after,'reboot':hs},
 'status':res.get('status'),'error':res.get('error'),
 'limitations':['只证明装置与候选冻结；JUDGE/ADJ 未接，不能算 pilot 可用性通过',
                '未做 (c)；未跑 judge；未对任何 GPU 进程发信号']}
p=OUT/'M5-36A-pilot.json';tmp=str(p)+'.tmp'
json.dump(art,open(tmp,'w',encoding='utf-8',newline='\n'),ensure_ascii=False,indent=1);os.replace(tmp,p)
print('STATUS',art['status'],'error',art['error'])
print('RESULT',json.dumps({'vulkan':art['device'].get('vulkan_imported'),'readback':art['device'].get('n_gpu_layers_readback'),'line':art['device'].get('offloaded_log_line'),'peak':art['device_proof']['peak_gib'],'pairs':art['candidate']['pairs']['sha16']},ensure_ascii=False))
print('PILOT',info(p))
