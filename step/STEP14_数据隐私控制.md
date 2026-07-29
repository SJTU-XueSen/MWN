# STEP 14: 数据隐私控制

## 完成内容

### 用户数据主权

用户对自己的数据有完全控制权：查看存储了什么、一键导出、永久删除。

### 新增文件

| 文件 | 说明 |
|------|------|
| `routers/settings.py` | 隐私仪表盘 / 数据导出 / 账户删除 |
| `templates/settings/index.html` | 数据概览 + 存储说明 + 操作入口 |
| `templates/settings/delete_confirm.html` | 删除确认页（警告+建议先导出） |

### 路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/settings` | GET | 隐私仪表盘（10类数据统计 + 存储说明 + 操作入口） |
| `/settings/export` | GET | 导出全部数据为 JSON 文件下载 |
| `/settings/delete-account` | GET | 删除确认页（警告 + 建议先备份） |
| `/settings/delete-account` | POST | 执行删除（级联清理 SQLite + ChromaDB + Session） |

### 隐私仪表盘内容

**数据概览**：10 类数据的数量统计
- 日常记录 / 人生事件 / 长期记忆 / 人格画像版本 / 目标 / 兴趣数据点 / 人生模拟 / 未来人格 / 对话消息 / 成长报告

**存储说明**：
- SQLite：结构化数据本地存储
- ChromaDB：语义向量，不含原始全文
- AI API：仅存储分析结果，不存原始调用记录

**操作**：
- 📥 导出 JSON 完整备份
- ⚠️ 删除账户（二次确认）

### 导出数据格式

```json
{
  "exported_at": "2026-07-29T...",
  "app": "AI人生镜像",
  "user": {...},
  "daily_records": [...],
  "life_events": [...],
  "life_memories": [...],
  "persona_profiles": [...],
  "life_goals": [...],
  "simulations": [...],
  "future_selves": [...],
  "chat_messages": [...],
  "growth_reports": [...]
}
```

### 删除流程

1. 用户点击"删除账户"→ 警告页（列明将删除的数据类型）
2. 建议先导出备份
3. 确认 → POST → 级联删除所有 SQLite 数据 → 清理 ChromaDB → 清除 Session → 回到登录页

### 侧边栏更新

底部新增"隐私与数据"入口（🛡️ 图标），与"个人资料""退出登录"同组。

### 设计决策

- **数据主权优先**：不是"请求删除"，而是用户自己操作，即时生效
- **导出先于删除**：确认页主动引导用户先备份
- **透明存储**：明确告知数据存在哪里、AI 过程如何处理
- **完整级联**：删除覆盖所有 11 张表 + ChromaDB 向量库

### 测试结果

```
✅ GET  /settings              → 200  (10类数据统计 + 存储说明)
✅ GET  /settings/export        → 200  (JSON 文件下载)
✅ GET  /settings/delete-account → 200 (确认页 + 警告)
✅ POST /settings/delete-account → 302 → /auth/login
✅ Sidebar 隐私与数据 → /settings
```

---

审核通过后，进入最后一步：**Step 15：部署与验收**。
