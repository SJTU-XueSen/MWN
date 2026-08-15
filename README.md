# 镜·界·联 · 智能体（Agent 版）

> 认识自己 · 走向世界 · 与他人共同创造
>
> 原"三合一"主站（活动大厅/工作台/团队聊天/爬虫）已废弃，全部能力收敛到**单智能体 + 看板**。

## 架构（单端口）

```
浏览器 (:5021 单端口, 生产伺服 agent_web/dist)
    │
    ▼
┌──────────────────────────────────────────────┐
│  backend/agent_app.py  智能体后端              │
│  · /api/auth       注册/登录/登出（独立闭环）   │
│  · /api/agent/stream   对话 SSE 流             │
│  · /api/agent/dashboard 看板（原主站 dashboard）│
│  · /api/agent/*    记录/历史/资料/隐私          │
└──────┬────────────────────────┬───────────────┘
       ▼                        ▼
┌───────────────┐      ┌──────────────────────┐
│ SQLite        │      │ ChromaDB 语义记忆     │
│ data/app.db   │      │ data/chroma/         │
└───────────────┘      └──────────────────────┘
       ▲
┌──────────────────────────────────────────────┐
│  LangGraph 引擎（思考 → 工具并行 → 回答）      │
│  20 个工具（14 检索 + 6 写入）                │
└──────────────────────────────────────────────┘
```

## 快速开始

```bash
# 1. 配置 .env（QWEN_* = agent 主通道 LLM）
# 2. 构建前端（首次或前端改动后）
cd agent_web && npm install && npm run build && cd ..

# 3. 启动（单进程单端口, uvicorn 必须 --workers 1）
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/start_all.py        # → http://localhost:5021

# 开发模式: cd agent_web && npm run dev（:5174, 代理 /api → :5021）
```

## 功能

| 模块 | 说明 |
|------|------|
| 💬 智能体对话 | SSE 流式（思维链/工具卡片/打字机），单全能"镜界导师" |
| 📝 全操作对话化 | 写日记/记事件/存感悟/建目标/刷画像/跑模拟/未来对话，说话即完成 |
| 🔍 检索工具 | 记忆 RAG/人格/事件/日记/目标/兴趣/未来路径/报告/证据链/模拟 |
| 🌐 联网 | web_search（Wikipedia + DuckDuckGo 背景摘要） |
| 🪞 看板 | 原主站 dashboard 全量：当前的我/可能的我/我与世界/我和他人/我要走向哪里 |
| 🗂 记录面板 | 日记/事件/目标 搜索·详情·删除·标注完成 |
| 👤 用户中心 | 主题/资料/改密/记忆个性化/数据删除/注销（级联 SQLite+Chroma） |
| 🪞 今日镜像 | 登录自动推送 7 天观察 + 每日一问 |

## LLM 配置（.env）

| 变量 | 说明 |
|------|------|
| `QWEN_API_KEY` / `QWEN_BASE_URL` / `QWEN_MODEL` | agent 主通道（OpenAI 兼容; 默认阿里云百炼） |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` | 辅助通道（兜底/摘要; 支持本地 LM Studio） |

## 数据与隐私

- 所有 AI 输出**锚定真实数据**，工具查不到就如实说，不编造
- 所有查询强制 **user_id 过滤**，未登录 401，越权返回 not_found
- 数据可删除（按类/单条/全部）、账户可注销（SQLite + 向量级联）
- 密码 bcrypt；会话 SameSite=Lax 7 天

## 已知限制（原主站功能废弃清单）

- 活动大厅/组队/战队/工作台/团队聊天：**接口随主站移除**；`activity_search`/`team_context`/`create_task` 工具保留但数据源为空（优雅降级）
- SJTU 6 站点爬虫与调度器：**已随主站移除**（赛事官网爬取从未实现过）
- 语音输入（FunASR）、数据导出 JSON、人生体验/推演人生：未迁移
