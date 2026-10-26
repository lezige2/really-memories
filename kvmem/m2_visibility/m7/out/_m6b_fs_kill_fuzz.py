# -*- coding: utf-8 -*-
"""Random-timing file-level SIGKILL fuzz (parent sends the kill; no GPU).
Atomic arm: temp + fsync + MoveFileExW(REPLACE_EXISTING|WRITE_THROUGH).
Red arm: direct open(target,'wb') chunk writes.
"""
import ctypes, hashlib, json, os, random, statistics, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(r'D:\llama-mem');OUT=ROOT/'kvmem/m2_visibility/m7/out';ART=OUT/'M6B-FS-KILL-FUZZ.json'
PAYLOAD=(b'AFTER!'*1365+b'A'*40)  # 8192+? keep exact 8192*1024 via build below
PAYLOAD=(b'A'*64)*131072           # 8,388,608 B
BEFORE=(b'B'*64)*131072
CHUNK=65536
SLEEP=0.006
def sha16b(b): return hashlib.sha256(b).hexdigest()[:16]
def state_of(target, before_sha, after_sha):
    if not target.exists(): return 'missing'
    b=target.read_bytes(); s=sha16b(b)
    if s==after_sha and len(b)==len(PAYLOAD): return 'after'
    if s==before_sha and len(b)==len(BEFORE): return 'before'
    return 'third'
def move_through(tmp,dst):
    fn=ctypes.windll.kernel32.MoveFileExW
    fn.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint];fn.restype=ctypes.c_int
    if not fn(str(tmp),str(dst),0x1|0x8): os.replace(tmp,dst)
def child(arm,target,progress,done):
    target=Path(target); progress=Path(progress); done=Path(done)
    if arm=='atomic':
        tmp=target.with_suffix(target.suffix+'.tmp')
        with open(tmp,'wb') as f:
            for i in range(0,len(PAYLOAD),CHUNK):
                f.write(PAYLOAD[i:i+CHUNK]); f.flush()
                progress.write_text('%.6f'%((i+CHUNK)/len(PAYLOAD)),encoding='ascii')
                time.sleep(SLEEP)
            os.fsync(f.fileno())
        move_through(tmp,target)
        progress.write_text('1.000000',encoding='ascii')
        time.sleep(0.40)          # window where target is already `after` but child is alive
    else:
        with open(target,'wb') as f:
            for i in range(0,len(PAYLOAD),CHUNK):
                f.write(PAYLOAD[i:i+CHUNK]); f.flush()
                progress.write_text('%.6f'%((i+CHUNK)/len(PAYLOAD)),encoding='ascii')
                time.sleep(SLEEP)
    progress.write_text('1.000000',encoding='ascii');done.write_text('1',encoding='ascii')
def run_one(run,arm,delay,root):
    target=root/('t_%s_%02d.bin'%(arm,run)); prog=root/('p_%s_%02d.txt'%(arm,run)); done=root/('d_%s_%02d.txt'%(arm,run))
    for p in (target,prog,done):
        try:p.unlink()
        except FileNotFoundError:pass
    target.write_bytes(BEFORE)
    before_sha=sha16b(BEFORE);after_sha=sha16b(PAYLOAD)
    t0=time.perf_counter()
    proc=subprocess.Popen([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'child',arm,str(target),str(prog),str(done)],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(delay)
    signalled=proc.poll() is None
    if signalled: proc.kill()
    rc=proc.wait(timeout=30)
    elapsed=time.perf_counter()-t0
    try: frac=float(prog.read_text(encoding='ascii').strip())
    except Exception: frac=0.0
    st=state_of(target,before_sha,after_sha)
    out={'run':run,'arm':arm,'delay_s':round(delay,4),'fraction_at_kill':round(frac,6),'elapsed_s':round(elapsed,4),
         'signal_sent':signalled,'returncode':rc,'target_state':st,'target_bytes':target.stat().st_size if target.exists() else None,
         'target_sha16':sha16b(target.read_bytes()) if target.exists() else None}
    for p in (target,prog,done):
        try:p.unlink()
        except FileNotFoundError:pass
    tmp=target.with_suffix(target.suffix+'.tmp')
    try:tmp.unlink()
    except FileNotFoundError:pass
    return out
def parent():
    root=Path(tempfile.mkdtemp(prefix='m6b_fuzz_'));random.seed(20261026)
    allruns=[]
    for arm in ('atomic','red'):
        for i in range(1,21):
            # uniform in the measured write window; child writes ~0.78s
            delay=random.uniform(0.05,1.15 if arm=='atomic' else 0.72)
            allruns.append(run_one(i,arm,delay,root))
    summary={}
    for arm in ('atomic','red'):
        rows=[r for r in allruns if r['arm']==arm];fr=sorted(r['fraction_at_kill'] for r in rows)
        summary[arm]={'runs':len(rows),'third':sum(r['target_state']=='third' for r in rows),
                      'before':sum(r['target_state']=='before' for r in rows),'after':sum(r['target_state']=='after' for r in rows),
                      'missing':sum(r['target_state']=='missing' for r in rows),'signal_sent':sum(r['signal_sent'] for r in rows),
                      'fraction_min':fr[0],'fraction_median':statistics.median(fr),'fraction_max':fr[-1],
                      'states':[{'run':r['run'],'fraction_at_kill':r['fraction_at_kill'],'delay_s':r['delay_s'],'state':r['target_state'],'bytes':r['target_bytes'],'sha16':r['target_sha16'],'signal_sent':r['signal_sent'],'rc':r['returncode']} for r in rows]}
    out={'schema':'m6b_fs_kill_fuzz_v1','at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
         'policy':'父进程对纯文件子进程发 SIGKILL（Windows Popen.kill/TerminateProcess）；无 GPU；结论边界=进程级非正常终止，驱动级 bug check 不在保证范围',
         'payload_bytes':len(PAYLOAD),'before_bytes':len(BEFORE),'chunk_bytes':CHUNK,'child_sleep_s':SLEEP,
         'seed':20261026,'random_window_s':{'atomic':[0.05,1.15],'red':[0.05,0.72]},'runs':allruns,'summary':summary,
         'verdict':{'atomic_third':summary['atomic']['third'],'red_third':summary['red']['third'],
                    'atomic_target_only_before_or_after':summary['atomic']['third']==0,
                    'red_hit_truncation':summary['red']['third']>=1,
                    'all_signals_real':all(r['signal_sent'] for r in allruns),
                    'atomic_pass':summary['atomic']['third']==0,
                    'red_pass_as_window_proof':summary['red']['third']>=1}}
    tmp=str(ART)+'.tmp';json.dump(out,open(tmp,'w',encoding='utf-8',newline='\n'),ensure_ascii=False,indent=1);os.replace(tmp,ART)
    print(json.dumps({'summary':summary,'verdict':out['verdict'],'artifact':{'path':str(ART),'sha16':hashlib.sha256(ART.read_bytes()).hexdigest()[:16],'bytes':ART.stat().st_size}},ensure_ascii=False,indent=1))
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='child': child(*sys.argv[2:])
    else: parent()
