"""
联网搜索服务 — 为 LLM 分析提供专业术语背景知识

优先级：Wikipedia → DuckDuckGo
均为免费，无需 API Key
"""
import logging
import asyncio

logger = logging.getLogger(__name__)


async def search_context(query: str, max_chars: int = 2000) -> str:
    """
    搜索某个话题的背景知识。

    用于 LLM 分析遇到不熟悉的专业术语时，
    提供搜索上下文帮助理解。
    """
    # 1. 先试 Wikipedia（学术/专业术语覆盖好）
    wiki = await _search_wikipedia(query)
    if wiki:
        return wiki[:max_chars]

    # 2. 回退 DuckDuckGo
    ddg = await _search_ddg(query)
    return ddg[:max_chars] if ddg else ""


async def _search_wikipedia(query: str) -> str:
    """Wikipedia 搜索（中文优先）"""
    try:
        import wikipedia
        wikipedia.set_lang("zh")

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: wikipedia.search(query, results=3))
        if not results:
            return ""

        parts = []
        for title in results[:2]:
            try:
                summary = await loop.run_in_executor(
                    None,
                    lambda t=title: wikipedia.summary(t, sentences=3, auto_suggest=False),
                )
                parts.append(f"【Wikipedia: {title}】\n{summary}")
            except Exception:
                continue

        return "\n\n".join(parts) if parts else ""
    except Exception as e:
        logger.debug(f"Wikipedia search failed for '{query}': {e}")
        return ""


async def _search_ddg(query: str) -> str:
    """DuckDuckGo 文本搜索"""
    try:
        from duckduckgo_search import DDGS

        loop = asyncio.get_event_loop()

        def _do_search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=3))

        results = await loop.run_in_executor(None, _do_search)

        if not results:
            return ""

        parts = [f"【{r['title']}】\n{r['body']}" for r in results]
        return "\n\n".join(parts)
    except Exception as e:
        logger.debug(f"DuckDuckGo search failed for '{query}': {e}")
        return ""


async def extract_and_search(content: str) -> str:
    """
    从用户内容中提取关键概念，搜索后返回汇总上下文。

    策略：取内容中最具信息量的片段（长度 > 2 的非停用词词组）
    作为搜索关键词。
    """
    # MVP：直接以整段内容的前 100 字作为搜索 query
    # LLM 本身会从上下文理解，搜索提供补充
    query = content[:100].strip()
    if len(query) < 10:
        return ""

    return await search_context(query)
