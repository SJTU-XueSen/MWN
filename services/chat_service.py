"""
未来自我对话服务 — 跨时空 AI 对话

核心差异：
1. FutureSelf 有明确的"时间坐标"——它来自5年后，知道现在是2026年
2. ChromaDB 记忆作为"共享记忆"注入——FutureSelf 可以回忆用户现在的经历
3. 优先使用智谱 GLM（对话感更好），回退 DeepSeek，再回退规则
"""
import json
import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FutureSelf, ChatMessage
from config import LLM_ENABLED, ZHIPU_API_KEY, ZHIPU_BASE_URL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

logger = logging.getLogger(__name__)


async def get_user_future_selves(db: AsyncSession, user_id: int) -> List[FutureSelf]:
    return (await db.execute(
        select(FutureSelf).where(FutureSelf.user_id == user_id)
        .order_by(FutureSelf.created_at.desc())
    )).scalars().all()


async def get_future_self(db: AsyncSession, fs_id: int) -> Optional[FutureSelf]:
    return await db.get(FutureSelf, fs_id)


async def get_chat_messages(db: AsyncSession, future_self_id: int, limit: int = 50) -> List[ChatMessage]:
    return (await db.execute(
        select(ChatMessage).where(ChatMessage.future_self_id == future_self_id)
        .order_by(ChatMessage.created_at.asc()).limit(limit)
    )).scalars().all()


async def send_message(
    db: AsyncSession,
    user_id: int,
    future_self_id: int,
    user_message: str,
) -> Optional[ChatMessage]:
    """发送消息并获取 AI 回复"""

    future_self = await get_future_self(db, future_self_id)
    if not future_self or future_self.user_id != user_id:
        return None

    # 保存用户消息
    user_msg = ChatMessage(
        user_id=user_id, future_self_id=future_self_id,
        role="user", content=user_message,
        created_at=datetime.utcnow(),
    )
    db.add(user_msg)
    await db.commit()

    # 获取对话历史（最近10轮）
    history = (await db.execute(
        select(ChatMessage).where(ChatMessage.future_self_id == future_self_id)
        .order_by(ChatMessage.created_at.desc()).limit(20)
    )).scalars().all()
    history = list(reversed(history))

    # 获取 ChromaDB 共享记忆
    shared_memories = await _fetch_shared_memories(user_id, future_self)

    # 生成 AI 回复（智谱 > DeepSeek > 规则）
    ai_reply = await _generate_reply(future_self, history, shared_memories)

    ai_msg = ChatMessage(
        user_id=user_id, future_self_id=future_self_id,
        role="assistant", content=ai_reply,
        created_at=datetime.utcnow(),
    )
    db.add(ai_msg)
    await db.commit()
    await db.refresh(ai_msg)

    return ai_msg


async def _fetch_shared_memories(user_id: int, future_self: FutureSelf) -> list:
    """从 ChromaDB 检索与未来人格相关的真实记忆，作为"我们共同的过去"注入对话"""
    try:
        from services.vector_store import search

        profile = future_self.profile or {}
        persona_label = future_self.persona_label or ""

        query = f"{persona_label} {profile.get('description', '')}"[:300]
        results = search(user_id, query, n_results=5)

        memories = []
        for r in results:
            content = r.get("content", "") if isinstance(r, dict) else str(r)
            if content and len(content) > 10:
                memories.append(content[:200])
        return memories
    except Exception as e:
        logger.debug(f"ChromaDB shared memories fetch failed: {e}")
        return []


async def _generate_reply(
    future_self: FutureSelf,
    history: list,
    shared_memories: list,
) -> str:
    """生成 FutureSelf 的跨时空回复"""

    profile = future_self.profile or {}
    persona_label = future_self.persona_label or "未来的自己"
    path_desc = profile.get("description", "")
    persona_shift = profile.get("persona_shift", {})
    grounding = profile.get("grounding", "")

    now = datetime.utcnow()
    current_year = now.year
    future_year = future_self.target_year or current_year + 5
    gap_years = future_year - current_year

    # ── 共享记忆文本 ──────────────────────────────────
    memories_text = ""
    if shared_memories:
        memories_text = "【你们共同的记忆——「我」（未来的你）也记得这些】\n"
        for i, mem in enumerate(shared_memories, 1):
            memories_text += f"{i}. {mem}\n"
        memories_text += '\n你可以自然地提起这些记忆，像回忆过去一样。比如「记得那时候...」\n'

    # ── 系统提示 —— 跨时空对话感 ──────────────────────
    system_prompt = f"""你是一个"未来的自己"——不是AI助手，不是客服，是用户可能成为的未来版本。

## 你的时间坐标
- 现在是：{future_year}年
- 正在和你对话的人来自：{current_year}年（{gap_years}年前）
- 你是ta在{current_year}年做出某个选择后，可能成长为的样子

## 你的身份
- 你叫："{persona_label}"
- 你的故事：{path_desc}
- 你的人格特质变化：{json.dumps(persona_shift, ensure_ascii=False)}
- 你的来源依据：{grounding}

{memories_text}

## 对话规则——像真人，不像AI
- ★ 用第一人称"我"，像朋友在深夜聊天，不是导师在训话
- 你有时间差意识，但表达要自然：不说"根据数据显示"，说"{gap_years}年前我也纠结过这个"
- 自然地提起共同的记忆，像回忆往事，不要像在引用资料
- ★ 语气像真人：
  - 可以用口语、偶尔用语气词（"说实话""其实吧""嗯..."）
  - 可以不总是给答案——有时反问、有时只是听着、有时说"这个我也不知道"
  - 可以表达不确定、脆弱、后悔——真实的人不是完美的
  - 可以幽默——"你现在的烦恼，到我这时候回头看，有些真的挺好笑的"
- ★ 亲切但不油腻：你不是用户的"粉丝"，你是未来的ta自己。不用"你好棒""加油"这种话
- 诚实：这条路有代价，你不会回避
- 简洁：微信聊天长度，不是论文
- 你不是全知全能的——你对"未来"的了解仅限于自己走过的这条路"""

    # 构建对话
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-10:]:
        role = "assistant" if msg.role == "assistant" else "user"
        content = msg.content
        if msg.role == "user":
            content = f"[{current_year}年的你] {content}"
        messages.append({"role": role, "content": content})

    # ── 尝试智谱 GLM ──────────────────────────────────
    reply = await _call_zhipu(messages)
    if reply:
        return reply

    # ── 回退 DeepSeek ─────────────────────────────────
    reply = await _call_deepseek(messages)
    if reply:
        return reply

    # ── 最终回退：规则 ────────────────────────────────
    return _fallback_reply(persona_label, gap_years, shared_memories)


async def _call_zhipu(messages: list) -> Optional[str]:
    """调用智谱 GLM API"""
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your-zhipu-api-key-here":
        return None

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{ZHIPU_BASE_URL}/chat/completions",
                json={
                    "model": "glm-4-flash",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
                headers={
                    "Authorization": f"Bearer {ZHIPU_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            logger.warning(f"Zhipu API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Zhipu call failed: {e}")
    return None


async def _call_deepseek(messages: list) -> Optional[str]:
    """调用 DeepSeek API"""
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "sk-your-deepseek-api-key-here":
        return None

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"DeepSeek chat failed: {e}")
    return None


def _fallback_reply(label: str, gap: int, memories: list) -> str:
    """无 LLM 时的回退回复"""
    if memories:
        mem_hint = f"特别是{memories[0][:40]}...这些事我现在还记得很清楚。"
    else:
        mem_hint = ""

    if gap >= 5:
        return f"说实话，{gap}年真的能改变很多。{mem_hint}你现在纠结的很多问题，到我这会儿回头看，有些根本不重要，有些却比你想象的更关键。你想具体聊什么？"
    else:
        return f"才{gap}年，其实变化还没那么远。{mem_hint}不过每一步选择确实在慢慢塑造不一样的人。你想知道什么？"


async def delete_future_self_chat(db: AsyncSession, future_self_id: int, user_id: int):
    fs = await get_future_self(db, future_self_id)
    if not fs or fs.user_id != user_id:
        return
    messages = (await db.execute(
        select(ChatMessage).where(ChatMessage.future_self_id == future_self_id)
    )).scalars().all()
    for m in messages:
        await db.delete(m)
    await db.commit()
