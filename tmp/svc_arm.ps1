param(
  [switch]$K2,
  [Parameter(Mandatory=$true)][string]$Tag
)
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe'
$wd = 'D:\llama-mem'
$outLog = Join-Path $wd ("kvmem\daily\service_" + $Tag + ".out")
$errLog = Join-Path $wd ("kvmem\daily\service_" + $Tag + ".err")
$argList = @(
  '-X','utf8','tools\chat_service.py','--port','8765',
  '--model','D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf',
  '--db','kvmem\daily\chat.db','--blocks','kvmem\daily\blocks',
  '--sessions','kvmem\daily\sessions','--session','kvc.json',
  '--n-ctx','32768','--chat-start','8192','--n-gpu-layers','28',
  '--retrieval','topk','--topk','4'
)
if ($K2) { $argList += '--k2-family' }
$p = Start-Process -FilePath $py -ArgumentList $argList -WorkingDirectory $wd `
  -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
  -PassThru
Write-Output ("PID=" + $p.Id + " K2=" + [bool]$K2 + " tag=" + $Tag)