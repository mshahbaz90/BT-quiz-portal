@echo off
title BreakThru Assessment Portal Server
cd /d "%~dp0"

echo ===================================================
echo     BreakThru Assessments Portal Server
echo ===================================================
echo.
echo Checking Python Virtual Environment...
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo Starting portal server on http://0.0.0.0:8000 ...
echo.
echo [Local Access]
echo   http://127.0.0.1:8000/
echo   http://localhost:8000/
echo   http://bt.assesment.pk:8000/
echo   http://breakthru.assesment.portal:8000/
echo.
echo [LAN / Mobile Phone Access on Wi-Fi]
echo   http://192.168.18.78:8000/
echo.
echo Press Ctrl+C to stop the server at any time.
echo ===================================================
echo.

"%PYTHON_EXE%" manage.py runserver 0.0.0.0:8000

pause
