#!/bin/bash
set -o pipefail
cd /d/llama-mem || exit 9
echo "=== 第二次重建（确定性检验） ==="
cp -f tools/kvshim_vk.dll /tmp/build1.dll
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\llama-mem\tools\build_tools.ps1' -Gpu -Dll -Only kvshim 2>&1 | tail -3
python -c "import hashlib;a=open(r'C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/kvshim_vk.baseline.dll','rb').read();b=open(r'D:/llama-mem/tools/kvshim_vk.dll','rb').read();d=[i for i in range(len(a)) if a[i]!=b[i]];print('  build2 vs baseline differing bytes:',len(d),'offsets:',d[:8])"
echo "=== 归一化哈希（把 4 个时间戳字节清零） ==="
python -X utf8 C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/norm_check.py
echo "=== 还原实验用 DLL（哈希 849e7281c74a5288） ==="
cp -f /c/Users/lezige/Documents/deepseek-harness/default-workspace/t030/kvshim_vk.baseline.dll tools/kvshim_vk.dll
python -c "import hashlib;b=open('tools/kvshim_vk.dll','rb').read();print('  restored sha16',hashlib.sha256(b).hexdigest()[:16])"
echo T030_STEP0B_DONE