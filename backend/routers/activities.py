"""活动平台 — 活动列表/详情/发布/审核/爬虫触发"""
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select

from backend.auth import require_uid
from backend.database.database import AsyncSessionLocal
from backend.database.models import Competition, Team, TeamMember, User

router = APIRouter(prefix="/api", tags=["activities"])


def _fmt_date(dt) -> str:
    return dt.strftime("%Y-%m-%d") if dt else ""


def _competition_list_item(c: Competition, team_count: int) -> dict:
    return {
        "id": c.id, "title": c.title, "category": c.category, "level": c.level,
        "description": (c.description or "")[:200], "organizer": c.organizer,
        "max_team_size": c.max_team_size, "min_team_size": c.min_team_size,
        "registration_deadline": _fmt_date(c.registration_deadline),
        "credit_info": c.credit_info, "tags": c.tags or [],
        "team_count": team_count, "created_at": _fmt_date(c.created_at),
        "is_competition": c.is_competition,
        "source_site": c.source_site or "",
        "ai_confidence": c.ai_confidence or 0.0,
        "publisher_type": c.publisher_type,
    }


@router.get("/competitions")
async def api_competitions(request: Request, category: str = "", level: str = "", search: str = "", kind: str = "activity"):
    """活动列表

    kind: activity=组队活动（默认，is_competition=False）
          competition=竞赛信息（is_competition=True）
    """
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        is_comp = kind == "competition"
        q = select(Competition).where(
            Competition.approval_status == "approved",
            Competition.is_competition == is_comp,
            Competition.status == "active",
        )
        if category:
            q = q.where(Competition.category == category)
        if level:
            q = q.where(Competition.level == level)
        if search:
            q = q.where(or_(Competition.title.contains(search), Competition.description.contains(search)))
        q = q.order_by(Competition.created_at.desc())
        comps = (await db.execute(q)).scalars().all()

        # 每个活动的战队数
        ids = [c.id for c in comps]
        counts: dict = {}
        if ids:
            rows = (
                await db.execute(
                    select(Team.competition_id, func.count(Team.id)).where(Team.competition_id.in_(ids))
                    .group_by(Team.competition_id)
                )
            ).all()
            counts = {row[0]: row[1] for row in rows}

        categories = sorted({c.category for c in comps if c.category})
        levels = sorted({c.level for c in comps if c.level})
        return JSONResponse({
            "activities": [_competition_list_item(c, counts.get(c.id, 0)) for c in comps],
            "categories": categories,
            "levels": levels,
            "kind": kind,
        })


@router.get("/competitions/{comp_id}")
async def api_competition_detail(request: Request, comp_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        comp = await db.get(Competition, comp_id)
        if not comp:
            return JSONResponse({"error": "not_found"}, 404)

        teams = (
            await db.execute(
                select(Team).where(Team.competition_id == comp_id).order_by(Team.created_at.asc())
            )
        ).scalars().all()
        teams_out = []
        for t in teams:
            members = (
                await db.execute(
                    select(func.count()).select_from(TeamMember).where(TeamMember.team_id == t.id)
                )
            ).scalar() or 0
            leader = await db.get(User, t.leader_id)
            teams_out.append({
                "id": t.id, "name": t.name, "slogan": t.slogan, "status": t.status,
                "member_count": members, "leader_name": leader.real_name if leader else "",
            })

        # 当前用户在此活动的战队
        my_team = None
        my_tm = (
            await db.execute(
                select(TeamMember).join(Team).where(
                    TeamMember.user_id == uid, Team.competition_id == comp_id
                ).limit(1)
            )
        ).scalar_one_or_none()
        if my_tm:
            team = await db.get(Team, my_tm.team_id)
            my_team = {"id": team.id, "name": team.name, "status": team.status, "role": my_tm.role}

        return JSONResponse({
            "id": comp.id, "title": comp.title, "category": comp.category, "level": comp.level,
            "description": comp.description, "organizer": comp.organizer,
            "max_team_size": comp.max_team_size, "min_team_size": comp.min_team_size,
            "registration_deadline": _fmt_date(comp.registration_deadline),
            "credit_info": comp.credit_info, "tags": comp.tags or [],
            "status": comp.status,
            "publisher_type": comp.publisher_type, "publisher_name": comp.publisher_name,
            "teams": teams_out, "my_team": my_team,
        })


@router.post("/competition/create")
async def api_competition_create(request: Request):
    uid = require_uid(request)
    body = await request.json()
    title = str(body.get("title", "")).strip()
    if not title:
        return JSONResponse({"error": "活动名称不能为空"}, 400)

    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        deadline = None
        if body.get("registration_deadline"):
            try:
                deadline = datetime.fromisoformat(body["registration_deadline"])
            except Exception:
                pass
        tags = body.get("tags", "")
        tags_list = [t.strip() for t in tags.split(",") if t.strip()] if isinstance(tags, str) else tags
        comp = Competition(
            title=title,
            category=str(body.get("category", "")),
            level=str(body.get("level", "")),
            description=str(body.get("description", "")),
            organizer=str(body.get("organizer", "")),
            max_team_size=int(body.get("max_team_size", 5) or 5),
            min_team_size=int(body.get("min_team_size", 1) or 1),
            registration_deadline=deadline,
            credit_info=str(body.get("credit_info", "")),
            tags=tags_list,
            status="active",
            approval_status="pending",
            publisher_type="user",
            publisher_name=user.real_name if user else "",
            publisher_id=uid,
            is_competition=False,
        )
        db.add(comp)
        await db.commit()
        await db.refresh(comp)
        return JSONResponse({"ok": True, "id": comp.id, "message": "活动已提交，等待审核"})


@router.get("/pending-activities")
async def api_pending_activities(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        comps = (
            await db.execute(
                select(Competition).where(Competition.approval_status == "pending")
                .order_by(Competition.created_at.desc())
            )
        ).scalars().all()
        return JSONResponse({"activities": [
            {"id": c.id, "title": c.title, "category": c.category, "level": c.level,
             "description": (c.description or "")[:200], "publisher_name": c.publisher_name,
             "registration_deadline": _fmt_date(c.registration_deadline)}
            for c in comps
        ]})


@router.post("/competition/{comp_id}/approve")
async def api_competition_approve(request: Request, comp_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        comp = await db.get(Competition, comp_id)
        if not comp:
            return JSONResponse({"error": "not_found"}, 404)
        comp.approval_status = "approved"
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/competition/{comp_id}/reject")
async def api_competition_reject(request: Request, comp_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        comp = await db.get(Competition, comp_id)
        if not comp:
            return JSONResponse({"error": "not_found"}, 404)
        comp.approval_status = "rejected"
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/scrape/trigger")
async def api_scrape_trigger(request: Request):
    """手动触发爬虫（同步执行，返回 stats）"""
    uid = require_uid(request)
    from backend.services.scheduler import do_scrape

    try:
        stats = await do_scrape()
        return JSONResponse({"ok": True, "stats": stats})
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"爬取失败: {e}"})
