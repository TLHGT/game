@echo off
rem Juega el nivel de prueba del hospital abandonado.
python "%~dp0main.py" "%~dp0maps\hospital_exterior.json"
if errorlevel 1 pause
