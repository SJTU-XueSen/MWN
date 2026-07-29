# 🪞 AI人生镜像 (AI Life Mirror)

> 基于数字人格的人生模拟与成长决策系统

AI人生镜像不是职业规划工具，也不是聊天机器人。它是一面**诚实的镜子**——通过记录你的日常经历、提炼数字人格、模拟未来路径、让你与未来的自己对话，帮助你更清晰地认识自己。

---

## 核心功能

### 🔵 阶段一：数据积累
- **日常记录** — 写日记，AI 自动分析情绪/兴趣/行为模式/专业知识
- **人生事件** — 记录重要里程碑（项目/比赛/决定/转折），时间线可视化
- **AI 成长报告** — 汇总一段时间的人生数据，生成结构化总结

### 🟣 阶段二：数字人格
- **五维人格画像** — 能力/兴趣/价值观/决策风格/行为模式，支持版本追踪
- **人生目标管理** — 设定目标（类型/周期/重要度），追踪进展

### 🟢 阶段三：未来镜像
- **人生模拟** — 基于真实人格生成 3 条差异化未来路径
- **未来自我对话** — 与 AI 生成的未来人格跨时空聊天
- **成长反馈** — 仪表盘持续追踪（连续记录天数/周度对比/AI洞察）

### 🔒 数据隐私
- **数据导出** — JSON 完整备份
- **账户删除** — 级联清理全部数据（SQLite + ChromaDB）

---

## 技术架构

| 层 | 技术 |
|---|------|
| 前端 | Jinja2 模板 + Tailwind CSS CDN + Font Awesome |
| 后端 | FastAPI + Uvicorn (async) |
| 数据库 | SQLite (aiosqlite) + ChromaDB (向量存储) |
| AI | DeepSeek / 智谱 GLM + Wikipedia/DuckDuckGo 联网搜索 |
| 认证 | bcrypt 密码哈希 + Starlette Session |

### 数据流

```
用户输入 → SQLite (结构化) + ChromaDB (语义向量)
                ↓
         LLM 分析 (DeepSeek/智谱)
                ↓
         LifeMemory + PersonaProfile
                ↓
         Simulation → FutureSelf → Chat
```

---

## 快速开始

### 1. 环境要求
- Python 3.11+
- pip

### 2. 安装

```bash
# 克隆项目
git clone <repo-url>
cd ai-camp

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置

```bash
cp .env.example .env
# 编辑 .env，填入 API Key（可选，不填则使用规则引擎）
```

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API（分析用） | 否 |
| `ZHIPU_API_KEY` | 智谱 GLM API（对话用，推荐） | 否 |
| `SECRET_KEY` | Session 加密密钥 | 否（开发默认值） |

### 4. 启动

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 5000
```

访问 http://localhost:5000

### 5. 首次使用

1. 注册账户
2. 写几条日常记录
3. 记录几个重要人生事件
4. 生成数字人格画像
5. 尝试人生模拟
6. 与未来的自己对话

---

## 项目结构

```
ai-camp/
├── main.py                  # FastAPI 入口
├── config.py                # 配置
├── templating.py            # Jinja2 渲染
├── requirements.txt         # 依赖
├── .env.example             # 环境变量模板
├── README.md
├── step/                    # 开发步骤文档（15步）
├── database/
│   ├── database.py          # 数据库连接
│   └── models.py            # 11 张表模型
├── services/
│   ├── auth_service.py      # 认证
│   ├── memory_service.py    # 日常记录分析
│   ├── event_service.py     # 事件管理 + AI分析
│   ├── report_service.py    # 成长报告生成
│   ├── persona_service.py   # 数字人格生成
│   ├── simulation_service.py # 人生模拟
│   ├── chat_service.py      # 未来对话
│   ├── dashboard_service.py # 仪表盘数据 + 成长洞察
│   ├── llm_service.py       # LLM 统一调用
│   ├── search_service.py    # 联网搜索
│   └── vector_store.py      # ChromaDB 操作
├── routers/
│   ├── auth.py              # 登录/注册/资料
│   ├── events.py            # 日常记录 + 人生事件
│   ├── reports.py           # 成长报告
│   ├── persona.py           # 数字人格
│   ├── goals.py             # 人生目标
│   ├── simulate.py          # 人生模拟
│   ├── future_chat.py       # 未来对话
│   ├── settings.py          # 隐私与数据
│   └── legal.py             # 法律页面
├── templates/               # Jinja2 模板
│   ├── base.html            # 全局布局
│   ├── index.html           # 仪表盘首页
│   ├── guest_base.html      # 未登录布局
│   ├── auth/                # 认证页面
│   ├── events/              # 记录/事件/时间线
│   ├── reports/             # 成长报告
│   ├── persona/             # 数字人格
│   ├── goals/               # 目标管理
│   ├── simulation/          # 人生模拟
│   ├── chat/                # 未来对话
│   ├── settings/            # 隐私设置
│   └── legal/               # 用户协议等
└── static/                  # 静态文件
```

---

## 数据库模型（11 表 + 4 枚举）

| 表 | 说明 |
|----|------|
| users | 用户账户 |
| daily_records | 日常记录（含 AI 分析 JSON） |
| life_events | 人生事件（11 种类型 + 人格增量） |
| life_memories | AI 提炼的长期记忆 |
| persona_profiles | 数字人格画像（版本管理） |
| interest_tracks | 兴趣变化追踪 |
| life_goals | 人生目标（类型/周期/重要度） |
| simulations | 人生模拟记录 |
| simulation_variables | 模拟变量 |
| future_selves | AI 生成的未来人格 |
| chat_messages | 未来对话记录 |
| growth_reports | 成长报告 |

---

## License

MIT
