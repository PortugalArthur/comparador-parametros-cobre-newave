@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 goto usar_py
python -m comparador.executar %*
if errorlevel 1 pause
exit /b
:usar_py
where py >nul 2>&1
if errorlevel 1 goto sem_python
py -3 -m comparador.executar %*
if errorlevel 1 pause
exit /b
:sem_python
echo Instale o Python 3.10 ou mais recente e execute este arquivo novamente.
pause
exit /b 1
