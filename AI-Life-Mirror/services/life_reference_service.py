"""
真实人生参考服务 — 联网爬取大学生的真实经历

搜索知乎/小红书/贴吧/论坛中的真实人生故事，
附带原始链接，供用户参考学习。
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 分类与搜索词
CATEGORIES = {
    "kaoyan": {
        "label": "考研深造",
        "icon": "📚",
        "queries": [
            "我的考研经历 site:zhihu.com",
            "考研失败 我的故事 个人经历",
            "\"我考研\" \"经历\" site:zhihu.com",
        ],
    },
    "job": {
        "label": "求职就业",
        "icon": "💼",
        "queries": [
            "我的求职经历 应届生 site:zhihu.com",
            "找工作 我的故事 毕业生 个人经历",
            "\"我拿到了\" \"offer\" 经历 site:zhihu.com",
        ],
    },
    "startup": {
        "label": "创业经历",
        "icon": "🚀",
        "queries": [
            "我创业 经历 教训 site:zhihu.com",
            "创业失败 我的故事 个人经历",
            "\"我创业\" \"经历\" 分享",
        ],
    },
    "cross": {
        "label": "转行跨界",
        "icon": "🔄",
        "queries": [
            "我转行 经历 site:zhihu.com",
            "跨专业 我的故事 个人经历",
            "\"我放弃了\" \"选择了\" 职业 经历",
        ],
    },
    "life": {
        "label": "大学生活",
        "icon": "🎓",
        "queries": [
            "我的大学四年 经历 site:zhihu.com",
            "大学 遗憾 我的故事 个人经历",
            "\"我大学\" \"后悔\" 经历分享",
        ],
    },
    "failure": {
        "label": "失败教训",
        "icon": "💡",
        "queries": [
            "我的失败经历 教训 site:zhihu.com",
            "人生低谷 我是怎么走出来的 个人经历",
            "\"我失败\" \"教训\" 成长经历",
        ],
    },
}


async def search_category(category_key: str, user_context: str = "") -> list[dict]:
    """搜索某个分类下的真实经历，根据用户画像精准化"""
    cat = CATEGORIES.get(category_key)
    if not cat:
        return []

    all_results = []

    # 基础搜索词
    queries_to_run = cat["queries"][:2]

    # 如果知道用户的专业/兴趣，追加精准搜索
    if user_context:
        precision_query = f"{user_context} {cat['label']} 个人经历"
        queries_to_run = [precision_query] + queries_to_run[:1]

    for query in queries_to_run:
        try:
            results = await _search_ddg(query)
            all_results.extend(results)
        except Exception as e:
            logger.debug(f"Search failed for '{query}': {e}")

    # 去重
    seen = set()
    unique = []
    for r in all_results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            r["source_icon"] = _guess_source_icon(url)
            r["source_name"] = _guess_source_name(url)
            unique.append(r)

    return unique[:10]


async def _search_ddg(query: str) -> list[dict]:
    """DuckDuckGo 搜索"""
    try:
        from duckduckgo_search import DDGS

        loop = asyncio.get_event_loop()

        def _do():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=8))

        results = await loop.run_in_executor(None, _do)

        return [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            }
            for r in results
            if r.get("href") and r.get("title")
        ]
    except Exception as e:
        logger.debug(f"DDG search failed: {e}")
        return []


def _guess_source_name(url: str) -> str:
    """根据 URL 猜测来源平台名"""
    url_lower = url.lower()
    if "zhihu.com" in url_lower:
        return "知乎"
    if "xiaohongshu.com" in url_lower:
        return "小红书"
    if "tieba.baidu.com" in url_lower:
        return "百度贴吧"
    if "douban.com" in url_lower:
        return "豆瓣"
    if "bilibili.com" in url_lower:
        return "B站"
    if "csdn.net" in url_lower:
        return "CSDN"
    if "jianshu.com" in url_lower:
        return "简书"
    if "weixin.qq.com" in url_lower or "mp.weixin" in url_lower:
        return "微信公众号"
    if "sspai.com" in url_lower:
        return "少数派"
    if "v2ex.com" in url_lower:
        return "V2EX"
    if "github.com" in url_lower or "github.io" in url_lower:
        return "GitHub"
    if "huputiyu" in url_lower or "hupu.com" in url_lower:
        return "虎扑"
    return "网页"


def _guess_source_icon(url: str) -> str:
    name = _guess_source_name(url)
    icons = {
        "知乎": "💬", "小红书": "📕", "百度贴吧": "📋",
        "豆瓣": "📗", "B站": "📺", "CSDN": "💻",
        "简书": "✍️", "微信公众号": "📰", "少数派": "🔧",
        "V2EX": "🌐", "GitHub": "🐙", "虎扑": "🏀",
        "网页": "🔗",
    }
    return icons.get(name, "🔗")


def get_all_categories() -> dict:
    return CATEGORIES
