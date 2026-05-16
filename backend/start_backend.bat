@echo off
chcp 65001 >nul
set VENV_DIR=..\venv

echo 启动 Steam 倒余额计算器后端服务 (FastAPI + Uvicorn)...
"%VENV_DIR%\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload