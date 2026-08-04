"""活动平台 — 信誉分记录"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from backend.auth import require_uid
from backend.database.database import AsyncSessionLocal
from backend.database.models import CreditLog, User

router = APIRouter(prefix="/api", tags=["credits"])


@router.get("/credit/log")
async def api_credit_log(request: Request):
    uid = require_uid(request)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        logs = (
            await db.execute(
                select(CreditLog).where(CreditLog.user_id == uid).order_by(CreditLog.created_at.desc()).limit(20)
            )
        ).scalars().all()
        return JSONResponse({
            "score": int(user.credit_score or 100) if user else 100,
            "logs": [
                {"change": l.change, "reason": l.reason, "detail": l.detail,
                 "time": l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else ""}
                for l in logs
            ],
        })
