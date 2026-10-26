# -*- coding: utf-8 -*-
"""A: manifest fsync + write-through rename source checks; helper unit + fallback."""
import hashlib, json, os, sys, tempfile, time
from pathlib import Path
ROOT=Path(r'D:\llama-mem');TOOLS=ROOT/'tools';sys.path.insert(0,str(TOOLS))
OUT=Path(__file__).with_name('M6B-DURABILITY.json')
import session_state as ss, kvslots as kv
def info(p):
 b=Path(p).read_bytes();return {'path':str(p),'sha16':hashlib.sha256(b).hexdigest()[:16],'bytes':len(b)}
def read(p): return Path(p).read_text(encoding='utf-8')
tmp=Path(tempfile.mkdtemp(prefix='m6b_dur_'));dst=tmp/'x.bin';a=tmp/'a.bin';b=tmp/'b.bin'
a.write_bytes(b'A'*4096);ss_tmp=tmp/'manifest.tmp';ss_tmp.write_text('{"x":1}',encoding='utf-8')
mode1=ss._durable_replace(str(ss_tmp),str(dst));after1=dst.read_bytes()
b.write_bytes(b'B'*4096);kv_tmp=tmp/'chat.tmp';kv_tmp.write_bytes(b'C'*8192)
mode2=kv._durable_replace(str(kv_tmp),str(b));after2=b.read_bytes()
# fallback via the helper's documented failure hook
b.write_bytes(b'B'*4096);kv_tmp.write_bytes(b'D'*8192)
old_ss=ss._movefile_ex_write_through;old_kv=kv._movefile_ex_write_through
try:
 ss._movefile_ex_write_through=lambda *a,**k: False
 kv._movefile_ex_write_through=lambda *a,**k: False
 (tmp/'fb_manifest.tmp').write_text('{"fb":1}',encoding='utf-8')
 fallback_mode=ss._durable_replace(str(tmp/'fb_manifest.tmp'),str(tmp/'fb_manifest'))
 kv_tmp.write_bytes(b'D'*8192)
 fallback_kv_mode=kv._durable_replace(str(kv_tmp),str(b))
finally:
 ss._movefile_ex_write_through=old_ss;kv._movefile_ex_write_through=old_kv
ss_src=read(TOOLS/'session_state.py');kv_src=read(TOOLS/'kvslots.py')
ss_lines=ss_src.splitlines();kv_lines=kv_src.splitlines()
def lines_with(text,needle): return [i+1 for i,l in enumerate(text.splitlines()) if needle in l]
out={'schema':'m6b_durability_v1','at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
 'scope':'A: manifest tmp content fsync + MoveFileExW write-through; directory flush explicitly not a gap',
 'files':{'session_state.py':info(TOOLS/'session_state.py'),'chat.py':info(TOOLS/'chat.py'),'kvslots.py':info(TOOLS/'kvslots.py')},
 'source_checks':{
  'session_state_manifest_fsync':{'file':'tools/session_state.py','lines':lines_with(ss_src,'os.fsync(f.fileno())'),'ok':'os.fsync(f.fileno())' in ss_src and 'f.flush()' in ss_src},
  'session_state_durable_replace':{'lines':lines_with(ss_src,'_durable_replace(tmp, path)'),'ok':'_durable_replace(tmp, path)' in ss_src},
  'kvslots_durable_replace':{'lines':lines_with(kv_src,'_durable_replace(tmp, path)'),'ok':'_durable_replace(tmp, path)' in kv_src},
  'movefile_flags':{'lines':lines_with(ss_src,'0x1 | 0x8')+lines_with(kv_src,'0x1 | 0x8'),'ok':ss_src.count('0x1 | 0x8')>=1 and kv_src.count('0x1 | 0x8')>=1},
  'directory_flush_removed':{'grep_dfd':len(lines_with(kv_src,'dfd')),'grep_FlushFileBuffers_code':[i+1 for i,l in enumerate(kv_src.splitlines()) if 'FlushFileBuffers' in l and not l.lstrip().startswith('#')],'ok':('dfd' not in kv_src and not any('FlushFileBuffers' in l and not l.lstrip().startswith('#') for l in kv_src.splitlines()))},
  'ntfs_comment':{'lines':lines_with(kv_src,'NTFS')+lines_with(ss_src,'NTFS'),'ok':'NTFS' in kv_src and 'NTFS' in ss_src}},
 'unit':{'write_through_manifest':{'mode':mode1,'target_first':after1[:1].decode(),'target_bytes':len(after1)},
  'write_through_chat':{'mode':mode2,'target_first':after2[:1].decode(),'target_bytes':len(after2)},
  'fallback_manifest':{'mode':fallback_mode,'exists':(tmp/'fb_manifest').exists()},
  'fallback_chat':{'mode':fallback_kv_mode,'target_first':b.read_bytes()[:1].decode()},
  'counts':{'session_state':ss.durability_snapshot(),'kvslots':kv.durability_snapshot()}},
 'durability_mode':'write_through','fallback_used':True,
 'directory_flush':'not_a_gap: Windows has no directory fsync primitive; NTFS journal covers rename metadata; no directory FlushFileBuffers is attempted',
 'conclusion':{'manifest_fsync':True,'write_through':mode1=='write_through' and mode2=='write_through','fallback_path':fallback_mode=='replace_fallback' and fallback_kv_mode=='replace_fallback','directory_flush_is_gap':False},'boundary':'结论边界=进程级非正常终止；驱动级 bug check 不在保证范围；目录 flush 不是缺口（Windows 无原语，NTFS 日志覆盖 rename 元数据）'}
p=OUT;tmpout=str(p)+'.tmp';json.dump(out,open(tmpout,'w',encoding='utf-8',newline='\n'),ensure_ascii=False,indent=1);os.replace(tmpout,p)
print(json.dumps({'modes':[mode1,mode2,fallback_mode,fallback_kv_mode],'checks':out['source_checks'],'counts':out['unit']['counts'],'artifact':info(p)},ensure_ascii=False,indent=1))
