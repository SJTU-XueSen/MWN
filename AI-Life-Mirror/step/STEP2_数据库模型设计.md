# STEP 2: 数据库模型设计 — 审核中（已修订）

## 修订说明

根据审核反馈，从 **9 表** 扩展为 **11 表**，补全了生命记忆层和目标层；并引入 **ChromaDB 向量数据库** 作为语义记忆层。

### 新增 2 表

| # | 表名 | 用途 | 为什么需要 |
|---|------|------|------------|
| 4 | `life_memories` ⭐ | AI 理解后的长期生命记忆 | 原始记录→人格画像的桥梁，RAG 架构基础 |
| 7 | `life_goals` ⭐ | 用户长期目标 | 模拟需要「目标未来 vs 当前状态」差距分析 |

### 新增 1 子表

| # | 表名 | 用途 | 为什么需要 |
|---|------|------|------------|
| 8b | `simulation_variables` | 每次模拟的可调变量 | 拆表后可以分析「什么变量最影响人生结果」 |

### 增强 4 表

| 表 | 增强内容 |
|---|---------|
| `life_events` | 新增 5 种事件类型：`habit`/`failure`/`achievement`/`relationship`/`emotion`；新增 `persona_delta` 人格增量字段 |
| `persona_profiles` | 新增 `version`/`trigger_event`/`confidence` 版本追踪 |
| `simulations` | 新增 `persona_snapshot_id` 外键，追溯基于哪版人格生成 |
| `future_selves` | 新增 `based_on_persona_id`/`confidence`/`generation_prompt`/`basis_summary` 可审计的生成追溯 |

### 完整 ER 链路（11 表）

```
users
  ├─ life_events       (11种事件类型)
  ├─ daily_records     (日常记录)
  │
  ├─ life_memories ⭐  (AI理解后的记忆, RAG桥梁)
  │    ↑ source: diary / event / chat / report
  │    ↓ persona_impact
  │
  ├─ interest_tracks   (兴趣变化时间序列)
  │
  ├─ persona_profiles  (数字人格, 版本追踪 v1/v2/v3)
  │    ↑ trigger_event + confidence
  │
  ├─ life_goals ⭐     (长期目标, 差距分析基准)
  │
  ├─ simulations       (人生模拟记录)
  │    ├─ simulation_variables ⭐ (可调变量)
  │    ├─ future_selves         (未来人格, 可追溯)
  │    │    └─ chat_messages     (未来自我对话)
  │    └─ persona_snapshot_id   (基于哪版人格)
  │
  └─ growth_reports    (成长报告, 含 goal_progress + gap_analysis)
```

### 数据流（完整闭环）

```
daily_records + life_events
        ↓
  life_memories        ← AI 提取意义 + 重要性评分
        ↓
  interest_tracks      ← 兴趣随时间变化
        ↓
  persona_profiles     ← 版本化数字人格
        ↓
  life_goals           ← 用户目标设定
        ↓
  simulations          ← 人生模拟引擎
        ↓
  future_selves        ← 可追溯的未来人格
        ↓
  chat_messages        ← 对话交互
        ↓
  growth_reports       ← 差距分析 + 反馈
```

---

## 审核确认

修订后的 11 表设计，评分从 7.5 → 9/10。可以进入步骤3？

---

## 补充：混合存储架构（SQLite + ChromaDB）

### 核心原则

> 数据库负责「记住事实」，向量数据库负责「理解记忆」。两者配合，不是替代。

### 架构分层

```
                   用户输入
                      ↓
             ┌────────────────┐
             │   数据理解层    │  ← LLM 提取语义
             └────────────────┘
                      ↓
      ┌───────────────┴───────────────┐
      ↓                               ↓
┌──────────────┐              ┌──────────────┐
│   SQLite     │              │   ChromaDB   │
│   人生档案    │              │   人生记忆    │
│              │              │              │
│ · users      │              │ · 日记文本    │
│ · life_events│              │ · 事件描述    │
│ · persona    │              │ · AI记忆提取  │
│ · simulations│              │ · 对话记录    │
│ · scores     │              │ · Embeddings  │
└──────────────┘              └──────────────┘
   结构化事实                     语义检索
      ↓                               ↓
      └───────────────┬───────────────┘
                      ↓
              ┌──────────────┐
              │  数字人格模型  │
              └──────────────┘
                      ↓
              ┌──────────────┐
              │  人生模拟器    │
              └──────────────┘
```

### 什么进 Chroma？

| 数据类型 | 进 Chroma？ | 理由 |
|---------|------------|------|
| 日记文本 (daily_records.content) | ✅ | 长文本，包含情感和隐含价值观 |
| 人生事件描述 (life_events.description) | ✅ | 叙事性内容，语义丰富 |
| AI 提取的记忆 (life_memories.memory_content) | ✅ | 核心记忆，人格建模关键输入 |
| 对话记录 (chat_messages.content) | ✅ | 暴露用户价值观和决策偏好 |
| 用户 ID / 年龄 / 学校 | ❌ | 结构化字段，SQL 直接查 |
| 能力分数 / 兴趣分数 | ❌ | 数值型，SQL 直接查 |
| simulation_id / persona_version | ❌ | 外键，SQL 直接查 |

### 具体场景：一次 RAG 检索

用户问：「我为什么适合创业？」

```
Chroma 语义搜索 "适合创业" →
  找到:
    1. "机器人比赛失败后反而更兴奋，喜欢从零创造"
    2. "自主开发项目比课堂作业更有动力"
    3. "享受解决没有标准答案的问题"

LLM 综合:
  "你的历史显示：① 喜欢从零创造而非执行既定方案
   ② 面对不确定性不会退缩 ③ 实践驱动型学习者
   → 创业环境比稳定职业更匹配你的驱动力。"
```

### Chroma：单一 Collection 设计

**4 Collection → 1 Collection `user_memory`** + `metadata.type` 区分

| metadata.type | 说明 | 来源 |
|--------------|------|------|
| `ai_memory` | AI 提取的长期记忆 | `life_memories` |
| `journal` | 原始日记 | `daily_records` |
| `event` | 人生事件描述 | `life_events` |
| `chat` | 对话记录 | `chat_messages` |
| `report` | 成长报告 | `growth_reports` |

优点：一条查询跨所有类型，无需多路搜索 + merge + rerank。

### life_memories 新增字段

| 字段 | 说明 |
|------|------|
| `embedding_id` | 关联 ChromaDB 向量 ID，格式 `"ai_memory:{id}"` |
| `persona_impact` (已有) | 对人格各维度的累积影响，如 `{creative: +5, risk_tolerance: +3}` |

### 不做的事

- Neo4j 知识图谱 → V2
- 多 Collection → 已合并为单一 Collection

### 代码实现

`services/vector_store.py` — 完整的 Chroma 封装：

- `add_memory()` / `add_journal()` / `add_event()` / `add_chat_message()` — 写入
- `search_memories(query, user_id)` — 语义检索（RAG 核心）
- `search_all(query, user_id)` — 跨集合搜索
- `delete_user_data(user_id)` — 账户注销时清理
