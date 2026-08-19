@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL-AND-OPEN-ABAAR.ps1"
if errorlevel 1 (
  echo.
  echo Installation failed. Send the red error text back.
  pause
)
