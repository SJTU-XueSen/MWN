"""镜·界·联 — 单一后端入口（:5000，伺服 API + React 构建产物）"""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.auth import AuthRequiredMiddleware
from backend.config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    BASE_DIR,
    DIST_DIR,
    SECRET_KEY,
    UPLOAD_DIR,
)
from backend.database.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(BASE_DIR / "data", exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    await init_db()
    # 爬虫调度器（阶段3启用）：后台任务，uvicorn 必须 --workers 1
    try:
        from backend.services.scheduler import start_scheduler

        scheduler_task = asyncio.create_task(start_scheduler())
        yield
        scheduler_task.cancel()
    except ImportError:
        yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    lifespan=lifespan,
)

# ── 中间件顺序（后加者最外层 → 请求流 CORS → Session → Auth）──
app.add_middleware(AuthRequiredMiddleware)                      # 内层：API 鉴权
app.add_middleware(                                            # 外层：会话读取
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",        # 关键修复：SameSite=None + http 会被浏览器丢弃 cookie
    https_only=False,
    max_age=7 * 86400,
)
app.add_middleware(                                            # 最外层：仅开发跨域
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 静态资源 ──
if (DIST_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ── 路由 ──
from backend.routers import (  # noqa: E402
    activities,
    auth,
    chat,
    credits,
    hub,
    mirror,
    tasks,
    teams,
    work,
)

app.include_router(auth.router)
app.include_router(mirror.router)
app.include_router(hub.router)
app.include_router(activities.router)
app.include_router(teams.router)
app.include_router(tasks.router)
app.include_router(work.router)
app.include_router(chat.router)
app.include_router(credits.router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


# ── SPA fallback：非 API 的 GET 一律返回前端 index.html（修复 /login 等 404）──
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith(("api/", "auth/")):
        return JSONResponse({"error": "not_found"}, status_code=404)
    index = DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"app": APP_NAME, "version": APP_VERSION})
