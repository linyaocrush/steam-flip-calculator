@echo off
chcp 65001 >nul
set VENV_DIR=venv

echo 启动 Steam 倒余额工具箱 (FastAPI + Flet)...

echo 启动后端服务 (FastAPI + Uvicorn)...
start cmd /k "cd backend && ..\%VENV_DIR%\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload"

echo 等待后端服务启动...
timeout /t 3 /nobreak >nul

echo 启动前端应用 (Flet)...
cd frontend
..\%VENV_DIR%\Scripts\python.exe app.py