"""数据库模型定义 — AI人生镜像"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship

from .database import Base


# ══════════════════════════════════════════════════════
#  枚举
# ══════════════════════════════════════════════════════

class EventType(str, enum.Enum):
    """人生事件类型"""
    PROJECT = "project"               # 项目经历
    COMPETITION = "competition"       # 比赛经历
    STUDY = "study"                   # 学习经历
    SOCIAL = "social"                 # 社交经历
    DECISION = "decision"             # 重要决定
    TURNING_POINT = "turning_point"   # 人生转折
    HABIT = "habit"                   # 长期习惯
    FAILURE = "failure"               # 失败经历
    ACHIEVEMENT = "achievement"       # 成就/突破
    RELATIONSHIP = "relationship"     # 重要关系变化
    EMOTION = "emotion"               # 情绪波动


class EmotionType(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class ScenarioType(str, enum.Enum):
    FURTHER_STUDY = "further_study"       # 深造
    EMPLOYMENT = "employment"              # 就业
    ENTREPRENEURSHIP = "entrepreneurship"  # 创业
    CROSS_DISCIPLINE = "cross_discipline"  # 跨学科


class MemorySourceType(str, enum.Enum):
    DIARY = "diary"          # 来自日常记录
    EVENT = "event"          # 来自人生事件
    CHAT = "chat"            # 来自对话
    REPORT = "report"        # 来自成长报告


# ══════════════════════════════════════════════════════
#  1. 用户表
# ══════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # 基本信息
    age = Column(Integer, nullable=True)
    major = Column(String(100), nullable=True)
    university = Column(String(100), nullable=True)
    grade = Column(String(20), nullable=True)

    bio = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    life_events = relationship("LifeEvent", back_populates="user", cascade="all, delete-orphan")
    daily_records = relationship("DailyRecord", back_populates="user", cascade="all, delete-orphan")
    life_memories = relationship("LifeMemory", back_populates="user", cascade="all, delete-orphan")
    persona_profiles = relationship("PersonaProfile", back_populates="user", cascade="all, delete-orphan")
    life_goals = relationship("LifeGoal", back_populates="user", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="user", cascade="all, delete-orphan")
    growth_reports = relationship("GrowthReport", back_populates="user", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════
#  2. 人生事件表
# ══════════════════════════════════════════════════════

class LifeEvent(Base):
    """重要人生事件：项目、比赛、决定、转折点、习惯、失败、成就等"""
    __tablename__ = "life_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(SAEnum(EventType), nullable=False)

    # AI 分析
    emotion = Column(SAEnum(EmotionType), nullable=True)
    interest_tags = Column(JSON, default=list)
    ai_impact = Column(Text, nullable=True)

    # 人格增量（此事件对人格各维度的影响值）
    persona_delta = Column(JSON, nullable=True)
    # { "creative": +5, "exploration": +8, "risk_tolerance": +3 }

    occurred_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="life_events")


# ══════════════════════════════════════════════════════
#  3. 日常记录表
# ══════════════════════════════════════════════════════

class DailyRecord(Base):
    """日常人生记录：每天的心情、经历、困惑"""
    __tablename__ = "daily_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    content = Column(Text, nullable=False)
    mood = Column(String(100), nullable=True)  # 用户自行描述心情，不限标签
    tags = Column(JSON, default=list)

    ai_analysis = Column(JSON, nullable=True)
    # {
    #   "event": "参加机器人比赛",
    #   "emotion": "positive",
    #   "interest_fields": ["工程实践"],
    #   "long_term_impact": "增强技术方向兴趣",
    #   "behavior_patterns": ["探索型", "主动型"]
    # }

    record_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="daily_records")


# ══════════════════════════════════════════════════════
#  4. 生命记忆表 ⭐ 新增
# ══════════════════════════════════════════════════════

class LifeMemory(Base):
    """
    AI 理解后的长期生命记忆。

    从 daily_records / life_events / chat 中提取，
    是原始数据 → 数字人格之间的桥梁。
    """
    __tablename__ = "life_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    source_type = Column(SAEnum(MemorySourceType), nullable=False)
    source_id = Column(Integer, nullable=True)               # 关联的原始记录 ID

    memory_content = Column(Text, nullable=False)
    # "用户在机器人比赛中发现自己喜欢工程创造，对失败容忍度高"

    importance_score = Column(Float, default=0.5)
    # 0-1，越高越影响人格建模

    # 对人格各维度的累积影响
    persona_impact = Column(JSON, nullable=True)
    # { "creative": +5, "exploration": +8 }

    embedding_id = Column(String(100), nullable=True)
    # 关联 ChromaDB 中的向量 ID，格式 "ai_memory:{id}"

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="life_memories")


# ══════════════════════════════════════════════════════
#  5. 数字人格画像表 (增强版)
# ══════════════════════════════════════════════════════

class PersonaProfile(Base):
    """数字人格：AI 生成的用户画像，支持版本追踪"""
    __tablename__ = "persona_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 版本管理
    version = Column(Integer, default=1)
    is_current = Column(Boolean, default=True)
    trigger_event = Column(String(300), nullable=True)
    # "完成三个AI项目后触发人格更新"
    confidence = Column(Float, default=0.5)
    # 当前人格画像的可信度 (0-1)，数据越多越准确

    # 五维画像
    ability_profile = Column(JSON, nullable=True)
    interest_profile = Column(JSON, nullable=True)
    value_profile = Column(JSON, nullable=True)
    decision_style = Column(JSON, nullable=True)
    behavior_profile = Column(JSON, nullable=True)

    persona_type = Column(String(100), nullable=True)
    persona_summary = Column(Text, nullable=True)

    generated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="persona_profiles")


# ══════════════════════════════════════════════════════
#  6. 兴趣变化追踪表
# ══════════════════════════════════════════════════════

class InterestTrack(Base):
    """兴趣随时间变化的记录点"""
    __tablename__ = "interest_tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    field = Column(String(100), nullable=False)
    score = Column(Float, default=50.0)
    source = Column(String(200), nullable=True)

    tracked_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  7. 人生目标表 ⭐ 新增
# ══════════════════════════════════════════════════════

class LifeGoal(Base):
    """
    用户设定的长期目标。

    用于人生模拟中的「目标未来 vs 当前状态」差距分析。
    """
    __tablename__ = "life_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    goal_type = Column(String(50), nullable=False)
    # "career" / "study" / "skill" / "lifestyle" / "relationship" / "other"

    title = Column(String(200), nullable=False, default="未命名目标")
    description = Column(Text, nullable=True)
    # 详细描述：为什么设定、如何达成

    importance = Column(Integer, default=50)        # 0-100 重要程度
    target_year = Column(Integer, nullable=True)    # 目标年份 2035
    target_period = Column(String(50), nullable=True)  # 周期：短期/中期/长期/每日/每周
    status = Column(String(20), default="active")   # active / achieved / abandoned

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="life_goals")


# ══════════════════════════════════════════════════════
#  8. 人生模拟记录表 (增强版)
# ══════════════════════════════════════════════════════

class Simulation(Base):
    """人生模拟：一次模拟请求及其生成的未来路径"""
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    persona_snapshot_id = Column(Integer, ForeignKey("persona_profiles.id"), nullable=True)
    # 基于哪一版人格画像生成

    scenario_type = Column(SAEnum(ScenarioType), nullable=False)
    question = Column(String(500), nullable=True)

    # 输入变量 (结构化)
    input_variables = Column(JSON, nullable=True)

    # 模拟输出
    output_paths = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="simulations")
    persona_snapshot = relationship("PersonaProfile", foreign_keys=[persona_snapshot_id])
    simulation_variables = relationship("SimulationVariable", back_populates="simulation", cascade="all, delete-orphan")
    future_selves = relationship("FutureSelf", back_populates="simulation", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════
#  8b. 模拟变量表 ⭐ 新增
# ══════════════════════════════════════════════════════

class SimulationVariable(Base):
    """
    每次模拟的可调变量。

    单独拆表以便未来分析「什么变量最影响人生结果」。
    """
    __tablename__ = "simulation_variables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False, index=True)

    variable_name = Column(String(50), nullable=False)
    # "career_choice" / "location" / "risk_level" / "study_time" / "interest_focus"

    variable_value = Column(String(200), nullable=False)
    # "AI研究员" / "北京" / "70" / "每周20小时" / "AI+哲学"

    simulation = relationship("Simulation", back_populates="simulation_variables")


# ══════════════════════════════════════════════════════
#  9. 未来人格表 (增强版)
# ══════════════════════════════════════════════════════

class FutureSelf(Base):
    """基于模拟路径生成的未来AI人格，可追溯生成来源"""
    __tablename__ = "future_selves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=True)
    based_on_persona_id = Column(Integer, ForeignKey("persona_profiles.id"), nullable=True)
    # 基于哪个版本的人格画像生成

    persona_label = Column(String(100), nullable=False)
    target_year = Column(Integer, nullable=False)
    path_type = Column(String(50), nullable=False)

    # 生成追溯
    confidence = Column(Float, default=0.5)
    # 这个人格的置信度
    generation_prompt = Column(Text, nullable=True)
    # 生成这个人格时使用的 prompt（可审计）
    basis_summary = Column(Text, nullable=True)
    # "AI兴趣80% / 科研倾向90% / 风险偏好60% → 推断此路径"

    profile = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="future_selves")
    based_on_persona = relationship("PersonaProfile", foreign_keys=[based_on_persona_id])
    chat_messages = relationship("ChatMessage", back_populates="future_self", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════
#  10. 未来自我对话记录表
# ══════════════════════════════════════════════════════

class ChatMessage(Base):
    """与未来人格的对话记录"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    future_self_id = Column(Integer, ForeignKey("future_selves.id"), nullable=False)

    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    future_self = relationship("FutureSelf", back_populates="chat_messages")


# ══════════════════════════════════════════════════════
#  11. 成长报告表
# ══════════════════════════════════════════════════════

class GrowthReport(Base):
    """AI 定期生成的成长总结报告"""
    __tablename__ = "growth_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    content = Column(JSON, nullable=False)
    # {
    #   "interest_changes": [...],
    #   "ability_growth": {...},
    #   "key_decisions": [...],
    #   "personality_changes": "...",
    #   "goal_progress": {...},
    #   "gap_analysis": "...",
    #   "summary": "..."
    # }

    generated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="growth_reports")
