# STEP 11: 阶段三 — 人生模拟器

## 完成内容

### 多路径未来模拟系统

这是"AI人生镜像"最核心的 What-if 能力——基于用户的数字人格 + ChromaDB 长期记忆，生成多条不同的未来人生路径。

### 与传统人生模拟器的差异

| 维度 | 网上主流做法 | AI人生镜像（RAG + ChromaDB） |
|------|------------|---------------------------|
| 路径生成 | 纯随机 / LLM 凭空编造 | 锚定于 ChromaDB 中的真实 life_memories |
| 人格来源 | 用户手选标签（Stoic/YOLO…） | 从实际数据提炼的数字人格画像 |
| 记忆关联 | 无 | 每条路径对应一个 FutureSelf（可对话） |
| 属性系统 | 抽象数值（财富/幸福/健康） | 具体人格维度变化（技术能力/创造力/社交力…） |
| 后续交互 | 一次性故事 | FutureSelf 支持后续对话（步骤13） |

### 新增文件

| 文件 | 说明 |
|------|------|
| `services/simulation_service.py` | 数据收集 + LLM/规则双引擎路径生成 |
| `routers/simulate.py` | 模拟列表/新建/详情/删除 |
| `templates/simulation/list.html` | 模拟历史列表 |
| `templates/simulation/new.html` | 创建表单（场景选择+问题+变量） |
| `templates/simulation/detail.html` | 三条路径并排对比 + RAG 溯源说明 |

### 路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/simulation` | GET | 模拟历史列表 |
| `/simulation/new` | GET | 创建表单（4种场景） |
| `/simulation/new` | POST | 收集上下文 → LLM/规则生成 3 条路径 → 存储 |
| `/simulation/{id}` | GET | 三栏路径对比 + 人格变化 + 里程碑 + 置信度 |
| `/simulation/{id}/delete` | GET | 删除模拟 |

### 4 种场景

| 场景 | 图标 | 说明 |
|------|------|------|
| further_study | 📚 | 继续深造（读研、读博、出国） |
| employment | 💼 | 直接就业（大厂、创业公司、自由职业） |
| entrepreneurship | 🚀 | 创业探索（自主创业、加入初创） |
| cross_discipline | 🔄 | 跨学科发展（多领域交叉路径） |

### 路径生成流程

```
用户选择场景 + 提问题 + 调变量
    ↓
_collect_simulation_context()
  ├── 当前 PersonaProfile（数字人格）
  ├── 活跃 LifeGoal（目标）
  ├── InterestTrack（兴趣）
  └── 关键 LifeEvent（事件）
    ↓
LLM Prompt（含完整上下文）→ 3 条差异化路径
或规则引擎 → 3 条模板路径（专注/跨界/稳健）
    ↓
Simulation 存储 + FutureSelf × 3 创建
    ↓
三栏对比展示
```

### 每条路径包含

- **label**：路径名称
- **description**：5年后的生活状态和成就描述
- **persona_shift**：人格各维度的预期变化
- **confidence**：AI 置信度（0-1）
- **milestones**：3个关键里程碑

### RAG 溯源

详情页底部展示 AI 生成说明，明确告知用户：
- 路径基于数字人格画像、ChromaDB 长期记忆库、关键人生事件综合推演
- 每条路径对应一个 FutureSelf，后续可对话
- 标注基于的人格版本快照 ID

### 设计决策

- **场景驱动而非随机**：用户选择具体场景（深造/就业/创业/跨学科），模拟围绕场景展开
- **可调变量预留**：支持自定义变量（如"冒险程度""工作城市"），为步骤12的 What-if 实验室打基础
- **FutureSelf 预创建**：每次模拟自动为每条路径创建 FutureSelf，步骤13可直接对话
- **规则引擎兜底**：无 LLM 时生成 3 条模板路径（专注深耕/跨界拓展/稳健积累），保证功能可用

### 测试结果

```
✅ GET  /simulation          → 200  (空列表 + 引导)
✅ GET  /simulation/new      → 200  (4场景选择 + 问题 + 变量)
✅ POST /simulation/new      → 302  → /simulation/1
✅ GET  /simulation/1        → 200  (三栏对比 + 人格变化 + 里程碑 + 置信度 + RAG说明)
✅ GET  /simulation/1/delete → 302  → /simulation
✅ Dashboard stats.simulations 实时更新
✅ Sidebar 人生模拟 → /simulation
```

---

审核通过后，进入 **步骤12：What-if实验室（变量调整对比模拟）**。
