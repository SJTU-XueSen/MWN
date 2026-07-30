"""AI人生镜像 — 主入口"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from config import APP_NAME, APP_VERSION, APP_DESCRIPTION, BASE_DIR, SECRET_KEY
from database import init_db
from database.database import get_db
from templating import render


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    await init_db()
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    lifespan=lifespan,
)

# CORS — 允许 React 前端跨域
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Session 中间件（signed cookie）
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="none", https_only=False, max_age=86400)


# ── iframe 嵌入模式：重写 redirect Location 以保持 /embed/ 前缀 ──
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class EmbedRedirectMiddleware(BaseHTTPMiddleware):
    """当请求来自 Vite /embed/ 代理时，自动重写 3xx 重定向的 Location 为 /embed/ 前缀"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        is_embedded = request.headers.get("X-Embedded") == "1"
        if is_embedded and 300 <= response.status_code < 400:
            location = response.headers.get("Location")
            if location and location.startswith("/") and not location.startswith("/embed/") and not location.startswith("/api/") and not location.startswith("/auth/"):
                response.headers["Location"] = "/embed" + location
        return response

app.add_middleware(EmbedRedirectMiddleware)

# React 构建产物（统一前端）
import os as _os
_react_dist = os.path.join(BASE_DIR, "SJTU-Activity-Hub", "dist")
if _os.path.exists(_react_dist):
    app.mount("/assets", StaticFiles(directory=_os.path.join(_react_dist, "assets")), name="react_assets")

# Mirror 自身的静态文件
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if _os.path.exists(_static_dir):
    app.mount("/mirror-static", StaticFiles(directory=_static_dir), name="mirror_static")

# 注册路由
from routers.auth import router as auth_router
from routers.legal import router as legal_router
from routers.events import router as events_router
from routers.reports import router as reports_router
from routers.persona import router as persona_router
from routers.goals import router as goals_router
from routers.simulate import router as simulate_router
from routers.future_chat import router as future_chat_router
from routers.settings import router as settings_router
from routers.references import router as references_router
from routers.activity import router as activity_router
from routers.experience import router as experience_router
from routers.hub_api import router as hub_api_router
from routers.mirror_api import router as mirror_api_router, _auth_router
app.include_router(auth_router)
app.include_router(legal_router)
app.include_router(events_router)
app.include_router(reports_router)
app.include_router(persona_router)
app.include_router(goals_router)
app.include_router(simulate_router)
app.include_router(future_chat_router)
app.include_router(settings_router)
app.include_router(references_router)
app.include_router(activity_router)
app.include_router(experience_router)
app.include_router(hub_api_router)
app.include_router(mirror_api_router)
app.include_router(_auth_router)


# ── 工具函数 ──────────────────────────────────────────

def _require_login(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/auth/login", status_code=302)
    return None


def _render(request: Request, template: str, **kwargs):
    return HTMLResponse(render(template, {
        "request": request,
        "user": request.session.get("user"),
        **kwargs,
    }))


# ── 核心页面 ──────────────────────────────────────────

@app.get("/")
async def index(request: Request):
    """API 服务器——前端由 Vite/React 负责"""
    return {"app": APP_NAME, "version": APP_VERSION}


# ── 占位路由（后续步骤实现）─────────────────────────────



@app.get("/health")
async def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


# ── SPA fallback：React 前端兜底 ──────────────────────
from fastapi.responses import FileResponse as _FileResponse

@app.get("/{full_path:path}")
async def spa_fallback(request: Request, full_path: str):
    if full_path.startswith(("api/", "auth/", "legal/", "health", "mirror-static/")):
        return HTMLResponse("", status_code=404)
    return HTMLResponse("", status_code=404)
