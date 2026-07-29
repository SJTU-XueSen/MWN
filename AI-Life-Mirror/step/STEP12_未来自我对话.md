# STEP 13: 阶段三 — 未来自我对话

## 完成内容

### 与未来人格实时对话

这是"AI人生镜像"的灵魂功能——用户不只看未来的自己，还能直接与 ta 对话。

### 数据流

```
用户打开 /future-chat
    ↓
选择一个人生模拟生成的 FutureSelf
    ↓
进入聊天室 /future-chat/{id}
    ↓
输入消息 → POST /send
    ↓
LLM 扮演该 FutureSelf 人格回复
  ├── System Prompt：该 FutureSelf 的 persona_label + description + persona_shift
  ├── 对话历史：最近 10 轮上下文
  └── temperature 0.7（对话需要自然感）
    ↓
ChatMessage 双双存入 SQLite
```

### 新增文件

| 文件 | 说明 |
|------|------|
| `services/chat_service.py` | FutureSelf 回复生成（LLM优先+回退） |
| `routers/future_chat.py` | 人格列表/聊天室/发送/清除 |
| `templates/chat/list.html` | 可选择对话的未来人格列表 |
| `templates/chat/room.html` | 聊天室界面 |

### 路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/future-chat` | GET | 未来人格列表（从 Simulation 生成的 FutureSelf） |
| `/future-chat/{id}` | GET | 对话房间（历史消息 + 输入框） |
| `/future-chat/{id}/send` | POST | 发送消息 → LLM 回复 → 存储 |
| `/future-chat/{id}/clear` | GET | 清除该人格的所有对话记录 |

### LLM 角色设定

FutureSelf 的 System Prompt：
- 身份：用户的"未来自我"——基于真实数据生成的未来人格投影
- 时态：第一人称，"我"是未来版本
- 语气：自然真实——不是客服或 AI 助手，有观点、会质疑、诚实
- 记忆：可以回忆"过去"（用户现在），但不虚构不存在的事件
- 长度：1-3 句为主，偶尔展开

### 界面设计

- 对话气泡：用户消息紫色右对齐（`bg-indigo-500/20`），AI 回复白色左对齐带 🪞 头像
- 顶部信息条：人格名称 + 目标年份 + 置信度
- 自动滚动到底部
- 空对话引导语："这是你和'{persona_label}'的对话空间"

### 设计决策

- **不是通用聊天机器人**：每个 FutureSelf 有具体的身份和背景，基于真实的 simulation path
- **诚实原则**：不粉饰——用户问"我做得对吗"，FutureSelf 会直接回答
- **无 LLM 时回退**：基于人格标签生成简单的角色化回复
- **对话持久化**：ChatMessage 存储完整历史，清除按钮可重置
- **链接闭环**：simulation detail → "与这个版本的自己对话" → /future-chat/{id}

### 测试结果

```
✅ GET  /future-chat          → 200  (9个已生成的FutureSelf可选)
✅ GET  /future-chat/1        → 200  (空对话 + 输入框)
✅ POST /future-chat/1/send   → 302  → /future-chat/1
✅ GET  /future-chat/1 (after) → 用户消息 + AI 回复双向显示
✅ GET  /future-chat/1/clear  → 302  → /future-chat/1
✅ Sidebar 未来对话 → /future-chat
✅ Dashboard 快速开始 → 未来对话
```

---

三大阶段全部完成：记录 → 人格 → 模拟 → 对话。后续步骤：数据隐私控制 + 部署验收。
