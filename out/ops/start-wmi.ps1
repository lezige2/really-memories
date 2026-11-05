$cmd = 'cmd.exe /c "D:\llama-mem\out\ops\run-service.cmd"'
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd }
$r | Format-List