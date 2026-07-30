"""全局模板引擎 — 使用 Jinja2 直连，绕过 Starlette 的 Jinja2Templates"""
import os
from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=True,
)


def render(name: str, context: dict) -> str:
    """渲染模板，返回 HTML 字符串"""
    template = _env.get_template(name)
    return template.render(**context)
