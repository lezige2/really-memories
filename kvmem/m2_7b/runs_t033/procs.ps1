Get-CimInstance Win32_Process -Filter "Name like 'python%'" | ForEach-Object { "{0}`t{1}" -f $_.ProcessId, $_.CommandLine }
