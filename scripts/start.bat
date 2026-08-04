@echo off
REM 镜·界·联 启动脚本（单后端 :5000）
cd /d %~dp0..
echo [1/2] 构建前端（如已构建可跳过）...
cd web
call npm run build
cd ..
echo [2/2] 启动后端 :5000 ...
.venv\Scripts\python.exe -m uvicorn backend.main:app --port 5000 --workers 1
