# STEP 3: AI 系统架构设计 — 审核

## 概述

定义 AI人生镜像的 4 条核心 Pipeline：Memory → Persona → Simulation → RAG Chat

---

## 整体架构

```
                        用户输入
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
         日记/事件      人生记录       AI 对话
                           │
                   ┌───────┴───────┐
                   │   LLM 理解层   │  ← 信息抽取 + 语义提炼
                   └───────┬───────┘
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
         SQLite        ChromaDB       人格模型
       (结构事实)     (语义记忆)     (版本画像)
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────┴──────┐
                    │ 模拟 Agent   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
         Future Self   What-if      Growth Report
```

---

## Pipeline 1: Memory Pipeline（记忆流水线）

**职责**：将用户原始输入转为 AI 理解的长期记忆

### 流程

```
用户输入: "今天参加机器人比赛输了，但第一次感觉自己喜欢工程创造"
                           │
                ┌──────────┴──────────┐
                │   Step 1: 信息抽取    │  LLM few-shot prompt
                │   提取: 事件/情绪/    │
                │   兴趣/行为模式       │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 2: 语义提炼    │  LLM 生成 memory_content
                │   "用户喜欢从创造     │
                │    过程获得满足，     │
                │    面对失败恢复力强"  │
                └──────────┬──────────┘
                           │
            ┌──────────────┼──────────────┐
            ↓              ↓              ↓
    ┌──────────────┐ ┌──────────┐ ┌──────────────┐
    │  SQLite 写入  │ │ 人格增量  │ │  Chroma 写入  │
    │ daily_record  │ │ creative │ │ embedding(text)│
    │ life_event    │ │ +5       │ │ type: journal  │
    │ life_memory   │ │ explore  │ │ metadata:      │
    │               │ │ +8       │ │ importance:0.8 │
    └──────────────┘ └──────────┘ └──────────────┘
```

### 输出

| 存储 | 写入内容 |
|------|---------|
| SQLite `daily_records` | 原始文本 + ai_analysis JSON |
| SQLite `life_memories` | memory_content + persona_impact + embedding_id |
| Chroma `user_memory` | 文本 Embedding，type=`journal`，metadata 含 importance |
| 人格更新缓存 | persona_delta 累积值，触发阈值后更新 persona_profiles |

### 触发条件

- 用户手动提交日记 → 实时触发
- 用户新增人生事件 → 实时触发
- 对话中 AI 识别到关键信息 → 异步触发

---

## Pipeline 2: Persona Pipeline（人格流水线）

**职责**：汇总生命记忆，生成/更新版本化数字人格

### 流程

```
触发条件: persona_delta 累积达阈值 OR 每30天定期 OR 用户手动
                           │
                ┌──────────┴──────────┐
                │   Step 1: 记忆汇总    │
                │   Chroma.search(      │
                │     "用户的人格特征", │
                │     type=ai_memory    │
                │   ) → top-50 记忆     │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 2: 人格分析    │  LLM 综合分析
                │   - 能力维度         │
                │   - 兴趣分布         │
                │   - 价值观排序       │
                │   - 决策风格         │
                │   - 行为模式         │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 3: 版本化存储  │
                │   旧版 is_current=   │
                │   False              │
                │   新版 version+1     │
                │   trigger_event=     │
                │   "完成3个AI项目"    │
                │   confidence=0.82    │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 4: 触发通知    │
                │   "根据过去一年记录， │
                │   你的人格类型从       │
                │   探索型学生 →        │
                │   跨学科创造者"       │
                └──────────────────────┘
```

### 五维分析 Prompt 结构（每维度独立 LLM call）

```
能力分析 Prompt:
  输入: top-50 记忆 + 当前能力画像
  输出: {tech, creative, expression, professional} 各 0-100

兴趣分析 Prompt:
  输入: interest_tracks 时间序列 + 记忆
  输出: {field: score} 分布

价值观分析 Prompt:
  输入: 决策事件记忆 + chat 记录
  输出: {stability, freedom, wealth, creativity, social_impact} 排序

决策风格 Prompt:
  输入: 关键选择事件
  输出: {type, time_horizon, risk_tolerance}

行为模式 Prompt:
  输入: 日常记录模式
  输出: {exploration, innovation, social, discipline}
```

### 输出

| 输出 | 示例 |
|------|------|
| persona_type | "跨学科创造者" |
| persona_summary | "具有技术与人文结合潜力，偏向长期探索…" |
| confidence | 0.82 |
| trigger_event | "完成3个AI项目 + 哲学阅读量激增" |

---

## Pipeline 3: Simulation Pipeline（模拟流水线）

**职责**：基于数字人格 + 变量 + 目标，生成多条未来人生路径

### 流程

```
用户触发: "我想看看要不要考研"
                           │
                ┌──────────┴──────────┐
                │   Step 1: 变量构建    │
                │   从用户输入提取:     │
                │   - 深造 vs 就业     │
                │   - 时间投入分布     │
                │   - 兴趣侧重         │
                │   加载 simulation_    │
                │   variables 表        │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 2: 人格快照    │
                │   锁定当前            │
                │   persona_profile    │
                │   (simulation 记录    │
                │    persona_snapshot_ │
                │    id)               │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 3: RAG 召回    │
                │   Chroma.search(     │
                │     "深造/科研/就业/ │
                │      创业相关经历"   │
                │   ) → 相关记忆       │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 4: 路径生成    │  LLM 多路径生成
                │   输入:              │
                │   - 人格快照         │
                │   - 变量设定         │
                │   - 相关记忆         │
                │   - 外部行业趋势     │
                │   输出:              │
                │   3条路径 × 3阶段    │
                │   + 分析 + 优劣      │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 5: 存储 +      │
                │   生成 Future Self   │
                │   每条路径 →          │
                │   一个 future_self   │
                │   含:                │
                │   - based_on_persona │
                │   - confidence       │
                │   - generation_prompt│
                │   - basis_summary    │
                └──────────────────────┘
```

### 模拟 Prompt 结构

```
System: 你是人生模拟引擎。基于以下信息，生成3条可能的未来人生路径。

输入:
  当前年龄: 21
  人格画像: {persona_snapshot}
  用户目标: "30岁在AI领域有影响力"
  变量设定: {simulation_variables}

  相关历史记忆: {Chroma RAG results}

要求:
  - 每条路径包含 21→25→30 三阶段
  - 输出 兴趣匹配度/稳定度/创造空间/压力水平
  - 列出 可能优势 和 潜在风险
  - 不输出确定性结论，只输出可能性
```

### 输出存储

| 存储 | 内容 |
|------|------|
| `simulations` | input_variables + output_paths + persona_snapshot_id |
| `simulation_variables` | 每条变量的 name-value 对 |
| `future_selves` | 每条路径一个未来人格，含完整追溯链 |

---

## Pipeline 4: RAG Chat Pipeline（检索增强对话）

**职责**：用户与"未来自己"对话时，基于记忆检索增强回复

### 流程

```
用户: "@2035科研型自己，我该继续读博吗？"
                           │
                ┌──────────┴──────────┐
                │   Step 1: 意图识别    │  LLM 分析
                │   - 查询意图:        │
                │     "科研相关经历"   │
                │   - 目标人格:        │
                │     2035科研型       │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 2: 多源检索    │
                │   Chroma.search(     │
                │     query="科研兴趣  │
                │     学术经历 研究    │
                │     坚持 耐心"       │
                │   ) → top-15 记忆    │
                │                     │
                │   SQL 查询:          │
                │   - life_events      │
                │     (科研相关)       │
                │   - interest_tracks  │
                │   - persona_profiles │
                │   - life_goals       │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 3: 人格注入    │
                │   加载 future_self   │
                │   .profile           │
                │   .basis_summary     │
                │   "这是我根据你的    │
                │    AI兴趣80%、       │
                │    科研倾向90%、     │
                │    长期主义倾向      │
                │    生成的人格"       │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 4: LLM 回复    │
                │   System:            │
                │   "你是用户的        │
                │    2035科研型人格。  │
                │   你的知识来自用户   │
                │   的真实经历和人格。" │
                │                     │
                │   Context:           │
                │   - 相关记忆         │
                │   - 人格依据         │
                │   - 模拟路径上下文   │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │   Step 5: 存储对话    │
                │   chat_messages      │
                │   + Chroma 异步写入  │
                │   (对话中可能暴露    │
                │    新价值观)         │
                └──────────────────────┘
```

### Chat System Prompt 模板

```
你是 {future_self.persona_label}。

你的人格基于:
  {future_self.basis_summary}

你的知识边界:
  - 你了解用户从大学至今的所有重要经历
  - 你基于用户真实人格推断未来
  - 你不是预言家，你展示的是基于数据的可能性

回复风格:
  - 使用第一人称 "我认为你…"
  - 引用用户过去的具体经历
  - 坦诚地讨论不确定性和风险
```

---

## 异步任务设计

部分 Pipeline 步骤不适合同步执行（如 Embedding、Chroma 写入、人格更新），需要异步队列：

```
同步（用户等待）:
  - 日记/事件写入 SQLite
  - Chroma 检索

异步（后台队列）:
  - Embedding 计算 + Chroma 写入
  - life_memory 生成 + persona_impact 计算
  - 人格定期更新检查
  - 成长报告生成
```

MVP 阶段用 FastAPI `BackgroundTasks`，后续切 RabbitMQ / Redis Stream。

---

## 各 Pipeline 触发关系

```
用户写日记
    ↓
Memory Pipeline ───→ SQLite + Chroma 写入
    ↓ (异步)
Persona 增量累积
    ↓ (达阈值)
Persona Pipeline ───→ 新版本 Persona Profile
    ↓
用户触发模拟
    ↓
Simulation Pipeline ───→ 加载 Persona + Chroma RAG → Future Self
    ↓
用户对话
    ↓
RAG Chat Pipeline ───→ Chroma RAG + Persona + Future Self → 回复
    ↓ (异步)
Chat 内容回写 Chroma（新价值观线索）
    ↓
Growth Report 定期生成
```

---

## 审核确认

1. 4 条 Pipeline 的输入/输出/流程 OK？
2. 同步 vs 异步的划分 OK？
3. Simulation Prompt 的设计方向 OK？

审核通过后，进入 **步骤4：用户系统实现**。
