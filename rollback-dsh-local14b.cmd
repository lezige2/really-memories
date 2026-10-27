@echo off
chcp 65001 >nul
echo 本脚本用于回滚 DSH 的 local14b provider 补丁（若 DSH 因配置无法启动）。
set P=%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml
set B=%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml.bak-20261027-local14b
if not exist "%B%" (
  echo 找不到备份：%B%
  pause
  exit /b 1
)
copy /y "%B%" "%P%"
echo 已回滚到补丁前版本。
echo 请重启 DSH。
pause