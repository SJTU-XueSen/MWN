# STEP 4: 用户系统 — 审核

## 完成内容

### 实现功能

| 功能 | 路由 | 方法 | 说明 |
|------|------|------|------|
| 注册页面 | `/auth/register` | GET | 暗色主题，表单校验 |
| 注册处理 | `/auth/register` | POST | 用户名/邮箱/密码校验，bcrypt 哈希，session 写入 |
| 登录页面 | `/auth/login` | GET | 已登录自动跳转首页 |
| 登录处理 | `/auth/login` | POST | 密码验证，session 写入 |
| 登出 | `/auth/logout` | GET | 清除 session |
| 个人资料 | `/auth/profile` | GET/POST | 查看/编辑学校、专业、年级、年龄、简介 |
| 全局守卫 | — | — | 所有页面检查 session，未登录跳转登录页 |

### 新增/修改文件

| 文件 | 说明 |
|------|------|
| `services/auth_service.py` | bcrypt 原生 API 哈希/验证，CRUD 操作 |
| `routers/auth.py` | 7 条路由，表单校验，session 管理 |
| `templates/guest_base.html` | 访客布局（暗色主题，居中卡片） |
| `templates/auth/login.html` | 登录表单页 |
| `templates/auth/register.html` | 注册表单页 |
| `templates/auth/profile.html` | 个人资料编辑页 |
| `templates/base.html` | 主布局（暗色侧边栏 + 导航） |
| `templates/index.html` | 首页仪表盘 |
| `templates/placeholder.html` | 占位页（后续步骤替换） |
| `templating.py` | Jinja2 直连渲染（绕过 Starlette 兼容问题） |
| `main.py` | SessionMiddleware + 路由注册 + 首页/占位路由 |

### 安全措施

- 密码 bcrypt 哈希存储，不存明文
- Session 使用 Starlette signed cookie（SECRET_KEY 签名）
- 表单校验：用户名 2-50 字符、密码 ≥ 6 位、邮箱唯一、用户名唯一

### 测试结果

```
✅ GET /auth/login       → 200
✅ GET /auth/register    → 200
✅ POST /auth/register   → 302 → /
✅ POST /auth/login      → 302 → /
✅ GET / (已登录)         → 200
✅ GET /auth/profile     → 200
✅ GET /auth/logout      → 302 → /auth/login
✅ GET / (未登录)         → 302 → /auth/login
```

### 已知技术细节

- 因 Starlette `Jinja2Templates` 与 Jinja2 3.1.6 兼容问题，改用 Jinja2 原生 `Environment.get_template()` + `HTMLResponse`
- 因 passlib 1.7.4 不兼容 bcrypt 5.0+，改用 bcrypt 原生 API

---

审核通过后，进入 **步骤5：法律页面（用户协议 + 隐私政策 + 免责声明）**。
