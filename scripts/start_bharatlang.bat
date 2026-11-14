@echo off
rem One-click start for Bharatlang after a restart (on demand, not at boot).
rem Starts Ollama, the backend and Vite, then the reverse tunnel to the AWS front door.
rem Safe to run twice: anything already running is left alone.
title Bharatlang - starting
set "ROOT=C:\dev\Bharatlang"
set "PS=powershell -NoProfile -ExecutionPolicy Bypass -File"

echo.
echo  [1/3] Starting Ollama, backend and frontend (first start can take ~1-2 min)...
%PS% "%ROOT%\scripts\start_services.ps1"
if errorlevel 1 goto fail

echo.
echo  [2/3] Opening the tunnel to the website...
%PS% "%ROOT%\scripts\start_tunnel.ps1"
if errorlevel 1 goto fail

echo.
echo  [3/3] Checking the backend...
curl.exe -s -m 30 -o nul -w "  backend health: HTTP %%{http_code}\n" http://127.0.0.1:8000/api/health
powershell -NoProfile -Command "Start-Sleep -Seconds 10"
%PS% "%ROOT%\scripts\start_tunnel.ps1" -Status

echo.
echo  Done. Website: https://bharatlang.ideasfreshly.store
echo  Keep this PC on; the site shows "temporarily unavailable" while it is off.
echo.
pause
exit /b 0

:fail
echo.
echo  Something failed. Logs are in %ROOT%\logs
echo.
pause
exit /b 1
