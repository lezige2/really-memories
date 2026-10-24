#!/bin/bash
set -o pipefail
cd /d/llama-mem || exit 9
W=/c/Users/lezige/Documents/deepseek-harness/default-workspace/t030
mkdir -p "$W"
echo "=== 0. 备份现盘 DLL ==="
cp -f tools/kvshim_vk.dll "$W/kvshim_vk.baseline.dll"
ls -l "$W/kvshim_vk.baseline.dll"
python -c "import hashlib;b=open(r'C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/kvshim_vk.baseline.dll','rb').read();print('  baseline sha16',hashlib.sha256(b).hexdigest()[:16],len(b))"
echo "=== 1. 重建 ==="
time powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\llama-mem\tools\build_tools.ps1' -Gpu -Dll -Only kvshim 2>&1 | tail -8
echo "=== 2. 比较 ==="
python -c "import hashlib;b=open('tools/kvshim_vk.dll','rb').read();print('  rebuilt sha16',hashlib.sha256(b).hexdigest()[:16],len(b))"
python -c "import hashlib;a=open(r'C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/kvshim_vk.baseline.dll','rb').read();b=open('tools/kvshim_vk.dll','rb').read();print('  EQUAL:',hashlib.sha256(a).hexdigest()==hashlib.sha256(b).hexdigest(),'sizes',len(a),len(b))"
echo T030_STEP0_DONE