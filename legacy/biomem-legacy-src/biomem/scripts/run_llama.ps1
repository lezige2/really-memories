param(
    [string]$Model = "D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
    [string]$LlamaDir = "D:\llama-vulkan",
    [int]$Port = 8080,
    [int]$Ctx = 8192,
    [int]$NGpuLayers = 99,
    [ValidateSet("f16", "q8_0", "q4_0")]
    [string]$CacheType = "q8_0",
    [switch]$Stop,
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$pidFile = Join-Path $logDir "server.pid"

function Stop-BiomemServer {
    if (Test-Path $pidFile) {
        $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($oldPid) {
            Get-Process -Id $oldPid -ErrorAction SilentlyContinue | Stop-Process -Force
            Write-Host "stopped old server pid=$oldPid"
        }
        Remove-Item $pidFile -ErrorAction SilentlyContinue
    }
}

if ($Stop) { Stop-BiomemServer; exit 0 }

$exe = Join-Path $LlamaDir "llama-server.exe"
if (-not (Test-Path $exe)) { throw "llama-server.exe not found: $exe" }
if (-not (Test-Path $Model)) { throw "model not found: $Model" }

Stop-BiomemServer

$serverArgs = @(
    "-m", $Model,
    "-ngl", "$NGpuLayers",
    "-c", "$Ctx",
    "--host", "127.0.0.1",
    "--port", "$Port",
    "-fa", "on",
    "--cache-type-k", $CacheType,
    "--cache-type-v", $CacheType,
    "--no-webui",
    "--parallel", "1"
)

Write-Host "starting llama-server (Vulkan)"
Write-Host "  model: $Model"
Write-Host "  port: $Port  ctx: $Ctx  ngl: $NGpuLayers  kv: $CacheType"

if ($Foreground) {
    & $exe @serverArgs
    exit $LASTEXITCODE
}

$proc = Start-Process -FilePath $exe -ArgumentList $serverArgs `
    -RedirectStandardOutput (Join-Path $logDir "server.out.log") `
    -RedirectStandardError (Join-Path $logDir "server.err.log") `
    -PassThru -WindowStyle Hidden
$proc.Id | Set-Content $pidFile
Write-Host "  pid=$($proc.Id), logs in $logDir"

for ($i = 0; $i -lt 150; $i++) {
    Start-Sleep -Seconds 2
    if ($proc.HasExited) {
        Write-Host "server exited, last log lines:" -ForegroundColor Red
        Get-Content (Join-Path $logDir "server.err.log") -Tail 30
        exit 1
    }
    try {
        $r = Invoke-RestMethod "http://127.0.0.1:$Port/v1/models" -TimeoutSec 3
        Write-Host "ready: $($r.data[0].id)" -ForegroundColor Green
        exit 0
    } catch {
        # still loading
    }
}

Write-Host "timeout waiting for server, see $logDir\server.err.log" -ForegroundColor Yellow
exit 1