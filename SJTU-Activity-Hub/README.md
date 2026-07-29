# 🏫 交大活动通 (SJTU Activity Hub)

> 上海交通大学学生活动信息聚合与智能推荐平台

自动抓取学校通知公告，AI 识别与学生相关的活动，判断是否仍可参与，
帮助学生高效发现值得参加的活动、竞赛和机会。

## 功能

- **活动聚合**：自动抓取 SJTU 通知公告，过滤已结束活动
- **AI 匹配**：智能判断活动是否与学生相关
- **竞赛搜索**：检索和浏览各类学科竞赛信息
- **备忘录**：收藏感兴趣的活动，设置提醒
- **通知系统**：关注的活动状态变更时推送通知

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vite + React 18 + TypeScript + Tailwind CSS |
| 状态管理 | Zustand |
| 后端 | Express + TypeScript |
| 爬虫 | Cheerio |
| AI | 规则引擎 + LLM 匹配 |
| 部署 | Vercel |

## 快速开始

```bash
# 安装依赖
npm install

# 开发模式（前后端同时启动）
npm run dev

# 构建
npm run build

# 生产启动
npm start
```

## 项目结构

```
compete/
├── src/                    # React 前端
│   ├── components/         # UI 组件
│   ├── pages/              # 页面
│   ├── hooks/              # Zustand stores
│   └── lib/                # 工具函数
├── api/                    # Express 后端
│   ├── routes/             # API 路由
│   └── services/           # 业务逻辑
├── shared/                 # 前后端共享类型
├── public/                 # 静态资源
└── dist/                   # 构建产物
```

## 相关项目

本项目是「青年成长生态系统」的 **Horizon（界）** 模块——世界探索层。

- **Mirror（镜）**：[AI人生镜像](https://github.com/SJTU-XueSen/AI-Life-Mirror) — 自我认知层
- **Nexus（联）**：组队平台 — 社交协作层（规划中）
