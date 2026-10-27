@echo off
rem C version: local 14B memory assistant (offline, KV-block memory, no prompt splicing).
rem Double-click to start the interactive assistant. /quit or Ctrl+C exits (auto-save).
rem First run creates the immutable log identity: kvmem\assistant\manifest.json
title C version - local 14B memory assistant (chat_daily / offline)
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python not found in PATH. Install Python 3.11+ first.
    pause
    exit /b 1
)

python -X utf8 tools\chat_daily.py %*
if errorlevel 1 (
    echo.
    echo [FAILED] exit code %errorlevel%
    echo Check: 1^) model and dll exist  2^) GPU free  3^) run from D:\llama-mem
    echo Log summary: python -X utf8 tools\inspect_logs.py --summary
    pause
)
