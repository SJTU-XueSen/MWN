"""为 txdsyl_ 补充人生事件（在 seed_user.py 之后运行，事件同样走 LLM 分析）

用法: cd ai-camp && .venv/Scripts/python.exe scripts/seed_events_extra.py
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database.database import AsyncSessionLocal
from backend.services.auth_service import get_user_by_username
from backend.services.event_service import create_event

USERNAME = "txdsyl_"

# (标题, 描述, 类型, 年, 月)
EXTRA_EVENTS = [
    ("拿到人生第一份奖学金", "大二学年综合成绩进了专业前 20%，拿到三等奖学金。领到奖学金那天请全宿舍吃了顿火锅。", "achievement", 2025, 9),
    ("第一次在技术沙龙做分享", "在学院技术沙龙分享强化学习入门路径，准备了两个星期，讲完收到了很多正向反馈，克服了对公开表达的恐惧。", "achievement", 2025, 11),
    ("第一次独自坐飞机回家", "大三寒假第一次一个人坐飞机，全程紧张但顺利。落地那一刻觉得'自己其实可以搞定很多事'。", "habit", 2026, 1),
    ("搬进新校区宿舍", "大三开学学院搬了新校区，宿舍从六人间换成四人间。收拾完新房间的那一刻，有了一点'新的开始'的感觉。", "turning_point", 2025, 9),
    ("社团招新季帮忙摆摊", "被同学拉去帮社团招新摆摊，一下午招了二十多个新人。第一次发现自己其实挺能聊。", "social", 2024, 9),
    ("第一次当众演讲", "课程展示时第一次在四十多人面前做完整演讲，紧张到手抖，但讲完之后老师和同学都鼓掌了。", "social", 2024, 12),
    ("室友搬去国外交换", "关系最好的室友拿到了交换名额去国外一年，送他去机场的路上谁都没说话。他的座位空了，但每周视频雷打不动。", "relationship", 2025, 2),
    ("换了人生第一台自己的电脑", "实习工资加上奖学金，换了人生第一台自己攒钱买的电脑。打开包装盒那一刻，觉得自己'长大了一点'。", "achievement", 2025, 8),
    ("第一次给家人买礼物", "用实习工资给爸妈各买了件外套，给奶奶买了按摩仪。快递到家那天妈妈打电话来说'以后别乱花钱'，但声音是笑着的。", "relationship", 2024, 8),
    ("半夜照顾发烧的室友", "室友半夜高烧，陪他去急诊输液到凌晨三点。回来路上他说'以后你生病我也陪你'。有些友情就是这么建立起来的。", "social", 2024, 11),
    ("被选为课程小组组长", "机器学习课程项目被选为组长，负责协调四个人分工。第一次当'领导'，学会了怎么把任务拆给别人而不是自己扛。", "achievement", 2025, 4),
    ("正式成为实验室核心成员", "大三成为实验室核心成员，负责一个子课题。学长说'以后这个方向就靠你们了'，责任感突然变重了。", "project", 2025, 10),
]


async def main():
    async with AsyncSessionLocal() as db:
        user = await get_user_by_username(db, USERNAME)
        if not user:
            print("用户不存在，请先运行 seed_user.py")
            return
        uid = user.id
        for title, desc, etype, year, month in EXTRA_EVENTS:
            await create_event(db, uid, title, desc, etype, datetime(year, month, 15))
            print(f"事件已注入: {title}")
        print(f"\n完成！补充 {len(EXTRA_EVENTS)} 个人生事件（均含 LLM 分析）")


asyncio.run(main())
