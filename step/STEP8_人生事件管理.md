# STEP 8: 阶段一 — 人生事件管理（时间线 + 分类标签）

## 完成内容

### 人生事件系统落地

在步骤7日常记录的基础上，实现了 LifeEvent（人生事件）的完整 CRUD + AI 分析 + 时间线展示。

### 与日常记录的区别

| 维度 | 日常记录 (Journal) | 人生事件 (LifeEvent) |
|------|-------------------|---------------------|
| 粒度 | 每天/随时记录 | 里程碑级别 |
| 内容 | 自由文本，心情随笔 | 结构化：标题 + 类型 + 描述 |
| AI 分析 | 情绪/兴趣/行为模式 | 情绪/兴趣标签/人格增量/影响摘要 |
| 重要性 | 默认 0.5，根据内容浮动 | 根据类型预设（转折点0.9 → 情绪波动0.35） |
| 入口 | `/journal` | `/events`（已从重定向升级为主页） |

### 新增文件

| 文件 | 说明 |
|------|------|
| `services/event_service.py` | 事件 CRUD + AI 分析引擎 + Memory Pipeline |
| `templates/events/timeline.html` | 时间线页面，按月分组，垂直时间线设计 |
| `templates/events/event_new.html` | 创建事件表单，11种事件类型可视化选择 |
| `templates/events/event_detail.html` | 事件详情 + AI分析面板 + 生命记忆关联 |

### 路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/events` | GET | 人生事件时间线（按月分组，含类型统计条） |
| `/events/new` | GET | 新建事件表单（11种类型 radio 卡片选择器） |
| `/events/new` | POST | 创建事件 → AI 分析 → life_memories → ChromaDB |
| `/events/{id}` | GET | 事件详情 + AI 分析面板（情绪/兴趣/人格影响/重要性） |
| `/events/{id}/delete` | GET | 删除事件 + 关联的 life_memories |
| `/journal` 及子路由 | — | 保持不变，日常记录 CRUD |

### 11种事件类型

| 类型 | 图标 | 标签 | 重要性 | 典型人格影响 |
|------|------|------|--------|-------------|
| project | 📁 | 项目经历 | 0.7 | creative, 专业能力 |
| competition | 🏆 | 比赛经历 | 0.7 | 竞争意识, 抗压能力 |
| study | 📖 | 学习经历 | 0.5 | 学习能力, 专注 |
| social | 👥 | 社交经历 | 0.45 | 社交能力, 同理心 |
| decision | 🧭 | 重要决定 | 0.85 | 决策力, 自主性 |
| turning_point | 🔀 | 人生转折 | 0.9 | 适应性, 勇气 |
| habit | 🔄 | 长期习惯 | 0.5 | 自律, 坚持 |
| failure | 💪 | 失败经历 | 0.75 | 韧性, 反思 |
| achievement | 🌟 | 成就突破 | 0.8 | 自信, 成就感 |
| relationship | 💞 | 重要关系 | 0.65 | 共情, 责任 |
| emotion | 💭 | 情绪波动 | 0.35 | 情绪觉察, 自我认知 |

### AI 分析流程

```
用户创建事件（title + description + event_type）
    ↓
analyze_event()
    ├── 1. 情绪检测（同 STEP7 规则引擎，60+ 情绪词库）
    ├── 2. 兴趣领域检测（10 个领域关键词匹配）
    ├── 3. 行为模式检测 → persona_delta
    ├── 4. 根据事件类型注入预设人格影响
    └── 5. 生成自然语言影响摘要（ai_impact）
    ↓
LifeEvent 写入 SQLite（含 ai_impact, persona_delta, interest_tags）
    ↓
_process_event_to_memory()
    ├── 提炼语义记忆（memory_content）
    ├── 根据事件类型计算重要性
    └── LifeMemory 写入 SQLite
    ↓
ChromaDB 向量写入（router 层）
```

### 设计决策

- **事件类型决定重要性基线**：转折点(0.9) > 决定(0.85) > 成就(0.8)，兴趣标签检测可以额外加分，但上限 0.95
- **人格影响 = 内容检测 + 类型预设**：内容中检测到的行为模式贡献 2 分/项，事件类型贡献 3-4 分/维度
- **删除级联**：删除事件时同时删除关联的 life_memories（通过 source_type + source_id 查找）
- **时间线设计**：垂直时间线 + 月份节点，每个事件卡片展示类型标签+兴趣标签+情绪图标
- **/events 升级**：从"重定向到 /journal"升级为独立的人生事件时间线主页

### 测试结果

```
✅ GET  /events          → 200  (时间线 + 5个事件 + 类型统计条)
✅ GET  /events/new      → 200  (11种类型选择表单)
✅ POST /events/new      → 302  (创建成功 → /events/3)
✅ GET  /events/3        → 200  (详情 + AI分析面板: 情绪/兴趣/人格影响/重要性)
✅ GET  /events/5/delete → 302  (删除 → /events)
✅ Dashboard stats.events 实时更新
✅ Sidebar 人生地图 → /events（时间线）
✅ Journal /journal 不受影响
```

### 当前项目结构

```
routers/events.py          ← 日常记录 + 人生事件（共 14 个端点）
services/event_service.py  ← 事件 CRUD + AI 分析 + 配置
templates/events/
├── journal_list.html      ← 日常记录列表
├── journal_new.html       ← 日常记录创建
├── journal_detail.html    ← 日常记录详情 + AI 分析
├── timeline.html          ← ★ 人生事件时间线
├── event_new.html         ← ★ 人生事件创建
└── event_detail.html      ← ★ 人生事件详情
```

---

审核通过后，进入 **步骤9：AI人生总结（阶段性成长报告自动生成）**。
