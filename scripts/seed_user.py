"""为指定账号注入演示数据（走完整 AI 管线：记录→分析→记忆→Chroma→人格→模拟→报告）

用法: cd ai-camp && .venv/Scripts/python.exe scripts/seed_user.py
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 项目根加入 sys.path

from backend.database.database import AsyncSessionLocal
from backend.services.auth_service import create_user, get_user_by_username
from backend.services.event_service import create_event
from backend.services.memory_service import process_daily_record
from backend.services.persona_service import generate_persona, should_regenerate_persona
from backend.services.report_service import generate_report
from backend.services.simulation_service import run_simulation

USERNAME = "txdsyl_"
PASSWORD = "090915"

# ── 日常记录（多样化主题，覆盖多个兴趣领域） ──
RECORDS = [
    ("今天在实验室调试了三天前搭的机器人底盘，传感器数据终于稳定了。虽然过程很折磨，但最后看到轮子按照预期轨迹转动的那一刻，真的很有成就感。晚上回去又翻了一遍 PPO 的论文，越看越觉得有意思。", "充实"),
    ("早八的机器学习课讲了 transformer 的注意力机制，老师讲得很快，下课自己在 B 站找视频又补了一遍。发现自己越来越喜欢这种'先被难住，再慢慢啃懂'的过程。", "专注"),
    ("和队友讨论比赛方案，争论了整整一个下午。最后我们把想法合并成了一个更完整的方案，这种感觉比一个人闷头做有意思多了。晚上一起吃了顿饭。", "开心"),
    ("今天状态不太好，写代码写了一天没进展，一个 bug 怎么都定位不到。有点怀疑自己是不是不适合做这个。晚上去操场跑了五公里，出了一身汗，感觉好多了。", "疲惫"),
    ("读了一本《深度工作》，里面讲注意力管理，挺有启发。反思自己最近确实碎片化太严重，手机一响就分心。决定明天开始每天上午两小时无手机时间。", "平静"),
    ("第一次在组会上讲自己的调研报告，讲的时候手都在抖，但讲完被导师夸了思路清晰。发现表达这件事，练是真的有用。", "紧张但收获"),
    ("看了交大的 AI 创新大赛通知，和室友聊了想参加的想法，他们都挺支持。已经想好大致方向了：用强化学习做一个智能体应用。", "兴奋"),
    ("最近连续熬夜，今天早上起不来，上午全废了。有点自责，但也意识到节奏控制很重要，不能靠透支来赶进度。给自己立个规矩：十二点前必须睡。", "焦虑"),
    ("参加学校的开源社区活动，认识了一群做前端和做硬件的同学，聊得很开心。发现不同方向的人看问题的方式真的不一样，很有意思。", "兴奋"),
    ("今天把强化学习的一章笔记整理完了，画了一张完整的框架图，从马尔可夫决策过程到 PPO 的整个脉络一下子清楚了。这种'突然通了'的时刻太棒了。", "成就感"),
    ("帮大一的学弟调试了一个 Arduino 项目，虽然花了我两个多小时，但看到他最后跑通时高兴的样子，觉得挺值的。也让我重新想了一遍基础的东西。", "温暖"),
    ("和几个同学组了个学习小组，每周四晚上一起读论文。今天第一篇读的是 DQN 那篇，大家各抒己见，比一个人读收获大得多。", "充实"),
]

# ── 人生事件 ──
EVENTS = [
    ("参加FTC机器人竞赛", "作为编程组核心成员，负责传感器调试和策略设计。备赛两个月，期间通宵过三次，最终队伍晋级地区赛。最大的收获不是名次，而是学会在高压下和队友配合。", "competition", -45),
    ("确定深入强化学习方向", "在尝试了 CV、NLP 之后，最终决定把强化学习作为长期钻研方向。这个决定基于大半年的探索：发现自己最享受的是'让智能体从经验中学习'这个过程。", "decision", -30),
    ("加入学院开源社区", "从围观者变成 contributor，第一次提交 PR 被合并时的开心记忆犹新。在这里认识了现在最好的几个技术朋友。", "project", -20),
    ("组建四人学习小组", "和同学组建了每周读论文的学习小组，坚持了三个月，形成了稳定的节奏。小组里有人擅长理论，有人擅长工程，互补得很好。", "social", -10),
    ("第一次做公开分享", "在学院技术沙龙上分享了自己整理的强化学习入门路径，准备了很久，讲完收到了很多正向反馈，克服了对公开表达的恐惧。", "achievement", -15),
    ("期末考试周崩溃后调整作息", "连续三天每天睡四小时复习，考完最后一门直接病倒。休息一周后彻底调整了作息规律，意识到长期主义比短期冲刺重要。", "turning_point", -60),
]

# ── 目标 ──
GOALS = [
    ("深入强化学习，达到能复现主流算法", "study", 90, "长期"),
    ("完成一个机器人智能体应用并参赛", "skill", 85, "中期"),
    ("每周读一篇论文并整理笔记", "study", 70, "每周"),
    ("训练公开表达，每月至少一次分享", "skill", 60, "中期"),
]


async def main():
    async with AsyncSessionLocal() as db:
        user = await get_user_by_username(db, USERNAME)
        if not user:
            user = await create_user(db, USERNAME, f"{USERNAME}@mirror.local", PASSWORD, "吴同学", True)
            print(f"创建用户 {USERNAME}")
        uid = user.id

        from backend.database.models import DailyRecord, LifeGoal

        # 清空该用户旧数据（若重复执行）
        for model in (DailyRecord, LifeGoal):
            rows = (await db.execute(__import__("sqlalchemy").select(model).where(model.user_id == uid))).scalars().all()
            for r in rows:
                await db.delete(r)
        await db.commit()

        # 注入日常记录（时间分散在过去 60 天）
        now = datetime.utcnow()
        for i, (content, mood) in enumerate(RECORDS):
            record = DailyRecord(
                user_id=uid, content=content, mood=mood,
                record_date=now - timedelta(days=(len(RECORDS) - i) * 4 + i % 3),
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            try:
                await process_daily_record(db, record, uid)
                from backend.services.vector_store import add_ai_memory, add_journal

                memory = (await __import__("sqlalchemy").select(__import__("backend.database.models", fromlist=["LifeMemory"]).LifeMemory)
                          .where(__import__("backend.database.models", fromlist=["LifeMemory"]).LifeMemory.source_type == "diary",
                                 __import__("backend.database.models", fromlist=["LifeMemory"]).LifeMemory.source_id == record.id)
                          .order_by(__import__("backend.database.models", fromlist=["LifeMemory"]).LifeMemory.id.desc())).scalars().first()
                if memory:
                    add_ai_memory(memory.id, uid, memory.memory_content, {"importance": memory.importance_score})
                add_journal(record.id, uid, record.content, {"mood": mood})
            except Exception as e:
                print(f"记录 {i} 记忆管线失败: {e}")
        print(f"已注入 {len(RECORDS)} 条日常记录（含 AI 分析）")

        # 注入人生事件
        for title, desc, etype, days_ago in EVENTS:
            await create_event(db, uid, title, desc, etype, now - timedelta(days=days_ago))
        print(f"已注入 {len(EVENTS)} 个人生事件")

        # 注入目标
        for title, gtype, importance, period in GOALS:
            db.add(LifeGoal(user_id=uid, title=title, goal_type=gtype, importance=importance,
                            target_period=period, status="active"))
        await db.commit()
        print(f"已注入 {len(GOALS)} 个目标")

        # 生成人格 + 模拟 + 报告（AI 分析齐活）
        persona = await generate_persona(db, uid, "演示数据注入后生成")
        print(f"人格已生成: {persona.persona_type} (置信度 {persona.confidence})")

        sim = await run_simulation(db, uid, "further_study", "在强化学习方向上继续深耕，同时兼顾工程实践")
        print(f"模拟已生成: {len(sim.output_paths or [])} 条路径")

        report = await generate_report(db, uid, f"成长报告 {now.strftime('%Y.%m.%d')}",
                                       now - timedelta(days=60), now, "")
        print(f"报告已生成: {report.title}")

        # 技能标签
        user.skill_tags = ["Python", "机器学习", "深度学习", "强化学习", "嵌入式", "机器人", "算法"]
        await db.commit()

        print(f"\n完成！账号 {USERNAME} 已就绪：{len(RECORDS)} 记录 + {len(EVENTS)} 事件 + {len(GOALS)} 目标 + 人格/模拟/报告")


asyncio.run(main())
