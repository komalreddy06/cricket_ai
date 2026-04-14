@echo off
title SRH Cricket AI — EIE115R01
color 0A
cd /d "%~dp0"

echo.
echo  ============================================================
echo   ☀  SRH CRICKET AI GAME — EIE115R01  (Komal Reddy)
echo  ============================================================
echo.
echo  [1] Installing Python dependencies...
pip install flask flask-cors -q --quiet

echo  [2] Starting AI Server...
start "Cricket AI Server" cmd /k "python ai_server.py"

echo  [3] Waiting for server...
timeout /t 3 /nobreak >nul

echo  [4] Opening Game in browser...
Start-Process "http://127.0.0.1:8888/"

echo.
echo  ✅ Game running at http://127.0.0.1:8888/
echo  ============================================================
pause
