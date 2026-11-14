$py = "C:\Users\lezige\AppData\Local\Programs\Python\Python314\python.exe"
$cmd = "`"$py`" -X utf8 out\ops\launch_service.py"
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = $cmd
  CurrentDirectory = "D:\llama-mem"
}
$r | Format-List