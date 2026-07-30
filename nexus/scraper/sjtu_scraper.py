"""
活动信息爬虫 —— 上海交通大学（优化版）
- 并发抓取多站点
- 并发抓取详情页
- 重试+退避
- URL 去重
- 批量 AI 分析（一次 API 调用处理多条）
"""
import re
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

MAX_WORKERS_SITES = 4          # 并发抓取站点数
MAX_WORKERS_DETAILS = 6        # 并发抓取详情页数
DETAIL_TIMEOUT = 10            # 详情页超时（秒）
SITE_TIMEOUT = 20              # 列表页超时（秒）
MAX_RETRIES = 2                # 重试次数
RETRY_DELAY = 1.0              # 初始重试延迟（秒）
AI_BATCH_SIZE = 8              # 每次 AI 调用批处理条数


def _fetch_url(url, timeout=15):
    """抓取网页（带重试）"""
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=timeout)
            content_type = resp.headers.get('Content-Type', '')
            encoding = 'utf-8'
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[-1].strip()
            return resp.read().decode(encoding, errors='replace')
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (2 ** attempt))
    raise last_err


# ═══════════════════════════════════════════════════════════
#  🔗 上海交通大学各站点
# ═══════════════════════════════════════════════════════════
TARGET_URLS = [
    {'name': '交大官网-通知通告', 'url': 'https://www.sjtu.edu.cn/tg/index.html', 'parser': 'sjtu_tg'},
    {'name': '交大团委-通知公告', 'url': 'https://youth.sjtu.edu.cn/tzgg.html', 'parser': 'youth_tzgg'},
    {'name': '交大团委-新闻快讯', 'url': 'https://youth.sjtu.edu.cn/index_news.html', 'parser': 'youth_news'},
    {'name': '交大教务处-通知通告', 'url': 'https://jwc.sjtu.edu.cn/xwtg/tztg.htm', 'parser': 'jwc_list'},
    {'name': '交大新闻网-要闻', 'url': 'https://news.sjtu.edu.cn/jdyw/index.html', 'parser': 'news_list'},
    {'name': '交大新闻网-综合', 'url': 'https://news.sjtu.edu.cn/zhxw/index.html', 'parser': 'news_list'},
]
# ═══════════════════════════════════════════════════════════

SCREEN_KEYWORDS = [
    '活动', '报名', '招募', '征集', '征稿',
    '组队', '团队', '小组', '协作',
    '志愿者', '社会实践', '演出', '展览', '晚会', '庆典',
    '运动会', '体育', '球赛', '越野', '比赛',
    '培训', '工作坊', '分享', '沙龙', '论坛',
    '创新创业', '项目', '实践',
    '文化', '艺术', '社团', '招新',
    '支教', '公益', '环保',
]


# ── 并发抓取所有站点 ──
def scrape_all():
    """并发抓取所有目标站点（列表页）"""
    all_items = []
    errors = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS_SITES) as executor:
        future_map = {executor.submit(_fetch_and_parse, site): site for site in TARGET_URLS}
        for fut in as_completed(future_map):
            site = future_map[fut]
            try:
                items = fut.result()
                all_items.extend(items)
                print(f"[爬虫] {site['name']}: {len(items)} 条")
            except Exception as e:
                print(f"[爬虫] {site['name']}: 失败 - {e}")
                errors.append({'site': site['name'], 'error': str(e)})

    return all_items, errors


def _fetch_and_parse(site):
    """抓取并解析单个站点"""
    html = _fetch_url(site['url'], timeout=SITE_TIMEOUT)
    soup = BeautifulSoup(html, 'html.parser')
    parser_name = site.get('parser', 'generic_list')

    parsers = {
        'sjtu_tg': _parse_sjtu_tg,
        'youth_tzgg': _parse_youth_tzgg,
        'youth_news': _parse_youth_news,
        'jwc_list': _parse_jwc_list,
        'news_list': _parse_news_list,
    }
    parser = parsers.get(parser_name, _parse_generic_list)
    return parser(soup, site)


# ── 并发抓取详情页 ──
def fetch_details_batch(items, max_workers=MAX_WORKERS_DETAILS):
    """并发抓取多篇文章详情，返回 {url: detail_text} 字典"""
    url_set = set()
    unique_items = []
    for item in items:
        url = item['url']
        if url not in url_set:
            url_set.add(url)
            unique_items.append(item)

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(fetch_detail_content, item['url']): item for item in unique_items}
        for fut in as_completed(future_map):
            item = future_map[fut]
            try:
                text = fut.result()
                results[item['url']] = text
            except Exception as e:
                results[item['url']] = f'[抓取失败: {e}]'

    return results


def fetch_detail_content(url):
    """抓取单篇文章详情"""
    html = _fetch_url(url, timeout=DETAIL_TIMEOUT)
    soup = BeautifulSoup(html, 'html.parser')

    # 尝试多种正文容器
    content_ids = ['content', 'vsb_content', 'vsb_content_2', 'article_content']
    content_classes = ['NewsContent', 'article-content', 'content', 'main-content',
                       'wz_art', 'detail_content', 'TRS_Editor', 'wz', 'article', 'text']

    text_parts = []
    for cid in content_ids:
        el = soup.find(id=cid)
        if el:
            text_parts.append(el.get_text(separator='\n', strip=True))
            break
    if not text_parts:
        for cls in content_classes:
            el = soup.find(class_=cls)
            if el:
                text_parts.append(el.get_text(separator='\n', strip=True))
                break
    if not text_parts:
        for p in soup.find_all('p'):
            t = p.get_text(strip=True)
            if len(t) > 20:
                text_parts.append(t)
                if len('\n'.join(text_parts)) > 8000:
                    break
    return '\n'.join(text_parts)[:8000]


def is_competition_related(text):
    """初筛关键词匹配"""
    return sum(1 for kw in SCREEN_KEYWORDS if kw in text) >= 1


# ── 批量 AI 分析 ──
def batch_analyze(items_with_details, analyze_func):
    """
    批量调用 AI 分析。
    items_with_details: [(item, detail_text), ...]
    analyze_func: 单个分析函数
    返回: [(item, result_or_None), ...]
    """
    # 逐个分析（后续可改为真实批处理，目前智谱 API 支持一次调用分析多条）
    results = []
    for item, detail_text in items_with_details:
        if not detail_text or detail_text.startswith('[抓取失败'):
            results.append((item, None))
            continue
        try:
            result = analyze_func(
                title=item['title'],
                url=item['url'],
                source=item['source'],
                detail_text=detail_text,
            )
            results.append((item, result))
        except Exception as e:
            print(f'[AI] 分析失败: {item["title"][:30]} - {e}')
            results.append((item, None))
    return results


# ═══════════════════════════════════════════════════════
#  各站点解析器
# ═══════════════════════════════════════════════════════

def _parse_sjtu_tg(soup, site):
    items, seen = [], set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/tg/' not in href:
            continue
        title = a.get_text(strip=True)
        if len(title) < 5:
            continue
        if href in seen:
            continue
        seen.add(href)
        if href.startswith('/'):
            href = 'https://www.sjtu.edu.cn' + href
        date_str = ''
        li = a.find_parent('li')
        if li:
            date_span = li.find('span')
            if date_span:
                date_str = date_span.get_text(strip=True)
        items.append({'title': title, 'url': href, 'source': site['name'], 'date_str': date_str})
    return items


def _parse_youth_tzgg(soup, site):
    items = []
    container = None
    for div in soup.find_all('div'):
        cls = div.get('class')
        if cls:
            cls_str = ' '.join(cls) if isinstance(cls, list) else str(cls)
            if 'tzgg-info' in cls_str:
                container = div
                break
    if not container:
        return items
    for li in container.find_all('li'):
        a_tag = li.find('a', href=True)
        if not a_tag:
            continue
        href = a_tag['href']
        title_div = li.find('div', class_='li-info')
        title = title_div.get_text(strip=True) if title_div else a_tag.get_text(strip=True)
        if len(title) < 5:
            continue
        if href.startswith('/'):
            href = 'https://youth.sjtu.edu.cn' + href
        elif not href.startswith('http'):
            href = 'https://youth.sjtu.edu.cn/' + href
        date_str = ''
        time_span = li.find('span')
        if time_span:
            date_str = time_span.get_text(strip=True)
        items.append({'title': title, 'url': href, 'source': site['name'], 'date_str': date_str})
    return items


def _parse_youth_news(soup, site):
    items = []
    container = None
    for div in soup.find_all('div'):
        cls = div.get('class')
        if cls:
            cls_str = ' '.join(cls) if isinstance(cls, list) else str(cls)
            if 'xwkx-li' in cls_str or 'kpzs-info' in cls_str:
                container = div
                break
    if not container:
        return items
    for li in container.find_all('li'):
        a_tag = li.find('a', href=True)
        if not a_tag:
            continue
        href = a_tag['href']
        title_span = a_tag.find('span', class_='tit-3')
        title = title_span.get_text(strip=True) if title_span else a_tag.get_text(strip=True)
        if len(title) < 5:
            continue
        if href.startswith('/'):
            href = 'https://youth.sjtu.edu.cn' + href
        elif not href.startswith('http'):
            href = 'https://youth.sjtu.edu.cn/' + href
        date_str = ''
        time_span = a_tag.find('span', class_='time')
        if time_span:
            date_str = time_span.get_text(strip=True)
        items.append({'title': title, 'url': href, 'source': site['name'], 'date_str': date_str})
    return items


def _parse_jwc_list(soup, site):
    items = []
    newslist = None
    for div in soup.find_all('div'):
        cls = div.get('class')
        if cls:
            cls_str = ' '.join(cls) if isinstance(cls, list) else str(cls)
            if 'Newslist' in cls_str:
                newslist = div
                break
    if not newslist:
        return items
    for li in newslist.find_all('li'):
        a_tag = li.find('a', href=True)
        if not a_tag:
            continue
        wz = li.find('div', class_='wz')
        title = ''
        if wz:
            h2 = wz.find('h2')
            if h2:
                title = h2.get_text(strip=True)
        if not title:
            h2 = li.find('h2')
            title = h2.get_text(strip=True) if h2 else a_tag.get_text(strip=True)
        if len(title) < 5:
            continue
        href = a_tag['href']
        if href.startswith('../'):
            href = 'https://jwc.sjtu.edu.cn' + href[2:]
        elif href.startswith('/'):
            href = 'https://jwc.sjtu.edu.cn' + href
        elif not href.startswith('http'):
            href = 'https://jwc.sjtu.edu.cn/xwtg/' + href
        date_str = ''
        sj = li.find('div', class_='sj')
        if sj:
            p = sj.find('p')
            if p:
                date_str = p.get_text(strip=True)
        items.append({'title': title, 'url': href, 'source': site['name'], 'date_str': date_str})
    return items


def _parse_news_list(soup, site):
    items = []
    car_links = [a for a in soup.find_all('a', href=True, class_='card')
                 if a.get('class') and 'card' in a.get('class')]
    for a in car_links:
        href = a['href']
        title_div = a.find('div', class_='card-title')
        title = title_div.get_text(strip=True) if title_div else a.get_text(strip=True)
        if len(title) < 5:
            continue
        if href.startswith('/'):
            href = 'https://news.sjtu.edu.cn' + href
        elif not href.startswith('http'):
            href = 'https://news.sjtu.edu.cn/' + href
        date_str = ''
        date_span = a.find('span', class_='date')
        if not date_span:
            date_span = a.find('span', class_='time')
        if date_span:
            date_str = date_span.get_text(strip=True)
        items.append({'title': title, 'url': href, 'source': site['name'], 'date_str': date_str})

    if not items:
        for ul in soup.find_all('ul'):
            for li in ul.find_all('li'):
                a_tag = li.find('a', href=True)
                if a_tag:
                    title = a_tag.get_text(strip=True)
                    if len(title) < 5:
                        continue
                    href = a_tag['href']
                    if href.startswith('/'):
                        href = 'https://news.sjtu.edu.cn' + href
                    items.append({'title': title, 'url': href, 'source': site['name'], 'date_str': ''})
    return items


def _parse_generic_list(soup, site):
    items = []
    for a in soup.find_all('a', href=True):
        title = a.get_text(strip=True)
        if len(title) < 8:
            continue
        href = a['href']
        if href.startswith('/'):
            base = '/'.join(site['url'].split('/')[:3])
            href = base + href
        elif not href.startswith('http'):
            base = site['url'].rsplit('/', 1)[0]
            href = base + '/' + href
        items.append({'title': title, 'url': href, 'source': site['name'], 'date_str': ''})
    return items


if __name__ == '__main__':
    import time as _t
    _start = _t.time()
    items, errs = scrape_all()
    _t1 = _t.time()
    print(f"\n{_t1-_start:.1f}s — 列表页抓取完成：{len(items)} 条，{len(errs)} 个错误")

    related = [i for i in items if is_competition_related(i['title'])]
    print(f"初筛通过: {len(related)} 条")

    if related:
        _start2 = _t.time()
        details = fetch_details_batch(related)
        _t2 = _t.time()
        print(f"{_t2-_start2:.1f}s — 详情页抓取完成：{len(details)} 篇")
        for idx, item in enumerate(related[:10]):
            text = details.get(item['url'], '')
            print(f"  [{item['source']}] {item['title'][:60]}")
            print(f"    正文: {len(text)} 字")
