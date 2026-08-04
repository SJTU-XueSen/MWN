# 镜·界·联 — 青年成长生态系统

> 认识自己 · 走向世界 · 与他人共同创造

**单一后端 + 单端口**：一个 FastAPI 服务同时承载全部 API 与前端构建产物，访问 `http://127.0.0.1:5000` 即可使用整个网站。

---

## 架构

```
浏览器 (:5000 单端口)
    │
    ▼
┌──────────────────────────────────────────────┐
│  backend/  FastAPI 单体后端                    │
│  · /api/auth      注册/登录/登出（JSON + 会话） │
│  · /api/mirror/*  记录/事件/人格/模拟/目标/报告 │
│  · /api/*         活动/组队/任务/工作台/聊天    │
│  · /api/activities SJTU 爬虫（6 站点 + AI 筛选）│
│  · /api/ai-search  DeepSeek 语义活动检索        │
│  · /uploads       团队作品/聊天图片             │
│  · /assets + SPA   前端构建产物直接伺服         │
└──────┬──────────────────────┬─────────────────┘
       ▼                      ▼
┌───────────────┐   ┌──────────────────────────┐
│ SQLite        │   │ ChromaDB                 │
│ data/app.db   │   │ data/chroma/             │
│ 全部业务表     │   │ 语义记忆（user_id 过滤）  │
└───────────────┘   └──────────────────────────┘
```

## 快速启动

```bash
# 1. 配置 API Key（.env：DEEPSEEK_API_KEY / ZHIPU_API_KEY）
# 2. 构建前端（首次或前端改动后）
cd web && npm install && npm run build && cd ..

# 3. 启动后端（单 worker——调度器/Chroma/STT 均为进程内单例）
.venv/Scripts/python.exe -m uvicorn backend.main:app --port 5000 --workers 1

# 4. 访问
open http://127.0.0.1:5000
```

开发模式：`cd web && npm run dev`（:5173，代理 /api → :5000）。

## 功能清单

| 模块 | 说明 |
|------|------|
| 🪞 日常记录 | AI 分析（DeepSeek）+ 生命记忆提炼 → ChromaDB |
| 🗺 人生事件 | 11 种类型，AI 情绪/兴趣/人格影响分析 |
| 🪞 数字人格 | 五维画像 + 多版本追踪 + 诚实置信度 |
| 🔮 人生模拟 | 3 条锚定真实记忆的未来路径 + 未来对话 + 人生体验 |
| 🔭 推演人生 | 无干预式逐年推演 |
| 📊 成长报告 | 周期内真实数据总结 |
| 🌏 活动大厅 | 活动发布/审核/组队 + SJTU 6 站点爬虫 + AI 检索 |
| 🤝 工作台 | AI 任务拆解/认领/审核/协作文档/信誉分 |
| 💬 团队聊天 | 组内/团队频道 + DeepSeek 协作助手 |
| 🎤 语音输入 | FunASR 语音转文字（可选，内置热词） |

## 数据与隐私

- 所有 AI 输出**锚定于用户真实数据**（SQLite + ChromaDB），绝不虚构
- 所有查询强制 **user_id 过滤**，未登录一律 401
- 数据可导出（设置页）、可注销（级联删除 SQLite + 向量）
- 密码 bcrypt 哈希；会话 SameSite=Lax 7 天

## 目录结构

```
ai-camp/
├── backend/           # FastAPI 单体后端
│   ├── main.py        # 入口（中间件/静态/SPA fallback/调度器）
│   ├── config.py      # 配置（.env）
│   ├── auth.py        # 登录中间件（强制登录）
│   ├── database/      # SQLAlchemy async 模型与引擎
│   ├── routers/       # auth/mirror/hub/activities/teams/tasks/work/chat/credits
│   └── services/      # LLM/记忆/人格/模拟/爬虫/AI筛选/AI检索/调度/STT
├── web/               # React 18 + Vite + TS 前端
└── data/              # SQLite + ChromaDB + uploads（自动创建）
```
