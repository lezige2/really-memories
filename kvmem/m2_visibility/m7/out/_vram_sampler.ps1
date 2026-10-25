param([string]$Flag, [int]$Interval = 100)
$max = 0
$n = 0
while (-not (Test-Path $Flag)) {
    $m = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction SilentlyContinue |
         Measure-Object -Property DedicatedUsage -Sum
    $v = [double]$m.Sum
    if ($v -gt $max) { $max = $v }
    $n++
    Start-Sleep -Milliseconds $Interval
}
[pscustomobject]@{peak_bytes=$max; samples=$n} | ConvertTo-Json -Compress
