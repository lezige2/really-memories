# build_tools.ps1 -- rebuild the KV memory probes against the local build trees.
#
# The handoff doc documents this link line; this script keeps it reproducible and
# ASCII-only (Windows PowerShell 5.1 chokes on non-ASCII literals in .ps1 files).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File D:\llama-mem\tools\build_tools.ps1
#   powershell -ExecutionPolicy Bypass -File D:\llama-mem\tools\build_tools.ps1 -Only kvmem_persist
#   powershell -ExecutionPolicy Bypass -File D:\llama-mem\tools\build_tools.ps1 -Gpu
#
# -Gpu links against build-vulkan and produces <name>_vk.exe.
# Verified working: llvm-mingw ld links MSVC's vulkan-1.lib directly.

param(
    [string]$Root = 'D:\llama-mem',
    [string]$Only = '',
    [switch]$Gpu,
    [switch]$Dll
)

$ErrorActionPreference = 'Stop'

$clang = 'C:\Users\lezige\AppData\Local\Microsoft\WinGet\Packages\MartinStorsjo.LLVM-MinGW.MSVCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\llvm-mingw-20260826-msvcrt-x86_64\bin'
$cxx   = Join-Path $clang 'clang++.exe'
$omp   = Join-Path (Split-Path $clang -Parent) 'x86_64-w64-mingw32\lib\libomp.dll.a'

$build = if ($Gpu) { Join-Path $Root 'build-vulkan' } else { Join-Path $Root 'build-cpu' }
$suffix = if ($Gpu) { '_vk' } else { '' }

$libs = @(
    (Join-Path $build 'src\libllama.a'),
    (Join-Path $build 'ggml\src\ggml.a'),
    (Join-Path $build 'ggml\src\ggml-cpu.a')
)
if ($Gpu) {
    $libs += (Join-Path $build 'ggml\src\ggml-vulkan\ggml-vulkan.a')
}
$libs += (Join-Path $build 'ggml\src\ggml-base.a')
if ($Gpu) {
    $libs += (Join-Path $Root 'vulkan-sdk\Lib\vulkan-1.lib')
}

foreach ($p in @($cxx, $omp) + $libs) {
    if (-not (Test-Path $p)) { throw "missing: $p" }
}

$common = @(
    '-std=c++17', '-O2', '-static',
    '-D_WIN32_WINNT=0x0A00', '-DWINVER=0x0A00',
    '-I', (Join-Path $Root 'llama.cpp\include'),
    '-I', (Join-Path $Root 'llama.cpp\ggml\include')
)

$winlibs = @(
    '-lpthread', '-lkernel32', '-luser32', '-lgdi32', '-lwinspool', '-lshell32',
    '-lole32', '-loleaut32', '-luuid', '-lcomdlg32', '-ladvapi32'
)

$targets = @('kvmem_probe', 'kvmem_persist', 'kvmem_quality', 'kvmem_page', 'kvshim')
if ($Only -ne '') { $targets = @($Only) }

foreach ($t in $targets) {
    $src = Join-Path $Root "tools\$t.cpp"
    if ($Dll) {
        # Shared object for ctypes. The llama/ggml archives are linked in statically
        # (-static), so the DLL has no runtime dependency on libstdc++/libgcc DLLs.
        $out = Join-Path $Root "tools\$t$suffix.dll"
    } else {
        $out = Join-Path $Root "tools\$t$suffix.exe"
    }
    Write-Host "== building $t$suffix$(if ($Dll) { '.dll' })"
    if ($Dll) {
        & $cxx @common $src -o $out '-shared' @libs '-pthread' $omp @winlibs
    } else {
        & $cxx @common $src -o $out @libs '-pthread' $omp @winlibs
    }
    if ($LASTEXITCODE -ne 0) { throw "compile failed: $t (exit $LASTEXITCODE)" }
    Write-Host "   ok -> $out"
}