@echo off
chcp 65001 >nul
rem One-shot: restart DSH so the local14b provider loads, then restart the local service.
rem Spawned outside the DSH job object (WMI Win32_Process.Create), so it survives DSH kill.
set LOG=D:\llama-mem\kvmem\daily\restart-dsh.log
echo [%date% %time%] restart start >> "%LOG%"
rem give the current session ~90 s to finish its final message before killing DSH
timeout /t 90 >nul

rem 1) stop the local service if it is holding 8765
powershell -NoProfile -Command "$c=Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue; if($c){$c.OwningProcess|Select-Object -Unique|ForEach-Object{Stop-Process -Id $_ -Force}}" >> "%LOG%" 2>&1
timeout /t 2 >nul

rem 2) start the local service (new config: 16384 ctx / 34 layers / retrieval topk)
cd /d D:\llama-mem
start "" /min python -X utf8 tools\chat_service.py --port 8765 --db kvmem\daily\chat.db --blocks kvmem\daily\blocks --sessions kvmem\daily\sessions --session daily.json --n-ctx 16384 --chat-start 8192 --n-gpu-layers 34 --retrieval topk --topk 4 >> kvmem\daily\service.out.log 2>> kvmem\daily\service.err.log
echo [%date% %time%] service start >> "%LOG%"

rem 3) restart DSH
taskkill /IM "DSH NEXT.exe" /F >> "%LOG%" 2>&1
timeout /t 8 >nul
start "" "D:\DSH\DSH NEXT\DSH NEXT.exe"
echo [%date% %time%] dsh start >> "%LOG%"