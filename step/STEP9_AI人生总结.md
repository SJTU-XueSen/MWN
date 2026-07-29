# STEP 9: 阶段一 — AI人生总结（成长报告自动生成）

## 完成内容

### 成长报告系统落地

在积累了日常记录 + 人生事件后，AI 可以将一段时间内的人生数据汇总，生成结构化的成长报告。

### 数据流

```
用户选择时间段
    ↓
POST /reports/generate
    ↓
_gather_period_data() 收集该时段内：
  ├── DailyRecord（日常记录）
  ├── LifeEvent（人生事件）
  ├── LifeMemory（长期记忆）
  ├── InterestTrack（兴趣变化）
  └── LifeGoal（活跃目标）
    ↓
LLM 分析（优先）或 规则聚合（回退）
    ↓
GrowthReport 存入 SQLite
    ↓
/reports/{id} 渲染多维报告
```

### 新增文件

| 文件 | 说明 |
|------|------|
| `services/report_service.py` | 数据收集 + LLM/规则双引擎报告生成 |
| `routers/reports.py` | 报告列表/生成/查看/删除 路由 |
| `templates/reports/list.html` | 报告列表页（含引擎标识） |
| `templates/reports/generate.html` | 生成表单（选择时间段 + 标题） |
| `templates/reports/detail.html` | 报告详情（多维度展示） |

### 路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/reports` | GET | 报告列表 + 引擎标识徽章 |
| `/reports/generate` | GET | 生成表单（默认最近30天） |
| `/reports/generate` | POST | 收集数据 → LLM/规则生成 → 存储 |
| `/reports/{id}` | GET | 报告详情（8个分析维度） |
| `/reports/{id}/delete` | GET | 删除报告 |

### 报告内容维度

| 维度 | LLM 模式 | 规则模式 |
|------|---------|---------|
| **summary** | 200字温暖概览 | 拼接统计数据 |
| **emotional_trend** | 情绪变化趋势 + 描述 | 正/负/中性百分比 |
| **ability_growth** | tech/creative/social/self_awareness 0-100 | 默认 0 |
| **interest_changes** | 各领域趋势（上升/稳定/下降）+ 说明 | 关键词计数排序 |
| **key_events_analysis** | 事件 + 为什么重要 | 事件标题列表 |
| **personality_changes** | 人格层面变化分析 | 占位文字 |
| **gap_analysis** | 当前 vs 潜在差距 | 占位文字 |
| **recommendation** | 2-3 条具体行动建议 | 通用建议 |
| **encouragement** | 温暖鼓励 | 无 |

### LLM Prompt 设计

- **system**: "温暖而有洞察力的 AI 人生分析师"
- **context**: 时间段 + 日常记录（前30条） + 事件（前20条） + 长期记忆（前10条）
- **temperature**: 0.4（保持一定创造性但不跑偏）
- **output**: JSON 结构化，response_format 强制 json_object

### 设计决策

- **一次生成，永久查看**：报告生成后存入 DB，不重复调用 API，与记录分析同理
- **数据上限控制**：Prompt 中记录最多 30 条、事件 20 条、记忆 10 条，防止超 token
- **规则聚合作为坚实基础**：即使没有 LLM，报告也会提供统计概览（情绪占比、兴趣分布、关键事件列表），不是完全空白
- **引擎标识透明**：每份报告标注生成引擎（DeepSeek/规则引擎），用户清楚知道质量来源
- **仪表盘集成**：首页新增"成长报告"统计卡片（6 列布局）

### 测试结果

```
✅ GET  /reports              → 200  (空列表 + 引导生成)
✅ GET  /reports/generate     → 200  (默认30天时间范围)
✅ POST /reports/generate     → 302  → /reports/1
✅ GET  /reports/1            → 200  (完整报告：摘要/情绪/兴趣/事件/建议)
✅ GET  /reports/1/delete     → 302  → /reports
✅ 仪表盘 stats.reports = 1
✅ Sidebar 成长报告 → /reports
```

---

审核通过后，进入 **步骤10：阶段二-数字人格画像**。
