"""应用配置"""
import os

# BASE_DIR = 项目根目录（ai-camp/），跨子文件夹引用 data/ 和 .env
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_BASE_DIR)  # 上一级 = ai-camp/

# 加载 .env 文件（在根目录）
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'data', 'app.db')}"

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

APP_NAME = "镜·界·联"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "认识自己 · 走向世界 · 与他人共同创造"

# ══════════════════════════════════════════════════════
#  LLM 配置
# ══════════════════════════════════════════════════════

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = os.environ.get("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

# LLM 是否可用（填了任一 key 才启用）
LLM_ENABLED = bool(
    (DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "sk-your-deepseek-api-key-here")
    or (ZHIPU_API_KEY and ZHIPU_API_KEY != "your-zhipu-api-key-here")
)
