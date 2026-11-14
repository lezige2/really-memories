$ErrorActionPreference = 'Stop'
$env:VERIFIER_VERSION = 'v2'
$py = (Get-Command python).Source
$argList = @(
  '-X','utf8','tools\chat_service.py',
  '--port','8765',
  '--model','D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf',
  '--db','kvmem\daily\chat.db',
  '--blocks','kvmem\daily\blocks',
  '--sessions','kvmem\daily\sessions',
  '--session','nok2v2.json',
  '--n-ctx','32768',
  '--chat-start','8192',
  '--n-gpu-layers','28',
  '--retrieval','topk',
  '--topk','4'
)
$p = Start-Process -FilePath $py -ArgumentList $argList `
  -WorkingDirectory 'D:\llama-mem' `
  -RedirectStandardOutput 'D:\llama-mem\kvmem\daily\service_nok2v2.out' `
  -RedirectStandardError  'D:\llama-mem\kvmem\daily\service_nok2v2.err' `
  -WindowStyle Hidden -PassThru
"started pid=$($p.Id) k2=off verifier=v2"