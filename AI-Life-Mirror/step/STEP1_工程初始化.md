# STEP 1: 项目工程初始化 — 审核

## 完成内容

### 1. 技术选型
| 层 | 选型 | 说明 |
|---|------|------|
| 框架 | FastAPI 0.140 | 异步 Python Web 框架 |
| 服务器 | Uvicorn 0.51 | ASGI 服务器 |
| ORM | SQLAlchemy 2.0 (async) | 异步数据库操作 |
| 数据库 | SQLite (aiosqlite) | MVP 阶段，后续迁移 MySQL |
| 模板 | Jinja2 3.1 | 服务端渲染 |
| 密码 | passlib + bcrypt | 密码哈希 |
| 表单 | python-multipart | 表单数据解析 |

### 2. 目录结构
```
ai-camp/
├── main.py                    # FastAPI 主入口 (lifespan, mount static)
├── config.py                  # 配置 (数据库URL, 密钥, 应用信息)
├── requirements.txt           # Python 依赖清单
├── .gitignore                 # 忽略 .venv/, data/, __pycache__/
├── database/
│   ├── __init__.py
│   ├── database.py            # 异步引擎, Session, init_db()
│   └── models.py              # 数据模型 (步骤2实现)
├── routers/
│   └── __init__.py            # 路由模块 (逐步注册)
├── services/
│   └── __init__.py            # 服务模块 (AI分析等)
├── templates/                 # Jinja2 模板
│   ├── auth/                  # 登录/注册页
│   ├── events/                # 人生事件
│   ├── persona/               # 数字人格
│   ├── simulation/            # 人生模拟
│   ├── legal/                 # 用户协议/隐私政策
│   └── components/            # 可复用组件
├── static/
│   ├── css/
│   └── js/
├── data/                      # SQLite 数据文件 (gitignored)
├── .venv/                     # Python 3.11 虚拟环境
└── AI人生镜像_PRD.md           # 产品需求文档
```

### 3. 关键代码

**main.py** — 应用入口：
- lifespan 管理：启动时创建 data/ 目录并建表
- 挂载 /static 静态文件
- /health 健康检查端点
- 路由待后续步骤逐步注册

**database/database.py** — 数据库层：
- 异步引擎 (aiosqlite)
- AsyncSession 工厂
- get_db() 依赖注入
- init_db() 自动建表

### 4. 依赖 (requirements.txt)
```
fastapi, uvicorn, sqlalchemy, aiosqlite, jinja2, python-multipart, passlib[bcrypt]
```

---

## 补充：数据库迁移策略 (SQLite → MySQL)

### 核心原则

用 SQLAlchemy 抽象层屏蔽差异，MVP 阶段 SQLite 零配置跑起来，生产切 MySQL 只改一行配置。

### 分层架构

```
                     routers / services
                           │
                     SQLAlchemy ORM          ← 业务代码只接触这一层
                           │
              ┌────────────┼────────────┐
              │            │            │
         SQLite         MySQL       PostgreSQL
        (MVP现在)     (生产将来)    (备选)
```

### 三类差异及处理

**一、连接串（只改 config.py 一行）**
```python
# MVP - SQLite
DATABASE_URL = "sqlite+aiosqlite:///data/app.db"

# 生产 - MySQL
DATABASE_URL = "mysql+asyncmy://user:pass@localhost:3306/ailifemirror"
```

**二、数据类型映射（SQLAlchemy 自动处理）**
| SQLite | MySQL | 影响 |
|--------|-------|------|
| `DateTime` 存字符串 | `DATETIME` | 自动适配 |
| `Boolean` 存 0/1 | `TINYINT(1)` | 自动适配 |
| `JSON` 存文本 | `JSON` | MySQL 5.7+ 原生支持 |
| 无 `ENUM` | `ENUM` | 用 `String` + 应用层校验 |

所有模型字段用 SQLAlchemy 通用类型（`String`, `Integer`, `Float`, `DateTime`, `Boolean`, `JSON`），不写原生 SQL 建表语句。

**三、迁移工具 Alembic（关键）**
- 第一天就接入 Alembic，`alembic/versions/` 管理每次模型变更
- 每次变更生成迁移脚本，可升级可回滚
- 切 MySQL 时：`alembic upgrade head` 一键建表
- 数据迁移：写脚本从 SQLite 导出，导入 MySQL

### MVP → 生产切换步骤
```
1. pip install asyncmy          # MySQL 异步驱动
2. 改 config.py 连接串           # 指向 MySQL
3. alembic upgrade head         # 在 MySQL 建表
4. 跑数据迁移脚本               # SQLite → MySQL 数据搬运
5. 回归测试
```

### 为什么 MVP 选 SQLite
- 零配置，不需要装 MySQL 服务
- `data/app.db` 一个文件，方便备份和重置
- SQLAlchemy 异步支持成熟 (`aiosqlite`)
- 单机并发 MVP 阶段完全够用

---

## 待审核确认

1. 技术选型 OK？
2. 目录结构 OK？
3. SQLite → MySQL 后续迁移策略 OK？

审核通过后，进入 **步骤2：数据库模型设计**。
