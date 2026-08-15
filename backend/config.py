"""全局配置 — 从项目根目录 .env 读取"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # ai-camp/
load_dotenv(BASE_DIR / ".env")

APP_NAME = "镜·界·联"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "认识自己 · 走向世界 · 与他人共同创造"

# 数据目录
DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'app.db'}"
CHROMA_DIR = BASE_DIR / "data" / "chroma"
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
DIST_DIR = BASE_DIR / "web" / "dist"

SECRET_KEY = os.getenv("SECRET_KEY", "mwn-dev-secret-key-change-me")

# AI 提供商（.env 中配置）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

# Qwen（阿里云百炼 compatible-mode, OpenAI 兼容）
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3.6-flash")


def _is_valid_key(key: str) -> bool:
    """排除占位符 key"""
    return bool(key) and not key.startswith(("sk-a1b2c3", "your-", "xxx", "sk-xxx"))


LLM_ENABLED = _is_valid_key(DEEPSEEK_API_KEY) or _is_valid_key(ZHIPU_API_KEY)
