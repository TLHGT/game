@echo off
rem Modo duelo original: combate de cartas PvP 1v1 en el mismo teclado (con menú y editor de mazos).
python "%~dp0main.py"
if errorlevel 1 pause
