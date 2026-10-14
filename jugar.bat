@echo off
rem Doble clic para jugar: el hospital abandonado (exploración + combate de cartas).
python "%~dp0main.py"
if errorlevel 1 pause
