# -*- coding: utf-8 -*-
"""单进程双端口启动 — :5000 主站 + :5021 智能体

同一 Python 进程内跑两个 uvicorn Server:
- Chroma client / SQLite 共享单例（单进程约束, 无跨进程锁）
- init_db 只由 5000 app 的 lifespan 执行（5021 lifespan="off" 跳过, 防 Chroma 二次实例化）
- session cookie 同 SECRET_KEY → 5021 自动复用 5000 的登录态
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # 项目根（backend 包）

import uvicorn

from backend.main import app as main_app
from backend.agent_app import app as agent_app

MAIN_PORT = 5000
AGENT_PORT = 5021


async def main():
    cfg_main = uvicorn.Config(main_app, host="0.0.0.0", port=MAIN_PORT,
                              workers=1, log_level="info")
    cfg_agent = uvicorn.Config(agent_app, host="0.0.0.0", port=AGENT_PORT,
                               workers=1, lifespan="off", log_level="info")
    s_main = uvicorn.Server(cfg_main)
    s_agent = uvicorn.Server(cfg_agent)
    print(f"镜·界·联 主站:    http://localhost:{MAIN_PORT}")
    print(f"镜·界·联 智能体:  http://localhost:{AGENT_PORT}")
    await asyncio.gather(s_main.serve(), s_agent.serve())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("已停止")
