@echo off
chcp 65001 >nul
set VENV_DIR=..\venv

echo 启动前端应用...
"%VENV_DIR%\Scripts\python.exe" app.py