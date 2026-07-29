"""全局模板引擎 — 使用 Jinja2 直连，绕过 Starlette 的 Jinja2Templates"""
import os
from jinja2 import Environment, FileSystemLoader

from config import BASE_DIR

_env = Environment(
    loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")),
    autoescape=True,
)


def render(name: str, context: dict) -> str:
    """渲染模板，返回 HTML 字符串"""
    template = _env.get_template(name)
    return template.render(**context)
