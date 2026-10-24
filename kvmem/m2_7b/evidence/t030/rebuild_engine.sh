#!/bin/bash
cd /d/llama-mem || exit 9
echo "=== 构建树里有什么 ==="
ls build-vulkan | head -6
ls build-vulkan/src/libllama.a 2>/dev/null && echo "  archive mtime: $(date -r build-vulkan/src/libllama.a)"
echo "=== 重建引擎（这一步之前被我漏掉：ps1 只链接，不重编 .a） ==="
if [ -f build-vulkan/build.ninja ]; then
  (cd build-vulkan && cmake --build . --target llama -j 8 2>&1 | tail -5)
else
  echo "NO_NINJA"
fi
echo "=== 重链接 DLL ==="
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\llama-mem\tools\build_tools.ps1' -Gpu -Dll -Only kvshim 2>&1 | tail -3
python -X utf8 -c "import hashlib;b=open('tools/kvshim_vk.dll','rb').read();print('  dll sha16',hashlib.sha256(b).hexdigest()[:16],len(b))"
echo T030_ENGINE_REBUILD_DONE