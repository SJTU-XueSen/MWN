"""活动平台 — 战队创建/加入/关闭/解散 + 潜在队友推荐"""
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from backend.auth import require_uid
from backend.database.database import AsyncSessionLocal
from backend.database.models import (
    Competition,
    CreditLog,
    DocVersion,
    TaskAssignment,
    TaskProgress,
    Team,
    TeamChatMessage,
    TeamDocument,
    TeamMember,
    TeamTask,
    User,
    WorkSubmission,
)

router = APIRouter(prefix="/api", tags=["teams"])


def _deduct_credit(db, user: User, amount: float, reason: str, detail: str = ""):
    """扣信誉分（不低于 0），写 CreditLog"""
    user.credit_score = max(0.0, (user.credit_score or 100) - amount)
    db.add(CreditLog(user_id=user.id, change=-amount, reason=reason, detail=detail))


@router.post("/team/create")
async def api_team_create(request: Request):
    uid = require_uid(request)
    body = await request.json()
    competition_id = body.get("competition_id")
    team_name = str(body.get("team_name", "")).strip()
    if not competition_id:
        return JSONResponse({"error": "缺少活动ID"}, 400)
    if not team_name:
        return JSONResponse({"error": "战队名称不能为空"}, 400)

    async with AsyncSessionLocal() as db:
        comp = await db.get(Competition, int(competition_id))
        if not comp:
            return JSONResponse({"error": "not_found"}, 404)
        if comp.status != "active":
            return JSONResponse({"error": "该活动已截止"}, 400)
        # 同一活动已有战队
        existing = (
            await db.execute(
                select(TeamMember).join(Team).where(
                    TeamMember.user_id == uid, Team.competition_id == comp.id
                ).limit(1)
            )
        ).scalar_one_or_none()
        if existing:
            return JSONResponse({"error": "你已在该活动中创建/加入战队"}, 400)

        team = Team(
            competition_id=comp.id,
            leader_id=uid,
            name=team_name,
            slogan=str(body.get("slogan", "")),
            description=str(body.get("description", "")),
            status="recruiting",
        )
        db.add(team)
        await db.commit()
        await db.refresh(team)
        db.add(TeamMember(team_id=team.id, user_id=uid, role="leader"))
        await db.commit()
        return JSONResponse({"ok": True, "id": team.id, "name": team.name})


@router.get("/teams/{team_id}")
async def api_team_detail(request: Request, team_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        team = await db.get(Team, team_id)
        if not team:
            return JSONResponse({"error": "not_found"}, 404)
        comp = await db.get(Competition, team.competition_id)
        members = (
            await db.execute(
                select(TeamMember).where(TeamMember.team_id == team.id)
            )
        ).scalars().all()
        members_out = []
        my_role = None
        for tm in members:
            user = await db.get(User, tm.user_id)
            if user is None:
                continue
            if tm.user_id == uid:
                my_role = tm.role
            members_out.append({
                "user_id": tm.user_id, "role": tm.role,
                "name": user.real_name or user.username,
                "skill_tags": user.skill_tags or [],
                "credit_score": int(user.credit_score or 100),
            })
        return JSONResponse({
            "id": team.id, "name": team.name, "slogan": team.slogan, "description": team.description,
            "status": team.status, "leader_id": team.leader_id,
            "competition": {
                "id": comp.id, "title": comp.title, "category": comp.category, "level": comp.level,
                "max_team_size": comp.max_team_size,
                "registration_deadline": comp.registration_deadline.strftime("%Y-%m-%d") if comp.registration_deadline else "",
                "credit_info": comp.credit_info,
            } if comp else None,
            "members": members_out,
            "my_role": my_role,
        })


@router.post("/teams/{team_id}/join")
async def api_team_join(request: Request, team_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        team = await db.get(Team, team_id)
        if not team:
            return JSONResponse({"error": "not_found"}, 404)
        if team.status != "recruiting":
            return JSONResponse({"error": "该战队已停止招募"}, 400)
        comp = await db.get(Competition, team.competition_id)
        # 同一活动内已有战队
        existing = (
            await db.execute(
                select(TeamMember).join(Team).where(
                    TeamMember.user_id == uid, Team.competition_id == comp.id
                ).limit(1)
            )
        ).scalar_one_or_none()
        if existing:
            return JSONResponse({"error": "你已在该活动中加入其他战队"}, 400)
        member_count = (
            await db.execute(select(func.count()).select_from(TeamMember).where(TeamMember.team_id == team.id))
        ).scalar() or 0
        if comp.max_team_size and member_count >= comp.max_team_size:
            return JSONResponse({"error": "该战队已满员"}, 400)

        db.add(TeamMember(team_id=team.id, user_id=uid, role="member"))
        if comp.max_team_size and member_count + 1 >= comp.max_team_size:
            team.status = "full"
        await db.commit()
        return JSONResponse({"ok": True, "message": "加入战队成功！"})


@router.get("/my-teams")
async def api_my_teams(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(TeamMember, Team, Competition)
                .join(Team, TeamMember.team_id == Team.id)
                .outerjoin(Competition, Team.competition_id == Competition.id)
                .where(TeamMember.user_id == uid)
            )
        ).all()
        teams_out = []
        for tm, team, comp in rows:
            member_count = (
                await db.execute(select(func.count()).select_from(TeamMember).where(TeamMember.team_id == team.id))
            ).scalar() or 0
            teams_out.append({
                "team_id": team.id, "team_name": team.name, "team_status": team.status,
                "role": tm.role,
                "competition_id": comp.id if comp else None,
                "competition_title": comp.title if comp else "",
                "member_count": member_count,
            })
        return JSONResponse({"teams": teams_out})


@router.post("/team/{team_id}/close")
async def api_team_close(request: Request, team_id: int):
    """队长关闭招募（进入工作阶段）"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        team = await db.get(Team, team_id)
        if not team:
            return JSONResponse({"error": "not_found"}, 404)
        if team.status not in ("recruiting", "full"):
            return JSONResponse({"error": "当前状态不允许关闭招募"}, 400)
        team.status = "closed"
        await db.commit()
        return JSONResponse({"ok": True, "message": "招募已关闭"})


@router.post("/team/disband")
async def api_team_disband(request: Request):
    """队长解散团队（级联删除，扣 50 分）"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        tm = (
            await db.execute(
                select(TeamMember).where(TeamMember.user_id == uid, TeamMember.role == "leader").limit(1)
            )
        ).scalar_one_or_none()
        if not tm:
            return JSONResponse({"error": "只有队长才能解散团队"}, 403)
        team = await db.get(Team, tm.team_id)
        team_id = team.id

        # 级联删除
        for model, fk in [
            (WorkSubmission, "team_id"), (TeamChatMessage, "team_id"),
            (TaskProgress, "team_id"), (DocVersion, "team_id"),
        ]:
            rows = (await db.execute(select(model).where(getattr(model, fk) == team_id))).scalars().all()
            for r in rows:
                await db.delete(r)
        docs = (await db.execute(select(TeamDocument).where(TeamDocument.team_id == team_id))).scalars().all()
        for doc in docs:
            await db.delete(doc)
        tasks = (await db.execute(select(TeamTask).where(TeamTask.team_id == team_id))).scalars().all()
        for task in tasks:
            assignments = (await db.execute(select(TaskAssignment).where(TaskAssignment.task_id == task.id))).scalars().all()
            for a in assignments:
                await db.delete(a)
            await db.delete(task)
        members = (await db.execute(select(TeamMember).where(TeamMember.team_id == team_id))).scalars().all()
        for m in members:
            await db.delete(m)
        await db.delete(team)

        user = await db.get(User, uid)
        _deduct_credit(db, user, 50, "解散团队", team.name)
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/team/{team_id}/invite")
async def api_team_invite(request: Request, team_id: int):
    """队长邀请用户加入战队 → 给对方发组队邀请通知"""
    uid = require_uid(request)
    body = await request.json()
    target_user_id = int(body.get("user_id", 0))
    if not target_user_id:
        return JSONResponse({"error": "缺少目标用户"}, 400)

    async with AsyncSessionLocal() as db:
        from backend.database.models import Notification

        team = await db.get(Team, team_id)
        if not team:
            return JSONResponse({"error": "not_found"}, 404)
        tm = (
            await db.execute(
                select(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == uid)
            )
        ).scalar_one_or_none()
        if not tm or tm.role != "leader":
            return JSONResponse({"error": "只有队长才能邀请成员"}, 403)
        if team.status not in ("recruiting", "full"):
            return JSONResponse({"error": "该战队当前不可邀请"}, 400)
        # 目标用户是否已在同活动战队
        comp = await db.get(Competition, team.competition_id)
        existing = (
            await db.execute(
                select(TeamMember).join(Team).where(
                    TeamMember.user_id == target_user_id, Team.competition_id == comp.id
                ).limit(1)
            )
        ).scalar_one_or_none()
        if existing:
            return JSONResponse({"error": "对方已在该活动中加入战队"}, 400)

        leader = await db.get(User, uid)
        db.add(Notification(
            user_id=target_user_id,
            title="组队邀请",
            message=f"{leader.real_name or leader.username} 邀请你加入战队「{team.name}」（活动：{comp.title}）",
            read=False,
            meta={"team_id": team.id, "competition_id": comp.id, "team_name": team.name},
        ))
        await db.commit()
        return JSONResponse({"ok": True, "message": "邀请已发送"})


@router.post("/notifications/{notif_id}/accept")
async def api_notification_accept(request: Request, notif_id: int):
    """接受组队邀请：加入战队 + 通知标记已读"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        from backend.database.models import Notification

        n = await db.get(Notification, notif_id)
        if not n or n.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        meta = n.meta or {}
        team_id = meta.get("team_id")
        if not team_id:
            return JSONResponse({"error": "该通知不可接受"}, 400)
        team = await db.get(Team, int(team_id))
        if not team:
            return JSONResponse({"error": "战队已不存在"}, 404)
        if team.status != "recruiting":
            return JSONResponse({"error": "该战队已停止招募"}, 400)
        comp = await db.get(Competition, team.competition_id)
        existing = (
            await db.execute(
                select(TeamMember).join(Team).where(
                    TeamMember.user_id == uid, Team.competition_id == comp.id
                ).limit(1)
            )
        ).scalar_one_or_none()
        if existing:
            return JSONResponse({"error": "你已在该活动中加入战队"}, 400)
        member_count = (
            await db.execute(select(func.count()).select_from(TeamMember).where(TeamMember.team_id == team.id))
        ).scalar() or 0
        if comp.max_team_size and member_count >= comp.max_team_size:
            return JSONResponse({"error": "该战队已满员"}, 400)

        db.add(TeamMember(team_id=team.id, user_id=uid, role="member"))
        if comp.max_team_size and member_count + 1 >= comp.max_team_size:
            team.status = "full"
        n.read = True
        await db.commit()
        return JSONResponse({"ok": True, "message": "已加入战队"})


@router.post("/notifications/{notif_id}/decline")
async def api_notification_decline(request: Request, notif_id: int):
    """拒绝组队邀请"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        from backend.database.models import Notification

        n = await db.get(Notification, notif_id)
        if not n or n.user_id != uid:
            return JSONResponse({"error": "not_found"}, 404)
        n.read = True
        await db.commit()
        return JSONResponse({"ok": True})


@router.get("/potential-friends")
async def api_potential_friends(request: Request):
    """按技能互补度推荐潜在队友（取前 8）"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        me = await db.get(User, uid)
        my_skills = set(str(s) for s in (me.skill_tags or []))
        others = (
            await db.execute(
                select(User).where(User.id != uid).order_by(User.credit_score.desc()).limit(50)
            )
        ).scalars().all()

        friends = []
        for other in others:
            other_skills = set(str(s) for s in (other.skill_tags or []))
            shared = list(my_skills & other_skills)[:5]
            complementary = list(other_skills - my_skills)[:5]
            if not other_skills:
                continue
            score = len(complementary) * 2 + len(shared)
            if score == 0:
                continue
            friends.append({
                "user_id": other.id,
                "real_name": other.real_name or other.username,
                "skill_tags": list(other_skills),
                "credit_score": int(other.credit_score or 100),
                "complementary_skills": complementary,
                "shared_skills": shared,
                "match_score": score,
            })
        friends.sort(key=lambda f: -f["match_score"])
        return JSONResponse({"friends": friends[:8]})


@router.post("/profile")
async def api_profile_update(request: Request):
    """更新技能标签（影响队友匹配）"""
    uid = require_uid(request)
    body = await request.json()
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        if not user:
            return JSONResponse({"error": "not_found"}, 404)
        if "skill_tags" in body:
            tags = body["skill_tags"]
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            user.skill_tags = tags
        if "avatar_url" in body:
            user.avatar_url = body["avatar_url"]
        await db.commit()
        return JSONResponse({"ok": True, "skill_tags": user.skill_tags})
