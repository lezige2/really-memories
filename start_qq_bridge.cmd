@echo off
chcp 65001 >nul 2>nul
setlocal EnableExtensions
cd /d "%~dp0"

rem ---- QQ bridge launcher (Windows) --------------------------------------
rem Reads tools\qq_bridge.local.json (copy the template if missing).
rem Token comes ONLY from env var QQ_BRIDGE_TOKEN; never stored in config.
rem Log: kvmem\qq_logs\bridge.log

if not exist "tools\qq_bridge.local.json" goto no_config
if "%QQ_BRIDGE_TOKEN%"=="" goto no_token

if not exist "kvmem\qq_logs" mkdir "kvmem\qq_logs"
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
echo [%DATE% %TIME%] starting qq_bridge (reverse ws://127.0.0.1:8766)>>"kvmem\qq_logs\bridge.log"
%PY% -X utf8 tools\qq_bridge.py --config tools\qq_bridge.local.json --token "%QQ_BRIDGE_TOKEN%" >>"kvmem\qq_logs\bridge.log" 2>&1
set "RC=%ERRORLEVEL%"
echo [%DATE% %TIME%] qq_bridge exited rc=%RC% >>"kvmem\qq_logs\bridge.log"
exit /b %RC%

:no_config
echo [ERROR] missing tools\qq_bridge.local.json
echo         copy tools\qq_bridge.local.example.json tools\qq_bridge.local.json
exit /b 2

:no_token
echo [ERROR] env var QQ_BRIDGE_TOKEN is not set
echo         set QQ_BRIDGE_TOKEN=your-random-token   (must match NapCat reverse WS token)
exit /b 2
