"""活动组队平台 —— 数据库模型"""
import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def gen_uuid():
    return str(uuid.uuid4())


# ── 用户表 ──────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    real_name     = db.Column(db.String(50), nullable=False)
    avatar_url    = db.Column(db.String(500), default='')
    skill_tags    = db.Column(db.JSON, default=list)
    credit_score  = db.Column(db.Float, default=100.0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    teams_led     = db.relationship('TeamMember', backref='user', lazy=True,
                                     foreign_keys='TeamMember.user_id')

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

    @property
    def team_role(self):
        """返回用户当前的角色和所属团队，若无则返回 None"""
        tm = TeamMember.query.filter_by(user_id=self.id).first()
        if tm:
            team = Team.query.get(tm.team_id)
            return {'role': tm.role, 'team': team}
        return None


# ── 活动信息表 ──────────────────────────────────────
class Competition(db.Model):
    __tablename__ = 'competitions'

    id              = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    title           = db.Column(db.String(200), nullable=False)
    source_url      = db.Column(db.String(500), default='')
    source_site     = db.Column(db.String(100), default='')
    category        = db.Column(db.String(50), default='')
    level           = db.Column(db.String(20), default='')
    description     = db.Column(db.Text, default='')
    registration_deadline = db.Column(db.DateTime, default=None)
    competition_date = db.Column(db.DateTime, default=None)
    organizer       = db.Column(db.String(200), default='')
    max_team_size   = db.Column(db.Integer, default=5)
    min_team_size   = db.Column(db.Integer, default=1)
    credit_info     = db.Column(db.Text, default='')
    tags            = db.Column(db.JSON, default=list)
    ai_confidence   = db.Column(db.Float, default=0.0)
    raw_content     = db.Column(db.Text, default='')
    status          = db.Column(db.String(20), default='active')       # active / expired / archived
    approval_status = db.Column(db.String(20), default='approved')    # pending / approved / rejected
    publisher_type  = db.Column(db.String(20), default='scraped')     # user / scraped
    publisher_name  = db.Column(db.String(100), default='')           # 发布者名字/爬取来源
    publisher_id    = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    is_competition  = db.Column(db.Boolean, default=False)             # AI 标记是否为竞赛
    scraped_at      = db.Column(db.DateTime, default=datetime.utcnow)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    publisher = db.relationship('User', backref='created_activities', lazy=True)
    teams = db.relationship('Team', backref='competition', lazy=True,
                            cascade='all, delete-orphan')
    registrations = db.relationship('UserActivity', backref='activity', lazy=True,
                                    cascade='all, delete-orphan')


# ── 用户报名活动表 ───────────────────────────────────
class UserActivity(db.Model):
    __tablename__ = 'user_activities'

    id          = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id     = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    activity_id = db.Column(db.String(36), db.ForeignKey('competitions.id'), nullable=False)
    status      = db.Column(db.String(20), default='registered')      # registered / cancelled
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='activity_registrations', lazy=True)

    __table_args__ = (db.UniqueConstraint('user_id', 'activity_id'),)


# ── 战队表 ──────────────────────────────────────────
class Team(db.Model):
    __tablename__ = 'teams'

    id             = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    competition_id = db.Column(db.String(36), db.ForeignKey('competitions.id'), nullable=False)
    leader_id      = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    name           = db.Column(db.String(50), nullable=False)
    slogan         = db.Column(db.String(200), default='')
    description    = db.Column(db.Text, default='')
    status         = db.Column(db.String(20), default='recruiting')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    leader  = db.relationship('User', backref='teams_led_ref', lazy=True)
    members = db.relationship('TeamMember', backref='team', lazy=True,
                              cascade='all, delete-orphan')


# ── 战队成员表 ──────────────────────────────────────
class TeamMember(db.Model):
    __tablename__ = 'team_members'

    id        = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    team_id   = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=False)
    user_id   = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    role      = db.Column(db.String(20), default='member')            # leader / member
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('team_id', 'user_id'),)


# ── 爬虫日志表 ──────────────────────────────────────
class ScrapeLog(db.Model):
    __tablename__ = 'scrape_logs'

    id           = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    source_url   = db.Column(db.String(500), default='')
    status       = db.Column(db.String(20), default='success')
    items_found  = db.Column(db.Integer, default=0)
    ai_filtered  = db.Column(db.Integer, default=0)
    error_msg    = db.Column(db.Text, default='')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


# ── 信誉变动记录表 ──────────────────────────────────
class CreditLog(db.Model):
    __tablename__ = 'credit_logs'

    id         = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id    = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    change     = db.Column(db.Float, nullable=False)
    reason     = db.Column(db.String(200), nullable=False)
    detail     = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='credit_logs', lazy=True)


# ── 团队任务表 ──────────────────────────────────────
class TeamTask(db.Model):
    __tablename__ = 'team_tasks'

    id             = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    team_id        = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=False)
    title          = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.Text, default='')
    required_roles = db.Column(db.JSON, default=list)   # [{role, count, skills}]
    deadline       = db.Column(db.DateTime, default=None)
    status         = db.Column(db.String(20), default='recruiting')  # recruiting/full/closed
    created_by     = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    team   = db.relationship('Team', backref='tasks', lazy=True)
    creator = db.relationship('User', backref='created_tasks', lazy=True)
    assignments = db.relationship('TaskAssignment', backref='task_ref', lazy=True,
                                  cascade='all, delete-orphan')


# ── 任务分配/申请表 ──────────────────────────────────
class TaskAssignment(db.Model):
    __tablename__ = 'task_assignments'

    id          = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    task_id     = db.Column(db.String(36), db.ForeignKey('team_tasks.id'), nullable=False)
    user_id     = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    role       = db.Column(db.String(100), default='')          # 担任的角色名称
    status      = db.Column(db.String(20), default='pending')   # pending/approved/rejected
    match_score = db.Column(db.Float, default=0.0)              # AI 技能匹配度
    applied_at  = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, default=None)

    user = db.relationship('User', backref='task_assignments', lazy=True)

    __table_args__ = (db.UniqueConstraint('task_id', 'user_id'),)


# ── 团队协作文档表 ──────────────────────────────────
class TeamDocument(db.Model):
    """AI 创建的公共协作文档（如海报、文创任务）"""
    __tablename__ = 'team_documents'

    id          = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    team_id     = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    content     = db.Column(db.Text, default='')            # AI 生成的文档内容 / 预览 HTML
    task_type   = db.Column(db.String(50), default='')      # poster / document / creative
    ai_suggestions = db.Column(db.Text, default='')          # AI 建议
    web_resources   = db.Column(db.JSON, default=list)       # 网络搜索资源
    created_by  = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    team    = db.relationship('Team', backref='documents', lazy=True)
    creator = db.relationship('User', backref='created_documents', lazy=True)
    submissions = db.relationship('WorkSubmission', backref='document', lazy=True,
                                  cascade='all, delete-orphan')


# ── 成员作品提交表 ──────────────────────────────────
class WorkSubmission(db.Model):
    """成员上传的作品 / 交付物"""
    __tablename__ = 'work_submissions'

    id          = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey('team_documents.id'), nullable=True)
    team_id     = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=False)
    user_id     = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    file_path   = db.Column(db.String(500), default='')     # 上传文件路径
    file_name   = db.Column(db.String(200), default='')     # 原始文件名
    description = db.Column(db.Text, default='')            # 成员描述
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='work_submissions', lazy=True)
    team = db.relationship('Team', backref='submissions', lazy=True)


# ── 聊天消息表 ──────────────────────────────────────
class ChatMessage(db.Model):
    """组内聊天 & 团队聊天消息"""
    __tablename__ = 'chat_messages'

    id          = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    team_id     = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=False)
    user_id     = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    chat_type   = db.Column(db.String(20), default='group')   # 'group' 组内 / 'team' 团队
    content     = db.Column(db.Text, default='')
    image_url   = db.Column(db.String(500), default='')       # 图片消息
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='chat_messages', lazy=True)
    team = db.relationship('Team', backref='chat_messages', lazy=True)


# ── 任务进度表 ──────────────────────────────────────
class TaskProgress(db.Model):
    """AI 计算的任务进度"""
    __tablename__ = 'task_progress'

    id              = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    team_id         = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=False)
    document_id     = db.Column(db.String(36), db.ForeignKey('team_documents.id'), nullable=True)
    total_tasks     = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    progress_pct    = db.Column(db.Float, default=0.0)        # 0-100
    ai_comment      = db.Column(db.Text, default='')          # AI 评语
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship('Team', backref='progress', lazy=True)


# ── 文档版本历史表 ──────────────────────────────────
class DocVersion(db.Model):
    """每次 AI 合并后的文档版本快照"""
    __tablename__ = 'doc_versions'

    id          = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey('team_documents.id'), nullable=False)
    team_id     = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=False)
    user_id     = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    content     = db.Column(db.Text, default='')             # 该版本的完整文档内容
    summary     = db.Column(db.Text, default='')             # AI 合并摘要
    version_num = db.Column(db.Integer, default=1)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='doc_versions', lazy=True)
    doc  = db.relationship('TeamDocument', backref='versions', lazy=True)
