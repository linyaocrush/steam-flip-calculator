@echo off
chcp 65001 >nul
set VENV_DIR=..\venv

echo 启动 Steam 倒余额计算器后端服务...
"%VENV_DIR%\Scripts\python.exe" app.py