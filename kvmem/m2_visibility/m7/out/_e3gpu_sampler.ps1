param(
    [string]$Flag,
    [string]$Out,
    [int]$Interval = 100
)
# M7 E3-GPU dedicated-VRAM sampler (skeleton; do not run before PREREG).
# Writes the running maximum (bytes) to $Out on every sample and exits when
# the stop flag appears.  The parent only writes the flag; it never signals
# the GPU child.
$max = 0
$n = 0
while (-not (Test-Path $Flag)) {
    $m = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction SilentlyContinue |
         Measure-Object -Property DedicatedUsage -Sum
    $v = [double]$m.Sum
    if ($v -gt $max) {
        $max = $v
        [System.IO.File]::WriteAllText($Out, [string]$max)
    }
    $n++
    Start-Sleep -Milliseconds $Interval
}
if (-not (Test-Path $Out)) {
    [System.IO.File]::WriteAllText($Out, [string]$max)
}
[pscustomobject]@{peak_bytes = $max; samples = $n} | ConvertTo-Json -Compress