$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dist = Join-Path $root "node_modules\electron\dist"
$out = Join-Path $root "release\llama-mem-win32-x64"
if (!(Test-Path (Join-Path $dist "electron.exe"))) { throw "electron runtime missing; run pnpm install" }
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Path $out -Force | Out-Null
Copy-Item -Recurse -Force (Join-Path $dist "*") $out
Move-Item (Join-Path $out "electron.exe") (Join-Path $out "llama-mem.exe")
$def = Join-Path $out "resources\default_app.asar"
if (Test-Path $def) { Remove-Item -Force $def }
$app = Join-Path $out "resources\app"
New-Item -ItemType Directory -Path $app -Force | Out-Null
Copy-Item -Recurse -Force (Join-Path $root "electron") $app
Copy-Item -Recurse -Force (Join-Path $root "dist") $app
Copy-Item -Force (Join-Path $root "package.json") $app
Write-Host "portable: $out\llama-mem.exe"