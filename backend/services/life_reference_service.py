"""人生参考服务 — 6 分类真实经历搜索（DuckDuckGo 爬知乎等），5 分钟缓存"""
import asyncio
import time
from datetime import datetime

QUERIES = {
    "kaoyan": ("考研深造", "考研 经验 知乎"),
    "job": ("求职就业", "求职 实习 经验 知乎"),
    "startup": ("创业经历", "大学生 创业 经历 知乎"),
    "cross": ("转行跨界", "转行 经历 经验 知乎"),
    "life": ("大学生活", "大学生活 感悟 知乎"),
    "failure": ("失败教训", "失败 教训 经历 知乎"),
}

_cache: dict = {}
_cache_ts: float = 0
CACHE_TTL = 300  # 5 分钟


def _search_bing(query: str) -> list[dict]:
    """必应中国版搜索（国内可用，解析 li.b_algo）"""
    import urllib.parse
    import urllib.request

    from bs4 import BeautifulSoup

    q = urllib.parse.quote(query)
    url = f"https://cn.bing.com/search?q={q}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    results = []
    for li in soup.select("li.b_algo"):
        a = li.select_one("h2 a")
        p = li.select_one(".b_caption p")
        if a:
            results.append({
                "title": a.get_text(strip=True)[:100],
                "url": a.get("href", ""),
                "snippet": (p.get_text(strip=True) if p else "")[:200],
                "source": "bing",
            })
    return results


def _search(query: str) -> list[dict]:
    """必应优先，DuckDuckGo 兜底"""
    try:
        items = _search_bing(query)
        if items:
            return items
    except Exception:
        pass
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=8))
        return [
            {"title": r.get("title", ""), "url": r.get("href", ""),
             "snippet": r.get("body", "")[:200], "source": "duckduckgo"}
            for r in results
            if r.get("title")
        ]
    except Exception:
        return []


async def get_references(category: str) -> dict:
    """获取某分类的真实经历参考（5 分钟缓存）"""
    global _cache, _cache_ts
    label, query = QUERIES.get(category, QUERIES["life"])

    if time.time() - _cache_ts < CACHE_TTL and category in _cache:
        return _cache[category]

    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(None, _search, query)

    result = {
        "category": category,
        "label": label,
        "items": items,
        "fetched_at": datetime.utcnow().isoformat(),
    }
    _cache[category] = result
    _cache_ts = time.time()
    return result
