# llama-mem per-user installer (portable copy + shortcuts)
# Run: powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $here "..\release\llama-mem-win32-x64"
if (!(Test-Path (Join-Path $src "llama-mem.exe"))) {
  throw "portable build missing: $src\llama-mem.exe (run build-portable.ps1 first)"
}
$dst = Join-Path $env:LOCALAPPDATA "Programs\llama-mem"
Get-Process "llama-mem" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 800
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
New-Item -ItemType Directory -Path $dst -Force | Out-Null
Copy-Item -Recurse -Force (Join-Path $src "*") $dst
$exe = Join-Path $dst "llama-mem.exe"

$ws = New-Object -ComObject WScript.Shell
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\llama-mem.lnk"
$desktop = Join-Path ([Environment]::GetFolderPath("Desktop")) "llama-mem.lnk"
foreach ($lnk in @($startMenu, $desktop)) {
  $s = $ws.CreateShortcut($lnk)
  $s.TargetPath = $exe
  $s.WorkingDirectory = $dst
  $s.IconLocation = $exe
  $s.Description = "llama-mem local memory"
  $s.Save()
}
# Windows Explorer context menu: "存入 llama-mem 记忆" on files
$root = "D:\llama-mem"
$py = "C:\Users\lezige\AppData\Local\Programs\Python\Python314\pythonw.exe"
$helper = Join-Path $root "tools\remember_file.py"
if ((Test-Path $py) -and (Test-Path $helper)) {
  $base = "HKCU:\Software\Classes\*\shell\llama-mem"
  Remove-Item -Recurse -Force $base -ErrorAction SilentlyContinue
  New-Item -Path $base -Force | Out-Null
  Set-ItemProperty -Path $base -Name "(default)" -Value "存入 llama-mem 记忆"
  New-Item -Path (Join-Path $base "command") -Force | Out-Null
  $cmd = '"' + $py + '" "' + $helper + '" "%1"'
  Set-ItemProperty -Path (Join-Path $base "command") -Name "(default)" -Value $cmd
  Write-Host "context menu: installed"
} else {
  Write-Warning "context menu skipped: pythonw/helper missing"
}

Write-Host "installed: $dst"
Write-Host "shortcuts: $startMenu ; $desktop"
Start-Process -FilePath $exe -WorkingDirectory $dst