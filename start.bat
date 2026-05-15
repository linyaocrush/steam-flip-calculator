@echo off
chcp 65001 >nul
set VENV_DIR=venv

echo 启动 Steam 倒余额工具箱...

echo 启动后端服务...
start cmd /k "cd backend && ..\%VENV_DIR%\Scripts\python.exe app.py"

echo 等待后端服务启动...
timeout /t 3 /nobreak >nul

echo 启动前端应用...
cd frontend
..\%VENV_DIR%\Scripts\python.exe app.py