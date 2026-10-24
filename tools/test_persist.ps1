# test_persist.ps1 -- acceptance test for HANDOFF section 5, step 1.
#
# Runs three SEPARATE processes (this matters: the point is a process boundary):
#   1. control : fresh context, question only            -> must NOT know the answer
#   2. write   : decode the memory into seq 0, dump KV   -> process exits
#   3. query   : fresh process, load KV from disk, ask   -> must answer correctly
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File D:\llama-mem\tools\test_persist.ps1
#   powershell -ExecutionPolicy Bypass -File ...\test_persist.ps1 -Kv q8_0
#
# Exit code 0 = all three phases behaved as expected.

param(
    [string]$Model   = 'D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf',
    [string]$Kv      = 'f16',
    [int]$Predict    = 24,
    [string]$ExeName = 'kvmem_persist.exe',
    [int]$Gpu        = 0
)

$ErrorActionPreference = 'Stop'
$exe  = Join-Path $PSScriptRoot $ExeName
$file = Join-Path $PSScriptRoot "mem_$Kv$Gpu.kvmem"

if (-not (Test-Path $exe))  { throw "missing $exe (run build_tools.ps1)" }
if (-not (Test-Path $Model)) { throw "missing model $Model" }

if (Test-Path $file) { Remove-Item $file -Force }

$results = @()

function Run-Phase {
    param([string]$Name, [string[]]$ArgList)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    # llama.cpp logs to stderr; under 'Stop' PowerShell 5.1 turns that into a
    # terminating NativeCommandError, so relax the preference for the call.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $out = & $exe @ArgList 2>$null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    $sw.Stop()
    $text = ($out | Out-String)
    Write-Host "----- $Name (exit $code, $([math]::Round($sw.Elapsed.TotalSeconds,1))s)"
    Write-Host $text.TrimEnd()
    return [pscustomobject]@{ Name = $Name; Code = $code; Out = $text }
}

# 1. control
$r1 = Run-Phase 'control' @('control', '-m', $Model, '--n', "$Predict", '--kv', $Kv, '--gpu', "$Gpu")
$results += $r1

# 2. write
$r2 = Run-Phase 'write' @('write', '-m', $Model, '-f', $file, '--kv', $Kv, '--gpu', "$Gpu")
$results += $r2

# 3. query
$r3 = Run-Phase 'query' @('query', '-m', $Model, '-f', $file, '--n', "$Predict", '--kv', $Kv, '--gpu', "$Gpu")
$results += $r3

Write-Host ''
Write-Host '===== summary'
$fail = 0
foreach ($r in $results) {
    $ok = ($r.Code -eq 0)
    if (-not $ok) { $fail++ }
    Write-Host ("  {0,-8} {1}" -f $r.Name, $(if ($ok) { 'PASS' } else { "FAIL (exit $($r.Code))" }))
}

# KV budget cross-check.
#   f16  : 28 layers * 512 kv-dim * 2 (k+v) * 2 B      = 57344 B/token
#   q8_0 : same but 1 B/value, 34-byte blocks per 32    = 30464 B/token
# The q8_0 block carries a 2-byte scale per 32 values, so the real cost is
# 34/32 = 1.0625x the naive "28 KiB" figure quoted in HANDOFF section 10.
$expect = if ($Kv -eq 'q8_0') { 30464 } else { 57344 }
$m = [regex]::Match($r2.Out, 'bytes/token=\s*(\d+)')
if ($m.Success) {
    $bpt = [int]$m.Groups[1].Value
    $delta = [math]::Abs($bpt - $expect) / $expect
    $ok = $delta -lt 0.05
    if (-not $ok) { $fail++ }
    Write-Host ("  bytes/token {0} (expected ~{1}) {2}" -f $bpt, $expect, $(if ($ok) { 'PASS' } else { 'FAIL' }))
} else {
    Write-Host '  bytes/token: could not parse'
    $fail++
}

if ($fail -eq 0) {
    Write-Host '=> ALL PASS: memory survived a real process boundary.'
    exit 0
}
Write-Host "=> $fail check(s) failed."
exit 1
