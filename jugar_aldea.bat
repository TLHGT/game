@echo off
rem Doble clic para jugar la Aldea del vacio (exploracion + combate de cartas).
python "%~dp0main_aldea.py"
if errorlevel 1 pause
