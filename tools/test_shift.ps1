# test_shift.ps1 -- step 2 "current behaviour" experiment.
#
# Question: does a context shift (server-context.cpp:3698-3699) destroy the memory
# that lives in the chat sequence via seq_cp? We vary n_keep, which decides where
# the discard range starts.
#
#   memory occupies positions 0..memory_len-1, chat starts at memory_len
#   server default n_keep = 0  -> seq_rm(chat, 0, n_discard) eats into the memory
#   correct      n_keep >= memory_len -> only chat cells are discarded
#
# Expectations (measured, not guessed -- see the summary at the end):
#   case                      n_keep  n_discard  observed
#   fill-only (no shift)      69      0          answer OK, positions untouched
#   shift, keep memory prefix 69      300        answer OK, memory still at 0..68
#   server default            0       300        answer BROKEN (memory claim removed)
#   discard = mem len         0       69         answer BROKEN (all memory cells dropped)
#   discard = 1               0       1          answer OK -- but the memory was silently
#                                               shifted down by one and lost its head
#
# Usage: powershell -ExecutionPolicy Bypass -File tools\test_shift.ps1 [-Kv q8_0]

param(
    [string]$Model   = 'D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf',
    [string]$Kv      = 'f16',
    [string]$ExeName = 'kvmem_persist_vk.exe',
    [int]$Gpu        = 99,
    [int]$Ctx        = 8192,
    [int]$Fill       = 900,
    [int]$MemLen     = 69
)

$ErrorActionPreference = 'Stop'
$exe  = Join-Path $PSScriptRoot $ExeName
$file = Join-Path $PSScriptRoot "mem_shift_$Kv.kvmem"

if (-not (Test-Path $exe))  { throw "missing $exe (run build_tools.ps1 -Gpu)" }
if (-not (Test-Path $Model)) { throw "missing model $Model" }

function Invoke-Case {
    param([string]$Name, [int]$Keep, [int]$Discard, [int]$Expect)
    $args = @('shift', '-m', $Model, '-f', $file, '--gpu', "$Gpu", '--ctx', "$Ctx",
              '--fill', "$Fill", '--n-keep', "$Keep", '--n-discard', "$Discard", '--kv', $Kv, '--n', '24')
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $out = & $exe @args 2>$null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev

    $text = ($out | Out-String)
    Write-Host "----- $Name  (n_keep=$Keep n_discard=$Discard, exit $code, expected $Expect)"
    Write-Host $text.TrimEnd()

    $verdict = $null
    if ($text -match '=> (PASS|FAIL)') { $verdict = $Matches[1] }

    return [pscustomobject]@{
        Name = $Name; Code = $code; Expect = $Expect; Verdict = $verdict
        Ok = ($code -eq $Expect)
    }
}

# make sure we have a KV file (write phase is a separate process, as always)
if (-not (Test-Path $file)) {
    Write-Host "== writing $file"
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $exe write -m $Model -f $file --gpu "$Gpu" --ctx "$Ctx" --kv $Kv 2>$null | Out-Null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($code -ne 0) { throw "write failed ($code)" }
}

$cases = @(
    @{ Name = 'fill only';            Keep = $MemLen; Discard = 0;   Expect = 0 },
    @{ Name = 'shift, keep memory';   Keep = $MemLen; Discard = 300; Expect = 0 },
    @{ Name = 'server default';       Keep = 0;       Discard = 300; Expect = 1 },
    @{ Name = 'discard = mem len';    Keep = 0;       Discard = 69;  Expect = 1 },
    @{ Name = 'discard = 1 (silent)'; Keep = 0;       Discard = 1;   Expect = 0 }
)

$rows = @()
foreach ($c in $cases) {
    $rows += Invoke-Case -Name $c.Name -Keep $c.Keep -Discard $c.Discard -Expect $c.Expect
}

Write-Host ''
Write-Host '===== summary (expectation = observed engine behaviour)'
$bad = 0
foreach ($r in $rows) {
    if (-not $r.Ok) { $bad++ }
    Write-Host ("  {0,-22} exit={1} expected={2} verdict={3}  {4}" -f `
        $r.Name, $r.Code, $r.Expect, $r.Verdict, $(if ($r.Ok) { 'as expected' } else { 'UNEXPECTED' }))
}

if ($bad -eq 0) {
    Write-Host '=> Confirmed: with n_keep=0 the shift eats into the memory.'
    Write-Host '   - small discards silently relocate + truncate it (the answer survives only'
    Write-Host '     because the fact sits at the tail of this particular memory text)'
    Write-Host '   - a realistic discard (n_left/2) wipes it completely'
    Write-Host '   - n_keep >= memory length is the only setting that leaves the memory untouched'
    exit 0
}
Write-Host "=> $bad case(s) contradicted the prediction."
exit 1