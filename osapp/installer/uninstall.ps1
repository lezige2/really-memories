$ErrorActionPreference = "Stop"
$dst = Join-Path $env:LOCALAPPDATA "Programs\llama-mem"
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\llama-mem.lnk"
$desktop = Join-Path ([Environment]::GetFolderPath("Desktop")) "llama-mem.lnk"
foreach ($p in @($startMenu, $desktop)) { if (Test-Path $p) { Remove-Item -Force $p } }
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
Write-Host "uninstalled (data in D:\llama-mem\kvmem is NOT deleted)"