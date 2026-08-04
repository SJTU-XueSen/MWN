"""LLM 统一分析层 — DeepSeek 驱动，全部失败回退规则引擎

数据铁律：分析结果必须锚定用户真实输入；无 LLM 时规则引擎兜底，
保证任何情况下都有基于数据（而非编造）的输出。
"""
import json
import logging
from typing import Optional

import httpx

from backend.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_ENABLED
from backend.services.search_service import extract_and_search

logger = logging.getLogger(__name__)


# ── 系统提示词（诚实镜子风格）────────────────────────

JOURNAL_SYSTEM_PROMPT = """你是一位诚实而有洞察力的 AI 人生分析师。你不是用户的朋友或啦啦队——你是一面诚实的镜子，既反映闪光点，也照出盲区。

## 你的任务
分析用户的大学生活记录，输出结构化的 JSON。你的价值在于诚实——粉饰太平对用户没有任何帮助。

## 分析维度
1. **event**: 核心事件摘要，30字以内
2. **emotion**: 整体情绪倾向（positive/neutral/negative）
3. **emotion_detail**: 情绪细节，捕捉矛盾情感（如"迷茫中带着激情""疲惫却充实"）
4. **interest_fields**: 涉及的兴趣领域，中文通用名
5. **behavior_patterns**: 行为模式标签（探索型/坚持型/社交型/创造型/反思型/主动型/回避型/拖延型）
6. **long_term_impact**: 对个人成长的潜在长期影响，40字以内
7. **persona_delta**: 人格维度影响值（-10 到 +10）
8. **knowledge_domains**: 专业/知识领域
9. **search_insight**: 搜索背景解读，无搜索时留空
10. **encouragement**: 真诚的肯定——找到具体的闪光点，不要泛泛而谈。但如果没有值得鼓励的，宁可简短也不要硬编
11. **outlook**: 展望总结，60字以内
12. **honest_reflection**: ★ 诚实的反思。如果用户展示了回避、拖延、三分钟热度、自我欺骗、不自律等倾向——温和但直接地指出来。如果这周什么都没做却说"想了很多"，指出"想"和"做"之间的差距。如果一直在重复同样的"开始"却从未坚持，指出这个循环

## 输出格式
只返回 JSON：
{
  "event": "...",
  "emotion": "positive",
  "emotion_detail": "...",
  "interest_fields": ["..."],
  "behavior_patterns": ["..."],
  "long_term_impact": "...",
  "persona_delta": {"维度名": 数值},
  "knowledge_domains": ["..."],
  "search_insight": "...",
  "encouragement": "...",
  "outlook": "...",
  "honest_reflection": "..."
}

## 关键原则
- ★ 诚实优先于温暖。如果用户表现出怠惰、拖延或自我欺骗，直接指出来。好的镜子不会只照好看的角度
- 情绪判断看语境不看表面词。"输了一场比赛但收获了成长"可能是 positive；"又刷了一天手机但告诉自己'在放松'"——这不是放松，是回避
- 鼓励要具体，不应付。如果没有闪光点，honest_reflection 比空洞的 encouragement 更有价值
- 如果搜索上下文包含相关专业知识，在 knowledge_domains 和 search_insight 中体现
"""

EVENT_SYSTEM_PROMPT = """你是一位诚实而有洞察力的 AI 人生分析师。你在分析一个用户标记的"重要人生事件"。你不是啦啦队——你是镜子，分析应该像日常记录一样有深度。

## 你的任务
分析这个人生事件，输出结构化的 JSON。分析粒度应不低于日常记录分析。

## 分析维度
1. **emotion**: 整体情绪倾向 (positive/neutral/negative)，注意理解语境
2. **emotion_detail**: 情绪细节，捕捉微妙的矛盾感受
3. **interest_tags**: 关联的兴趣领域标签（如"机器人""机器学习""文学创作"）
4. **behavior_patterns**: ★ 从这个事件中反映出的行为模式（探索型/坚持型/社交型/创造型/反思型/回避型/拖延型等）
5. **ai_impact**: 综合分析这个事件对用户的影响，60字以内
6. **long_term_impact**: ★ 此事件对个人成长的潜在长期影响，40字以内
7. **persona_delta**: 人格维度影响值（-10 到 +10）
8. **knowledge_domains**: 涉及的专业/知识领域
9. **search_insight**: 结合搜索背景解读，无搜索时留空
10. **encouragement**: 真诚的肯定，具体不浮夸。没有闪光点就简短，不要硬编
11. **outlook**: 展望总结，60字以内
12. **honest_reflection**: ★ 诚实的反思。如果这个事件反映了三分钟热度、半途而废、从失败中没有吸取教训、重复犯同样的错——直接指出来。如果用户把一次普通经历拔高成"人生转折"——温和地给出更客观的视角

## 输出格式
只返回 JSON：
{
  "emotion": "positive",
  "emotion_detail": "...",
  "interest_tags": ["..."],
  "behavior_patterns": ["..."],
  "ai_impact": "...",
  "long_term_impact": "...",
  "persona_delta": {"维度": 数值},
  "knowledge_domains": ["..."],
  "search_insight": "...",
  "encouragement": "...",
  "outlook": "...",
  "honest_reflection": "..."
}

## 关键原则
- ★ 人生事件比日常记录更重要——分析深度和诚实程度应该更高，而不是更低
- 不要因为用户标记为"重要事件"就默认都是正面的。一次失败如果能学到东西就是成长，一次"成就"如果纯属运气就不应过度鼓励
- 诚实优先。好的镜子不会因为事件被标记为"重要"就只挑好话说
"""


# ── LLM 客户端 ────────────────────────────────────────

async def _call_deepseek(
    system_prompt: str,
    user_content: str,
    search_context: str = "",
    temperature: float = 0.3,
    max_tokens: int = 1200,
    json_mode: bool = True,
) -> Optional[str]:
    """调用 DeepSeek Chat API，返回原始文本（调用方自行解析）"""
    if not LLM_ENABLED or not DEEPSEEK_API_KEY:
        return None

    messages = [{"role": "system", "content": system_prompt}]
    user_message = f"用户内容：\n{user_content}"
    if search_context:
        user_message += f"\n\n搜索上下文（帮助你理解专业术语）：\n{search_context}"
    messages.append({"role": "user", "content": user_message})

    payload: dict = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions", json=payload, headers=headers
            )
            if resp.status_code != 200:
                logger.warning(f"DeepSeek API error {resp.status_code}: {resp.text[:300]}")
                return None
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"DeepSeek API call failed: {e}")
        return None


def _parse_json_content(content: str) -> Optional[dict]:
    """解析 LLM 输出，处理 markdown 代码块包装"""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        if content.startswith("json\n"):
            content = content[5:]
    try:
        return json.loads(content)
    except Exception:
        return None


# ── 公开接口 ──────────────────────────────────────────

async def analyze_journal(content: str, mood: str = "") -> dict:
    """LLM 分析日常记录 → 规则引擎回退"""
    from backend.services.memory_service import analyze_daily_record as rule_based

    result = {
        "event": "",
        "emotion": "neutral",
        "emotion_detail": "",
        "interest_fields": [],
        "behavior_patterns": [],
        "long_term_impact": "",
        "persona_delta": {},
        "knowledge_domains": [],
        "search_insight": "",
        "encouragement": "",
        "outlook": "",
        "engine": "rule_based",
    }
    if not LLM_ENABLED:
        return rule_based(content)

    search_context = ""
    try:
        search_context = await extract_and_search(content)
    except Exception:
        pass

    user_content = f"【用户自述心情】{mood}\n\n【记录内容】\n{content}" if mood else content
    raw = await _call_deepseek(JOURNAL_SYSTEM_PROMPT, user_content, search_context)
    if raw is None:
        return rule_based(content)

    llm_result = _parse_json_content(raw)
    if llm_result is None:
        return rule_based(content)

    result.update(llm_result)
    result["engine"] = "deepseek"
    result.setdefault("event", content[:80] + ("..." if len(content) > 80 else ""))
    result.setdefault("emotion", "neutral")
    result.setdefault("interest_fields", [])
    result.setdefault("behavior_patterns", [])
    result.setdefault("long_term_impact", "")
    result.setdefault("persona_delta", {})
    result.setdefault("encouragement", "")
    result.setdefault("outlook", "")
    return result


async def analyze_event(title: str, description: str, event_type: str) -> dict:
    """LLM 分析人生事件 → 规则引擎回退 + 规则补足"""
    from backend.services.event_service import analyze_event as rule_based

    result = {
        "emotion": "neutral",
        "emotion_detail": "",
        "interest_tags": [],
        "behavior_patterns": [],
        "ai_impact": "",
        "long_term_impact": "",
        "persona_delta": {},
        "knowledge_domains": [],
        "search_insight": "",
        "encouragement": "",
        "outlook": "",
        "honest_reflection": "",
        "engine": "rule_based",
    }
    if not LLM_ENABLED:
        return rule_based(title, description, event_type)

    search_context = ""
    try:
        search_context = await extract_and_search(f"{title} {description}")
    except Exception:
        pass

    user_content = f"事件类型：{event_type}\n事件标题：{title}\n事件描述：{description or '(无)'}"
    raw = await _call_deepseek(EVENT_SYSTEM_PROMPT, user_content, search_context)
    if raw is None:
        return rule_based(title, description, event_type)

    llm_result = _parse_json_content(raw)
    if llm_result is None:
        return rule_based(title, description, event_type)

    result.update(llm_result)
    result["engine"] = "deepseek"
    for key, default in (
        ("emotion", "neutral"), ("interest_tags", []), ("ai_impact", ""),
        ("persona_delta", {}), ("encouragement", ""), ("outlook", ""),
        ("honest_reflection", ""), ("behavior_patterns", []), ("long_term_impact", ""),
    ):
        result.setdefault(key, default)

    # ★ LLM 结果用规则引擎补足深度和具体性
    rb = rule_based(title, description, event_type)
    if not result["interest_tags"]:
        result["interest_tags"] = rb.get("interest_tags", [])
    if not result["behavior_patterns"]:
        result["behavior_patterns"] = rb.get("behavior_patterns", [])
    if not result["persona_delta"]:
        result["persona_delta"] = rb.get("persona_delta", {})
    llm_impact = result.get("ai_impact", "")
    rb_impact = rb.get("ai_impact", "")
    if not llm_impact or len(llm_impact) < 80:
        result["ai_impact"] = rb_impact
    elif len(llm_impact) < 200:
        result["ai_impact"] = llm_impact + "。" + rb_impact
    if not result.get("encouragement"):
        result["encouragement"] = rb.get("encouragement", "")
    if not result.get("outlook"):
        result["outlook"] = rb.get("outlook", "")
    if not result.get("honest_reflection"):
        result["honest_reflection"] = rb.get("honest_reflection", "")
    if not result.get("emotion_detail"):
        result["emotion_detail"] = rb.get("emotion_detail", "")
    return result


async def extract_memory_content_llm(record_content: str, analysis: dict) -> str:
    """从记录+分析提炼一句话生命记忆，失败回退模板拼接"""
    from backend.services.memory_service import extract_memory_content

    if not LLM_ENABLED:
        return extract_memory_content(record_content, analysis)

    prompt = """从以下大学生活记录和分析结果中，提炼一句话的"生命记忆"。
这句话将被存入长期记忆库，用于未来构建数字人格。
要求：精炼、有洞察力、突出关键转折和成长点（40字以内）。
只返回这句话，不要额外文字。"""
    user_content = f"记录：{record_content[:300]}\n分析：{json.dumps(analysis, ensure_ascii=False)}"
    raw = await _call_deepseek(
        prompt, user_content, temperature=0.3, max_tokens=200, json_mode=False
    )
    if raw:
        return raw
    return extract_memory_content(record_content, analysis)
