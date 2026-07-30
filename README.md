# 镜·界·联 — 青年成长生态系统

> 认识自己 · 走向世界 · 与他人共同创造

---

## 架构总览

```
浏览器 (:5173)
    │
    ▼
┌─────────────────────────────────────────────────┐
│  unified/ (React + Vite)                         │
│  深/浅双主题 · 28个页面组件                       │
└──────┬──────────────┬──────────────┬─────────────┘
       │ /api         │ /nexus       │ /api/activities
       ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ Mirror :5000 │ │Nexus:3002│ │ Express:3001 │
│ (FastAPI)    │ │ (Flask)  │ │ (Node/tsx)   │
│              │ │          │ │              │
│ · 数字人格   │ │ · 组队   │ │ · SJTU 爬虫  │
│ · AI 分析    │ │ · 任务   │ │ · AI 检索    │
│ · 人生模拟   │ │ · 聊天   │ │ · 活动聚合   │
│ · 成长报告   │ │ · 学分   │ │              │
└──────┬───────┘ └────┬─────┘ └──────────────┘
       │              │
       ▼              ▼
┌──────────────────────────────────────┐
│  SQLite (data/app.db)  │  ChromaDB  │
│  · users, life_events  │  · 语义记忆 │
│  · persona_profiles    │  · RAG 检索 │
│  · simulations, goals  │             │
└──────────────────────────────────────┘
```

---

## 快速启动

```bash
# 1. 安装依赖
cd ai-camp && pip install -r AI-Life-Mirror/requirements.txt

# 2. 配置 API Key
cp .env.example .env  # 填入 DEEPSEEK_API_KEY

# 3. 启动后端（3个终端）
python -m uvicorn AI-Life-Mirror.main:app --host 127.0.0.1 --port 5000
python nexus/app.py                                              # :3002
cd ../compete/api && npx tsx server.ts                            # :3001

# 4. 启动前端
cd unified && npm install && npx vite --host --port 5173

# 5. 访问
open http://127.0.0.1:5173
```

---

## 数据库设计

### SQLite — 结构化数据

**位置：** `data/app.db`

| 表 | 字段 | 用途 |
|----|------|------|
| `users` | id, username, password_hash, real_name, email | 统一用户 |
| `daily_records` | user_id, content, mood, ai_analysis(JSON) | 日常记录 + LLM 分析结果 |
| `life_events` | user_id, title, description, event_type, emotion, interest_tags, persona_delta | 重要人生事件 |
| `life_memories` | user_id, source_type, memory_content, importance_score, persona_impact | 提炼后的生命记忆 |
| `persona_profiles` | user_id, persona_type, ability_profile, interest_profile, value_profile, decision_style, behavior_profile, version, is_current | 数字人格画像（多版本） |
| `life_goals` | user_id, title, goal_type, importance, target_period, ai_gap_analysis | 人生目标 |
| `simulations` | user_id, scenario_type, input_variables, output_paths(JSON) | 人生模拟 |
| `future_selves` | simulation_id, persona_label, confidence, profile(JSON) | 模拟出来的未来人格 |
| `growth_reports` | user_id, title, period_start, period_end, content(JSON) | 成长报告 |
| `interest_tracks` | user_id, field, score | 兴趣追踪 |
| `chat_messages` | future_self_id, role, content | 未来对话 |

**Flask 独立 DB：** `nexus/competition_platform.db`

| 表 | 用途 |
|----|------|
| `users` | Flask 本地用户（UUID 主键，通过 Mirror cookie 桥接） |
| `competitions` | 组队活动（用户发布 + AI 爬取） |
| `teams`, `team_members` | 战队与成员 |
| `team_tasks`, `task_assignments` | AI 拆解任务与角色分配 |
| `team_documents`, `work_submissions` | 协作文档与作品提交 |
| `chat_messages` | 团队/群组聊天 |
| `credit_logs` | 学分变动记录 |

### ChromaDB — 语义向量

**位置：** `data/chroma/`

| Collection | 内容 | 用途 |
|-----------|------|------|
| `life_memories` | 从日记/事件提炼的生命记忆 | 人格画像、模拟推演 |
| `ai_memories` | AI 分析结果的向量化 | RAG 上下文检索 |
| `journals` | 日常记录原文 | 相似经历检索 |

---

## AI 人格算法

### 数据流

```
日常记录 / 人生事件
       │
       ▼
┌──────────────────────┐
│ LLM 分析 (DeepSeek)   │
│ · 情绪检测            │
│ · 兴趣标签提取         │
│ · 行为模式识别         │
│ · 人格维度增量计算     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ 规则引擎补位           │
│ · 20领域 120+ 关键词  │
│ · 事件类型预设人格映射  │
│ · 情绪词库匹配         │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Memory Pipeline       │
│ · extract_memory()    │
│ · ChromaDB 向量化     │
│ · 重要性评分          │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Persona 聚合          │
│ · ability_profile     │
│ · interest_profile    │
│ · value_profile       │
│ · decision_style      │
│ · behavior_profile    │
│                      │
│ 五维加权归一化         │
│ 多版本历史追踪         │
└──────────────────────┘
```

### 五维人格画像

| 维度 | 来源 | 更新方式 |
|------|------|---------|
| **能力** (ability) | 事件 persona_delta 累加 | 每次新事件后增量更新 |
| **兴趣** (interest) | 兴趣标签频率 + InterestTrack | 实时追踪 |
| **价值观** (value) | 决策类事件推断 | 决策事件触发重算 |
| **决策风格** (decision) | 行为模式聚类 | 行为模式积累后重算 |
| **行为模式** (behavior) | 行为关键词统计 | 每次记录/事件后更新 |

### 置信度计算

```
confidence = f(记录数, 事件数, 目标数)
           × 数据时间跨度因子
           × 兴趣领域覆盖度
           上限 95%（保留不确定性）
```

### 人生模拟引擎

1. 收集上下文：当前人格 + ChromaDB 长期记忆 + 活跃目标 + 最近事件
2. LLM 生成 3 条差异化路径（每条 180 字以内）
3. 每条路径包含：人格倾向变化 + 人生节点（条件语气）+ 成长课题 + 90 天建议
4. LLM 不可用时回退规则引擎（基于用户真实数据构建）
5. 约束：不编造经历 · 不预测职业 · 不存在好坏排序

---

## 爬虫系统

### 1. Express 端 — SJTU 通知公告（:3001）

**文件：** `compete/api/services/sjtuCrawler.ts`

- 爬取 `www.sjtu.edu.cn/tg` 全部页面
- 并发抓取详情页 → 规则引擎 `activityRules.ts` 判断是否学生活动
- 提取：标题、日期、摘要、截止日期、匹配关键词
- 30 分钟内存缓存 + JSON 文件持久化
- 数据流向：「活动大厅 → SJTU通知」标签

### 2. Flask 端 — 多源 AI 筛选（:3002）

**文件：** `nexus/scraper/sjtu_scraper.py` + `nexus/ai_filter.py`

- 爬取多个 SJTU 子站
- **AI 筛选** (智谱 GLM)：判断是否学生竞赛/活动 → 提取分类、级别、学分、标签
- AI 不可用时回退规则引擎（关键词 + 正则）
- 每天 00:00 & 12:00 定时执行
- 自动去重、过期清理
- 数据流向：「活动大厅 → 组队活动」标签

### AI 检索

**文件：** `compete/api/services/aiMatcher.ts`

- 用户输入查询 → Express → DeepSeek 语义匹配
- 返回匹配活动 + 推荐理由 + 匹配度分数
- 代理链：`前端 → Mirror(:5000) → Express(:3001) → DeepSeek`

---

## 前端页面清单

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard | 5 段叙事：当前的我 · 可能的我 · 我与世界 · 我和他人 · 我要走向哪里 |
| `/journal` | 日常记录 | 列表 + 创建 |
| `/journal/:id` | 记录详情 | AI 分析面板 |
| `/events` | 人生地图 | 时间线 + 类型统计 |
| `/events/:id` | 事件详情 | AI 分析 + 关联记忆 |
| `/persona` | 数字人格 | 五维画像 + 版本历史 |
| `/simulation` | 人生模拟 | 创建实验 + 历史列表 |
| `/simulation/:id` | 模拟结果 | 3 条路径 + 人格对比 |
| `/experience/:fsId` | 人生体验 | 交互式选择叙事 |
| `/future-chat` | 未来对话 | 与未来人格聊天 |
| `/goals` | 人生目标 | 创建 + AI 分析 + 完成/删除 |
| `/reports` | 成长报告 | 生成表单 + 列表 |
| `/reports/:id` | 报告详情 | 情绪趋势 + 能力成长 + 建议 |
| `/connections` | 活动大厅 | 组队活动 + SJTU 通知 + 发布 + 创建战队 |
| `/connections/chat` | 聊天 | 组内/团队聊天 + DeepSeek + 潜在好友 |
| `/connections/work` | 工作台 | AI 任务拆分 + 招募/工作双阶段 |
| `/ai-search` | AI 检索 | DeepSeek 语义活动搜索 |
| `/memo` | 备忘录 | 便签记录 |
| `/references` | 人生参考 | 兴趣领域分布 |
| `/settings` | 设置 | 个人信息 |
| `/login` | 登录 | Mirror 认证 |

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS CDN |
| Mirror 后端 | Python 3.11 + FastAPI + SQLAlchemy (async) + ChromaDB |
| Nexus 后端 | Python 3.11 + Flask + Flask-SQLAlchemy + Flask-Login |
| Express | Node.js + Express + TypeScript + cheerio + axios |
| AI | DeepSeek Chat API + 智谱 GLM-4-Flash |
| 数据库 | SQLite (3 个 DB) + ChromaDB (向量) |
| 认证 | Mirror Session → cookie 桥接 Flask |
