#!/bin/bash
set -o pipefail
cd /d/llama-mem || exit 9
W=/c/Users/lezige/Documents/deepseek-harness/default-workspace/t030
echo "=== 重建 #1（含新导出） ==="
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\llama-mem\tools\build_tools.ps1' -Gpu -Dll -Only kvshim 2>&1 | tail -4
cp -f tools/kvshim_vk.dll $W/kvshim_vk_topk_b1.dll
echo "=== 重建 #2（确定性） ==="
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\llama-mem\tools\build_tools.ps1' -Gpu -Dll -Only kvshim 2>&1 | tail -4
cp -f tools/kvshim_vk.dll $W/kvshim_vk_topk_b2.dll
echo "=== 归一化比对（两次构建 vs 旧基线） ==="
python -X utf8 $W/norm_dll.py tools/kvshim_vk.dll $W/kvshim_vk_topk_b1.dll $W/kvshim_vk_topk_b2.dll $W/kvshim_vk.baseline.dll 2>&1 | grep -E "sha16|NORMALIZED"
echo "=== 新导出在不在 ==="
python -X utf8 -c "import ctypes;l=ctypes.WinDLL(r'D:/llama-mem/tools/kvshim_vk.dll');print('  kvshim_ask_at_topk:',hasattr(l,'kvshim_ask_at_topk'));print('  kvshim_ask_at:',hasattr(l,'kvshim_ask_at'))"
echo T030_TOPK_BUILD_DONE