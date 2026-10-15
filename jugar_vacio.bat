@echo off
rem Doble clic para jugar la Dimension del vacio (exploracion + combate de cartas).
python "%~dp0main_vacio.py"
if errorlevel 1 pause
