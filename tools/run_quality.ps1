# run_quality.ps1 -- experiment "A": does a KV memory get read, and at what scale?
#
# Arms:
#   none / f16      control   -- question only, must NOT answer (catches leaked answers)
#   full / f16      baseline  -- whole document stuffed into the context
#   full / q8_0     baseline  -- same, production KV type
#   kv   / f16      memory    -- document in KV, prompt holds only the question
#   kv   / q8_0     memory    -- same, production KV type
#
# `full` and `kv` are the same token sequence at the same positions, so their answers
# should be identical; a difference means a bug. `full` exists to provide the
# denominator for the ">=90% of full context" acceptance bar.
#
# Each arm writes:
#   tools\quality\results_<prefix><arm>_<kv>.tsv   graded rows
#   tools\quality\log_<prefix><arm>_<kv>.txt       the arm's own stdout/stderr
#
# Usage:
#   powershell -File ...\run_quality.ps1 -Gpu                                   # 5k, all arms
#   powershell -File ...\run_quality.ps1 -Gpu -Tag 20k -Ctx 32768 -Configs kv_q8_0
#   powershell -File ...\run_quality.ps1 -Gpu -Tag 100k -Ctx 131072 -Configs kv_q8_0
#
# ASCII only (PowerShell 5.1 mangles non-ASCII literals in .ps1 files).

param(
    [string]$Root   = 'D:\llama-mem',
    [string]$Model  = 'D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf',
    [switch]$Gpu,
    [string]$Tag    = '5k',
    [int]$Ctx       = 8192,
    [int]$NPredict  = 64,
    [int]$Limit     = 0,
    [string]$Configs = 'none:f16,full:f16,full:q8_0,kv:f16,kv:q8_0'
)

$ErrorActionPreference = 'Stop'

$dir = Join-Path $Root 'tools\quality'
$exe = if ($Gpu) { Join-Path $Root 'tools\kvmem_quality_vk.exe' } else { Join-Path $Root 'tools\kvmem_quality.exe' }
$gpuArgs = @('--gpu', $(if ($Gpu) { '99' } else { '0' }))

$doc = Join-Path $dir "doc_$Tag.txt"
$qa  = Join-Path $dir "qa_$Tag.tsv"
foreach ($p in @($exe, $Model, $doc, $qa)) {
    if (-not (Test-Path $p)) { throw "missing: $p" }
}

foreach ($cfg in ($Configs -split ',')) {
    $cfg = $cfg.Trim()
    if ($cfg -eq '') { continue }
    # "arm:kv" -- the separator must not be '_' because q8_0 contains one.
    $parts = $cfg -split ':'
    $arm   = $parts[0]
    $kv    = $parts[1]

    $name = "${Tag}_$($arm)_$kv"
    $out  = Join-Path $dir "results_$name.tsv"
    $log  = Join-Path $dir "log_$name.txt"
    if (Test-Path $out) { Remove-Item $out -Force }

    $argv = @('run', '-m', $Model, '-f', $doc, '-q', $qa, '--arm', $arm, '--kv', $kv,
              '--ctx', "$Ctx", '--n', "$NPredict", '--out', $out) + $gpuArgs
    if ($Limit -gt 0) { $argv += @('--limit', "$Limit") }

    $t0 = Get-Date
    # PS 5.1 promotes any stderr line from a native command to a NativeCommandError,
    # which $ErrorActionPreference='Stop' turns fatal. Relax it for this call only and
    # rely on $LASTEXITCODE.
    $ErrorActionPreference = 'Continue'
    & $exe @argv *> $log
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    $secs = ((Get-Date) - $t0).TotalSeconds

    if ($code -ne 0) { throw "run failed: $name (exit $code), see $log" }

    $hits = Select-String -Path $log -Pattern 'exact-substring hits: (\d+/\d+)'
    $pre  = Select-String -Path $log -Pattern 'pos_max=\d+, ([\d.]+) t/s'
    $tail = if ($hits) { $hits.Matches[0].Groups[1].Value } else { 'no summary' }
    $rate = if ($pre)  { $pre.Matches[0].Groups[1].Value }  else { '?' }
    Write-Host ("== {0,-18} {1,7:N0}s  hits={2,-6} prefill={3} t/s" -f $name, $secs, $tail, $rate)
}

Write-Host ''
Write-Host '== grading'
$py = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
& $py -X utf8 (Join-Path $Root 'tools\grade_quality.py') --dir $dir --qa "qa_$Tag.tsv" --glob "results_${Tag}_*.tsv"