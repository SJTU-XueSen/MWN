"""活动平台 — 任务拆解/发布/申请/审核/退出/取消 + 团队分析/进度"""
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from backend.auth import require_uid
from backend.database.database import AsyncSessionLocal
from backend.database.models import (
    Competition,
    CreditLog,
    TaskAssignment,
    TaskProgress,
    Team,
    TeamDocument,
    TeamMember,
    TeamTask,
    User,
)
from backend.services.ai_filter import breakdown_task, calc_match_score

router = APIRouter(prefix="/api", tags=["tasks"])


async def _user_team(db, user_id: int):
    """获取用户当前所在战队"""
    return (
        await db.execute(
            select(TeamMember).where(TeamMember.user_id == user_id).limit(1)
        )
    ).scalar_one_or_none()


async def _check_task_full(db, task: TeamTask):
    """所有角色招满 → task.status='full'"""
    roles = task.required_roles or []
    for role in roles:
        approved = (
            await db.execute(
                select(func.count()).select_from(TaskAssignment).where(
                    TaskAssignment.task_id == task.id,
                    TaskAssignment.role == role.get("role", ""),
                    TaskAssignment.status == "approved",
                )
            )
        ).scalar() or 0
        if approved < int(role.get("count", 1)):
            return
    task.status = "full"
    await db.commit()


@router.post("/breakdown-task")
async def api_breakdown_task(request: Request):
    """AI 拆解任务为子角色（LLM 优先，规则回退）"""
    import asyncio

    uid = require_uid(request)
    body = await request.json()
    title = str(body.get("title", ""))
    description = str(body.get("description", ""))
    async with AsyncSessionLocal() as db:
        tm = await _user_team(db, uid)
        member_skills: list[str] = []
        if tm:
            members = (
                await db.execute(select(TeamMember).where(TeamMember.team_id == tm.team_id))
            ).scalars().all()
            for m in members:
                user = await db.get(User, m.user_id)
                if user:
                    member_skills.extend(user.skill_tags or [])
        roles = await asyncio.to_thread(breakdown_task, title, description, member_skills)
        return JSONResponse({"roles": roles})


@router.post("/create-task")
async def api_create_task(request: Request):
    """队长发布任务"""
    uid = require_uid(request)
    body = await request.json()
    title = str(body.get("title", "")).strip()
    if not title:
        return JSONResponse({"error": "任务名称不能为空"}, 400)
    roles = body.get("roles", []) or []

    async with AsyncSessionLocal() as db:
        tm = await _user_team(db, uid)
        if not tm:
            return JSONResponse({"error": "未找到战队"}, 404)
        if tm.role != "leader":
            return JSONResponse({"error": "只有队长才能发布任务"}, 403)
        team = await db.get(Team, tm.team_id)

        deadline = None
        if body.get("deadline"):
            try:
                deadline = datetime.fromisoformat(body["deadline"])
            except Exception:
                pass
        task = TeamTask(
            team_id=team.id,
            title=title,
            description=str(body.get("description", "")),
            required_roles=roles,
            deadline=deadline,
            status="recruiting",
            created_by=uid,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return JSONResponse({"ok": True, "task_id": task.id})


@router.post("/task/{task_id}/apply")
async def api_task_apply(request: Request, task_id: int):
    uid = require_uid(request)
    body = await request.json()
    role_name = str(body.get("role", ""))
    if not role_name:
        return JSONResponse({"error": "请选择角色"}, 400)

    async with AsyncSessionLocal() as db:
        task = await db.get(TeamTask, task_id)
        if not task:
            return JSONResponse({"error": "not_found"}, 404)
        # 重复申请
        existing = (
            await db.execute(
                select(TaskAssignment).where(TaskAssignment.task_id == task.id, TaskAssignment.user_id == uid)
            )
        ).scalar_one_or_none()
        if existing:
            return JSONResponse({"error": "你已申请该角色"}, 400)
        # 同队已有 approved 且进度 <100% 的任务
        tm = await _user_team(db, uid)
        if tm:
            approved_other = (
                await db.execute(
                    select(TaskAssignment).join(TeamTask).where(
                        TaskAssignment.user_id == uid,
                        TaskAssignment.status == "approved",
                        TeamTask.team_id == tm.team_id,
                    ).limit(1)
                )
            ).scalar_one_or_none()
            if approved_other:
                return JSONResponse({"error": "你已认领了其他任务，请先完成任务"}, 400)

        role_info = next((r for r in (task.required_roles or []) if r.get("role") == role_name), {})
        user = await db.get(User, uid)
        if tm and tm.role == "leader":
            status = "approved"
            match_score = 1.0
        else:
            status = "pending"
            match_score = calc_match_score(user.skill_tags or [], role_info, user.credit_score or 100)

        assignment = TaskAssignment(
            task_id=task.id, user_id=uid, role=role_name,
            status=status, match_score=match_score,
        )
        db.add(assignment)
        await db.commit()
        if status == "approved":
            await _check_task_full(db, task)
        return JSONResponse({"ok": True, "status": status})


@router.post("/task/{task_id}/review")
async def api_task_review(request: Request, task_id: int):
    """审核申请（仅任务创建者）"""
    uid = require_uid(request)
    body = await request.json()
    assignment_id = int(body.get("assignment_id", 0))
    action = str(body.get("action", ""))

    async with AsyncSessionLocal() as db:
        task = await db.get(TeamTask, task_id)
        if not task:
            return JSONResponse({"error": "not_found"}, 404)
        if task.created_by != uid:
            return JSONResponse({"error": "只有任务创建者才能审核"}, 403)
        assignment = await db.get(TaskAssignment, assignment_id)
        if not assignment or assignment.task_id != task.id:
            return JSONResponse({"error": "not_found"}, 404)
        assignment.status = "approved" if action == "approve" else "rejected"
        assignment.resolved_at = datetime.utcnow()
        await db.commit()
        if assignment.status == "approved":
            await _check_task_full(db, task)
        return JSONResponse({"ok": True})


@router.post("/task/{task_id}/leave")
async def api_task_leave(request: Request, task_id: int):
    """退出任务（队长 -35，成员 -30）"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        task = await db.get(TeamTask, task_id)
        if not task:
            return JSONResponse({"error": "not_found"}, 404)
        assignment = (
            await db.execute(
                select(TaskAssignment).where(TaskAssignment.task_id == task.id, TaskAssignment.user_id == uid)
            )
        ).scalar_one_or_none()
        if not assignment or assignment.status not in ("pending", "approved"):
            return JSONResponse({"error": "当前状态无法退出"}, 400)

        is_leader = assignment.role == "leader" or (
            (await db.execute(select(TeamMember).where(TeamMember.user_id == uid, TeamMember.role == "leader"))).scalar_one_or_none() is not None
        )
        # 队长退出 → 该任务所有申请清空，任务回退招募中
        if is_leader:
            others = (
                await db.execute(select(TaskAssignment).where(TaskAssignment.task_id == task.id))
            ).scalars().all()
            for a in others:
                await db.delete(a)
            task.status = "recruiting"
            amount = 35
        else:
            await db.delete(assignment)
            amount = 30
        user = await db.get(User, uid)
        user.credit_score = max(0.0, (user.credit_score or 100) - amount)
        db.add(CreditLog(user_id=uid, change=-amount, reason="中途退出任务", detail=task.title))
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/task/{task_id}/cancel")
async def api_task_cancel(request: Request, task_id: int):
    """队长取消任务（级联删除）"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        task = await db.get(TeamTask, task_id)
        if not task:
            return JSONResponse({"error": "not_found"}, 404)
        if task.created_by != uid:
            return JSONResponse({"error": "只有队长才能取消任务"}, 403)
        assignments = (await db.execute(select(TaskAssignment).where(TaskAssignment.task_id == task.id))).scalars().all()
        for a in assignments:
            await db.delete(a)
        docs = (await db.execute(select(TeamDocument).where(TeamDocument.team_id == task.team_id))).scalars().all()
        for d in docs:
            await db.delete(d)
        await db.delete(task)
        await db.commit()
        return JSONResponse({"ok": True})


@router.post("/task/{task_id}/mark-incomplete/{user_id}")
async def api_task_mark_incomplete(request: Request, task_id: int, user_id: int):
    """队长标记成员未完成（扣 20 分）"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        task = await db.get(TeamTask, task_id)
        if not task:
            return JSONResponse({"error": "not_found"}, 404)
        tm = (
            await db.execute(
                select(TeamMember).where(TeamMember.user_id == uid, TeamMember.role == "leader")
            )
        ).scalar_one_or_none()
        if not tm:
            return JSONResponse({"error": "只有队长才能标记"}, 403)
        assignment = (
            await db.execute(
                select(TaskAssignment).where(TaskAssignment.task_id == task.id, TaskAssignment.user_id == user_id)
            )
        ).scalar_one_or_none()
        if not assignment or assignment.status != "approved":
            return JSONResponse({"error": "该用户未认领此任务"}, 400)
        target = await db.get(User, user_id)
        target.credit_score = max(0.0, (target.credit_score or 100) - 20)
        db.add(CreditLog(user_id=user_id, change=-20, reason="任务未完成", detail=task.title))
        await db.commit()
        return JSONResponse({"ok": True, "msg": f"已标记 {target.real_name or target.username} 未完成，扣除 20 信誉分"})


@router.get("/task/{task_id}/data")
async def api_task_data(request: Request, task_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        task = await db.get(TeamTask, task_id)
        if not task:
            return JSONResponse({"error": "not_found"}, 404)

        roles_out = []
        for role in (task.required_roles or []):
            rname = role.get("role", "")
            needed = int(role.get("count", 1))
            approved = (
                await db.execute(
                    select(func.count()).select_from(TaskAssignment).where(
                        TaskAssignment.task_id == task.id,
                        TaskAssignment.role == rname,
                        TaskAssignment.status == "approved",
                    )
                )
            ).scalar() or 0
            applied = (
                await db.execute(
                    select(func.count()).select_from(TaskAssignment).where(
                        TaskAssignment.task_id == task.id,
                        TaskAssignment.role == rname,
                        TaskAssignment.status != "rejected",
                    )
                )
            ).scalar() or 0
            roles_out.append({
                "name": rname, "needed": needed, "approved": approved, "applied": applied,
                "skills": role.get("skills", []), "hours": role.get("estimated_hours", 0),
            })

        applicants = []
        assignments = (
            await db.execute(
                select(TaskAssignment).where(TaskAssignment.task_id == task.id)
                .order_by(TaskAssignment.applied_at.asc())
            )
        ).scalars().all()
        for a in assignments:
            user = await db.get(User, a.user_id)
            if user:
                applicants.append({
                    "id": a.id, "user_id": a.user_id,
                    "user_name": user.real_name or user.username,
                    "user_skills": user.skill_tags or [],
                    "role": a.role, "status": a.status, "match_score": a.match_score,
                })

        return JSONResponse({
            "task": {
                "id": task.id, "title": task.title, "description": task.description,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "status": task.status,
            },
            "roles": roles_out,
            "applicants": applicants,
        })


@router.post("/team/analyze-tasks")
async def api_team_analyze_tasks(request: Request):
    """分析团队任务 → 判断是否需要协作文档（LLM 优先）"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        tm = await _user_team(db, uid)
        if not tm:
            return JSONResponse({"error": "未找到战队"}, 404)
        team = await db.get(Team, tm.team_id)
        tasks = (
            await db.execute(
                select(TeamTask).where(TeamTask.team_id == team.id, TeamTask.status == "full")
            )
        ).scalars().all()
        if not tasks:
            return JSONResponse({"needs_doc": False, "message": "暂无任务"})

        # 关键词规则判断任务类型
        task_text = " ".join([f"{t.title} {t.description}" for t in tasks])
        task_type = "document"
        creative_keywords = ["海报", "宣传", "设计", "美工", "文创", "logo", "视频", "剪辑", "拍摄"]
        document_keywords = ["策划", "方案", "文档", "报告", "文案", "申报书", "材料"]
        if any(kw in task_text for kw in creative_keywords):
            task_type = "poster"
        elif any(kw in task_text for kw in document_keywords):
            task_type = "document"

        doc = TeamDocument(
            team_id=team.id,
            title=f"协作产出（{task_type}）",
            content="",
            task_type=task_type,
            ai_suggestions="",
            web_resources=[],
            created_by=uid,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return JSONResponse({
            "needs_doc": True, "doc_id": doc.id, "doc_title": doc.title, "task_type": task_type,
        })


@router.get("/team/progress")
async def api_team_progress(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        tm = await _user_team(db, uid)
        if not tm:
            return JSONResponse({"error": "未找到战队"}, 404)
        progress = (
            await db.execute(
                select(TaskProgress).where(TaskProgress.team_id == tm.team_id).limit(1)
            )
        ).scalar_one_or_none()
        if not progress:
            progress = TaskProgress(team_id=tm.team_id, total_tasks=0, completed_tasks=0, progress_pct=0.0, ai_comment="")
            db.add(progress)
            await db.commit()
        return JSONResponse({
            "progress_pct": progress.progress_pct or 0.0,
            "total_tasks": progress.total_tasks or 0,
            "completed_tasks": progress.completed_tasks or 0,
            "ai_comment": progress.ai_comment or "",
        })
