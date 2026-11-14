; llama-mem NSIS context menu (HKCU, no admin)
!macro preInit
  SetRegView 64
  WriteRegExpandStr HKCU "${INSTALL_REGISTRY_KEY}" InstallLocation "D:\llama-mem-os"
!macroend

!macro customInstall
  WriteRegStr HKCU "Software\Classes\*\shell\llama-mem" "" "存入 llama-mem 记忆"
  WriteRegStr HKCU "Software\Classes\*\shell\llama-mem\command" "" '"C:\Users\lezige\AppData\Local\Programs\Python\Python314\pythonw.exe" "$INSTDIR\resources\backend\tools\remember_file.py" "%1"'
!macroend

!macro customUnInstall
  DeleteRegKey HKCU "Software\Classes\*\shell\llama-mem"
!macroend