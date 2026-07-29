"""成长报告路由"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from services.report_service import generate_report, get_user_reports, get_report_by_id
from templating import render

router = APIRouter(prefix="/reports", tags=["reports"])


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


# ── 报告列表 ──────────────────────────────────────────

@router.get("")
async def report_list(request: Request, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    reports = await get_user_reports(db, uid)
    return _render(request, "reports/list.html", active="reports", reports=reports)


# ── 生成报告 ──────────────────────────────────────────

@router.get("/generate")
async def report_generate_form(request: Request):
    if r := _require_login(request): return r
    # 默认：最近 30 天
    end = datetime.utcnow()
    start = end - timedelta(days=30)
    return _render(request, "reports/generate.html", active="reports",
                   default_start=start.strftime("%Y-%m-%d"),
                   default_end=end.strftime("%Y-%m-%d"))


@router.post("/generate")
async def report_generate(
    request: Request,
    title: str = Form(""),
    period_start: str = Form(""),
    period_end: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]

    # 解析日期
    now = datetime.utcnow()
    start = datetime.fromisoformat(period_start) if period_start else now - timedelta(days=30)
    end = datetime.fromisoformat(period_end) if period_end else now

    # 默认标题
    if not title:
        title = f"成长报告 {start.strftime('%Y.%m.%d')} - {end.strftime('%Y.%m.%d')}"

    # 用户背景（用于 LLM 理解）
    user = request.session.get("user", {})
    user_context = f"用户 {user.get('username', '')}"

    report = await generate_report(db, uid, title, start, end, user_context)

    return RedirectResponse(url=f"/reports/{report.id}", status_code=302)


# ── 报告详情 ──────────────────────────────────────────

@router.get("/{report_id}")
async def report_detail(request: Request, report_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    report = await get_report_by_id(db, report_id)
    if not report or report.user_id != uid:
        return RedirectResponse(url="/reports", status_code=302)

    return _render(request, "reports/detail.html", active="reports", report=report)


# ── 删除报告 ──────────────────────────────────────────

@router.get("/{report_id}/delete")
async def report_delete(request: Request, report_id: int, db: AsyncSession = Depends(get_db)):
    if r := _require_login(request): return r
    uid = request.session["user"]["id"]
    report = await get_report_by_id(db, report_id)
    if not report or report.user_id != uid:
        return RedirectResponse(url="/reports", status_code=302)
    await db.delete(report)
    await db.commit()
    return RedirectResponse(url="/reports", status_code=302)
