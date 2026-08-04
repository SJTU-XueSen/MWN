"""活动平台 — 工作台聚合 + 协作文档 + 作品提交 + AI 建议"""
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from backend.auth import require_uid
from backend.config import UPLOAD_DIR
from backend.database.database import AsyncSessionLocal
from backend.database.models import (
    Competition,
    DocVersion,
    TaskAssignment,
    TaskProgress,
    Team,
    TeamDocument,
    TeamMember,
    TeamTask,
    User,
    WorkSubmission,
)

router = APIRouter(prefix="/api", tags=["work"])


async def _user_team(db, user_id: int):
    return (
        await db.execute(
            select(TeamMember).where(TeamMember.user_id == user_id).limit(1)
        )
    ).scalar_one_or_none()


@router.get("/work/data")
async def api_work_data(request: Request):
    """工作台聚合数据"""
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        tm = await _user_team(db, uid)
        if not tm:
            return JSONResponse({"has_team": False})

        team = await db.get(Team, tm.team_id)
        comp = await db.get(Competition, team.competition_id) if team.competition_id else None

        tasks = (
            await db.execute(
                select(TeamTask).where(TeamTask.team_id == team.id).order_by(TeamTask.created_at.desc())
            )
        ).scalars().all()
        members = (
            await db.execute(select(TeamMember).where(TeamMember.team_id == team.id))
        ).scalars().all()
        members_out = []
        for m in members:
            user = await db.get(User, m.user_id)
            if user:
                members_out.append({"user_id": m.user_id, "role": m.role, "name": user.real_name or user.username})

        return JSONResponse({
            "has_team": True,
            "my_role": tm.role,
            "is_working_phase": team.status in ("full", "closed"),
            "team": {"id": team.id, "name": team.name, "status": team.status,
                     "slogan": team.slogan, "description": team.description},
            "competition": {
                "id": comp.id, "title": comp.title,
                "registration_deadline": comp.registration_deadline.strftime("%Y-%m-%d") if comp.registration_deadline else "",
            } if comp else None,
            "tasks": [
                {"id": t.id, "title": t.title, "description": t.description, "status": t.status,
                 "deadline": (t.deadline.strftime("%Y-%m-%d") if t.deadline else "") or ""}
                for t in tasks
            ],
            "members": members_out,
        })


@router.get("/team/doc/{doc_id}")
async def api_team_doc(request: Request, doc_id: int):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        doc = await db.get(TeamDocument, doc_id)
        if not doc:
            return JSONResponse({"error": "not_found"}, 404)
        submissions = (
            await db.execute(
                select(WorkSubmission).where(WorkSubmission.document_id == doc.id)
                .order_by(WorkSubmission.created_at.desc())
            )
        ).scalars().all()
        subs_out = []
        for s in submissions:
            user = await db.get(User, s.user_id)
            subs_out.append({
                "id": s.id,
                "user_name": user.real_name if user else "",
                "file_path": s.file_path, "file_name": s.file_name,
                "file_url": s.file_path, "description": s.description,
                "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
            })
        # merged：简单拼接成员提交内容
        merged = ""
        if subs_out:
            parts = [f"<p><b>{s['user_name']}</b>：{s['description'] or '提交了作品'}</p>" for s in subs_out]
            merged = "".join(parts)
        return JSONResponse({
            "doc": {"id": doc.id, "title": doc.title, "content": doc.content, "task_type": doc.task_type},
            "submissions": subs_out,
            "merged": merged,
        })


@router.post("/team/doc/{doc_id}/merge")
async def api_team_doc_merge(request: Request, doc_id: int):
    """AI 融合提交到文档（LLM 优先，失败返回当前内容）"""
    import asyncio

    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        doc = await db.get(TeamDocument, doc_id)
        if not doc:
            return JSONResponse({"error": "not_found"}, 404)
        submissions = (
            await db.execute(
                select(WorkSubmission).where(WorkSubmission.document_id == doc.id)
                .order_by(WorkSubmission.created_at.asc())
            )
        ).scalars().all()
        if not submissions:
            return JSONResponse({"ok": True, "merged": doc.content or "<p>暂无成员提交，等待协作...</p>"})

        parts = []
        for s in submissions:
            user = await db.get(User, s.user_id)
            parts.append(f"{user.real_name if user else '成员'}：{s.description or ''}（附件：{s.file_name or '无'}）")

        merged_html = ""
        from backend.config import ZHIPU_API_KEY

        if ZHIPU_API_KEY:
            def _do_merge():
                from backend.services.ai_filter import _llm_api_request

                prompt = f"""你是团队文档编辑。将以下成员的提交融合为一份完整的团队文档（HTML 格式，简洁清晰）。

任务主题：{doc.title}
成员提交：
{chr(10).join(parts)}

请输出 HTML（<h3>小节标题</h3><p>内容</p> 结构），整合重复内容，保持信息完整。只返回 HTML。"""
                return _llm_api_request([{"role": "user", "content": prompt}], max_tokens=3000, temperature=0.5, timeout=60)

            try:
                merged_html = await asyncio.to_thread(_do_merge)
            except Exception:
                merged_html = ""

        if not merged_html:
            merged_html = "".join(f"<p><b>{p.split('：')[0]}</b>：{p.split('：', 1)[1] if '：' in p else ''}</p>" for p in parts)

        # 版本快照
        version_num = (
            await db.execute(
                select(func.count()).select_from(DocVersion).where(DocVersion.document_id == doc.id)
            )
        ).scalar() or 0
        db.add(DocVersion(
            document_id=doc.id, team_id=doc.team_id, user_id=uid,
            content=merged_html, summary=f"第{version_num + 1}次合并", version_num=version_num + 1,
        ))
        doc.content = merged_html
        await db.commit()
        return JSONResponse({"ok": True, "merged": merged_html})


@router.post("/team/upload-work")
async def api_team_upload_work(
    request: Request,
    doc_id: int = Form(...),
    description: str = Form(""),
    file: UploadFile = File(None),
):
    """提交作品（multipart）"""
    uid = require_uid(request)
    file_path = ""
    file_name = ""
    if file and file.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(file.filename)[1] or ""
        fname = f"{uuid.uuid4().hex}{ext}"
        content = await file.read()
        with open(UPLOAD_DIR / fname, "wb") as f:
            f.write(content)
        file_path = f"/uploads/{fname}"
        file_name = file.filename

    async with AsyncSessionLocal() as db:
        doc = await db.get(TeamDocument, int(doc_id))
        if not doc:
            return JSONResponse({"error": "not_found"}, 404)
        sub = WorkSubmission(
            document_id=doc.id, team_id=doc.team_id, user_id=uid,
            file_path=file_path, file_name=file_name, description=description,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)

        # 更新进度 = 已提交人数 / 成员数 * 100
        member_count = (
            await db.execute(select(func.count()).select_from(TeamMember).where(TeamMember.team_id == doc.team_id))
        ).scalar() or 1
        submitted = (
            await db.execute(
                select(func.count()).select_from(WorkSubmission).where(
                    WorkSubmission.document_id == doc.id,
                    WorkSubmission.user_id.in_(
                        select(TeamMember.user_id).where(TeamMember.team_id == doc.team_id)
                    ),
                )
            )
        ).scalar() or 0
        progress = (
            await db.execute(select(TaskProgress).where(TaskProgress.team_id == doc.team_id).limit(1))
        ).scalar_one_or_none()
        if not progress:
            progress = TaskProgress(team_id=doc.team_id)
            db.add(progress)
        progress.progress_pct = round(min(submitted / max(member_count, 1), 1.0) * 100, 1)
        progress.completed_tasks = submitted
        await db.commit()
        return JSONResponse({"ok": True, "submission_id": sub.id})


@router.post("/team/ai-suggestions")
async def api_team_ai_suggestions(request: Request):
    """根据用户已认领任务，搜索相关网络资料（AI 建议）"""
    import asyncio

    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        assignment = (
            await db.execute(
                select(TaskAssignment).where(
                    TaskAssignment.user_id == uid, TaskAssignment.status == "approved"
                ).limit(1)
            )
        ).scalar_one_or_none()
        if not assignment:
            return JSONResponse({
                "suggestions": "你还没有认领任何任务，请先加入任务后再搜索相关资料。",
                "web_resources": [],
            })
        task = await db.get(TeamTask, assignment.task_id)
        query = f"{task.title} {task.description}"

        def _search():
            from backend.services.ai_filter import web_search

            return web_search(query, max_results=8)

        try:
            results = await asyncio.to_thread(_search)
        except Exception:
            results = []
        suggestions = "已根据你认领的任务「{0}」搜索到相关资源：".format(task.title)
        return JSONResponse({"suggestions": suggestions, "web_resources": results})
