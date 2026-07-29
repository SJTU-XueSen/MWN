"""法律页面路由：用户协议、隐私政策、免责声明"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from templating import render

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/terms")
async def terms_page(request: Request):
    return HTMLResponse(render("legal/terms.html", {
        "request": request,
        "user": request.session.get("user"),
    }))


@router.get("/privacy")
async def privacy_page(request: Request):
    return HTMLResponse(render("legal/privacy.html", {
        "request": request,
        "user": request.session.get("user"),
    }))


@router.get("/disclaimer")
async def disclaimer_page(request: Request):
    return HTMLResponse(render("legal/disclaimer.html", {
        "request": request,
        "user": request.session.get("user"),
    }))
