# -*- coding: utf-8 -*-
"""agent 单服务启动 — :5021（智能体 + 内置认证 + 静态前端）

- 单 uvicorn Server, lifespan 执行 init_db（建表/迁移/Chroma 清理）
- session cookie 独立闭环（agent 自带 /api/auth 注册登录）
- 生产模式直接伺服 agent_web/dist（同源单端口）; 开发模式 vite :5174 代理 /api → :5021
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # 项目根（backend 包）

import uvicorn

from backend.agent_app import app as agent_app

AGENT_PORT = int(os.environ.get("AGENT_PORT", "5021"))


async def main():
    cfg = uvicorn.Config(agent_app, host="0.0.0.0", port=AGENT_PORT,
                         workers=1, log_level="info")
    server = uvicorn.Server(cfg)
    print(f"镜·界·联 智能体:  http://localhost:{AGENT_PORT}")
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("已停止")
