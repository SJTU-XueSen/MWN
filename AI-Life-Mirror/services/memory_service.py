"""
AI 记忆分析服务 — Memory Pipeline 核心

对用户的日常记录进行：
1. 信息抽取（事件/情绪/兴趣标签/行为模式）
2. 生命记忆提炼（语义总结 + 人格影响值）
3. ChromaDB 向量化存储
"""
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import DailyRecord, LifeMemory, EmotionType


# ── 关键词库（MVP 规则引擎，后续切 LLM）─────────────

_INTEREST_KEYWORDS = {
    "AI": ["人工智能", "机器学习", "深度学习", "神经网络", "NLP", "大模型", "AI", "算法", "模型训练", "强化学习", "transformer", "GPT", "LLM", "Agent", "智能体"],
    "编程": ["编程", "代码", "开发", "Python", "Java", "C++", "Rust", "Go", "前端", "后端", "全栈", "debug", "调试", "API", "接口", "框架", "Vue", "React", "Flask", "FastAPI", "Django", "Spring"],
    "工程实践": ["机器人", "硬件", "嵌入式", "电路", "机械", "动手", "搭建", "调试", "FTC", "FRC", "单片机", "Arduino", "树莓派", "stm32", "PCB", "焊接", "传感器"],
    "数学": ["数学", "统计", "概率", "线性代数", "微积分", "优化", "建模", "数论", "离散", "图论"],
    "哲学": ["哲学", "伦理", "意义", "存在", "认知", "意识", "思维", "价值观", "人生"],
    "创业": ["创业", "融资", "产品", "商业化", "市场", "用户", "增长", "商业模式", "BP", "路演", "孵化", "startup"],
    "科研": ["研究", "论文", "实验", "学术", "导师", "实验室", "文献", "课题", "发paper", "期刊", "会议", "综述", "方法论"],
    "社交": ["朋友", "社团", "聚会", "交流", "团队", "合作", "沟通", "组织", "活动", "社群", "学生会"],
    "艺术": ["音乐", "绘画", "设计", "摄影", "写作", "创作", "美学", "UI", "UX", "视觉", "排版", "字体", "颜色", "插画", "视频", "剪辑"],
    "运动": ["跑步", "健身", "篮球", "足球", "游泳", "锻炼", "运动", "健身", "体能", "比赛", "训练"],
    "心理学": ["心理", "情绪", "行为", "认知偏差", "MBTI", "人格", "性格", "潜意识"],
    "教育": ["教学", "课程", "学习", "知识", "教育", "培训", "指导", "mentor", "自学", "MOOC", "Coursera"],
    "游戏": ["游戏", "RPG", "FPS", "MOBA", "主机", "电竞", "game", "玩法", "关卡", "叙事"],
    "文学": ["文学", "小说", "诗歌", "阅读", "书籍", "经典", "科幻", "散文", "读书"],
    "经济": ["经济", "金融", "投资", "股票", "货币", "市场", "通胀", "理财"],
    "政治": ["政治", "政策", "国际关系", "外交", "治理", "民主", "制度", "社会学"],
    "生物": ["生物", "基因", "DNA", "细胞", "进化", "生态", "神经科学", "蛋白质"],
    "物理": ["物理", "量子", "力学", "光学", "电磁", "热力学", "相对论"],
    "化学": ["化学", "反应", "分子", "材料", "催化剂", "有机", "无机"],
    "法律": ["法律", "法规", "知识产权", "合同", "版权", "专利", "合规"],
}

_EMOTION_KEYWORDS = {
    EmotionType.POSITIVE: ["兴奋", "开心", "满足", "成就", "喜欢", "热爱", "有趣", "收获", "进步", "成功", "突破", "享受"],
    EmotionType.NEGATIVE: ["失落", "焦虑", "迷茫", "沮丧", "失败", "压力", "疲惫", "困惑", "孤独", "烦躁", "后悔"],
}

_BEHAVIOR_KEYWORDS = {
    "探索型": ["尝试", "探索", "发现", "新领域", "未知", "冒险", "好奇心"],
    "坚持型": ["坚持", "持续", "毅力", "努力", "克服", "不放弃"],
    "社交型": ["交流", "分享", "团队", "协作", "帮助", "讨论"],
    "创造型": ["创造", "构建", "设计", "制作", "创作", "开发"],
    "反思型": ["反思", "总结", "复盘", "思考", "回顾", "分析"],
}


def analyze_daily_record(content: str) -> dict:
    """
    对一段日常记录进行 AI 分析（MVP：规则引擎）。

    Returns:
        {
            "event": str,            # 核心事件摘要
            "emotion": str,          # positive/neutral/negative
            "interest_fields": [str],# 检测到的兴趣领域
            "behavior_patterns": [str], # 检测到的行为模式
            "long_term_impact": str, # 长期影响描述
            "persona_delta": dict,   # 人格增量
        }
    """
    result = {
        "event": "",
        "emotion": "neutral",
        "interest_fields": [],
        "behavior_patterns": [],
        "long_term_impact": "",
        "persona_delta": {},
    }

    # 1. 情绪检测
    pos_count = sum(1 for kw in _EMOTION_KEYWORDS[EmotionType.POSITIVE] if kw in content)
    neg_count = sum(1 for kw in _EMOTION_KEYWORDS[EmotionType.NEGATIVE] if kw in content)
    if pos_count > neg_count:
        result["emotion"] = "positive"
    elif neg_count > pos_count:
        result["emotion"] = "negative"

    # 2. 兴趣领域检测
    for field, keywords in _INTEREST_KEYWORDS.items():
        if any(kw in content for kw in keywords):
            result["interest_fields"].append(field)
            result["persona_delta"].setdefault(field.lower().replace(" ", "_"), 0)
            result["persona_delta"][field.lower().replace(" ", "_")] += 3

    # 3. 行为模式检测
    for pattern, keywords in _BEHAVIOR_KEYWORDS.items():
        if any(kw in content for kw in keywords):
            result["behavior_patterns"].append(pattern)
            key = pattern.rstrip("型").lower()
            result["persona_delta"].setdefault(key, 0)
            result["persona_delta"][key] += 2

    # 4. 事件摘要（取前80字作为事件描述）
    result["event"] = content[:80] + ("..." if len(content) > 80 else "")

    # 5. 长期影响（基于检测到的兴趣和模式生成自然语言描述）
    impacts = []
    if result["interest_fields"]:
        impacts.append(f"对{', '.join(result['interest_fields'][:3])}的兴趣增强")
    if result["behavior_patterns"]:
        impacts.append(f"表现出{', '.join(result['behavior_patterns'][:3])}倾向")

    if impacts:
        result["long_term_impact"] = "；".join(impacts)
    else:
        result["long_term_impact"] = "记录日常经历，积累人生数据"

    # 标记引擎来源
    result["engine"] = "rule_based"
    result["encouragement"] = ""
    result["outlook"] = ""
    result["emotion_detail"] = ""
    result["knowledge_domains"] = []
    result["search_insight"] = ""

    return result


def extract_memory_content(record_content: str, analysis: dict) -> str:
    """
    从日常记录中提炼语义记忆。
    这是 PRD 中 life_memories.memory_content 的生成逻辑。
    MVP 使用模板，后续接入 LLM。
    """
    parts = []
    if analysis.get("event"):
        parts.append(f"经历：{analysis['event'][:60]}")
    if analysis.get("interest_fields"):
        parts.append(f"兴趣领域：{', '.join(analysis['interest_fields'])}")
    if analysis.get("behavior_patterns"):
        parts.append(f"行为倾向：{', '.join(analysis['behavior_patterns'])}")
    if analysis.get("emotion") and analysis["emotion"] != "neutral":
        emo_map = {"positive": "积极体验", "negative": "消极体验"}
        parts.append(f"情绪：{emo_map.get(analysis['emotion'], analysis['emotion'])}")

    return "。".join(parts) + "。" if parts else record_content[:150]


async def process_daily_record(
    db: AsyncSession,
    record: DailyRecord,
    user_id: int,
) -> Optional[LifeMemory]:
    """
    处理一条日常记录：LLM 分析 → 存储分析结果 → 生成生命记忆

    LLM 可用时用 DeepSeek + 联网搜索；
    不可用时自动回退规则引擎。

    Returns:
        LifeMemory 对象，或 None（当重要性过低时跳过）
    """
    # 1. AI 分析（LLM 优先，规则引擎回退）
    from services.llm_service import analyze_journal, extract_memory_content_llm

    analysis = await analyze_journal(record.content, record.mood or "")

    # 2. 更新 DailyRecord
    record.ai_analysis = analysis
    await db.commit()

    # 3. 生成语义记忆（LLM 优先）
    memory_content = await extract_memory_content_llm(record.content, analysis)

    # 4. 重要性评分
    # LLM 模式下基于人格增量绝对值 + 知识领域数 + 兴趣领域数
    delta_sum = sum(abs(v) for v in analysis.get("persona_delta", {}).values())
    knowledge_count = len(analysis.get("knowledge_domains", []))
    interest_count = len(analysis.get("interest_fields", []))
    behavior_count = len(analysis.get("behavior_patterns", []))

    importance = min(0.95, 0.25 + delta_sum * 0.03 + knowledge_count * 0.08 + interest_count * 0.1 + behavior_count * 0.07)

    if importance < 0.35:
        return None  # 太普通，不值得存为长期记忆

    # 5. 存入 life_memories
    memory = LifeMemory(
        user_id=user_id,
        source_type="diary",
        source_id=record.id,
        memory_content=memory_content,
        importance_score=round(importance, 2),
        persona_impact=analysis.get("persona_delta", {}),
        embedding_id=f"ai_memory:daily:{record.id}",
        created_at=datetime.utcnow(),
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)

    return memory
