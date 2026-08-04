"""数字人格画像服务 — 五维人格，LLM 优先 + 规则引擎回退，多版本追踪

数据铁律：画像完全由用户真实数据（记录/事件/记忆/兴趣/行为）聚合而成，
数据不足时置信度诚实偏低，绝不虚构。
"""
import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import LLM_ENABLED
from backend.database.models import (
    DailyRecord,
    InterestTrack,
    LifeEvent,
    LifeGoal,
    LifeMemory,
    PersonaProfile,
)
from backend.services.llm_service import _call_deepseek, _parse_json_content

logger = logging.getLogger(__name__)


# ── 数据聚合 ──────────────────────────────────────────

async def _collect_user_data(db: AsyncSession, user_id: int) -> dict:
    """收集用户全部真实数据（画像生成的唯一素材）"""
    record_count = (
        await db.execute(select(func.count()).select_from(DailyRecord).where(DailyRecord.user_id == user_id))
    ).scalar() or 0
    event_count = (
        await db.execute(select(func.count()).select_from(LifeEvent).where(LifeEvent.user_id == user_id))
    ).scalar() or 0

    memories = (
        await db.execute(
            select(LifeMemory).where(LifeMemory.user_id == user_id)
            .order_by(LifeMemory.importance_score.desc()).limit(30)
        )
    ).scalars().all()

    tracks = (
        await db.execute(
            select(InterestTrack).where(InterestTrack.user_id == user_id)
            .order_by(InterestTrack.tracked_at.desc()).limit(50)
        )
    ).scalars().all()
    latest_interests: dict = {}
    for t in tracks:
        latest_interests.setdefault(t.field, t.score)

    from backend.services.activity_service import REFERENCE_CATEGORY_MAP, get_reference_interests

    ref_data = await get_reference_interests(db, user_id)
    ref_weights = {cat: count * 3 for cat, count in ref_data.get("category_counts", {}).items()}

    goals = (
        await db.execute(
            select(LifeGoal).where(LifeGoal.user_id == user_id, LifeGoal.status == "active")
        )
    ).scalars().all()

    records = (
        await db.execute(
            select(DailyRecord).where(DailyRecord.user_id == user_id)
            .order_by(DailyRecord.record_date.desc()).limit(30)
        )
    ).scalars().all()

    all_interests: dict = defaultdict(int)
    all_patterns: dict = defaultdict(int)
    all_emotions: dict = defaultdict(int)
    for r in records:
        if r.ai_analysis:
            for f in r.ai_analysis.get("interest_fields", []):
                all_interests[f] += 1
            for p in r.ai_analysis.get("behavior_patterns", []):
                all_patterns[p] += 1
            all_emotions[r.ai_analysis.get("emotion", "neutral")] += 1

    events = (
        await db.execute(
            select(LifeEvent).where(LifeEvent.user_id == user_id)
            .order_by(LifeEvent.occurred_at.desc()).limit(20)
        )
    ).scalars().all()
    event_types: dict = defaultdict(int)
    for e in events:
        event_types[e.event_type] += 1

    boosted_interests = dict(all_interests)
    for cat_name, weight in ref_weights.items():
        mapped = REFERENCE_CATEGORY_MAP.get(cat_name, cat_name)
        boosted_interests[mapped] = boosted_interests.get(mapped, 0) + weight

    return {
        "record_count": record_count,
        "event_count": event_count,
        "memory_count": len(memories),
        "top_memories": [m.memory_content[:100] for m in memories[:10]],
        "interests": dict(sorted(boosted_interests.items(), key=lambda x: -x[1])[:8]),
        "patterns": dict(sorted(all_patterns.items(), key=lambda x: -x[1])[:5]),
        "emotions": dict(all_emotions),
        "goals": [g.description or g.title for g in goals],
        "event_types": dict(event_types),
        "latest_interests": latest_interests,
        "ref_weights": ref_weights,
        "ref_insight": ref_data.get("insight", ""),
    }


# ── 规则引擎生成 ──────────────────────────────────────

def _rule_based_persona(data: dict) -> dict:
    """基于统计规则生成画像（LLM 不可用时的兜底，诚实低分优先）"""
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

    ability = {
        "技术能力": min(95, data["interests"].get("AI", 0) * 8 + data["interests"].get("编程", 0) * 8 + 20),
        "创造力": min(95, data["interests"].get("艺术", 0) * 10 + data["patterns"].get("创造型", 0) * 15 + 20),
        "社交力": min(95, data["interests"].get("社交", 0) * 10 + data["patterns"].get("社交型", 0) * 15 + 20),
        "自我认知": min(95, data["patterns"].get("反思型", 0) * 15 + 25),
    }
    ability = {k: max(5, round(v)) for k, v in ability.items()}

    interest_profile = dict(data["latest_interests"]) if data["latest_interests"] else dict(data["interests"])
    interest_profile = {k: min(95, v) for k, v in sorted(interest_profile.items(), key=lambda x: -x[1])[:6]}

    values: dict = {}
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

    decision = {"style": "数据积累中", "traits": top_patterns[:3] if top_patterns else ["待更多数据"]}
    behavior = dict(data["patterns"]) if data["patterns"] else {"记录不足": 0}
    confidence = min(0.85, 0.2 + data["record_count"] * 0.03 + data["event_count"] * 0.05)

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
        "value_profile": values,
        "decision_style": decision,
        "behavior_profile": behavior,
        "confidence": round(confidence, 2),
        "engine": "rule_based",
    }


# ── LLM 生成 ──────────────────────────────────────────

async def _llm_persona(data: dict):
    """LLM 生成深度画像（失败返回 None → 规则回退）"""
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
  "ability_profile": {{"技术能力": 0-100, "创造力": 0-100, "社交力": 0-100, "自我认知": 0-100}},
  "interest_profile": {{"用中文命名领域": 0-100}},
  "value_profile": {{"用中文命名价值观": 0-100}},
  "decision_style": {{"style": "决策风格描述（如数据驱动型/直觉型/平衡型）", "traits": ["用中文描述特征1", "特征2", "特征3"]}},
  "behavior_profile": {{"用中文命名行为模式": 0-100}},
  "confidence": 0.0-1.0
}}

★ 约束：
- 所有维度必须从上面给出的用户真实数据中推断——数据中没有的领域不要硬编
- 数据稀少时 confidence 必须诚实偏低（<0.5），并用 persona_summary 说明当前样本有限
- 不要贴人格标签式定性（如"你是逃避型"），用"经历中出现过…"的表达
- 只返回 JSON。"""

    raw = await _call_deepseek("你是专业的 AI 人格分析师，输出精确的 JSON。", prompt, temperature=0.3, max_tokens=1500)
    result = _parse_json_content(raw) if raw else None
    if result:
        result["engine"] = "deepseek"
    return result


# ── 公开接口 ──────────────────────────────────────────

async def generate_persona(db: AsyncSession, user_id: int, trigger_event: str = "") -> PersonaProfile:
    """生成新版本人格画像（旧版本标记为非当前）"""
    data = await _collect_user_data(db, user_id)

    profile_data = await _llm_persona(data)
    if profile_data is None:
        profile_data = _rule_based_persona(data)

    await db.execute(
        update(PersonaProfile)
        .where(PersonaProfile.user_id == user_id, PersonaProfile.is_current == True)
        .values(is_current=False)
    )
    last_version = (
        await db.execute(select(func.max(PersonaProfile.version)).where(PersonaProfile.user_id == user_id))
    ).scalar() or 0

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


async def get_current_persona(db: AsyncSession, user_id: int):
    return (
        await db.execute(
            select(PersonaProfile).where(
                PersonaProfile.user_id == user_id, PersonaProfile.is_current == True
            ).order_by(PersonaProfile.generated_at.desc()).limit(1)
        )
    ).scalar_one_or_none()


async def get_persona_history(db: AsyncSession, user_id: int) -> list:
    return (
        await db.execute(
            select(PersonaProfile).where(PersonaProfile.user_id == user_id)
            .order_by(PersonaProfile.version.desc())
        )
    ).scalars().all()


async def get_persona_by_id(db: AsyncSession, persona_id: int):
    return await db.get(PersonaProfile, persona_id)


# ── 自动更新阈值 ──────────────────────────────────────

async def should_regenerate_persona(db: AsyncSession, user_id: int) -> tuple[bool, str]:
    """无人格且数据≥3条 → 生成；有人格且新增≥5条 或 >24h 且新增≥3条 → 更新"""
    current = await get_current_persona(db, user_id)
    record_count = (
        await db.execute(select(func.count()).select_from(DailyRecord).where(DailyRecord.user_id == user_id))
    ).scalar() or 0
    event_count = (
        await db.execute(select(func.count()).select_from(LifeEvent).where(LifeEvent.user_id == user_id))
    ).scalar() or 0
    total_data = record_count + event_count

    if not current:
        if total_data >= 3:
            return True, f"首次生成：基于{total_data}条记录"
        return False, ""

    new_records = (
        await db.execute(
            select(func.count()).select_from(DailyRecord).where(
                DailyRecord.user_id == user_id, DailyRecord.created_at > current.generated_at
            )
        )
    ).scalar() or 0
    new_events = (
        await db.execute(
            select(func.count()).select_from(LifeEvent).where(
                LifeEvent.user_id == user_id, LifeEvent.occurred_at > current.generated_at
            )
        )
    ).scalar() or 0
    total_new = new_records + new_events
    hours_since = (datetime.utcnow() - current.generated_at).total_seconds() / 3600

    if total_new >= 5:
        return True, f"自动更新：新增{total_new}条记录"
    if hours_since > 24 and total_new >= 3:
        return True, f"自动更新：距上次{hours_since:.0f}小时，新增{total_new}条"
    return False, ""


async def regenerate_persona_background(user_id: int, trigger: str):
    """后台异步重新生成人格（独立 DB session）"""
    from backend.database.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            await generate_persona(db, user_id, trigger)
            logger.info(f"✅ 人格已更新 user={user_id}: {trigger}")
    except Exception as e:
        logger.error(f"❌ 后台人格更新失败 user={user_id}: {e}")
