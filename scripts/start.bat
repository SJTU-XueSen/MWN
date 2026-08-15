@echo off
REM 镜·界·联 启动脚本（:5000 主站 + :5021 智能体, 单进程双端口）
cd /d %~dp0..
echo [1/3] 构建主站前端（如已构建可跳过）...
cd web
call npm run build
cd ..
echo [2/3] 构建智能体前端（如已构建可跳过）...
cd agent_web
call npm run build
cd ..
echo [3/3] 启动服务 :5000 + :5021 ...
.venv\Scripts\python.exe scripts\start_all.py
