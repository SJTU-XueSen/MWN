"""AI 信息筛选与摘要 — 智谱 GLM 优先，规则引擎回退

密钥统一从 backend.config 读取（.env），绝不硬编码。
"""
import html as _html_lib
import json
import random
import re
import urllib.parse
import urllib.request
from datetime import datetime

from backend.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    ZHIPU_API_KEY,
    ZHIPU_BASE_URL,
)

ZHIPU_MODEL = "glm-4-flash"
DEEPSEEK_MODEL = "deepseek-chat"


def _llm_available():
    return bool(ZHIPU_API_KEY)


# ── API 调用（urllib 同步实现，供爬虫线程池使用）────────

def _llm_api_request(messages, max_tokens=1500, temperature=0.3, timeout=30):
    """调用智谱 GLM API（同步）"""
    data = json.dumps({
        "model": ZHIPU_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{ZHIPU_BASE_URL}/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())["choices"][0]["message"]["content"]


def deepseek_chat(messages, max_tokens=2000, temperature=0.7, timeout=30):
    """调用 DeepSeek API（同步，key 从 config 读取）"""
    if not DEEPSEEK_API_KEY:
        return None
    data = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())["choices"][0]["message"]["content"]


def deepseek_chat_with_key(api_key, messages, max_tokens=2000, temperature=0.7, timeout=30):
    """使用调用方提供的 Key 调用 DeepSeek（前端用户自填 key 的场景）"""
    data = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())["choices"][0]["message"]["content"]


def _call_llm(prompt, max_tokens=1500):
    return _llm_api_request([
        {"role": "system", "content": "你是一个竞赛信息分析助手。请严格按照要求的 JSON 格式输出，不要输出任何其他内容。"},
        {"role": "user", "content": prompt},
    ], max_tokens=max_tokens)


# ── 关键词库 ────────────────────────────────────────

CATEGORY_MAP = {
    "学科竞赛": [
        "数学建模", "电子设计", "程序设计", "acm", "icpc", "英语竞赛",
        "物理竞赛", "化学竞赛", "生物竞赛", "力学竞赛", "机器人", "智能车",
        "机械创新", "节能减排", "结构设计", "化工设计", "计算机设计",
        "信息安全", "电气", "自动化", "测绘", "地质", "iGEM", "飞思卡尔",
    ],
    "创新创业": [
        "互联网+", "挑战杯", "创青春", "三创", "大创", "创新创业",
        "创业计划", "商业计划", "路演", "孵化", "创客",
    ],
    "科研项目": ["大创项目", "创新项目", "科研", "论文", "专利", "课题", "基金", "实验室"],
    "文体活动": ["辩论", "演讲", "征文", "歌手", "运动会", "篮球", "足球", "艺术", "摄影", "微电影"],
    "社会实践": ["社会实践", "志愿", "支教", "调研", "三下乡", "暑期实践"],
}

LEVEL_MAP = {
    "国家级": ["全国", "国家", "中国", "教育部", "国家级", "国赛"],
    "省市级": ["上海", "省", "市", "长三角", "华东", "省级", "市级"],
    "校级": ["交大", "上海交大", "校内", "院系", "学院", "校级", "校园"],
}

CREDIT_PATTERNS = [
    r"(?:可获得?|获|计|认定)\s*(?:相应)?\s*(\d+\.?\d*)\s*(?:个)?学分",
    r"学分[：:]*\s*(\d+\.?\d*)",
    r"(\d+\.?\d*)\s*(?:个)?学分",
    r"可获\s*(\d+\.?\d*)\s*学分",
]

DATE_PATTERNS = [
    r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
    r"截止\s*(?:日期|时间|报名)[：:]*\s*(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
    r"报名时间[：:]*.*?(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
]

TEAM_SIZE_PATTERNS = [
    r"(\d+)\s*[-~至到]\s*(\d+)\s*人组",
    r"每组\s*(\d+)\s*[-~至到]*\s*(\d+)*\s*人",
    r"团队\s*(\d+)\s*[-~至到]*\s*(\d+)*\s*人",
    r"组队.*?(\d+)\s*[-~至到]*\s*(\d+)*\s*人",
    r"不超过\s*(\d+)\s*人",
]

SKILL_TAGS = [
    "编程", "算法", "数据分析", "UI设计", "前端开发", "后端开发",
    "文案写作", "PPT制作", "演讲汇报", "调研访谈", "视频剪辑",
    "3D建模", "项目管理", "测试", "文档编写", "Python", "C++",
    "Java", "JavaScript", "MATLAB", "嵌入式", "硬件设计", "机器学习",
    "人工智能", "深度学习", "数学", "英语", "财务分析", "路演",
]


# ── LLM 分析 ──────────────────────────────────────────

def _llm_analyze(title, url, source, detail_text):
    """使用智谱大模型分析页面 — 只保留需要学生主动参与的活动"""
    text = detail_text or ""
    text_snippet = text[:4000] if len(text) > 4000 else text

    prompt = f"""你是大学生校园活动的筛选专家。请分析以下网页内容，判断它是否是一个「需要学生主动报名参与」的活动。

核心筛选标准（必须同时满足）：
1. 目标受众是学生（本科生/研究生）
2. 需要学生主动报名参与（不是被通知、被评选）
3. 学生需要完成某种任务或产出（作品、表演、比赛、实践等），可以个人参加也可以组队

应该排除的内容：
- 纯通知公告（放假通知、评奖公示、政策文件、换届通知）
- 被动参与（被评选、被评奖、被公示）
- 纯听课/听讲座（没有互动的单向输出）
- 教务通知（选课、考试、评教）
- 教师评奖/课题申报
- 纯竞赛（学科竞赛、数学建模、ACM、挑战杯等由平台其他功能处理）

应该保留的内容：
- 校园文化活动（晚会、演出、合唱、艺术展）
- 体育赛事（运动会、球赛、越野赛）
- 志愿者/社会实践招募
- 创新创业实践项目
- 培训/工作坊（需要实操的）
- 作品征集（海报、视频、文创等需要创作的）
- 社团活动
- 主题团队/个人活动

网页标题：{title}
来源：{source}
网页正文（截取）：
{text_snippet}

请严格按照以下 JSON 格式返回：

{{
  "is_competition": true/false,
  "needs_participation": true/false,
  "type": "activity/competition/volunteer/project/training/recruitment/notice/lecture/other",
  "title": "清理后的活动名称",
  "category": "文体活动/志愿服务/创新创业/社会实践/培训工作坊/体育赛事/招新招募/作品征集/学科竞赛/通知公告",
  "level": "校级/院级/省市级/国家级",
  "summary": "用1-2句话概括：这是什么活动、学生需要做什么",
  "organizer": "主办单位",
  "credit_info": "学分/素拓信息，无则为空",
  "deadline": "报名截止日期 YYYY-MM-DD，无则为null",
  "max_team_size": 组队最大人数（整数，默认1）,
  "min_team_size": 组队最少人数（整数，默认1）,
  "tags": ["标签1", "标签2", "标签3"]
}}

关键判定：needs_participation 表示学生是否需要主动报名参与。只要学生需要报名并完成某项任务（无论个人还是组队），就是 true。
如果只是被动接收通知、被评选、被公示、单纯听课，则 needs_participation=false。
如果完全不相关，所有字段设为 false/null。"""

    try:
        response = _call_llm(prompt)
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            return None
        data = json.loads(json_match.group(0))
        if not data.get("title") or data.get("title") == "false":
            return None

        deadline = None
        if data.get("deadline"):
            try:
                deadline = datetime.fromisoformat(data["deadline"])
            except (ValueError, TypeError):
                pass

        return {
            "title": str(data.get("title", title)).strip(),
            "type": data.get("type", "notice"),
            "needs_participation": data.get("needs_participation", False),
            "is_competition": data.get("is_competition", False),
            "category": data.get("category", "通知公告"),
            "level": data.get("level", "校级"),
            "description": data.get("summary", "暂无摘要"),
            "organizer": data.get("organizer", "上海交通大学"),
            "credit_info": data.get("credit_info", ""),
            "tags": data.get("tags", [])[:8],
            "ai_confidence": 0.88,
            "deadline": deadline.isoformat() if deadline else None,
            "max_team_size": int(data.get("max_team_size", 5)),
            "min_team_size": int(data.get("min_team_size", 1)),
            "source_url": url,
            "source_site": source or "上海交通大学",
        }
    except Exception:
        return None


# ── 主分析函数 ────────────────────────────────────────

def analyze_competition_page(title, url, source, detail_text):
    """分析详情页 → 结构化信息（LLM 优先，规则回退），非学生可参与活动返回 None"""
    if _llm_available():
        result = _llm_analyze(title, url, source, detail_text)
        if result:
            return result

    text = detail_text or ""
    combined = title + " " + text

    if not _is_competition_related(combined):
        return None

    category = _classify(text.lower(), CATEGORY_MAP, "学科竞赛")
    level = _classify(combined, LEVEL_MAP, "校级")
    deadline = _extract_deadline(text)
    credit_info = _extract_credit(text)
    max_size, min_size = _extract_team_size(text)
    organizer = _extract_organizer(text)
    tags = _extract_tags(combined, category, level)
    description = _generate_summary(title, text, category, level, organizer, credit_info, deadline)
    confidence = _calc_confidence(combined, category, level)

    return {
        "title": _clean_title(title),
        "category": category,
        "level": level,
        "description": description,
        "organizer": organizer,
        "credit_info": credit_info,
        "tags": tags,
        "ai_confidence": round(confidence, 2),
        "deadline": deadline.isoformat() if deadline else None,
        "max_team_size": max_size,
        "min_team_size": min_size,
        "source_url": url,
        "source_site": source or "上海交通大学",
    }


# ── 子分析函数 ────────────────────────────────────────

def _is_competition_related(text):
    all_kw = [kw for kws in CATEGORY_MAP.values() for kw in kws]
    all_kw.extend(["竞赛", "大赛", "比赛", "赛", "创新创业", "训练计划", "项目申报"])
    return sum(1 for kw in all_kw if kw in text) >= 2


def _classify(text_lower, mapping, default):
    scores = {cat: sum(1 for kw in kws if kw.lower() in text_lower) for cat, kws in mapping.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else default


def _extract_deadline(text):
    for pattern in DATE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            try:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 2024 <= y <= 2028 and 1 <= mo <= 12 and 1 <= d <= 31:
                    return datetime(y, mo, d)
            except ValueError:
                continue
    return None


def _extract_credit(text):
    for pattern in CREDIT_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return f"可获得 {m.group(1)} 学分"
    return ""


def _extract_team_size(text):
    for pattern in TEAM_SIZE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            g1 = int(m.group(1))
            g2 = int(m.group(2)) if m.lastindex >= 2 and m.group(2) else g1
            return max(g1, g2), min(g1, g2)
    return 5, 3


def _extract_organizer(text):
    patterns = [
        r"(?:主办|承办|组织)(?:单位|方)?[：:]\s*(.+?)(?:[\n\r]|$)",
        r"(上海交通大学[^\n\r]{0,30}(?:学院|处|部|中心|团委))",
        r"(上海市[^\n\r]{0,20}(?:委|局|会|中心))",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            org = m.group(1).strip()
            if len(org) < 50:
                return org
    org_matches = re.findall(r"上海交通大学[^，。\n\r]{0,20}(?:学院|处|部|中心|团委|学生会)", text)
    return org_matches[0] if org_matches else "上海交通大学"


def _extract_tags(text, category, level):
    tags = [category, level]
    for tag in SKILL_TAGS:
        if tag.lower() in text.lower():
            tags.append(tag)
    return list(set(tags))[:8]


def _calc_confidence(text, category, level):
    kw_count = sum(1 for kw in SKILL_TAGS + [
        "竞赛", "报名", "截止", "组队", "学分", "获奖",
        "参赛", "作品", "提交", "答辩", "评审",
    ] if kw in text)
    conf = 0.5 + min(kw_count * 0.03, 0.3)
    if level in ("国家级", "省市级"):
        conf += 0.1
    return min(conf, 0.95)


def _clean_title(title):
    title = title.strip()
    for prefix in ["通知：", "公告：", "关于", "【通知】", "[通知]"]:
        if title.startswith(prefix):
            title = title[len(prefix):]
    title = re.sub(r"\s*[-–—]\s*上海交通大学.*$", "", title)
    title = title.strip().rstrip("。；;.")
    return title if len(title) >= 4 else title


def _generate_summary(title, text, category, level, organizer, credit_info, deadline):
    sentences = [s.strip() for s in re.split(r"[。！\n]", text) if len(s.strip()) > 15]
    best_sentences = []
    priority_kw = ["竞赛", "参赛", "报名", "作品", "答辩", "项目", "组队"]
    for s in sentences:
        if any(kw in s for kw in priority_kw) and len(best_sentences) < 5:
            best_sentences.append(s)

    if best_sentences:
        summary = "；".join(best_sentences[:4])
        if len(summary) > 400:
            summary = summary[:400] + "…"
    else:
        summary = f"{level}{category}——{title}。"
        if organizer:
            summary += f"由{organizer}主办。"
        summary += "详见来源网站。"

    lines = [f"【{level}{category}】{title}"]
    if organizer:
        lines.append(f"主办单位：{organizer}")
    lines.append(summary)
    if credit_info:
        lines.append(f"学分信息：{credit_info}")
    lines.append(f"截止时间：{deadline.strftime('%Y年%m月%d日')}" if deadline else "截止时间：详见网站")
    return "\n".join(lines)


# ── 任务拆解 & 技能匹配 ────────────────────────────────

ROLE_EXAMPLES = {
    "前端开发": ["UI设计", "React", "Vue", "HTML", "CSS", "JavaScript"],
    "后端开发": ["Python", "Java", "Go", "数据库", "API设计"],
    "数据分析": ["Python", "Pandas", "数据可视化", "Excel", "统计"],
    "算法设计": ["Python", "C++", "数据结构", "数学建模"],
    "文档编写": ["文案写作", "PPT制作", "Markdown", "Word"],
    "硬件设计": ["嵌入式", "PCB设计", "电路", "单片机"],
    "测试": ["测试用例", "自动化测试", "Python", "Selenium"],
    "项目管理": ["项目管理", "沟通协调", "甘特图", "Jira"],
    "视频剪辑": ["Premiere", "剪辑", "动画", "拍摄"],
    "演讲汇报": ["演讲", "PPT制作", "表达", "答辩"],
}


def breakdown_task(title, description, member_skills: list[str]):
    """根据任务描述拆解子角色（LLM 优先，规则回退）

    返回: list of {role, count, estimated_hours, skills}
    """
    if ZHIPU_API_KEY:
        result = _llm_breakdown_task(title, description, member_skills)
        if result:
            return result
    return _rule_breakdown_task(title, description, member_skills)


def calc_match_score(user_skills: list[str], task_role: dict, credit_score: float = 100.0):
    """计算用户与任务角色的技能匹配度 (0-1)"""
    if not task_role or not task_role.get("skills"):
        return 0.5
    required_skills = [str(s).lower() for s in task_role.get("skills", [])]
    if not required_skills:
        return 0.5

    user_skills = [str(s).lower() for s in (user_skills or [])]

    matched = sum(1 for rs in required_skills for us in user_skills if rs in us or us in rs)
    base = min(matched / max(len(required_skills), 1), 1.0)
    credit_bonus = (credit_score - 80) / 200
    return round(min(max(base * 0.9 + credit_bonus, 0.1), 1.0), 2)


def _rule_breakdown_task(title, description, member_skills: list[str]):
    text = (title + " " + description).lower()
    roles = []
    member_count = max(len(member_skills), 3)
    max_per_role = max(1, member_count // 2)

    for role, skills in ROLE_EXAMPLES.items():
        matched_skills = [s for s in skills if s.lower() in text]
        if matched_skills or any(kw in text for kw in role.lower().split()):
            count = 1
            if any(kw in text for kw in ["大量", "多个", "多名", "组队", "团队"]):
                count = min(2, max_per_role)
            roles.append({
                "role": role,
                "count": count,
                "estimated_hours": random.choice([4, 8, 16, 24]),
                "skills": matched_skills[:5] if matched_skills else skills[:3],
            })

    if not roles:
        roles = [{"role": "执行成员", "count": member_count, "estimated_hours": 8,
                  "skills": ["认真负责", "按时完成"]}]

    total_needed = sum(r["count"] for r in roles)
    if total_needed > member_count and member_count > 0:
        scale = member_count / total_needed
        for r in roles:
            r["count"] = max(1, int(r["count"] * scale))
    return roles


def _llm_breakdown_task(title, description, member_skills: list[str]):
    if not ZHIPU_API_KEY:
        return None
    try:
        skills_text = "\n".join(f"- {s}" for s in (member_skills or ["未设置"]))
        prompt = f"""你是任务拆解专家。请将以下团队任务拆解为具体子角色/子任务。

任务标题：{title}
任务描述：{description}
团队成员及其技能：
{skills_text or '无'}

请返回 JSON 列表，每个元素包含：
- role: 角色名称
- count: 需要人数
- estimated_hours: 预估工时(小时)
- skills: 所需技能列表

格式：```json[...]```
只返回 JSON，不要其他文字。"""
        content = _llm_api_request([{"role": "user", "content": prompt}], max_tokens=1000, timeout=20)
        json_match = re.search(r"\[[\s\S]*\]", content)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
    return None


# ── Web 搜索（urllib，DuckDuckGo HTML 版）──────────────

def web_search(query, max_results=5):
    """返回 [{title, url, snippet}]"""
    results = []
    try:
        q = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={q}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        resp = urllib.request.urlopen(req, timeout=10)
        html_content = resp.read().decode("utf-8", errors="ignore")

        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html_content, re.DOTALL)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</', html_content, re.DOTALL)
        urls_raw = re.findall(r'class="result__url"[^>]*>(.*?)</', html_content, re.DOTALL)

        for i in range(min(len(titles), max_results)):
            title = _html_lib.unescape(re.sub(r"<[^>]+>", "", titles[i])).strip()
            snippet = _html_lib.unescape(re.sub(r"<[^>]+>", "", snippets[i])).strip() if i < len(snippets) else ""
            link = ""
            if i < len(urls_raw):
                link = _html_lib.unescape(re.sub(r"<[^>]+>", "", urls_raw[i])).strip()
                if not link.startswith("http"):
                    link = "https://" + link
            if title:
                results.append({
                    "title": title[:100],
                    "url": link or f"https://duckduckgo.com/?q={q}",
                    "snippet": snippet[:200],
                })
    except Exception:
        pass
    return results
