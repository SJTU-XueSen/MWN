"""数据库模型 — 镜·界·联 全量表（镜像核心 + 备忘录 + 活动平台）"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from backend.database.database import Base


# ══════════════════════════════════════════════════════
#  事件类型 / 枚举（存 String 值，读取时统一用 .value 形式）
# ══════════════════════════════════════════════════════

EVENT_TYPES = [
    "project", "competition", "study", "social", "decision",
    "turning_point", "habit", "failure", "achievement", "relationship", "emotion",
]
EMOTION_TYPES = ["positive", "neutral", "negative"]
SCENARIO_TYPES = ["further_study", "employment", "entrepreneurship", "cross_discipline"]
MEMORY_SOURCES = ["diary", "event", "chat", "report"]
GOAL_TYPES = ["career", "study", "skill", "lifestyle", "relationship", "other"]


# ══════════════════════════════════════════════════════
#  1. 用户表（镜像字段 + 活动平台扩展字段）
# ══════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    real_name = Column(String(50), nullable=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    agreed_terms_at = Column(DateTime, nullable=True)

    # 活动平台扩展
    avatar_url = Column(String(500), default="")
    skill_tags = Column(JSON, default=list)
    credit_score = Column(Float, default=100.0)

    # 基本信息
    age = Column(Integer, nullable=True)
    major = Column(String(100), nullable=True)
    university = Column(String(100), nullable=True)
    grade = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  2. 人生事件
# ══════════════════════════════════════════════════════

class LifeEvent(Base):
    __tablename__ = "life_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(30), nullable=False)          # EVENT_TYPES
    emotion = Column(String(20), nullable=True)              # EMOTION_TYPES
    interest_tags = Column(JSON, default=list)
    ai_impact = Column(Text, nullable=True)
    persona_delta = Column(JSON, nullable=True)              # {"creative": +5, ...}
    occurred_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  3. 日常记录
# ══════════════════════════════════════════════════════

class DailyRecord(Base):
    __tablename__ = "daily_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    mood = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)
    ai_analysis = Column(JSON, nullable=True)
    record_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  4. 生命记忆
# ══════════════════════════════════════════════════════

class LifeMemory(Base):
    __tablename__ = "life_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_type = Column(String(20), nullable=False)         # MEMORY_SOURCES
    source_id = Column(Integer, nullable=True)
    memory_content = Column(Text, nullable=False)
    importance_score = Column(Float, default=0.5)
    persona_impact = Column(JSON, nullable=True)
    embedding_id = Column(String(100), nullable=True)        # ChromaDB id "ai_memory:{id}"
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  5. 数字人格画像（多版本）
# ══════════════════════════════════════════════════════

class PersonaProfile(Base):
    __tablename__ = "persona_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    version = Column(Integer, default=1)
    is_current = Column(Boolean, default=True)
    trigger_event = Column(String(300), nullable=True)
    confidence = Column(Float, default=0.5)
    ability_profile = Column(JSON, nullable=True)
    interest_profile = Column(JSON, nullable=True)
    value_profile = Column(JSON, nullable=True)
    decision_style = Column(JSON, nullable=True)
    behavior_profile = Column(JSON, nullable=True)
    persona_type = Column(String(100), nullable=True)
    persona_summary = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  6. 兴趣追踪
# ══════════════════════════════════════════════════════

class InterestTrack(Base):
    __tablename__ = "interest_tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    field = Column(String(100), nullable=False)
    score = Column(Float, default=50.0)
    source = Column(String(200), nullable=True)
    tracked_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  7. 人生目标
# ══════════════════════════════════════════════════════

class LifeGoal(Base):
    __tablename__ = "life_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_type = Column(String(50), nullable=False)           # GOAL_TYPES
    title = Column(String(200), nullable=False, default="未命名目标")
    description = Column(Text, nullable=True)
    importance = Column(Integer, default=50)
    target_year = Column(Integer, nullable=True)
    target_period = Column(String(50), nullable=True)
    status = Column(String(20), default="active")            # active / achieved / abandoned
    ai_gap_analysis = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  8. 人生模拟
# ══════════════════════════════════════════════════════

class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    persona_snapshot_id = Column(Integer, ForeignKey("persona_profiles.id"), nullable=True)
    scenario_type = Column(String(30), nullable=False)       # SCENARIO_TYPES
    question = Column(String(500), nullable=True)
    input_variables = Column(JSON, nullable=True)
    output_paths = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SimulationVariable(Base):
    __tablename__ = "simulation_variables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False, index=True)
    variable_name = Column(String(50), nullable=False)
    variable_value = Column(String(200), nullable=False)


# ══════════════════════════════════════════════════════
#  9. 未来人格
# ══════════════════════════════════════════════════════

class FutureSelf(Base):
    __tablename__ = "future_selves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=True)
    based_on_persona_id = Column(Integer, ForeignKey("persona_profiles.id"), nullable=True)
    persona_label = Column(String(100), nullable=False)
    target_year = Column(Integer, nullable=False)
    path_type = Column(String(50), nullable=False)
    confidence = Column(Float, default=0.5)
    generation_prompt = Column(Text, nullable=True)
    basis_summary = Column(Text, nullable=True)
    profile = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  10. 未来自我对话
# ══════════════════════════════════════════════════════

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    future_self_id = Column(Integer, ForeignKey("future_selves.id"), nullable=False)
    role = Column(String(10), nullable=False)                # user / assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  11. 成长报告
# ══════════════════════════════════════════════════════

class GrowthReport(Base):
    __tablename__ = "growth_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    content = Column(JSON, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  12. 页面访问追踪
# ══════════════════════════════════════════════════════

class AgentChatMessage(Base):
    """智能体对话历史（agent 页刷新后恢复）"""
    __tablename__ = "agent_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    agent = Column(String(20), default="mentor")
    role = Column(String(10), nullable=False)                # user / assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PageVisit(Base):
    __tablename__ = "page_visits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    path = Column(String(100), nullable=False)
    label = Column(String(50), nullable=True)
    visit_count = Column(Integer, default=1)
    last_visited = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    first_visited = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  13. 人生拟真体验会话
# ══════════════════════════════════════════════════════

class SimulationSession(Base):
    __tablename__ = "simulation_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    future_self_id = Column(Integer, ForeignKey("future_selves.id"), nullable=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=True)
    random_seed = Column(Integer, default=42)
    start_year = Column(Integer, nullable=False)
    current_year = Column(Integer, nullable=False)
    current_age = Column(Integer, nullable=True)
    persona_snapshot = Column(JSON, nullable=True)
    current_state = Column(JSON, nullable=True)
    event_log = Column(JSON, default=list)
    status = Column(String(20), default="active")            # active / finished
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  14. 备忘录 / 通知 / 学生活动（原内存存储 → 持久化）
# ══════════════════════════════════════════════════════

class Memo(Base):
    __tablename__ = "memos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    note = Column(Text, default="")
    deadline = Column(String(50), default="")                # ISO 字符串，前端直接显示
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), default="")
    message = Column(Text, default="")
    read = Column(Boolean, default=False)
    meta = Column(JSON, default=dict)          # 附加数据（如组队邀请 {team_id}）
    created_at = Column(DateTime, default=datetime.utcnow)


class StudentActivity(Base):
    __tablename__ = "student_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), default="")
    description = Column(Text, default="")
    url = Column(String(500), default="")
    date = Column(String(50), default="")
    location = Column(String(200), default="")
    organizer = Column(String(200), default="")
    contact = Column(String(200), default="")
    status = Column(String(20), default="pending")           # pending / approved / rejected
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  15. 活动平台：活动 / 报名
# ══════════════════════════════════════════════════════

class Competition(Base):
    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    source_url = Column(String(500), default="")
    source_site = Column(String(100), default="")
    category = Column(String(50), default="")
    level = Column(String(20), default="")
    description = Column(Text, default="")
    registration_deadline = Column(DateTime, nullable=True)
    competition_date = Column(DateTime, nullable=True)
    organizer = Column(String(200), default="")
    max_team_size = Column(Integer, default=5)
    min_team_size = Column(Integer, default=1)
    credit_info = Column(Text, default="")
    tags = Column(JSON, default=list)
    ai_confidence = Column(Float, default=0.0)
    raw_content = Column(Text, default="")
    status = Column(String(20), default="active")            # active / expired / archived
    approval_status = Column(String(20), default="approved") # pending / approved / rejected
    publisher_type = Column(String(20), default="scraped")   # user / scraped
    publisher_name = Column(String(100), default="")
    publisher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_competition = Column(Boolean, default=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserActivity(Base):
    """用户报名活动"""
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    status = Column(String(20), default="registered")        # registered / cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "activity_id"),)


# ══════════════════════════════════════════════════════
#  16. 战队 / 成员
# ══════════════════════════════════════════════════════

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    slogan = Column(String(200), default="")
    description = Column(Text, default="")
    status = Column(String(20), default="recruiting")        # recruiting / full / closed
    created_at = Column(DateTime, default=datetime.utcnow)


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")              # leader / member
    joined_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("team_id", "user_id"),)


# ══════════════════════════════════════════════════════
#  17. 爬虫日志 / 学分记录
# ══════════════════════════════════════════════════════

class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_url = Column(String(500), default="")
    status = Column(String(20), default="success")
    items_found = Column(Integer, default=0)
    ai_filtered = Column(Integer, default=0)
    error_msg = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class CreditLog(Base):
    __tablename__ = "credit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    change = Column(Float, nullable=False)
    reason = Column(String(200), nullable=False)
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  18. 团队任务 / 申请
# ══════════════════════════════════════════════════════

class TeamTask(Base):
    __tablename__ = "team_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    required_roles = Column(JSON, default=list)              # [{role, count, skills}]
    deadline = Column(DateTime, nullable=True)
    status = Column(String(20), default="recruiting")        # recruiting / full / closed
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TaskAssignment(Base):
    __tablename__ = "task_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("team_tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(100), default="")
    status = Column(String(20), default="pending")           # pending / approved / rejected
    match_score = Column(Float, default=0.0)
    applied_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("task_id", "user_id"),)


# ══════════════════════════════════════════════════════
#  19. 协作文档 / 作品提交 / 文档版本
# ══════════════════════════════════════════════════════

class TeamDocument(Base):
    __tablename__ = "team_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, default="")
    task_type = Column(String(50), default="")               # poster / document / creative
    ai_suggestions = Column(Text, default="")
    web_resources = Column(JSON, default=list)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkSubmission(Base):
    __tablename__ = "work_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("team_documents.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(500), default="")
    file_name = Column(String(200), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class DocVersion(Base):
    __tablename__ = "doc_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("team_documents.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, default="")
    summary = Column(Text, default="")
    version_num = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  20. 团队聊天（与镜像 chat_messages 分离，避免主键/外键语义冲突）
# ══════════════════════════════════════════════════════

class TeamChatMessage(Base):
    __tablename__ = "team_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chat_type = Column(String(20), default="group")          # group 组内 / team 团队
    content = Column(Text, default="")
    image_url = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════
#  21. 任务进度
# ══════════════════════════════════════════════════════

class TaskProgress(Base):
    __tablename__ = "task_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("team_documents.id"), nullable=True)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    progress_pct = Column(Float, default=0.0)
    ai_comment = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
