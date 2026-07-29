"""AI人生镜像 — 主入口"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
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

# Session 中间件（signed cookie）
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="static"), name="static")

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
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    from services.dashboard_service import get_dashboard_data
    data = await get_dashboard_data(db, request.session["user"]["id"])
    return _render(request, "index.html", active="index", **data)


# ── 占位路由（后续步骤实现）─────────────────────────────



@app.get("/health")
async def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}
