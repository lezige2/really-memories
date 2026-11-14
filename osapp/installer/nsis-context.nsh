; llama-mem NSIS context menu (HKCU, no admin)
!macro customInstall
  WriteRegStr HKCU "Software\Classes\*\shell\llama-mem" "" "存入 llama-mem 记忆"
  WriteRegStr HKCU "Software\Classes\*\shell\llama-mem\command" "" '"C:\Users\lezige\AppData\Local\Programs\Python\Python314\pythonw.exe" "D:\llama-mem\tools\remember_file.py" "%1"'
!macroend

!macro customUnInstall
  DeleteRegKey HKCU "Software\Classes\*\shell\llama-mem"
!macroend