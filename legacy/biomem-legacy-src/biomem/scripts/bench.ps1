param(
    [string]$Model = "D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
    [string]$LlamaDir = "D:\llama-vulkan",
    [int]$Ctx = 8192,
    [int]$Rounds = 2
)

# Stage 0 baseline: Vulkan prefill/decode speed and memory footprint.
$ErrorActionPreference = "Stop"
$bench = Join-Path $LlamaDir "llama-bench.exe"
if (-not (Test-Path $bench)) { throw "llama-bench.exe not found: $bench" }
if (-not (Test-Path $Model)) { throw "model not found: $Model" }

Write-Host "== model =="
Get-Item $Model | Select-Object Name, @{n = "GB"; e = { [math]::Round($_.Length / 1GB, 2) } } | Format-Table -AutoSize

$sw = [Diagnostics.Stopwatch]::StartNew()
& $bench -m $Model -ngl 99 -fa on -p 512 -n 128 -r $Rounds
$sw.Stop()

Write-Host ("total {0:N1}s" -f $sw.Elapsed.TotalSeconds)
Write-Host "== process memory (if server is running) =="
Get-Process llama-server -ErrorAction SilentlyContinue |
    Select-Object Id, @{n = "WorkingSetGB"; e = { [math]::Round($_.WorkingSet64 / 1GB, 2) } },
                  @{n = "PrivateGB"; e = { [math]::Round($_.PrivateMemorySize64 / 1GB, 2) } } |
    Format-Table -AutoSize