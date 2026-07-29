"""应用配置"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'data', 'app.db')}"

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

APP_NAME = "AI人生镜像"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "基于数字人格的人生模拟与成长决策系统"

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
