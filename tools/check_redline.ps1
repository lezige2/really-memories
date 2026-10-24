# check_redline.ps1 -- mechanically verify the three red-line rules.
#
# The red line (README-HANDOFF-2.md section 7) is not "you may not train". It is
# "the product must not depend on anything you trained". These three rules turn that
# into something a machine can check:
#
#   R1  the 7B weight file is byte-identical to the shipped model   (sha256)
#   R2  with every training artifact removed, the memory still works  (test_persist)
#   R3  no artifact has been merged into the model                  (implied by R1)
#
# R2 is the important one: it is the difference between "gradual enhancement" and
# "covert retraining". It runs the same three-process acceptance test that already
# passes on the untouched engine, but with the artifact directory moved aside.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File D:\llama-mem\tools\check_redline.ps1
#   powershell -ExecutionPolicy Bypass -File D:\llama-mem\tools\check_redline.ps1 -Gpu
#   powershell -ExecutionPolicy Bypass -File D:\llama-mem\tools\check_redline.ps1 -ArtifactDir D:\llama-mem\artifacts
#
# Exit code: 0 = all rules hold, 1 = at least one rule violated.
# ASCII only (PowerShell 5.1 mangles non-ASCII literals in .ps1 files).

param(
    [string]$Root        = 'D:\llama-mem',
    [string]$Model       = 'D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf',
    [string]$ArtifactDir = 'D:\llama-mem\artifacts',
    [string]$HashFile    = 'D:\llama-mem\tools\redline_model.sha256',
    [switch]$Gpu,
    [switch]$Init
)

$ErrorActionPreference = 'Stop'
$fail = @()

function Say($text) { Write-Host $text }

# ---------------------------------------------------------------- R1: model hash

Say '== R1: the 7B weight file must not change'
$now = (Get-FileHash -Path $Model -Algorithm SHA256).Hash.ToLower()
Say ("   model   : {0}" -f $Model)
Say ("   sha256  : {0}" -f $now)

if (-not (Test-Path $HashFile) -or $Init) {
    $now | Out-File -FilePath $HashFile -Encoding ascii -NoNewline
    Say ("   baseline pinned -> {0}" -f $HashFile)
    Say '   R1: PASS (baseline recorded on this run; future runs are compared against it)'
} else {
    $base = (Get-Content $HashFile -Raw).Trim().ToLower()
    if ($base -eq $now) {
        Say '   R1: PASS (model unchanged since the baseline was pinned)'
    } else {
        Say '   R1: FAIL (model file changed -- this is the "you shipped a different model" case)'
        Say ("        baseline was {0}" -f $base)
        $fail += 'R1'
    }
}

# ------------------------------------------------- R2: works with artifacts removed

Say ''
Say '== R2: memory must work with every training artifact removed'

$existed = Test-Path $ArtifactDir
$moved   = "$ArtifactDir.__hidden_for_redline_test"

if ($existed) {
    $count = @(Get-ChildItem -Path $ArtifactDir -Recurse -File).Count
    Say ("   artifacts present: {0} files -- moving aside to prove they are optional" -f $count)
    if (Test-Path $moved) { Remove-Item $moved -Recurse -Force }
    Move-Item -Path $ArtifactDir -Destination $moved
} else {
    Say '   no artifact directory: nothing to remove, the test runs on the bare model'
}

try {
    $psArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $Root 'tools\test_persist.ps1'), '-Kv', 'q8_0')
    if ($Gpu) {
        $psArgs += @('-ExeName', 'kvmem_persist_vk.exe', '-Gpu', '99')
    }
    $log = Join-Path $Root 'tools\quality\redline_persist.log'
    New-Item -ItemType Directory -Force -Path (Split-Path $log -Parent) | Out-Null
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $out = & powershell @psArgs 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    $out | Out-File -FilePath $log -Encoding utf8
    $allPass  = ($out | Select-String -Pattern '=> ALL PASS' | Measure-Object).Count
    $failLine = ($out | Select-String -Pattern 'check\(s\) failed' | Measure-Object).Count

    Say ("   test_persist.ps1 exit={0}  all-pass={1}  fail-lines={2}" -f $code, $allPass, $failLine)
    if ($code -eq 0 -and $allPass -gt 0 -and $failLine -eq 0) {
        Say '   R2: PASS (write -> restart -> query still answers with no artifacts on disk)'
    } else {
        Say ("   R2: FAIL -- see {0}" -f $log)
        $fail += 'R2'
    }
} finally {
    if (Test-Path $moved) {
        Move-Item -Path $moved -Destination $ArtifactDir
        Say '   artifacts restored'
    }
}

# ---------------------------------------------------------------- R3: no merging

Say ''
Say '== R3: no artifact may be merged into the model'
if (Test-Path $ArtifactDir) {
    $big = @(Get-ChildItem -Path $ArtifactDir -Recurse -File |
             Where-Object { $_.Length -gt 1GB })
    if ($big.Count -gt 0) {
        Say '   R3: WARN -- an artifact is larger than 1 GB; a LoRA merged into the base model'
        Say '             would show up here. Confirm it is a separate decoder, not a rewritten GGUF.'
    } else {
        Say '   R3: PASS (all artifacts are small side-car files)'
    }
} else {
    Say '   R3: PASS (vacuously: no artifacts exist)'
}
Say '   note: R1 already proves the shipped GGUF was not rewritten in place.'

Say ''
if ($fail.Count -eq 0) {
    Say 'RED LINE: HOLDS (R1 + R2 + R3)'
    exit 0
} else {
    Say ("RED LINE: VIOLATED -> {0}" -f ($fail -join ', '))
    exit 1
}