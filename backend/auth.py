"""认证中间件 — 强制登录（数据铁律：所有 /api 必须按真实用户隔离）"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# 免登录前缀（注册/登录本身）
PUBLIC_API_PREFIXES = ("/api/auth/",)


class AuthRequiredMiddleware(BaseHTTPMiddleware):
    """除 /api/auth/* 外，所有 /api 请求必须已登录，否则 401 JSON。

    注意：Starlette 的 add_middleware 后加者最外层，SessionMiddleware 必须
    加在 AuthRequiredMiddleware 之后（更外层），否则 dispatch 里读不到 session。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and not path.startswith(PUBLIC_API_PREFIXES):
            if not request.session.get("user"):
                return JSONResponse(
                    {"error": "not_logged_in", "detail": "请先登录"}, status_code=401
                )
        return await call_next(request)


def require_uid(request: Request) -> int:
    """路由内获取当前登录用户 id（中间件已保证 session 存在）"""
    return int(request.session["user"]["id"])
