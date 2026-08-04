"""联网搜索背景 — Wikipedia（中文优先）→ DuckDuckGo，免费无需 key"""
import asyncio
import logging

logger = logging.getLogger(__name__)


def _search_wikipedia(query: str) -> str:
    try:
        import wikipedia

        wikipedia.set_lang("zh")
        results = wikipedia.search(query, results=3)
        if results:
            try:
                page = wikipedia.page(results[0])
                return page.summary[:500]
            except Exception:
                return ""
    except Exception as e:
        logger.debug(f"Wikipedia search failed: {e}")
    return ""


def _search_duckduckgo(query: str) -> str:
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if results:
            snippets = [r.get("body", "")[:200] for r in results if r.get("body")]
            return "\n".join(snippets)[:800]
    except Exception as e:
        logger.debug(f"DuckDuckGo search failed: {e}")
    return ""


async def extract_and_search(query: str) -> str:
    """异步搜索，返回背景文本（最多 ~800 字）"""
    loop = asyncio.get_event_loop()
    results = await asyncio.gather(
        loop.run_in_executor(None, _search_wikipedia, query),
        loop.run_in_executor(None, _search_duckduckgo, query),
    )
    combined = "\n".join(r for r in results if r)
    return combined[:900]
