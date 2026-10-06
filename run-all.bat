@echo off
echo Starting LogMaster Full-Stack App...
start "Django Backend (8000)" cmd /k "%~dp0run-backend.bat"
timeout /t 2 /nobreak >nul
start "React Frontend (5173)" cmd /k "%~dp0run-frontend.bat"
echo Both servers are launching!
echo Frontend will be at: http://localhost:5173
echo Backend API will be at: http://127.0.0.1:8000/api/health/
