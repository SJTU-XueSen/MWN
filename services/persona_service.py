"""
数字人格画像服务 — 从人生数据中提炼五维人格

五维：能力画像 / 兴趣画像 / 价值观画像 / 决策风格 / 行为画像
LLM 优先生成，规则引擎回退。
"""
import json
import logging
from datetime import datetime
from collections import defaultdict
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    PersonaProfile, LifeMemory, DailyRecord, LifeEvent,
    InterestTrack, LifeGoal,
)
from config import LLM_ENABLED

logger = logging.getLogger(__name__)


# ── 数据聚合 ──────────────────────────────────────────

async def _collect_user_data(db: AsyncSession, user_id: int) -> dict:
    """收集用户全部人生数据用于画像生成"""

    # 记录总数
    record_count = (await db.execute(
        select(func.count()).select_from(DailyRecord).where(DailyRecord.user_id == user_id)
    )).scalar() or 0

    # 事件总数
    event_count = (await db.execute(
        select(func.count()).select_from(LifeEvent).where(LifeEvent.user_id == user_id)
    )).scalar() or 0

    # 生命记忆（重要性排序，取前30条）
    memories = (await db.execute(
        select(LifeMemory).where(LifeMemory.user_id == user_id)
        .order_by(LifeMemory.importance_score.desc()).limit(30)
    )).scalars().all()

    # 兴趣追踪（去重最新值）
    tracks = (await db.execute(
        select(InterestTrack).where(InterestTrack.user_id == user_id)
        .order_by(InterestTrack.tracked_at.desc()).limit(50)
    )).scalars().all()
    latest_interests = {}
    for t in tracks:
        if t.field not in latest_interests:
            latest_interests[t.field] = t.score

    # 活跃目标
    goals = (await db.execute(
        select(LifeGoal).where(
            LifeGoal.user_id == user_id, LifeGoal.status == "active"
        )
    )).scalars().all()

    # AI 分析汇总（从 recent records 提取）
    records = (await db.execute(
        select(DailyRecord).where(DailyRecord.user_id == user_id)
        .order_by(DailyRecord.record_date.desc()).limit(30)
    )).scalars().all()

    all_interests = defaultdict(int)
    all_patterns = defaultdict(int)
    all_emotions = defaultdict(int)
    for r in records:
        if r.ai_analysis:
            for f in r.ai_analysis.get("interest_fields", []):
                all_interests[f] += 1
            for p in r.ai_analysis.get("behavior_patterns", []):
                all_patterns[p] += 1
            all_emotions[r.ai_analysis.get("emotion", "neutral")] += 1

    # 事件类型统计
    events = (await db.execute(
        select(LifeEvent).where(LifeEvent.user_id == user_id)
        .order_by(LifeEvent.occurred_at.desc()).limit(20)
    )).scalars().all()

    event_types = defaultdict(int)
    for e in events:
        event_types[e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type)] += 1

    return {
        "record_count": record_count,
        "event_count": event_count,
        "memory_count": len(memories),
        "top_memories": [m.memory_content[:100] for m in memories[:10]],
        "interests": dict(sorted(all_interests.items(), key=lambda x: -x[1])[:8]),
        "patterns": dict(sorted(all_patterns.items(), key=lambda x: -x[1])[:5]),
        "emotions": dict(all_emotions),
        "goals": [g.description for g in goals],
        "event_types": dict(event_types),
        "latest_interests": latest_interests,
    }


# ── 规则引擎生成 ──────────────────────────────────────

def _rule_based_persona(data: dict) -> dict:
    """基于统计规则生成简单画像"""

    # 人格类型推断
    top_interests = list(data["interests"].keys())[:3]
    top_patterns = list(data["patterns"].keys())[:2]

    if "探索型" in top_patterns and "创造型" in top_patterns:
        persona_type = "探索型创造者"
    elif "坚持型" in top_patterns:
        persona_type = "坚韧实践者"
    elif "社交型" in top_patterns:
        persona_type = "社交连接者"
    elif "反思型" in top_patterns:
        persona_type = "深度思考者"
    else:
        persona_type = "成长中的探索者"

    # 能力画像（中文维度名）
    record_count = max(data["record_count"], 1)
    ability = {
        "技术能力": min(95, data["interests"].get("AI", 0) * 8 + data["interests"].get("编程", 0) * 8 + 20),
        "创造力": min(95, data["interests"].get("艺术", 0) * 10 + data["patterns"].get("创造型", 0) * 15 + 20),
        "社交力": min(95, data["interests"].get("社交", 0) * 10 + data["patterns"].get("社交型", 0) * 15 + 20),
        "自我认知": min(95, data["patterns"].get("反思型", 0) * 15 + 25),
    }
    ability = {k: max(5, round(v)) for k, v in ability.items()}

    # 兴趣画像
    interest_profile = dict(data["latest_interests"]) if data["latest_interests"] else dict(data["interests"])
    interest_profile = {k: min(95, v) for k, v in sorted(interest_profile.items(), key=lambda x: -x[1])[:6]}

    # 价值观（从事件类型推断）
    values = {}
    et = data["event_types"]
    if et.get("competition", 0) + et.get("achievement", 0) > 0:
        values["成就导向"] = 70
    if et.get("social", 0) + et.get("relationship", 0) > 0:
        values["关系重视"] = 65
    if et.get("study", 0) + et.get("project", 0) > 3:
        values["求知欲"] = 80
    if et.get("turning_point", 0) + et.get("decision", 0) > 0:
        values["自主性"] = 75
    values["成长心态"] = 70
    value_profile = values

    # 决策风格
    decision = {
        "style": "数据积累中",
        "traits": top_patterns[:3] if top_patterns else ["待更多数据"],
    }

    # 行为画像
    behavior = dict(data["patterns"]) if data["patterns"] else {"记录不足": 0}

    # 置信度
    confidence = min(0.85, 0.2 + data["record_count"] * 0.03 + data["event_count"] * 0.05)

    # 摘要
    summary_parts = []
    if persona_type:
        summary_parts.append(f"你是一位{persona_type}")
    if top_interests:
        summary_parts.append(f"核心兴趣集中在{', '.join(top_interests)}")
    if data["record_count"] > 0:
        summary_parts.append(f"基于{data['record_count']}条记录和{data['event_count']}个重要事件生成")

    return {
        "persona_type": persona_type,
        "persona_summary": "。".join(summary_parts) + "。",
        "ability_profile": ability,
        "interest_profile": interest_profile,
        "value_profile": value_profile,
        "decision_style": decision,
        "behavior_profile": behavior,
        "confidence": round(confidence, 2),
        "engine": "rule_based",
    }


# ── LLM 生成 ──────────────────────────────────────────

async def _llm_persona(data: dict) -> Optional[dict]:
    """用 LLM 生成深度人格画像"""
    if not LLM_ENABLED:
        return None

    interests_text = "\n".join([f"- {k}: {v}次" for k, v in data["interests"].items()]) or "(无)"
    patterns_text = "\n".join([f"- {k}: {v}次" for k, v in data["patterns"].items()]) or "(无)"
    goals_text = "\n".join([f"- {g}" for g in data["goals"]]) or "(无)"
    memories_text = "\n".join([f"- {m}" for m in data["top_memories"]]) or "(无)"

    prompt = f"""你是一位专业的 AI 人格分析师。基于用户积累的人生数据，生成一份数字人格画像。

## 数据概况
- 日常记录数：{data['record_count']}
- 重要事件数：{data['event_count']}
- 生命记忆数：{data['memory_count']}

## 兴趣分布
{interests_text}

## 行为模式
{patterns_text}

## 活跃目标
{goals_text}

## 核心记忆片段
{memories_text}

## 请输出 JSON
{{
  "persona_type": "一个中文人格类型名称（如探索型创造者、坚韧实践者、深度连接者），反映核心特质",
  "persona_summary": "150字以内，温暖、有洞察力的人格概述",
  "ability_profile": {{
    "技术能力": 0-100,
    "创造力": 0-100,
    "社交力": 0-100,
    "自我认知": 0-100
  }},
  "interest_profile": {{
    "用中文命名领域": 0-100
  }},
  "value_profile": {{
    "用中文命名价值观": 0-100
  }},
  "decision_style": {{
    "style": "决策风格描述（如数据驱动型/直觉型/平衡型）",
    "traits": ["用中文描述特征1", "特征2", "特征3"]
  }},
  "behavior_profile": {{
    "用中文命名行为模式": 0-100
  }},
  "confidence": 0.0-1.0
}}

只返回 JSON。"""

    try:
        import httpx
        from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是专业的 AI 人格分析师，输出精确的 JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1500,
                    "response_format": {"type": "json_object"},
                },
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0]
                result = json.loads(content)
                result["engine"] = "deepseek"
                return result
    except Exception as e:
        logger.warning(f"LLM persona generation failed: {e}")

    return None


# ── 公开接口 ──────────────────────────────────────────

async def generate_persona(
    db: AsyncSession,
    user_id: int,
    trigger_event: str = "",
) -> PersonaProfile:
    """生成一份新的数字人格画像（标记为当前版本）"""

    # 1. 收集数据
    data = await _collect_user_data(db, user_id)

    # 2. 生成画像（LLM 优先）
    profile_data = await _llm_persona(data)
    if profile_data is None:
        profile_data = _rule_based_persona(data)

    # 3. 将旧版本标记为非当前
    await db.execute(
        update(PersonaProfile).where(
            PersonaProfile.user_id == user_id,
            PersonaProfile.is_current == True,
        ).values(is_current=False)
    )

    # 4. 获取版本号
    last_version = (await db.execute(
        select(func.max(PersonaProfile.version)).where(PersonaProfile.user_id == user_id)
    )).scalar() or 0

    # 5. 存入
    persona = PersonaProfile(
        user_id=user_id,
        version=last_version + 1,
        is_current=True,
        trigger_event=trigger_event or f"基于{data['record_count']}条记录自动生成",
        confidence=profile_data.get("confidence", 0.5),
        ability_profile=profile_data.get("ability_profile", {}),
        interest_profile=profile_data.get("interest_profile", {}),
        value_profile=profile_data.get("value_profile", {}),
        decision_style=profile_data.get("decision_style", {}),
        behavior_profile=profile_data.get("behavior_profile", {}),
        persona_type=profile_data.get("persona_type", "探索中"),
        persona_summary=profile_data.get("persona_summary", ""),
        generated_at=datetime.utcnow(),
    )
    db.add(persona)
    await db.commit()
    await db.refresh(persona)

    return persona


async def get_current_persona(db: AsyncSession, user_id: int) -> Optional[PersonaProfile]:
    """获取用户当前人格画像"""
    return (await db.execute(
        select(PersonaProfile).where(
            PersonaProfile.user_id == user_id,
            PersonaProfile.is_current == True,
        ).order_by(PersonaProfile.generated_at.desc()).limit(1)
    )).scalar_one_or_none()


async def get_persona_history(db: AsyncSession, user_id: int) -> list:
    """获取画像版本历史"""
    return (await db.execute(
        select(PersonaProfile).where(PersonaProfile.user_id == user_id)
        .order_by(PersonaProfile.version.desc())
    )).scalars().all()


async def get_persona_by_id(db: AsyncSession, persona_id: int) -> Optional[PersonaProfile]:
    """获取指定版本的画像"""
    return await db.get(PersonaProfile, persona_id)
