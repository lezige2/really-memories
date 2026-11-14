$ErrorActionPreference = "Stop"
$py = "C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe"
$root = "D:\llama-mem"
$args = @(
  "-X","utf8","tools\chat_service.py",
  "--db","kvmem\daily\chat.db",
  "--blocks","kvmem\daily\blocks",
  "--sessions","kvmem\daily\sessions",
  "--host","127.0.0.1","--port","8765",
  "--retrieval","topk","--topk","4","--n-gpu-layers","28",
  "--model","D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"
)
$out = Join-Path $root "out\p1-enable\service.out"
$err = Join-Path $root "out\p1-enable\service.err"
$p = Start-Process -FilePath $py -ArgumentList $args -WorkingDirectory $root `
  -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
$p.Id | Set-Content (Join-Path $root "out\p1-enable\service.pid")
Write-Output "pid=$($p.Id)"