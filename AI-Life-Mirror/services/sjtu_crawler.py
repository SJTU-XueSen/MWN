"""SJTU 通知公告爬虫 — Python 异步版，并发控制等同 Node.js 版"""
import asyncio
import hashlib
import logging
import re
import time
from datetime import date, datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.sjtu.edu.cn"
LIST_URL = f"{BASE_URL}/tg"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36",
}
PAGE_CONCURRENCY = 10
DETAIL_CONCURRENCY = 8
CACHE_TTL = 1800  # 30 分钟

_cache = {"expires": 0, "data": None}
_semaphore = None


def _get_semaphore(limit: int) -> asyncio.Semaphore:
    return asyncio.Semaphore(limit)


def _sanitize_title(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip())


def _extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for sel in [".Article_content", ".article-content", "#vsb_content", ".v_news_content", ".content", ".pageMain"]:
        el = soup.select_one(sel)
        if el and len(el.get_text(strip=True)) > 80:
            return re.sub(r"\s+", " ", el.get_text(strip=True))
    return re.sub(r"\s+", " ", soup.body.get_text(strip=True)) if soup.body else ""


def _build_list_url(page: int) -> str:
    return f"{LIST_URL}/index.html" if page == 1 else f"{LIST_URL}/index_{page}.html"


def _create_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


# ── 关键词匹配规则 ──────────────────────────────────

_STUDENT_KEYWORDS = [
    "学生", "本科", "研究生", "博士生", "同学", "校园",
    "竞赛", "比赛", "创新创业", "社团", "志愿者", "报名",
    "讲座", "论坛", "沙龙", "征集", "招募", "奖学金",
    "实习", "就业", "创业", "项目", "课题", "课程",
]

_DATE_PATTERNS = [
    (r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})日?", "%Y-%m-%d"),
    (r"截止(?:日期|时间)[：:]\s*(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})日?", "%Y-%m-%d"),
    (r"报名(?:截止|时间)[：:]\s*(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})日?", "%Y-%m-%d"),
    (r"活动时间[：:]\s*(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})日?", "%Y-%m-%d"),
]


def _analyze(title: str, text: str, publish_date: str) -> dict:
    """分析通知是否与学生相关、是否未结束"""
    full = f"{title} {text[:2000]}"

    matched = [kw for kw in _STUDENT_KEYWORDS if kw in full]

    # 提取日期
    extracted_dates = []
    inferred_end = None
    for pattern, fmt in _DATE_PATTERNS:
        for m in re.finditer(pattern, full):
            try:
                d = f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
                if d not in extracted_dates:
                    extracted_dates.append(d)
                if inferred_end is None:
                    inferred_end = d
            except Exception:
                pass

    # 如果没有提取到截止日期，用发布日期 + 30 天
    if not inferred_end:
        try:
            pub = datetime.strptime(publish_date, "%Y-%m-%d")
            inferred_end = (pub.replace(day=min(pub.day + 30, 28))).strftime("%Y-%m-%d")
        except Exception:
            inferred_end = date.today().strftime("%Y-%m-%d")

    is_student = len(matched) >= 2
    is_ongoing = inferred_end >= date.today().strftime("%Y-%m-%d") if inferred_end else True
    summary = text[:200] if text else ""

    return {
        "isStudentRelated": is_student,
        "matchedKeywords": matched,
        "extractedDates": extracted_dates,
        "inferredEndDate": inferred_end,
        "relevanceReason": f"匹配关键词：{', '.join(matched)}" if matched else "未匹配学生关键词",
        "isOngoing": is_ongoing,
        "summary": summary,
    }


async def _fetch(client: httpx.AsyncClient, url: str) -> str:
    resp = await client.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


async def _evaluate(client: httpx.AsyncClient, notice: dict, as_of: date) -> dict:
    try:
        html = await _fetch(client, notice["url"])
        text = _extract_article_text(html)
        analysis = _analyze(notice["title"], text, notice["publishDate"])

        if not analysis["isStudentRelated"]:
            return {"reason": "not-student-related", "item": None}
        if not analysis["inferredEndDate"]:
            return {"reason": "no-end-date", "item": None}
        if analysis["inferredEndDate"] < as_of.strftime("%Y-%m-%d"):
            return {"reason": "already-ended", "item": None}

        return {"reason": "matched", "item": {
            "id": _create_id(notice["url"]),
            "title": notice["title"],
            "url": notice["url"],
            "publishDate": notice["publishDate"],
            "matchedKeywords": analysis["matchedKeywords"],
            "extractedDates": analysis["extractedDates"],
            "inferredEndDate": analysis["inferredEndDate"],
            "summary": analysis["summary"],
            "status": "ongoing",
            "relevanceReason": analysis["relevanceReason"],
        }}
    except Exception:
        return {"reason": "fetch-failed", "item": None}


async def get_activities(force_refresh: bool = False) -> dict:
    """主入口：获取活动列表，30 分钟缓存"""
    now = time.time()
    if not force_refresh and _cache["data"] and _cache["expires"] > now:
        return _cache["data"]

    as_of = date.today()
    sem = asyncio.Semaphore(PAGE_CONCURRENCY)

    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        # 获取第一页，确定总页数
        first_html = await _fetch(client, _build_list_url(1))
        total_match = re.search(r"totalPage:\s*(\d+)", first_html)
        total_pages = int(total_match.group(1)) if total_match else 1

        # 并发获取所有列表页
        async def _fetch_page(page: int):
            async with sem:
                if page == 1:
                    return first_html
                return await _fetch(client, _build_list_url(page))

        pages_html = await asyncio.gather(*[_fetch_page(p) for p in range(1, total_pages + 1)])

    # 解析列表
    all_notices = []
    seen = set()
    for html in pages_html:
        soup = BeautifulSoup(html, "lxml")
        for li in soup.select("ul.list-date li"):
            a = li.select_one("a")
            time_el = li.select_one(".time")
            if not a or not time_el:
                continue
            title = _sanitize_title(a.get("title", "") or a.get_text(strip=True))
            href = a.get("href", "")
            pub = time_el.get_text(strip=True).replace(".", "-")
            if not title or not href or not pub:
                continue
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            if url in seen:
                continue
            seen.add(url)
            if pub <= as_of.strftime("%Y-%m-%d"):
                all_notices.append({"title": title, "url": url, "publishDate": pub})

    # 过滤标题候选
    title_keywords = ["活动", "竞赛", "比赛", "讲座", "论坛", "报名", "通知", "征集", "招募", "项目"]
    candidates = [n for n in all_notices if any(kw in n["title"] for kw in title_keywords)]
    if len(candidates) < 5:
        candidates = all_notices[-50:]

    # 并发评估详情
    sem_detail = asyncio.Semaphore(DETAIL_CONCURRENCY)
    async with httpx.AsyncClient(verify=False, timeout=30) as client:

        async def _eval_one(notice):
            async with sem_detail:
                return await _evaluate(client, notice, as_of)

        evaluated = await asyncio.gather(*[_eval_one(n) for n in candidates])

    # 统计和筛选
    stats = {"scannedCount": len(all_notices), "matchedCount": 0,
             "filteredByReason": {"not-student-related": 0, "no-end-date": 0, "already-ended": 0, "fetch-failed": 0}}
    items = []
    for r in evaluated:
        if r["reason"] != "matched":
            stats["filteredByReason"][r["reason"]] = stats["filteredByReason"].get(r["reason"], 0) + 1
        if r["item"]:
            items.append(r["item"])

    items.sort(key=lambda x: x.get("inferredEndDate", ""), reverse=True)
    stats["matchedCount"] = len(items)

    result = {"asOfDate": as_of.strftime("%Y-%m-%d"), "source": LIST_URL, "stats": stats, "items": items}
    _cache["expires"] = now + CACHE_TTL
    _cache["data"] = result
    return result
