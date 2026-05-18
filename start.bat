@echo off
cd /d "%~dp0"
set VENV_DIR=venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo 虚拟环境不存在，正在创建...
    python -m venv %VENV_DIR%
    echo 虚拟环境创建完成，正在安装依赖...
    %VENV_DIR%\Scripts\python.exe -m pip install -r requirements.txt
)

%VENV_DIR%\Scripts\python.exe main.py
pause