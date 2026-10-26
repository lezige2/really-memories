$ErrorActionPreference = 'Stop'
$Root = 'D:\llama-mem'
$clang = 'C:\Users\lezige\AppData\Local\Microsoft\WinGet\Packages\MartinStorsjo.LLVM-MinGW.MSVCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\llvm-mingw-20260826-msvcrt-x86_64\bin'
$cxx = Join-Path $clang 'clang++.exe'
$omp = Join-Path (Split-Path $clang -Parent) 'x86_64-w64-mingw32\lib\libomp.dll.a'
$build = Join-Path $Root 'build-vulkan'
$libs = @(
  (Join-Path $build 'src\libllama.a'),
  (Join-Path $build 'ggml\src\ggml.a'),
  (Join-Path $build 'ggml\src\ggml-cpu.a'),
  (Join-Path $build 'ggml\src\ggml-vulkan\ggml-vulkan.a'),
  (Join-Path $build 'ggml\src\ggml-base.a'),
  (Join-Path $Root 'vulkan-sdk\Lib\vulkan-1.lib')
)
$common = @('-std=c++17','-O2','-static','-D_WIN32_WINNT=0x0A00','-DWINVER=0x0A00',
  '-I',(Join-Path $Root 'llama.cpp\include'),'-I',(Join-Path $Root 'llama.cpp\ggml\include'))
$winlibs = @('-lpthread','-lkernel32','-luser32','-lgdi32','-lwinspool','-lshell32',
  '-lole32','-loleaut32','-luuid','-lcomdlg32','-ladvapi32')
& $cxx @common (Join-Path $Root 'tools\kvshim_gbnf.cpp') -o (Join-Path $Root 'tools\kvshim_gbnf_vk.dll') '-shared' @libs '-pthread' $omp @winlibs
if ($LASTEXITCODE -ne 0) { throw "compile failed: $LASTEXITCODE" }
Write-Host 'OK'
