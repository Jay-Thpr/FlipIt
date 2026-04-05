@echo off
cd /d "%~dp0"

REM --- Ensure localtunnel is installed ---
call node -e "require('localtunnel')" >nul 2>&1
if errorlevel 1 (
    echo Installing localtunnel...
    call npm install localtunnel
)

REM --- Kill anything already on port 8000 ---
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul

REM --- Start uvicorn in a new window ---
echo Starting uvicorn on 0.0.0.0:8000 ...
start "uvicorn" cmd /c "python -m uvicorn backend.main:app --port 8000 --host 0.0.0.0"
timeout /t 3 >nul

REM --- Start tunnel via separate script ---
echo Starting localtunnel...
node tunnel.js

pause
