@echo off
rem Arrastra un mapa .json encima de este archivo para jugarlo.
if "%~1"=="" (
  echo Arrastra un mapa .json encima de este archivo para probarlo en el juego.
  pause
  exit /b
)
python "%~dp0..\main.py" "%~1"
if errorlevel 1 pause
