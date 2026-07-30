"""活动组队平台 —— Flask 主应用"""
import sys
import os
import threading
import time as _time_module
# 修复 site-packages 路径
_site_pkgs = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages')
if os.path.isdir(_site_pkgs) and _site_pkgs not in sys.path:
    sys.path.insert(0, _site_pkgs)

import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Competition, Team, TeamMember, ScrapeLog, CreditLog, UserActivity, TeamTask, TaskAssignment, TeamDocument, WorkSubmission, ChatMessage, TaskProgress, DocVersion

# ── 初始化 ──────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'activity-team-platform-2026'
app.config['TEMPLATES_AUTO_RELOAD'] = True
_basedir = os.path.dirname(os.path.abspath(__file__))
_db_path = os.path.join(_basedir, 'competition_platform.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + _db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(_basedir, 'static', 'backgrounds')
app.config['WORK_UPLOAD_FOLDER'] = os.path.join(_basedir, 'static', 'uploads')
_BG_DIR = os.path.join(_basedir, 'static', 'backgrounds')
_WORK_UPLOAD_DIR = os.path.join(_basedir, 'static', 'uploads')

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'
login_manager.login_message = '\u8bf7\u5148\u767b\u5f55'

@app.route('/api/team/<team_id>/close', methods=['POST'])
def api_team_close(team_id):
    team = Team.query.get_or_404(team_id)
    if team.status not in ('recruiting', 'full'):
        return jsonify({'error': '\u5f53\u524d\u72b6\u6001\u4e0d\u5141\u8bb8\u5173\u95ed\u62db\u52df'}), 400
    team.status = 'closed'
    db.session.commit()
    return jsonify({'ok': True, 'message': '\u62db\u52df\u5df2\u5173\u95ed'})


@app.route('/api/work/data')
def api_work_data():
    """\u5de5\u4f5c\u53f0\u805a\u5408\u6570\u636e"""
    tm = TeamMember.query.filter_by(user_id=current_user.id).first() if current_user.is_authenticated else None
    if not tm:
        return jsonify({'has_team': False})
    team = Team.query.get(tm.team_id)
    if not team:
        return jsonify({'has_team': False})
    comp = Competition.query.get(team.competition_id)
    tasks = TeamTask.query.filter_by(team_id=team.id).order_by(TeamTask.created_at.desc()).all()
    members = TeamMember.query.filter_by(team_id=team.id).all()
    return jsonify({
        'has_team': True,
        'my_role': tm.role,
        'is_working_phase': team.status in ('full', 'closed'),
        'team': {'id': team.id, 'name': team.name, 'status': team.status, 'slogan': team.slogan, 'description': team.description},
        'competition': {'id': comp.id, 'title': comp.title, 'registration_deadline': comp.registration_deadline.strftime('%Y-%m-%d') if comp.registration_deadline else ''} if comp else None,
        'tasks': [{'id': t.id, 'title': t.title, 'description': t.description, 'status': t.status, 'deadline': t.deadline.strftime('%Y-%m-%d') if t.deadline else ''} for t in tasks],
        'members': [{'user_id': m.user_id, 'role': m.role, 'name': (lambda u: u.real_name if u else '')(User.query.get(m.user_id))} for m in members],
    })


# \u2500\u2500 \u6821\u56ed\u6d3b\u52a8\u63a5\u53e3\uff08\u7ed9 Activities \u9875\u9762\u7528\uff09\u2500\u2500
@app.route('/api/activities')
def api_activities():
    """\u8fd4\u56de\u683c\u5f0f\u517c\u5bb9\u65e7 Activities \u9875\u9762"""
    q = Competition.query.filter(
        Competition.approval_status == 'approved',
        Competition.is_competition == False,
    ).order_by(Competition.created_at.desc()).limit(30)
    activities = q.all()
    return jsonify({'items': [{
        'id': a.id, 'title': a.title, 'summary': (a.description or '')[:200],
        'category': a.category, 'level': a.level,
        'publishDate': a.registration_deadline.strftime('%Y-%m-%d') if a.registration_deadline else '',
        'url': a.source_url or '', 'source_site': a.source_site or '',
        'tags': a.tags or [], 'organizer': a.organizer or '',
        'credit_info': a.credit_info or '',
    } for a in activities]})

# \u2500\u2500 \u7edf\u4e00\u8ba4\u8bc1\uff1a\u901a\u8fc7 Mirror cookie \u81ea\u52a8\u767b\u5f55 Flask \u2500\u2500
@app.before_request
def _mirror_auth():
    if request.path.startswith('/api/') and request.path != '/api/check-username':
        if not current_user.is_authenticated:
            uid = request.cookies.get('mirror_uid', '1')
            uname = request.cookies.get('mirror_username', 'dev')
            user = User.query.filter_by(username=uname).first()
            if not user:
                user = User(username=uname, real_name=uname)
                user.set_password('mirror_auto_' + str(uid))
                db.session.add(user)
                db.session.commit()
            login_user(user)


@login_manager.user_loader
def load_user(uid):
    return User.query.get(uid)


# ═══════════════════════════════════════════════════════
#  认证路由
# ═══════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'\u6b22\u8fce\u56de\u6765\uff0c{user.real_name}\uff01', 'success')
            return redirect(url_for('dashboard'))
        flash('\u7528\u6237\u540d\u6216\u5bc6\u7801\u9519\u8bef', 'danger')
    bg_images = _get_background_images()
    if not bg_images and os.path.isdir(_BG_DIR):
        for f in os.listdir(_BG_DIR):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                bg_images.append(f)
    bg_url = url_for('static', filename='backgrounds/' + bg_images[0]) if bg_images else ''
    show_register = request.args.get('register') == '1'
    return render_template('login.html', bg_images=bg_images, bg_url=bg_url, show_register=show_register)


@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        real_name = request.form.get('real_name', '').strip()
        skill_tags_str = request.form.get('skill_tags', '')
        skill_tags = [t.strip() for t in skill_tags_str.split(',') if t.strip()] if skill_tags_str else []

        if User.query.filter_by(username=username).first():
            flash('\u8be5\u7528\u6237\u540d\u5df2\u6ce8\u518c\uff0c\u65e0\u6cd5\u91cd\u590d\u6ce8\u518c', 'danger')
            return redirect(url_for('login_page', register='1'))

        if len(password) < 8 or len(password) > 16:
            flash('\u5bc6\u7801\u957f\u5ea6\u5fc5\u987b\u57288-16\u4f4d\u4e4b\u95f4', 'danger')
            return redirect(url_for('login_page', register='1'))
        if not any(c.isupper() for c in password):
            flash('\u5bc6\u7801\u5fc5\u987b\u5305\u542b\u5927\u5199\u5b57\u6bcd', 'danger')
            return redirect(url_for('login_page', register='1'))
        if not any(c.islower() for c in password):
            flash('\u5bc6\u7801\u5fc5\u987b\u5305\u542b\u5c0f\u5199\u5b57\u6bcd', 'danger')
            return redirect(url_for('login_page', register='1'))
        if not any(c.isdigit() for c in password) and not any(not c.isalnum() for c in password):
            flash('\u5bc6\u7801\u5fc5\u987b\u5305\u542b\u6570\u5b57\u6216\u7279\u6b8a\u5b57\u7b26', 'danger')
            return redirect(url_for('login_page', register='1'))

        user = User(username=username, real_name=real_name, skill_tags=skill_tags)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('\u6ce8\u518c\u6210\u529f\uff0c\u8bf7\u767b\u5f55', 'success')
        return redirect(url_for('login_page'))
    return redirect(url_for('login_page', register='1'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))


@app.route('/api/check-username')
def api_check_username():
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({'exists': False})
    exists = User.query.filter_by(username=username).first() is not None
    return jsonify({'exists': exists})


# ═══════════════════════════════════════════════════════
#  JSON API — 供 React 前端调用
# ═══════════════════════════════════════════════════════

@app.route('/api/competitions')
@login_required
def api_competitions():
    """活动列表 JSON"""
    category = request.args.get('category', '')
    level = request.args.get('level', '')
    search = request.args.get('search', '').strip()
    q = Competition.query.filter(
        Competition.approval_status == 'approved',
        Competition.is_competition == False,
        Competition.status == 'active'
    )
    if category: q = q.filter_by(category=category)
    if level: q = q.filter_by(level=level)
    if search: q = q.filter(Competition.title.contains(search) | Competition.description.contains(search))
    activities = q.order_by(Competition.created_at.desc()).all()
    categories = sorted(set(c.category for c in Competition.query.filter(Competition.approval_status == 'approved', Competition.is_competition == False).all() if c.category))
    levels = sorted(set(c.level for c in Competition.query.filter(Competition.approval_status == 'approved', Competition.is_competition == False).all() if c.level))
    return jsonify({
        'activities': [{'id': a.id, 'title': a.title, 'category': a.category, 'level': a.level,
            'description': (a.description or '')[:200], 'organizer': a.organizer,
            'max_team_size': a.max_team_size, 'min_team_size': a.min_team_size,
            'registration_deadline': a.registration_deadline.strftime('%Y-%m-%d') if a.registration_deadline else '',
            'credit_info': a.credit_info, 'tags': a.tags or [],
            'team_count': Team.query.filter_by(competition_id=a.id).count(),
            'created_at': a.created_at.strftime('%Y-%m-%d') if a.created_at else ''} for a in activities],
        'categories': categories, 'levels': levels,
    })


@app.route('/api/competitions/<comp_id>')
@login_required
def api_competition_detail(comp_id):
    """活动详情 JSON"""
    a = Competition.query.get_or_404(comp_id)
    teams = Team.query.filter_by(competition_id=a.id).all()
    my_team = None
    for tm in TeamMember.query.filter_by(user_id=current_user.id).all():
        t = Team.query.get(tm.team_id)
        if t and t.competition_id == a.id:
            my_team = {'id': t.id, 'name': t.name, 'status': t.status, 'role': tm.role}
            break
    return jsonify({
        'id': a.id, 'title': a.title, 'category': a.category, 'level': a.level,
        'description': a.description, 'organizer': a.organizer,
        'max_team_size': a.max_team_size, 'min_team_size': a.min_team_size,
        'registration_deadline': a.registration_deadline.strftime('%Y-%m-%d') if a.registration_deadline else '',
        'credit_info': a.credit_info, 'tags': a.tags or [], 'status': a.status,
        'teams': [{'id': t.id, 'name': t.name, 'slogan': t.slogan,
            'status': t.status, 'member_count': TeamMember.query.filter_by(team_id=t.id).count(),
            'leader_name': User.query.get(t.leader_id).real_name if t.leader_id else ''} for t in teams],
        'my_team': my_team,
    })


@app.route('/api/teams/<team_id>')
@login_required
def api_team_detail(team_id):
    """战队详情 JSON"""
    t = Team.query.get_or_404(team_id)
    comp = t.competition
    members = TeamMember.query.filter_by(team_id=t.id).all()
    my_membership = TeamMember.query.filter_by(team_id=t.id, user_id=current_user.id).first()
    return jsonify({
        'id': t.id, 'name': t.name, 'slogan': t.slogan, 'description': t.description,
        'status': t.status, 'leader_id': t.leader_id,
        'competition': {'id': comp.id, 'title': comp.title, 'category': comp.category,
            'level': comp.level, 'max_team_size': comp.max_team_size,
            'registration_deadline': comp.registration_deadline.strftime('%Y-%m-%d') if comp.registration_deadline else '',
            'credit_info': comp.credit_info},
        'members': [{'user_id': m.user_id, 'role': m.role,
            'name': (lambda u: u.real_name if u else '')(User.query.get(m.user_id)),
            'skill_tags': (lambda u: u.skill_tags or [] if u else [])(User.query.get(m.user_id)),
            'credit_score': (lambda u: int(u.credit_score) if u else 0)(User.query.get(m.user_id))} for m in members],
        'my_role': my_membership.role if my_membership else None,
    })


@app.route('/api/teams/<team_id>/join', methods=['POST'])
@login_required
def api_team_join(team_id):
    """加入战队 JSON"""
    team = Team.query.get_or_404(team_id)
    comp = team.competition
    if team.status != 'recruiting':
        return jsonify({'error': '该战队已停止招募'}), 400
    for tm in TeamMember.query.filter_by(user_id=current_user.id).all():
        t = Team.query.get(tm.team_id)
        if t and t.competition_id == comp.id:
            return jsonify({'error': '你已在该活动中加入了其他战队'}), 400
    current_count = TeamMember.query.filter_by(team_id=team.id).count()
    if comp.max_team_size and current_count >= comp.max_team_size:
        return jsonify({'error': '该战队已满员'}), 400
    db.session.add(TeamMember(team_id=team.id, user_id=current_user.id, role='member'))
    db.session.commit()
    if comp.max_team_size and TeamMember.query.filter_by(team_id=team.id).count() >= comp.max_team_size:
        team.status = 'full'
        db.session.commit()
    return jsonify({'ok': True, 'message': '加入战队成功！'})


@app.route('/api/my-teams')
@login_required
def api_my_teams():
    """我的战队 JSON"""
    my_teams = TeamMember.query.filter_by(user_id=current_user.id).all()
    result = []
    for tm in my_teams:
        team = Team.query.get(tm.team_id)
        if team:
            comp = Competition.query.get(team.competition_id)
            if comp:
                result.append({
                    'team_id': team.id, 'team_name': team.name, 'team_status': team.status,
                    'role': tm.role,
                    'competition_id': comp.id, 'competition_title': comp.title,
                    'member_count': TeamMember.query.filter_by(team_id=team.id).count(),
                })
    return jsonify({'teams': result})


@app.before_request
def _api_auth_check():
    """所有 /api/ 请求未登录时返回 JSON 错误，而非 HTML 重定向"""
    if request.path.startswith('/api/') and not current_user.is_authenticated:
        # 排除不需要登录的端点
        if request.path == '/api/check-username':
            return None
        return jsonify({'error': '请先登录', 'need_login': True}), 401

@app.route('/api/competition/create', methods=['POST'])
def api_create_competition():
    """创建活动 JSON"""
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title: return jsonify({'error': '活动名称不能为空'}), 400
    comp = Competition(
        title=title,
        category=data.get('category', ''),
        level=data.get('level', ''),
        description=data.get('description', '').strip(),
        organizer=data.get('organizer', '').strip(),
        max_team_size=int(data.get('max_team_size', 5)),
        min_team_size=int(data.get('min_team_size', 1)),
        registration_deadline=datetime.fromisoformat(data['registration_deadline']) if data.get('registration_deadline') else None,
        credit_info=data.get('credit_info', '').strip(),
        tags=[t.strip() for t in data.get('tags', '').split(',') if t.strip()],
        approval_status='pending',
        publisher_type='user',
        publisher_name=current_user.real_name,
        publisher_id=current_user.id,
        is_competition=False,
    )
    db.session.add(comp)
    db.session.commit()
    return jsonify({'ok': True, 'id': comp.id, 'message': '活动已提交，等待审核'})


@app.route('/api/competition/<comp_id>/approve', methods=['POST'])
@login_required
def api_approve_competition(comp_id):
    comp = Competition.query.get_or_404(comp_id)
    comp.approval_status = 'approved'
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/competition/<comp_id>/reject', methods=['POST'])
@login_required
def api_reject_competition(comp_id):
    comp = Competition.query.get_or_404(comp_id)
    comp.approval_status = 'rejected'
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/pending-activities')
@login_required
def api_pending_activities():
    pending = Competition.query.filter_by(approval_status='pending', is_competition=False)\
        .order_by(Competition.created_at.desc()).all()
    return jsonify({'activities': [{
        'id': a.id, 'title': a.title, 'category': a.category, 'level': a.level,
        'description': (a.description or '')[:200], 'publisher_name': a.publisher_name,
        'registration_deadline': a.registration_deadline.strftime('%Y-%m-%d') if a.registration_deadline else '',
    } for a in pending]})


@app.route('/api/team/create', methods=['POST'])
@login_required
def api_create_team():
    """创建战队 JSON"""
    data = request.get_json() or {}
    comp_id = data.get('competition_id', '')
    team_name = data.get('team_name', '').strip()
    if not team_name: return jsonify({'error': '战队名称不能为空'}), 400
    activity = Competition.query.get_or_404(comp_id)
    if activity.status != 'active':
        return jsonify({'error': '该活动已截止'}), 400
    for tm in TeamMember.query.filter_by(user_id=current_user.id).all():
        t = Team.query.get(tm.team_id)
        if t and t.competition_id == activity.id:
            return jsonify({'error': '你已在该活动中加入了战队'}), 400
    team = Team(
        competition_id=activity.id, leader_id=current_user.id,
        name=team_name,
        slogan=data.get('slogan', '').strip(),
        description=data.get('description', '').strip(),
    )
    db.session.add(team)
    db.session.flush()
    db.session.add(TeamMember(team_id=team.id, user_id=current_user.id, role='leader'))
    db.session.commit()
    return jsonify({'ok': True, 'id': team.id, 'name': team.name})


@app.route('/api/scrape/trigger', methods=['POST'])
@login_required
def api_trigger_scrape():
    """触发爬虫 JSON"""
    stats = _do_scrape()
    return jsonify({'ok': True, 'stats': stats})


@app.route('/api/potential-friends')
@login_required
def api_potential_friends():
    """潜在好友推荐 —— 基于技能标签互补匹配"""
    my_skills = set(current_user.skill_tags or [])
    # 简单互补匹配：对方有我没有的技能
    all_users = User.query.filter(User.id != current_user.id).limit(100).all()
    scored = []
    for u in all_users:
        their_skills = set(u.skill_tags or [])
        complementary = their_skills - my_skills
        shared = their_skills & my_skills
        score = len(complementary) * 2 + len(shared)
        if score > 0:
            scored.append({
                'user_id': u.id, 'real_name': u.real_name,
                'skill_tags': u.skill_tags or [],
                'credit_score': int(u.credit_score),
                'complementary_skills': list(complementary)[:5],
                'shared_skills': list(shared)[:5],
                'match_score': score,
            })
    scored.sort(key=lambda x: -x['match_score'])
    return jsonify({'friends': scored[:8]})


def _get_background_images():
    images = []
    if os.path.isdir(_BG_DIR):
        for f in os.listdir(_BG_DIR):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                images.append(f)
    return images


# ═══════════════════════════════════════════════════════
#  首页
# ═══════════════════════════════════════════════════════

@app.route('/')
@login_required
def dashboard():
    # 统计
    total_activities = Competition.query.filter(
        Competition.approval_status == 'approved',
        Competition.is_competition == False
    ).count()
    active_activities = Competition.query.filter(
        Competition.approval_status == 'approved',
        Competition.is_competition == False,
        Competition.status == 'active'
    ).count()

    # 有截止日期的活动（给日历用）
    activities_with_deadline = Competition.query.filter(
        Competition.approval_status == 'approved',
        Competition.is_competition == False,
        Competition.status == 'active',
        Competition.registration_deadline != None
    ).all()

    deadline_events = []
    for a in activities_with_deadline:
        if a.registration_deadline:
            deadline_events.append({
                'date': a.registration_deadline.strftime('%Y-%m-%d'),
                'title': a.title[:20],
                'id': a.id,
            })

    return render_template('dashboard.html',
                           stats={'total': total_activities, 'active': active_activities},
                           deadline_events=deadline_events)


# ═══════════════════════════════════════════════════════
#  个人信息 & 修改密码
# ═══════════════════════════════════════════════════════

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    old_pwd = request.form.get('old_password', '')
    new_pwd = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    if not current_user.check_password(old_pwd):
        flash('\u5f53\u524d\u5bc6\u7801\u9519\u8bef', 'danger')
        return redirect(url_for('profile'))

    if new_pwd != confirm:
        flash('\u4e24\u6b21\u8f93\u5165\u7684\u65b0\u5bc6\u7801\u4e0d\u4e00\u81f4', 'danger')
        return redirect(url_for('profile'))

    if len(new_pwd) < 8 or len(new_pwd) > 16:
        flash('\u5bc6\u7801\u957f\u5ea6\u5fc5\u987b\u57288-16\u4f4d\u4e4b\u95f4', 'danger')
        return redirect(url_for('profile'))
    if not any(c.isupper() for c in new_pwd):
        flash('\u5bc6\u7801\u5fc5\u987b\u5305\u542b\u5927\u5199\u5b57\u6bcd', 'danger')
        return redirect(url_for('profile'))
    if not any(c.islower() for c in new_pwd):
        flash('\u5bc6\u7801\u5fc5\u987b\u5305\u542b\u5c0f\u5199\u5b57\u6bcd', 'danger')
        return redirect(url_for('profile'))
    if not any(c.isdigit() for c in new_pwd) and not any(not c.isalnum() for c in new_pwd):
        flash('\u5bc6\u7801\u5fc5\u987b\u5305\u542b\u6570\u5b57\u6216\u7279\u6b8a\u5b57\u7b26', 'danger')
        return redirect(url_for('profile'))

    current_user.set_password(new_pwd)
    db.session.commit()
    flash('\u5bc6\u7801\u4fee\u6539\u6210\u529f', 'success')
    return redirect(url_for('profile'))


# ═══════════════════════════════════════════════════════
#  我的活动
# ═══════════════════════════════════════════════════════

@app.route('/my-activities')
@login_required
def my_activities():
    # 用户参与的战队的对应活动
    my_teams = TeamMember.query.filter_by(user_id=current_user.id).all()
    team_activity_ids = set()
    team_data = []
    for tm in my_teams:
        team = Team.query.get(tm.team_id)
        if team:
            comp = Competition.query.get(team.competition_id)
            if comp and comp.id not in team_activity_ids:
                team_activity_ids.add(comp.id)
                team_data.append({
                    'team': team,
                    'activity': comp,
                    'role': tm.role,
                })

    return render_template('my_activities.html',
                           team_data=team_data)


# ═══════════════════════════════════════════════════════
#  工作页
# ═══════════════════════════════════════════════════════

@app.route('/work')
@login_required
def work_page():
    # 查找用户当前所在战队的任务
    my_team = None
    my_role = None
    tm = TeamMember.query.filter_by(user_id=current_user.id).first()
    if tm:
        my_team = Team.query.get(tm.team_id)
        my_role = tm.role

    tasks = []
    documents = []
    submissions = []
    progress = None
    is_working_phase = False

    if my_team:
        tasks = TeamTask.query.filter_by(team_id=my_team.id).order_by(
            TeamTask.created_at.desc()
        ).all()
        # 招募结束（closed / full）→ 进入工作阶段
        if my_team.status in ('closed', 'full'):
            is_working_phase = True
            documents = TeamDocument.query.filter_by(team_id=my_team.id).order_by(
                TeamDocument.created_at.desc()
            ).all()
            submissions = WorkSubmission.query.filter_by(team_id=my_team.id).order_by(
                WorkSubmission.created_at.desc()
            ).all()
            progress = TaskProgress.query.filter_by(team_id=my_team.id).first()

    # 成员任务分配详情（按人展示AI拆解的子任务）
    member_tasks = {}  # {user_id: {name, roles: [{task_title, role_name, task_id}]}}
    for task in tasks:
        assigns = TaskAssignment.query.filter_by(task_id=task.id, status='approved').all()
        for a in assigns:
            u = User.query.get(a.user_id)
            uid = str(a.user_id)
            if uid not in member_tasks:
                member_tasks[uid] = {
                    'name': u.real_name if u else '',
                    'roles': [],
                }
            member_tasks[uid]['roles'].append({
                'task_title': task.title,
                'role_name': a.role,
                'task_id': task.id,
            })

    # 战队成员列表（用于聊天显示）
    team_members = []
    if my_team:
        for m in TeamMember.query.filter_by(team_id=my_team.id).all():
            u = User.query.get(m.user_id)
            if u:
                team_members.append({
                    'id': str(u.id),
                    'real_name': str(u.real_name or ''),
                    'role': str(m.role or 'member'),
                    'skill_tags': list(u.skill_tags) if u.skill_tags else [],
                })

    # 任务分配总览（汇总所有任务的待审核和已分配）
    assignments_summary = []  # [{task_title, task_id, applicant_name, role, status, assign_id}]
    if my_team:
        for task in tasks:
            assigns = TaskAssignment.query.filter_by(task_id=task.id).all()
            for a in assigns:
                u = User.query.get(a.user_id)
                assignments_summary.append({
                    'task_title': task.title,
                    'task_id': task.id,
                    'applicant_name': u.real_name if u else '',
                    'role': a.role,
                    'status': a.status,
                    'assign_id': a.id,
                })

    # 计算最近截止时间
    next_deadline = None
    for task in tasks:
        if task.deadline:
            if next_deadline is None or task.deadline < next_deadline:
                next_deadline = task.deadline

    return render_template('work.html',
                           my_team=my_team,
                           my_role=my_role,
                           tasks=tasks,
                           is_working_phase=is_working_phase,
                           documents=documents,
                           submissions=submissions,
                           progress=progress,
                           team_members_json=json.dumps(team_members, ensure_ascii=False),
                           assignments_summary=assignments_summary,
                           member_tasks=list(member_tasks.values()),
                           credit_score=current_user.credit_score,
                           next_deadline=next_deadline)


# ── AI 拆解任务 ─────────────────────────────────
@app.route('/api/breakdown-task', methods=['POST'])
@login_required
def api_breakdown_task():
    data = request.get_json()
    title = data.get('title', '')
    description = data.get('description', '')

    # 找到用户所在战队的成员
    tm = TeamMember.query.filter_by(user_id=current_user.id).first()
    team_members = []
    if tm:
        team = Team.query.get(tm.team_id)
        if team:
            team_members = TeamMember.query.filter_by(team_id=team.id).all()

    from ai_filter import breakdown_task
    roles = breakdown_task(title, description, team_members)
    return jsonify({'roles': roles})


# ── 发布任务 ────────────────────────────────────
@app.route('/api/create-task', methods=['POST'])
@login_required
def api_create_task():
    data = request.get_json()
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    roles = data.get('roles', [])
    deadline_str = data.get('deadline', '')

    if not title:
        return jsonify({'error': '任务标题不能为空'}), 400

    tm = TeamMember.query.filter_by(user_id=current_user.id, role='leader').first()
    if not tm:
        return jsonify({'error': '只有队长才能发布任务'}), 403

    team = Team.query.get(tm.team_id)
    if not team:
        return jsonify({'error': '战队未找到'}), 404

    deadline = None
    if deadline_str:
        try:
            deadline = datetime.fromisoformat(deadline_str)
        except (ValueError, TypeError):
            pass

    task = TeamTask(
        team_id=team.id,
        title=title,
        description=description,
        required_roles=roles,
        deadline=deadline,
        created_by=current_user.id,
    )
    db.session.add(task)
    db.session.flush()

    db.session.commit()
    return jsonify({'ok': True, 'task_id': task.id})


# ── 队员申请加入任务角色 ─────────────────────────
@app.route('/api/task/<task_id>/apply', methods=['POST'])
@login_required
def api_task_apply(task_id):
    data = request.get_json()
    role_name = data.get('role', '')

    task = TeamTask.query.get_or_404(task_id)

    # 检查是否已申请
    existing = TaskAssignment.query.filter_by(
        task_id=task_id, user_id=current_user.id, role=role_name
    ).first()
    if existing:
        return jsonify({'error': '你已申请该角色'}), 400

    # 检查是否已有进行中的任务（同一团队内）
    other_approved = TaskAssignment.query.filter_by(
        user_id=current_user.id, status='approved'
    ).join(TeamTask).filter(
        TeamTask.team_id == task.team_id,
        TeamTask.id != task_id,
    ).all()
    if other_approved:
        for assign in other_approved:
            other_task = TeamTask.query.get(assign.task_id)
            if other_task:
                progress = TaskProgress.query.filter_by(team_id=task.team_id).first()
                if not progress or progress.progress_pct < 100:
                    return jsonify({'error': f'你已在「{other_task.title}」中担任角色，请先完成当前任务（进度 100%）再加入新任务'}), 400

    # 队长无需审核
    status = 'pending'
    match_score = 0.7
    tm = TeamMember.query.filter_by(
        team_id=task.team_id, user_id=current_user.id, role='leader'
    ).first()
    if tm:
        status = 'approved'
        match_score = 1.0
    else:
        from ai_filter import calc_match_score
        matches = [r for r in (task.required_roles or []) if r.get('role') == role_name]
        if matches:
            match_score = calc_match_score(current_user, matches[0])

    db.session.add(TaskAssignment(
        task_id=task_id,
        user_id=current_user.id,
        role=role_name,
        status=status,
        match_score=round(match_score, 2),
    ))
    db.session.commit()
    return jsonify({'ok': True, 'status': status})


# ── 队长审核 ────────────────────────────────────
@app.route('/api/task/<task_id>/review', methods=['POST'])
@login_required
def api_task_review(task_id):
    data = request.get_json()
    assign_id = data.get('assignment_id')
    action = data.get('action')  # 'approve' or 'reject'

    task = TeamTask.query.get_or_404(task_id)
    if task.created_by != current_user.id:
        return jsonify({'error': '只有队长才能审核'}), 403

    assignment = TaskAssignment.query.get_or_404(assign_id)
    assignment.status = 'approved' if action == 'approve' else 'rejected'
    assignment.resolved_at = datetime.utcnow()
    db.session.commit()

    # 检查是否所有角色都招满了
    _check_task_full(task)

    return jsonify({'ok': True})


# ── 获取信誉分 ───────────────────────────────────
@app.route('/api/credit/log')
@login_required
def api_credit_log():
    logs = CreditLog.query.filter_by(user_id=current_user.id)\
        .order_by(CreditLog.created_at.desc()).limit(20).all()
    return jsonify({
        'score': current_user.credit_score,
        'logs': [{
            'change': l.change,
            'reason': l.reason,
            'detail': l.detail,
            'time': l.created_at.strftime('%Y-%m-%d %H:%M') if l.created_at else '',
        } for l in logs],
    })


# ═══════════════════════════════════════════════════════
#  信誉分系统
# ═══════════════════════════════════════════════════════

def _deduct_credit(user, amount, reason, detail=''):
    """扣除信誉分，扣到 0 为止，记录日志"""
    user.credit_score = max(0, user.credit_score - amount)
    log = CreditLog(
        user_id=user.id,
        change=-amount,
        reason=reason,
        detail=detail,
    )
    db.session.add(log)
    db.session.flush()


# ── 退出任务 ────────────────────────────────────
@app.route('/api/task/<task_id>/leave', methods=['POST'])
@login_required
def api_task_leave(task_id):

    assignment = TaskAssignment.query.filter_by(
        task_id=task_id, user_id=current_user.id
    ).first()

    if not assignment:
        return jsonify({'error': '你未参与该任务'}), 400

    if assignment.status not in ('approved', 'pending'):
        return jsonify({'error': '当前状态无法退出'}), 400

    # 检查是否是队长 — 队长退出时拒绝整个任务（重置招募状态）
    tm = TeamMember.query.filter_by(
        team_id=task.team_id, user_id=current_user.id, role='leader'
    ).first()

    db.session.delete(assignment)

    if tm:
        # 队长退出任务 → 扣除 35 分（等同取消任务）
        _deduct_credit(current_user, 35, '中途退出任务（队长）', f'退出任务「{task.title}」并取消该任务')
        TaskAssignment.query.filter_by(task_id=task_id).delete()
        task.status = 'recruiting'
        team = Team.query.get(task.team_id)
        if team and team.status in ('full', 'member_partial'):
            other_tasks = TeamTask.query.filter(
                TeamTask.team_id == team.id,
                TeamTask.id != task_id,
                TeamTask.status.in_(['recruiting', 'full'])
            ).count()
            if other_tasks == 0:
                team.status = 'recruiting'
    else:
        # 普通成员中途退出 → 扣除 30 分
        _deduct_credit(current_user, 30, '中途退出任务', f'退出任务「{task.title}」')

    db.session.commit()
    return jsonify({'ok': True})


# ── 队长取消任务 ────────────────────────────────
@app.route('/api/task/<task_id>/cancel', methods=['POST'])
@login_required
def api_task_cancel(task_id):
    task = TeamTask.query.get_or_404(task_id)

    tm = TeamMember.query.filter_by(
        team_id=task.team_id, user_id=current_user.id, role='leader'
    ).first()
    if not tm:
        return jsonify({'error': '只有队长才能取消任务'}), 403

    # 删除所有分配记录
    TaskAssignment.query.filter_by(task_id=task_id).delete()
    # 删除关联文档
    TeamDocument.query.filter_by(task_id=task_id).delete()
    # 删除关联的作品提交
    WorkSubmission.query.filter_by(task_id=task_id).delete()
    # 删除任务
    db.session.delete(task)

    # 检查团队状态是否需要回退
    team = Team.query.get(tm.team_id)
    if team and team.status in ('full', 'member_partial'):
        other_tasks = TeamTask.query.filter(
            TeamTask.team_id == team.id,
            TeamTask.status.in_(['recruiting', 'full'])
        ).count()
        if other_tasks == 0:
            team.status = 'recruiting'

    db.session.commit()
    return jsonify({'ok': True})


# ── 队长解散团队 ────────────────────────────────
@app.route('/api/team/disband', methods=['POST'])
@login_required
def api_team_disband():
    tm = TeamMember.query.filter_by(
        user_id=current_user.id, role='leader'
    ).first()
    if not tm:
        return jsonify({'error': '只有队长才能解散团队'}), 403

    team_id = tm.team_id
    team = Team.query.get_or_404(team_id)

    # 删除团队所有相关数据
    TeamDocument.query.filter_by(team_id=team_id).delete()
    WorkSubmission.query.filter_by(team_id=team_id).delete()
    TaskAssignment.query.filter(
        TaskAssignment.task_id.in_(
            db.session.query(TeamTask.id).filter_by(team_id=team_id)
        )
    ).delete(synchronize_session='fetch')
    TeamTask.query.filter_by(team_id=team_id).delete()
    TaskProgress.query.filter_by(team_id=team_id).delete()
    ChatMessage.query.filter_by(team_id=team_id).delete()
    TeamMember.query.filter_by(team_id=team_id).delete()
    db.session.delete(team)

    # 解散团队 → 扣除 50 分
    _deduct_credit(current_user, 50, '擅自解散团队', f'解散团队「{team.name}」，所属任务全部取消')

    db.session.commit()
    return jsonify({'ok': True})


# ── 队长标记成员未完成任务 ─────────────────────────
@app.route('/api/task/<task_id>/mark-incomplete/<user_id>', methods=['POST'])
@login_required
def api_mark_incomplete(task_id, user_id):
    """队长标记某成员未完成任务 → 扣除 20 分"""
    task = TeamTask.query.get_or_404(task_id)
    tm = TeamMember.query.filter_by(
        team_id=task.team_id, user_id=current_user.id, role='leader'
    ).first()
    if not tm:
        return jsonify({'error': '只有队长才能操作'}), 403

    assignment = TaskAssignment.query.filter_by(
        task_id=task_id, user_id=user_id, status='approved'
    ).first()
    if not assignment:
        return jsonify({'error': '该成员未批准参与此任务'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    _deduct_credit(user, 20, '未完成任务', f'未完成「{task.title}」中的任务')
    db.session.commit()
    return jsonify({'ok': True, 'msg': f'已标记 {user.real_name} 未完成，扣除 20 信誉分'})


# ── 获取任务详情 ────────────────────────────────
@app.route('/api/task/<task_id>/data')
@login_required
def api_task_data(task_id):
    task = TeamTask.query.get_or_404(task_id)
    assignments = TaskAssignment.query.filter_by(task_id=task_id).all()

    roles = task.required_roles or []
    role_status = []
    for r in roles:
        role_name = r.get('role', '')
        applied = [a for a in assignments if a.role == role_name and a.status == 'pending']
        approved = [a for a in assignments if a.role == role_name and a.status == 'approved']
        role_status.append({
            'name': role_name,
            'needed': r.get('count', 1),
            'approved': len(approved),
            'applied': len(applied),
            'skills': r.get('skills', []),
            'hours': r.get('estimated_hours', 0),
        })

    # 申请人列表（待审核 + 已通过）
    applicants = []
    for a in assignments:
        u = User.query.get(a.user_id)
        applicants.append({
            'id': a.id,
            'user_id': a.user_id,
            'user_name': u.real_name if u else '',
            'user_skills': u.skill_tags if u else [],
            'role': a.role,
            'status': a.status,
            'match_score': a.match_score,
        })

    return jsonify({
        'task': {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'deadline': task.deadline.isoformat() if task.deadline else None,
            'status': task.status,
        },
        'roles': role_status,
        'applicants': applicants,
    })


def _check_task_full(task):
    """检查任务是否所有角色都已招满"""
    assignments = TaskAssignment.query.filter_by(task_id=task.id, status='approved').all()
    roles = task.required_roles or []
    all_full = True
    for r in roles:
        approved_count = len([a for a in assignments if a.role == r.get('role', '')])
        if approved_count < r.get('count', 1):
            all_full = False
            break
    if all_full:
        task.status = 'full'
        db.session.commit()


# ═══════════════════════════════════════════════════════
#  工作阶段 API —— AI 识别任务 & 协作文档
# ═══════════════════════════════════════════════════════

@app.route('/api/team/analyze-tasks', methods=['POST'])
@login_required
def api_analyze_tasks():
    """AI 识别团队任务，判断是否需要协作文档"""
    tm = TeamMember.query.filter_by(user_id=current_user.id).first()
    if not tm:
        return jsonify({'error': '你尚未加入任何团队'}), 400
    team = Team.query.get(tm.team_id)
    if not team:
        return jsonify({'error': '团队未找到'}), 404

    tasks = TeamTask.query.filter_by(team_id=team.id).all()
    if not tasks:
        return jsonify({'needs_doc': False, 'message': '暂无任务'})

    task_titles = [t.title for t in tasks]
    task_descs = [t.description or '' for t in tasks]

    # 任务关键词检测（需要协作文档的任务类型）
    creative_keywords = ['海报', '文创', '宣传', '设计', '视频', '剪辑', '动画',
                         'logo', 'banner', '封面', '展板', '画册', '插画', '手绘',
                         '海报设计', '视觉', '品牌', 'VI', '包装', '手册', '折页',
                         'poster', 'design', 'creative', 'illustration']
    document_keywords = ['ppt', '幻灯片', '演示', '文档', '报告', '论文', '文章',
                         '写稿', '文案', '写作', '总结', '汇报', '方案', '计划书',
                         '结题', '申报', '标书', '提案', '纪要', '记录', '说明书',
                         '白皮书', '调研', '分析报告', '策划', '脚本', '编剧',
                         '写文', '宣传稿', '新闻稿', '通讯', '推送', '排版',
                         '数据', '图表', '表格', 'excel', 'word', 'pdf',
                         '笔记', '整理', '编撰', '撰写', '起草', '编写']
    combined = ' '.join(task_titles + task_descs).lower()
    is_creative = any(kw in combined for kw in creative_keywords)
    is_document = any(kw in combined for kw in document_keywords)
    needs_doc = is_creative or is_document

    if not needs_doc:
        return jsonify({'needs_doc': False, 'message': '任务类型无需协作文档'})

    # 用大模型分析
    from ai_filter import ZHIPU_API_KEY, _llm_api_request
    doc_info = None
    try:
        if ZHIPU_API_KEY:
            prompt = f"""你是任务分析师。请分析以下团队任务，判断最佳协作方式。

任务列表：{json.dumps([{'title': t, 'desc': d[:200]} for t, d in zip(task_titles, task_descs)], ensure_ascii=False)}

请注意以下任务类型都需要创建共享协作文档：
- 文档类：PPT/幻灯片、Word文档、PDF报告、论文、文案、总结、策划方案、申报书等
- 设计类：海报、文创、宣传物料、视频、动画、LOGO、封面等

请返回 JSON：
{{
  "needs_doc": true,
  "task_type": "poster / video / document / creative",
  "doc_title": "协作文档标题",
  "doc_content": "AI 预生成的文档框架或设计需求概述（HTML格式，含结构大纲、要点提示）",
  "suggestions": "AI 给团队的具体执行建议",
  "milestones": ["阶段1", "阶段2", "阶段3"]
}}"""
            content = _llm_api_request([{'role': 'user', 'content': prompt}], max_tokens=1500)
            import re as _re
            json_match = _re.search(r'\{[\s\S]*\}', content)
            if json_match:
                doc_info = json.loads(json_match.group())
    except Exception as e:
        print(f'[AI分析] 失败: {e}')

    # 回退：使用规则引擎
    if not doc_info:
        fb_type = 'document' if is_document else 'creative'
        fb_milestones = ['需求分析', '大纲撰写', '内容分工', '汇总整合', '终稿审核'] if is_document else ['需求分析', '初稿设计', '汇总整合', '终稿审核']
        fb_suggestions = '建议先分工认领各自部分，完成后汇总整合、统一风格。' if is_document else '建议先分工，各自完成初稿后汇总整合。'
        doc_info = {
            'needs_doc': True,
            'task_type': fb_type,
            'doc_title': f'{task_titles[0]} — 协作空间',
            'doc_content': f'<h3>📋 {task_titles[0]}</h3><p>请团队成员在此协作完成各部分内容。</p>',
            'suggestions': fb_suggestions,
            'milestones': fb_milestones,
        }

    # 自动创建协作文档
    doc = TeamDocument(
        team_id=team.id,
        title=doc_info.get('doc_title', task_titles[0]),
        content=doc_info.get('doc_content', ''),
        task_type=doc_info.get('task_type', 'creative'),
        ai_suggestions=doc_info.get('suggestions', ''),
        web_resources=[],
        created_by=current_user.id,
    )
    db.session.add(doc)
    db.session.flush()

    # 自动创建进度记录
    milestones = doc_info.get('milestones', ['分析', '设计', '整合'])
    prog = TaskProgress(
        team_id=team.id,
        document_id=doc.id,
        total_tasks=len(milestones),
        completed_tasks=0,
        progress_pct=0.0,
        ai_comment=f'共 {len(milestones)} 个阶段待完成',
    )
    db.session.add(prog)
    db.session.commit()

    return jsonify({
        'needs_doc': True,
        'doc_id': doc.id,
        'doc_title': doc.title,
        'task_type': doc.task_type,
    })


@app.route('/api/team/doc/<doc_id>')
@login_required
def api_get_document(doc_id):
    """获取协作文档详情"""
    doc = TeamDocument.query.get_or_404(doc_id)
    submissions = WorkSubmission.query.filter_by(document_id=doc_id).order_by(
        WorkSubmission.created_at.desc()
    ).all()

    sub_data = []
    for s in submissions:
        u = User.query.get(s.user_id)
        sub_data.append({
            'id': s.id,
            'user_name': u.real_name if u else '',
            'file_path': s.file_path,
            'file_name': s.file_name,
            'file_url': url_for('static', filename='uploads/' + s.file_path) if s.file_path else '',
            'description': s.description,
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else '',
        })

    # AI 合并结果（将所有提交的描述合并）
    merged = ''
    if sub_data:
        parts = [f"<p><strong>{s['user_name']}</strong>: {s['description']}</p>" for s in sub_data if s['description']]
        if parts:
            merged = '<div class="merged-work">' + ''.join(parts) + '</div>'

    return jsonify({
        'doc': {
            'id': doc.id,
            'title': doc.title,
            'content': doc.content,
            'task_type': doc.task_type,
        },
        'submissions': sub_data,
        'merged': merged,
    })


@app.route('/api/team/doc/<doc_id>/merge', methods=['POST'])
@login_required
def api_merge_document(doc_id):
    """AI 智能融合所有成员的作品到协作文档中"""
    doc = TeamDocument.query.get_or_404(doc_id)
    submissions = WorkSubmission.query.filter_by(document_id=doc_id).order_by(
        WorkSubmission.created_at.desc()
    ).all()

    if not submissions:
        return jsonify({'ok': True, 'merged': doc.content or '<p>暂无成员提交，等待协作...</p>'})

    sub_info = []
    for s in submissions:
        u = User.query.get(s.user_id)
        sub_info.append({
            'user_name': u.real_name if u else '未知',
            'description': s.description or '',
            'file_name': s.file_name or '',
        })

    from ai_filter import ZHIPU_API_KEY, _llm_api_request
    merged_content = ''
    try:
        if ZHIPU_API_KEY:
            prompt = f"""你是团队协作文档的智能融合助手。请将以下成员的提交内容融合到文档框架中，生成一份完整的协同文档。

文档标题：{doc.title}
文档框架：
{doc.content}

各成员提交：
{json.dumps(sub_info, ensure_ascii=False)}

请将所有人的成果有机融合进文档框架，保持条理清晰。返回完整的 HTML 格式文档，用色块区分不同成员的贡献区域
（每个成员的贡献用 <div class="member-section" style="border-left:3px solid #6366f1;padding-left:12px;margin:12px 0;"> 包裹，
在其中用 <strong style="color:#6366f1;">成员名</strong> 标注），最后再加一段综合总结。
只返回 HTML，不要其他文字。"""
            merged_content = _llm_api_request(
                [{'role': 'user', 'content': prompt}],
                max_tokens=3000, temperature=0.5
            )
            import re as _re
            html_match = _re.search(r'(<div|<p|<h|<ul|<ol|<!DOCT)[\s\S]*', merged_content)
            if html_match:
                merged_content = html_match.group()
            else:
                merged_content = f'<div class="merged-work">{merged_content}</div>'
    except Exception as e:
        print(f'[AI合并] 失败: {e}')

    if not merged_content:
        parts = []
        for s in sub_info:
            if s['description']:
                parts.append(
                    f'<div class="member-section" style="border-left:3px solid #6366f1;padding-left:12px;margin:8px 0;">'
                    f'<strong style="color:#6366f1;">{s["user_name"]}</strong>'
                    f'{" · " + s["file_name"] if s["file_name"] else ""}'
                    f'<p>{s["description"]}</p></div>'
                )
        merged_content = (
            f'{doc.content or ""}'
            f'<h4 style="margin-top:20px;">成员贡献</h4>'
            f'{"".join(parts) if parts else "<p>暂无成员提交</p>"}'
        )

    doc.content = merged_content
    db.session.commit()

    return jsonify({'ok': True, 'merged': merged_content})


# ── 上传作品 ────────────────────────────────────
@app.route('/api/team/upload-work', methods=['POST'])
@login_required
def api_upload_work():
    """成员上传作品"""
    tm = TeamMember.query.filter_by(user_id=current_user.id).first()
    if not tm:
        return jsonify({'error': '你尚未加入任何团队'}), 400
    team = Team.query.get(tm.team_id)

    doc_id = request.form.get('doc_id', '')
    description = request.form.get('description', '').strip()
    file = request.files.get('file')

    os.makedirs(_WORK_UPLOAD_DIR, exist_ok=True)

    file_path = ''
    file_name = ''
    if file and file.filename:
        file_name = file.filename
        import uuid as _uuid
        ext = os.path.splitext(file.filename)[1]
        save_name = f"{_uuid.uuid4().hex}{ext}"
        file_path = os.path.join('uploads', save_name)
        file.save(os.path.join(_WORK_UPLOAD_DIR, save_name))

    submission = WorkSubmission(
        document_id=doc_id if doc_id else None,
        team_id=team.id,
        user_id=current_user.id,
        file_path=file_path,
        file_name=file_name,
        description=description,
    )
    db.session.add(submission)
    db.session.commit()

    # AI 更新进度
    _update_progress(team.id)

    return jsonify({'ok': True, 'submission_id': submission.id})


def _update_progress(team_id):
    """AI 根据提交情况更新进度"""
    doc = TeamDocument.query.filter_by(team_id=team_id).first()
    if not doc:
        return

    progress = TaskProgress.query.filter_by(team_id=team_id).first()
    if not progress:
        return

    members = TeamMember.query.filter_by(team_id=team_id).all()
    submissions = WorkSubmission.query.filter_by(team_id=team_id).all()
    submitter_ids = set(s.user_id for s in submissions)

    member_count = len(members)
    submitted_count = len(submitter_ids)

    if member_count > 0:
        pct = round(submitted_count / member_count * 100, 1)
    else:
        pct = 0

    progress.progress_pct = min(pct, 100)
    progress.completed_tasks = submitted_count
    progress.total_tasks = member_count
    progress.ai_comment = f'{submitted_count}/{member_count} 位成员已提交作品'
    progress.updated_at = datetime.utcnow()
    db.session.commit()


# ── AI 建议 & 网络搜索 ───────────────────────────
@app.route('/api/team/ai-suggestions', methods=['POST'])
@login_required
def api_ai_suggestions():
    """AI 帮当前用户搜索其认领任务的相关资料"""
    tm = TeamMember.query.filter_by(user_id=current_user.id).first()
    if not tm:
        return jsonify({'error': '未加入团队'}), 400
    team = Team.query.get(tm.team_id)
    doc = TeamDocument.query.filter_by(team_id=team.id).first()

    from ai_filter import ZHIPU_API_KEY, _llm_api_request, web_search
    suggestions = (doc.ai_suggestions or '') if doc else ''
    web_results = (doc.web_resources or []) if doc else []

    # 只取当前用户已批准的任务分配
    my_assignments = TaskAssignment.query.filter_by(
        user_id=current_user.id, status='approved'
    ).join(TeamTask).filter(TeamTask.team_id == team.id).all()

    if not my_assignments:
        return jsonify({
            'suggestions': '你还没有认领任何任务，请先加入任务后再搜索相关资料。',
            'web_resources': [],
        })

    my_task_info = []
    for a in my_assignments:
        task = TeamTask.query.get(a.task_id)
        if task:
            my_task_info.append(f'【{a.role}】{task.title}: {task.description or ""}')

    task_info = '\n'.join(my_task_info)

    try:
        if ZHIPU_API_KEY:
            # 第1步：让 AI 分析任务并生成搜索关键词
            prompt = f"""你是团队资料研究员。请根据以下成员认领的任务，为该成员推荐最相关的搜索关键词，帮 TA 找到有用的参考资料。

成员认领的任务：
{task_info}

请返回 JSON：
{{
  "suggestions": "一句话概述可以帮这位成员找到什么方向的资料",
  "search_queries": ["搜索关键词1", "搜索关键词2", "搜索关键词3"]
}}"""
            content = _llm_api_request([{'role': 'user', 'content': prompt}], max_tokens=600, temperature=0.4)
            import re as _re
            json_match = _re.search(r'\{[\s\S]*\}', content)
            if json_match:
                ai_result = json.loads(json_match.group())
                suggestions = ai_result.get('suggestions', '')

                # 第2步：用这些关键词真实搜索网络
                queries = ai_result.get('search_queries', [])
                web_results = []
                if not queries:
                    # 如果没有返回关键词，根据任务标题生成
                    queries = [t.title for t in tasks[:3]]

                for q in queries[:5]:
                    q = q.strip()
                    if not q:
                        continue
                    search_results = web_search(q, max_results=3)
                    web_results.extend(search_results)

                # 去重（按 URL）
                seen = set()
                unique_results = []
                for r in web_results:
                    if r['url'] not in seen:
                        seen.add(r['url'])
                        unique_results.append(r)
                web_results = unique_results[:8]

            # 保存到数据库（仅当有文档时）
            if doc:
                doc.ai_suggestions = suggestions
                doc.web_resources = web_results
                db.session.commit()
    except Exception as e:
        print(f'[AI建议] 失败: {e}')
        if not web_results:
            # 回退：直接用任务名搜索
            for task in tasks[:3]:
                search_results = web_search(task.title, max_results=3)
                web_results.extend(search_results)
            if doc:
                doc.web_resources = web_results
                db.session.commit()

    return jsonify({
        'suggestions': suggestions or '以下是为你找到的相关网络资源',
        'web_resources': web_results or [],
    })


# ═══════════════════════════════════════════════════════
#  聊天 API
# ═══════════════════════════════════════════════════════

@app.route('/api/chat/send', methods=['POST'])
@login_required
def api_chat_send():
    """发送聊天消息"""
    tm = TeamMember.query.filter_by(user_id=current_user.id).first()
    if not tm:
        return jsonify({'error': '未加入团队'}), 400

    data = request.get_json()
    content = data.get('content', '').strip()
    chat_type = data.get('chat_type', 'group')  # 'group' 或 'team'
    image_data = data.get('image_data', '')      # base64 图片
    image_url = data.get('image_url', '')        # 已上传的图片 URL

    if not content and not image_data and not image_url:
        return jsonify({'error': '消息不能为空'}), 400

    if image_data and not image_url:
        import base64
        import uuid as _uuid
        os.makedirs(_WORK_UPLOAD_DIR, exist_ok=True)
        try:
            img_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            img_name = f"chat_{_uuid.uuid4().hex}.png"
            img_path = os.path.join(_WORK_UPLOAD_DIR, img_name)
            with open(img_path, 'wb') as f:
                f.write(img_bytes)
            image_url = url_for('static', filename=f'uploads/{img_name}')
        except Exception as e:
            return jsonify({'error': f'图片处理失败: {str(e)}'}), 400

    msg = ChatMessage(
        team_id=tm.team_id,
        user_id=current_user.id,
        chat_type=chat_type,
        content=content,
        image_url=image_url,
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({
        'ok': True,
        'msg': {
            'id': msg.id,
            'user_name': current_user.real_name,
            'user_id': current_user.id,
            'content': msg.content,
            'image_url': msg.image_url,
            'chat_type': msg.chat_type,
            'created_at': msg.created_at.strftime('%H:%M'),
        }
    })


@app.route('/api/chat/messages/<chat_type>')
@login_required
def api_chat_messages(chat_type):
    """获取聊天消息列表"""
    tm = TeamMember.query.filter_by(user_id=current_user.id).first()
    if not tm:
        return jsonify({'messages': []})

    msgs = ChatMessage.query.filter_by(
        team_id=tm.team_id, chat_type=chat_type
    ).order_by(ChatMessage.created_at.asc()).limit(100).all()

    result = []
    for m in msgs:
        u = User.query.get(m.user_id)
        result.append({
            'id': m.id,
            'user_name': u.real_name if u else '',
            'user_id': m.user_id,
            'content': m.content,
            'image_url': m.image_url,
            'created_at': m.created_at.strftime('%H:%M'),
        })

    return jsonify({'messages': result})


@app.route('/api/chat/upload-image', methods=['POST'])
@login_required
def api_chat_upload_image():
    """上传聊天图片"""
    tm = TeamMember.query.filter_by(user_id=current_user.id).first()
    if not tm:
        return jsonify({'error': '未加入团队'}), 400

    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'error': '未选择文件'}), 400

    os.makedirs(_WORK_UPLOAD_DIR, exist_ok=True)
    import uuid as _uuid
    ext = os.path.splitext(file.filename)[1]
    save_name = f"chat_{_uuid.uuid4().hex}{ext}"
    file.save(os.path.join(_WORK_UPLOAD_DIR, save_name))
    image_url = url_for('static', filename=f'uploads/{save_name}')

    return jsonify({'ok': True, 'image_url': image_url})


# ── DeepSeek 对话 API ───────────────────────────
@app.route('/api/deepseek/chat', methods=['POST'])
@login_required
def api_deepseek_chat():
    """代理 DeepSeek 对话请求"""
    data = request.get_json()
    messages = data.get('messages', [])
    api_key = data.get('api_key', '').strip()
    if not messages:
        return jsonify({'error': '消息不能为空'}), 400

    from ai_filter import deepseek_chat, DEEPSEEK_API_KEY as _default_key

    effective_key = api_key or _default_key
    if not effective_key or (not api_key and _default_key.startswith('sk-a1b2c3')):
        return jsonify({
            'reply': '⚠ 请先点击左上角 ⚙ 设置按钮，输入你的 DeepSeek API Key。',
            'need_config': True,
        })

    try:
        system_msg = {
            'role': 'system',
            'content': '你是团队协作助手，帮助团队成员完成任务协作。回答简洁、实用、有建设性。'
        }
        full_messages = [system_msg] + messages

        reply = deepseek_chat(full_messages, max_tokens=2000, temperature=0.7)
        if reply is None:
            # 用用户提供的 key 重试
            if api_key:
                reply = _direct_deepseek(api_key, full_messages)
            if reply is None:
                return jsonify({'error': 'API 调用失败'}), 500
        return jsonify({'ok': True, 'reply': reply})
    except Exception as e:
        return jsonify({'error': f'DeepSeek API 错误: {str(e)}'}), 500


# ── 进度 API ────────────────────────────────────
@app.route('/api/team/progress')
@login_required
def api_team_progress():
    """获取任务进度"""
    tm = TeamMember.query.filter_by(user_id=current_user.id).first()
    if not tm:
        return jsonify({'progress_pct': 0, 'total_tasks': 0, 'completed_tasks': 0, 'ai_comment': ''})

    progress = TaskProgress.query.filter_by(team_id=tm.team_id).first()
    if not progress:
        # 自动创建
        tasks = TeamTask.query.filter_by(team_id=tm.team_id).all()
        members = TeamMember.query.filter_by(team_id=tm.team_id).all()
        progress = TaskProgress(
            team_id=tm.team_id,
            total_tasks=len(tasks),
            completed_tasks=0,
            progress_pct=0.0,
            ai_comment='任务刚开始',
        )
        db.session.add(progress)
        db.session.commit()

    return jsonify({
        'progress_pct': progress.progress_pct,
        'total_tasks': progress.total_tasks,
        'completed_tasks': progress.completed_tasks,
        'ai_comment': progress.ai_comment or '',
    })


# ═══════════════════════════════════════════════════════
#  信誉分记录
# ═══════════════════════════════════════════════════════

@app.route('/credit-log')
@login_required
def credit_log():
    logs = CreditLog.query.filter_by(user_id=current_user.id).order_by(
        CreditLog.created_at.desc()
    ).all()
    return render_template('credit_log.html', logs=logs)


# ═══════════════════════════════════════════════════════
#  活动大厅
# ═══════════════════════════════════════════════════════

@app.route('/competitions')
@login_required
def competition_list():
    category = request.args.get('category', '')
    level = request.args.get('level', '')
    search = request.args.get('search', '').strip()

    q = Competition.query.filter(
        Competition.approval_status == 'approved',
        Competition.is_competition == False,
        Competition.status == 'active'
    )
    if category:
        q = q.filter_by(category=category)
    if level:
        q = q.filter_by(level=level)
    if search:
        q = q.filter(Competition.title.contains(search) |
                     Competition.description.contains(search))

    activities = q.order_by(Competition.created_at.desc()).all()

    categories = sorted(set(
        c.category for c in Competition.query.filter(
            Competition.approval_status == 'approved',
            Competition.is_competition == False
        ).all() if c.category
    ))
    levels = sorted(set(
        c.level for c in Competition.query.filter(
            Competition.approval_status == 'approved',
            Competition.is_competition == False
        ).all() if c.level
    ))

    # 获取待审核活动
    pending_competitions = Competition.query.filter_by(
        approval_status='pending',
        is_competition=False
    ).order_by(Competition.created_at.desc()).all()

    return render_template('competitions.html',
                           competitions=activities,
                           categories=categories,
                           levels=levels,
                           current_category=category,
                           current_level=level,
                           search=search,
                           pending_competitions=pending_competitions)


# ═══════════════════════════════════════════════════════
#  创建活动（用户提交，需审核）
# ═══════════════════════════════════════════════════════

@app.route('/competition/create', methods=['GET', 'POST'])
@login_required
def create_activity():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '')
        level = request.form.get('level', '')
        description = request.form.get('description', '').strip()
        organizer = request.form.get('organizer', '').strip()
        max_team_size = int(request.form.get('max_team_size', 5))
        min_team_size = int(request.form.get('min_team_size', 1))
        deadline_str = request.form.get('registration_deadline', '').strip()
        credit_info = request.form.get('credit_info', '').strip()
        tags_str = request.form.get('tags', '')
        tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []

        if not title:
            flash('\u8bf7\u8f93\u5165\u6d3b\u52a8\u540d\u79f0', 'danger')
            return redirect(url_for('create_activity'))

        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str)
            except (ValueError, TypeError):
                pass

        activity = Competition(
            title=title,
            category=category,
            level=level,
            description=description,
            organizer=organizer or current_user.real_name,
            max_team_size=max_team_size,
            min_team_size=min_team_size,
            registration_deadline=deadline,
            credit_info=credit_info,
            tags=tags,
            publisher_type='user',
            publisher_name=current_user.real_name,
            publisher_id=current_user.id,
            approval_status='pending',
            is_competition=False,
            status='active',
            ai_confidence=1.0,
            source_url='',
            source_site='\u7528\u6237\u53d1\u5e03',
        )
        db.session.add(activity)
        db.session.commit()
        flash(f'\u6d3b\u52a8\u201c{title}\u201d\u5df2\u63d0\u4ea4\uff0c\u7b49\u5f85\u5ba1\u6838\u3002', 'success')
        return redirect(url_for('competition_list'))

    return render_template('create_activity.html')


@app.route('/competition/<comp_id>/approve', methods=['POST'])
@login_required
def approve_activity(comp_id):
    activity = Competition.query.get_or_404(comp_id)
    activity.approval_status = 'approved'
    db.session.commit()
    flash(f'\u6d3b\u52a8\u201c{activity.title}\u201d\u5df2\u901a\u8fc7\u5ba1\u6838', 'success')
    return redirect(url_for('competition_list'))


# ═══════════════════════════════════════════════════════
#  活动详情
# ═══════════════════════════════════════════════════════

@app.route('/competition/<comp_id>')
@login_required
def competition_detail(comp_id):
    activity = Competition.query.get_or_404(comp_id)
    teams = Team.query.filter_by(competition_id=activity.id).all()

    # 用户是否已有此活动的战队
    my_team = None
    for tm in TeamMember.query.filter_by(user_id=current_user.id).all():
        t = Team.query.get(tm.team_id)
        if t and t.competition_id == activity.id:
            my_team = t
            break

    # 用户是否已报名（保留字段，不再使用报名功能）
    is_registered = False

    # 发布者显示
    if activity.publisher_type == 'user':
        publisher_display = activity.publisher_name or '\u7528\u6237'
    else:
        publisher_display = activity.source_url or activity.source_site or '\u722c\u53d6'

    return render_template('competition_detail.html',
                           competition=activity,
                           teams=teams,
                           my_team=my_team,
                           is_registered=is_registered,
                           publisher_display=publisher_display)


# ═══════════════════════════════════════════════════════
#  活动报名（已移除）
#  用户可通过创建/加入战队参与活动


# ═══════════════════════════════════════════════════════
#  战队管理
# ═══════════════════════════════════════════════════════

@app.route('/competition/<comp_id>/create_team', methods=['POST'])
@login_required
def team_create(comp_id):
    activity = Competition.query.get_or_404(comp_id)
    if activity.status != 'active':
        flash('\u8be5\u6d3b\u52a8\u5df2\u622a\u6b62\uff0c\u65e0\u6cd5\u521b\u5efa\u6218\u961f', 'danger')
        return redirect(url_for('competition_detail', comp_id=activity.id))

    for tm in TeamMember.query.filter_by(user_id=current_user.id).all():
        t = Team.query.get(tm.team_id)
        if t and t.competition_id == activity.id:
            flash('\u4f60\u5df2\u5728\u8be5\u6d3b\u52a8\u4e2d\u52a0\u5165\u4e86\u6218\u961f', 'danger')
            return redirect(url_for('competition_detail', comp_id=activity.id))

    team_name = request.form.get('team_name', '').strip()
    slogan = request.form.get('slogan', '').strip()
    desc = request.form.get('description', '').strip()

    if not team_name:
        flash('\u6218\u961f\u540d\u79f0\u4e0d\u80fd\u4e3a\u7a7a', 'danger')
        return redirect(url_for('competition_detail', comp_id=activity.id))

    team = Team(
        competition_id=activity.id,
        leader_id=current_user.id,
        name=team_name,
        slogan=slogan,
        description=desc
    )
    db.session.add(team)
    db.session.flush()
    db.session.add(TeamMember(team_id=team.id, user_id=current_user.id, role='leader'))
    db.session.commit()

    flash(f'\u6218\u961f\u201c{team_name}\u201d\u521b\u5efa\u6210\u529f\uff01\u4f60\u662f\u961f\u957f\u3002', 'success')
    return redirect(url_for('team_detail', team_id=team.id))


@app.route('/team/<team_id>')
@login_required
def team_detail(team_id):
    team = Team.query.get_or_404(team_id)
    comp = team.competition

    my_membership = TeamMember.query.filter_by(
        team_id=team.id, user_id=current_user.id
    ).first()
    my_role = my_membership.role if my_membership else None
    members = TeamMember.query.filter_by(team_id=team.id).all()

    return render_template('team_detail.html',
                           team=team, competition=comp,
                           members=members, my_role=my_role)


@app.route('/team/<team_id>/join', methods=['POST'])
@login_required
def team_join(team_id):
    team = Team.query.get_or_404(team_id)
    comp = team.competition

    if team.status != 'recruiting':
        flash('\u8be5\u6218\u961f\u5df2\u505c\u6b62\u62db\u52df', 'danger')
        return redirect(url_for('team_detail', team_id=team.id))

    for tm in TeamMember.query.filter_by(user_id=current_user.id).all():
        t = Team.query.get(tm.team_id)
        if t and t.competition_id == comp.id:
            flash('\u4f60\u5df2\u5728\u8be5\u6d3b\u52a8\u4e2d\u52a0\u5165\u4e86\u5176\u4ed6\u6218\u961f', 'danger')
            return redirect(url_for('team_detail', team_id=team.id))

    current_count = TeamMember.query.filter_by(team_id=team.id).count()
    if comp.max_team_size and current_count >= comp.max_team_size:
        flash('\u8be5\u6218\u961f\u5df2\u6ee1\u5458', 'danger')
        return redirect(url_for('team_detail', team_id=team.id))

    db.session.add(TeamMember(team_id=team.id, user_id=current_user.id, role='member'))
    db.session.commit()

    if comp.max_team_size and TeamMember.query.filter_by(team_id=team.id).count() >= comp.max_team_size:
        team.status = 'full'
        db.session.commit()

    flash('\u52a0\u5165\u6218\u961f\u6210\u529f\uff01', 'success')
    return redirect(url_for('team_detail', team_id=team.id))


@app.route('/team/<team_id>/close', methods=['POST'])
@login_required
def team_close(team_id):
    team = Team.query.get_or_404(team_id)
    if team.leader_id != current_user.id:
        flash('\u53ea\u6709\u961f\u957f\u624d\u80fd\u64cd\u4f5c', 'danger')
        return redirect(url_for('team_detail', team_id=team.id))
    team.status = 'closed'
    db.session.commit()
    flash('\u6218\u961f\u62db\u52df\u5df2\u5173\u95ed', 'info')
    return redirect(url_for('team_detail', team_id=team.id))


# ═══════════════════════════════════════════════════════
#  爬虫 + AI 筛选
# ═══════════════════════════════════════════════════════
#  爬虫核心逻辑（供手动触发 + 定时调度共用）
# ═══════════════════════════════════════════════════════

def _do_scrape():
    """执行完整爬取流程，返回 stats 字典"""
    from scraper.sjtu_scraper import (
        scrape_all, is_competition_related, fetch_details_batch, TARGET_URLS,
    )
    from ai_filter import analyze_competition_page

    stats = {
        'raw': 0, 'screened': 0, 'saved': 0,
        'skipped_competition': 0, 'skipped_expired': 0, 'errors': 0,
        'site_errors': [],
    }

    try:
        raw_items, site_errors = scrape_all()
        stats['raw'] = len(raw_items)
        stats['site_errors'] = site_errors
    except Exception as e:
        stats['errors'] = 1
        print(f'[爬虫] 抓取失败: {e}')
        return stats

    related = [item for item in raw_items if is_competition_related(item['title'])]
    stats['screened'] = len(related)
    if not related:
        return stats

    details_map = fetch_details_batch(related)
    print(f'[爬虫] 详情页抓取完成：{len(details_map)} 篇')

    now = datetime.utcnow()

    for item in related:
        try:
            detail_text = details_map.get(item['url'], '')
            if not detail_text or detail_text.startswith('[\u6293\u53d6\u5931\u8d25'):
                stats['errors'] += 1
                continue

            result = analyze_competition_page(
                title=item['title'],
                url=item['url'],
                source=item['source'],
                detail_text=detail_text,
            )
            if not result:
                continue

            if result.get('is_competition') or result.get('type') == 'competition':
                stats['skipped_competition'] += 1
                continue
            if not result.get('needs_participation'):
                stats['skipped_competition'] += 1
                continue
            if result.get('type') in ('notice', 'lecture'):
                stats['skipped_competition'] += 1
                continue

            deadline = result.get('deadline')
            if deadline:
                try:
                    dl = datetime.fromisoformat(deadline)
                    if dl < now:
                        stats['skipped_expired'] += 1
                        continue
                except (ValueError, TypeError):
                    pass

            existing = Competition.query.filter_by(title=result['title']).first()
            if existing:
                continue

            comp = Competition(
                title=result['title'],
                source_url=result.get('source_url', item['url']),
                source_site=result.get('source_site', ''),
                category=result.get('category', ''),
                level=result.get('level', ''),
                description=result.get('description', ''),
                organizer=result.get('organizer', ''),
                max_team_size=result.get('max_team_size', 5),
                min_team_size=result.get('min_team_size', 1),
                credit_info=result.get('credit_info', ''),
                tags=result.get('tags', []),
                ai_confidence=result.get('ai_confidence', 0.7),
                raw_content=detail_text[:5000],
                publisher_type='scraped',
                publisher_name=item['url'],
                approval_status='approved',
                is_competition=False,
            )
            if result.get('deadline'):
                try:
                    comp.registration_deadline = datetime.fromisoformat(result['deadline'])
                except (ValueError, TypeError):
                    comp.registration_deadline = now + timedelta(days=45)
            else:
                comp.registration_deadline = now + timedelta(days=45)

            db.session.add(comp)
            stats['saved'] += 1
        except Exception as inner_e:
            stats['errors'] += 1
            print(f'[\u722c\u866b] \u5904\u7406\u5931\u8d25: {item.get("title","")[:30]} - {inner_e}')
            continue

    log = ScrapeLog(
        source_url=','.join(s['url'] for s in TARGET_URLS),
        items_found=stats['raw'],
        ai_filtered=stats['saved'],
        error_msg=f'{stats["errors"]} \u6761\u5904\u7406\u5931\u8d25' if stats['errors'] else '',
    )
    db.session.add(log)
    db.session.commit()

    print(f'[爬虫] 完成: {stats["raw"]}→{stats["screened"]}→{stats["saved"]} '
          f'(跳竞赛{stats["skipped_competition"]} 跳过期{stats["skipped_expired"]})')
    return stats


@app.route('/scrape', methods=['POST'])
@login_required
def trigger_scrape():
    """从活动大厅手动触发爬虫"""
    stats = _do_scrape()
    flash(f'\u6293\u53d6\u5b8c\u6210\uff01\u626b\u63cf {stats["raw"]} \u6761 \u2192 \u521d\u7b5b {stats["screened"]} \u6761 '
          f'\u2192 \u6392\u9664\u7ade\u8d5b {stats["skipped_competition"]} \u6761 '
          f'\u2192 \u6392\u9664\u8fc7\u671f {stats["skipped_expired"]} \u6761 '
          f'\u2192 \u5b58\u5165 {stats["saved"]} \u6761\u3002', 'success')
    return redirect(url_for('competition_list'))


@app.route('/dev/api/scrape', methods=['POST'])
def dev_trigger_scrape():
    """从开发者面板手动触发爬虫"""
    stats = _do_scrape()
    return jsonify({
        'ok': True,
        'raw': stats['raw'],
        'screened': stats['screened'],
        'saved': stats['saved'],
        'skipped_competition': stats['skipped_competition'],
        'skipped_expired': stats['skipped_expired'],
        'errors': stats['errors'],
        'site_errors': stats['site_errors'],
        'msg': f'{stats["raw"]}条→初筛{stats["screened"]}→入库{stats["saved"]}',
    })


@app.route('/dev/api/cleanup', methods=['POST'])
def dev_trigger_cleanup():
    """从开发者面板手动触发清理"""
    cleaned = _cleanup_activities()
    return jsonify({
        'ok': True,
        'cleaned': cleaned,
        'msg': f'清理完成: {cleaned} 条',
    })


# ═══════════════════════════════════════════════════════
#  定时调度（每天 00:00 和 12:00）
# ═══════════════════════════════════════════════════════

_last_scrape_run = None


def _cleanup_activities():
    """清理过期、不合要求、重复的活动"""
    with app.app_context():
        removed_count = 0
        now = datetime.utcnow()

        # 1. 删除过期活动（截止时间已过 或 爬取超过30天）
        expired = Competition.query.filter(
            db.or_(
                db.and_(Competition.registration_deadline != None, Competition.registration_deadline < now),
                Competition.scraped_at < now - timedelta(days=30),
            )
        ).all()
        for c in expired:
            db.session.delete(c)
            removed_count += 1
        if expired:
            db.session.commit()
            print(f'[清理] 过期活动: {len(expired)} 条')

        # 2. 删除竞赛类活动（is_competition=True）
        competitions = Competition.query.filter_by(is_competition=True).all()
        for c in competitions:
            db.session.delete(c)
            removed_count += 1
        if competitions:
            db.session.commit()
            print(f'[清理] 竞赛类活动: {len(competitions)} 条')

        # 3. 删除低置信度活动
        low_conf = Competition.query.filter(
            Competition.ai_confidence < 0.3,
            Competition.publisher_type == 'scraped',
        ).all()
        for c in low_conf:
            db.session.delete(c)
            removed_count += 1
        if low_conf:
            db.session.commit()
            print(f'[清理] 低置信度: {len(low_conf)} 条')

        # 4. 删除重复活动（相同标题+来源，保留最新的）
        dup_groups = db.session.execute(
            db.text("""
                SELECT title, source_site
                FROM competitions
                WHERE publisher_type = 'scraped'
                GROUP BY title, source_site
                HAVING COUNT(*) > 1
            """)
        ).fetchall()
        dup_removed = 0
        for title, site in dup_groups:
            dupes = Competition.query.filter_by(
                title=title, source_site=site, publisher_type='scraped'
            ).order_by(Competition.scraped_at.desc()).all()
            # 保留最新的，删除其余
            for c in dupes[1:]:
                db.session.delete(c)
                dup_removed += 1
                removed_count += 1
        if dup_removed:
            db.session.commit()
            print(f'[清理] 重复活动: {dup_removed} 条')

        print(f'[清理] 总计清理: {removed_count} 条')
        return removed_count


def _schedule_loop():
    """后台线程：每天 00:00 和 12:00 执行爬虫，10分钟后清理"""
    while True:
        now = datetime.now()
        # 计算下一个目标时间 (00:00 或 12:00)
        targets = [
            now.replace(hour=0, minute=0, second=0, microsecond=0),
            now.replace(hour=12, minute=0, second=0, microsecond=0),
        ]
        # 如果目标时间已过，推到下一天
        next_targets = [t if t > now else t + timedelta(days=1) for t in targets]
        # 上午优先选12点，否则选0点后下一个最早
        next_run = min(next_targets)
        wait_seconds = (next_run - now).total_seconds()
        print(f'[调度] 下次爬虫: {next_run.strftime("%Y-%m-%d %H:%M")} (等待 {wait_seconds/60:.0f} 分钟)')

        # 等待到目标时间
        _time_module.sleep(min(wait_seconds, 3600))  # 每小时重新检查一次，防止偏差
        now = datetime.now()
        if now.hour in (0, 12) and now.minute < 5:
            # 在实际时间窗口内（0点或12点后5分钟内）
            global _last_scrape_run
            if _last_scrape_run and (now - _last_scrape_run).total_seconds() < 600:
                continue  # 10分钟内不重复运行
            _last_scrape_run = now
            print(f'[调度] 开始定时爬虫 {now.strftime("%Y-%m-%d %H:%M:%S")}')
            try:
                with app.app_context():
                    stats = _do_scrape()
                    print(f'[调度] 定时爬虫完成: {stats["raw"]}条→入库{stats["saved"]}条')
            except Exception as e:
                print(f'[调度] 定时爬虫异常: {e}')

            # 爬虫完成后 10 分钟执行清理
            print(f'[调度] 清理将在 10 分钟后执行')
            _time_module.sleep(600)
            print(f'[调度] 开始定时清理 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            try:
                cleaned = _cleanup_activities()
                print(f'[调度] 定时清理完成: {cleaned} 条')
            except Exception as e:
                print(f'[调度] 定时清理异常: {e}')


# ═══════════════════════════════════════════════════════
#  种子数据
# ═══════════════════════════════════════════════════════

def init_db():
    os.makedirs(_WORK_UPLOAD_DIR, exist_ok=True)
    with app.app_context():
        db.create_all()
        _seed_data()

    # 启动定时爬虫线程
    scheduler_thread = threading.Thread(target=_schedule_loop, daemon=True, name='scrape-scheduler')
    scheduler_thread.start()
    print('[调度] 定时爬虫线程已启动（每天 00:00 & 12:00）')


def _seed_data():
    if User.query.first():
        return

    users_data = [
        ('zhang', '\u5f20\u540c\u5b66', ['Python', '\u673a\u5668\u5b66\u4e60', '\u6570\u636e\u5206\u6790'], 95),
        ('li', '\u674e\u540c\u5b66', ['C++', '\u7b97\u6cd5', 'ACM'], 98),
        ('wang', '\u738b\u540c\u5b66', ['PPT\u5236\u4f5c', '\u6f14\u8bb2', '\u6587\u6848\u5199\u4f5c'], 88),
        ('zhao', '\u8d75\u540c\u5b66', ['\u524d\u7aef\u5f00\u53d1', 'UI\u8bbe\u8ba1', 'React'], 92),
        ('sun', '\u5b59\u540c\u5b66', ['\u540e\u7aef\u5f00\u53d1', 'Java', '\u6570\u636e\u5e93'], 90),
        ('zhou', '\u5468\u540c\u5b66', ['\u5d4c\u5165\u5f0f', '\u786c\u4ef6', 'PCB\u8bbe\u8ba1'], 85),
        ('wu', '\u5434\u540c\u5b66', ['\u6570\u5b66\u5efa\u6a21', 'MATLAB', '\u7b97\u6cd5'], 96),
        ('chen', '\u9648\u540c\u5b66', ['\u89c6\u9891\u526a\u8f91', '\u52a8\u753b', '3D\u5efa\u6a21'], 82),
    ]
    for uname, rname, tags, credit in users_data:
        u = User(username=uname, real_name=rname, skill_tags=tags, credit_score=credit)
        u.set_password('Aa123456!')
        db.session.add(u)
    db.session.commit()

    now = datetime.utcnow()
    activities = [
        {
            'title': '\u6821\u56ed\u6587\u5316\u8282\u5fd7\u613f\u8005\u62db\u52df',
            'category': '\u793e\u4f1a\u5b9e\u8df5', 'level': '\u6821\u7ea7',
            'description': '\u4e00\u5e74\u4e00\u5ea6\u7684\u6821\u56ed\u6587\u5316\u8282\u5373\u5c06\u5f00\u5e55\uff0c\u73b0\u62db\u52df\u5fd7\u613f\u8005\u8d1f\u8d23\u6d3b\u52a8\u7b79\u5907\u3001\u73b0\u573a\u7ef4\u62a4\u3001\u5609\u5bbe\u63a5\u5f85\u7b49\u5de5\u4f5c\u3002',
            'organizer': '\u4e0a\u6d77\u4ea4\u901a\u5927\u5b66\u5b66\u751f\u4f1a', 'credit_info': '\u53c2\u4e0e\u53ef\u83b7\u5f971-2\u5b66\u5206',
            'tags': ['\u5fd7\u613f\u8005', '\u6587\u5316\u8282', '\u6821\u56ed'], 'max_team_size': 10,
        },
        {
            'title': '\u5b66\u672f\u8bb2\u5ea7\uff1a\u4eba\u5de5\u667a\u80fd\u4e0e\u672a\u6765\u79d1\u6280',
            'category': '\u5b66\u672f\u6d3b\u52a8', 'level': '\u6821\u7ea7',
            'description': '\u9080\u8bf7\u77e5\u540d\u6559\u6388\u5206\u4eab\u4eba\u5de5\u667a\u80fd\u6700\u65b0\u53d1\u5c55\u8d8b\u52bf\u4e0e\u5e94\u7528\uff0c\u6b22\u8fce\u5404\u4e13\u4e1a\u540c\u5b66\u53c2\u52a0\u3002',
            'organizer': '\u4e0a\u6d77\u4ea4\u901a\u5927\u5b66\u6559\u52a1\u5904', 'credit_info': '\u53c2\u52a0\u53ef\u83b7\u5f970.5\u5b66\u5206',
            'tags': ['AI', '\u8bb2\u5ea7', '\u5b66\u672f'], 'max_team_size': 1,
        },
        {
            'title': '2026\u5e74\u6821\u56ed\u8fd0\u52a8\u4f1a\u5fd7\u613f\u8005\u62db\u52df',
            'category': '\u793e\u4f1a\u5b9e\u8df5', 'level': '\u6821\u7ea7',
            'description': '\u6821\u56ed\u8fd0\u52a8\u4f1a\u9700\u8981\u5927\u91cf\u5fd7\u613f\u8005\u8d1f\u8d23\u8d5b\u573a\u670d\u52a1\u3001\u8ba1\u5206\u7edf\u8ba1\u3001\u533b\u7597\u534f\u52a9\u7b49\u5de5\u4f5c\u3002',
            'organizer': '\u4e0a\u6d77\u4ea4\u901a\u5927\u5b66\u4f53\u80b2\u7cfb', 'credit_info': '\u53c2\u4e0e\u53ef\u83b7\u5f972\u5b66\u5206',
            'tags': ['\u8fd0\u52a8\u4f1a', '\u5fd7\u613f\u8005', '\u4f53\u80b2'], 'max_team_size': 20,
        },
        {
            'title': '\u521b\u4e1a\u7ecf\u9a8c\u5206\u4eab\u4f1a\uff1a\u4ece0\u52301\u7684\u521b\u4e1a\u4e4b\u8def',
            'category': '\u5176\u4ed6', 'level': '\u6821\u7ea7',
            'description': '\u9080\u8bf7\u4f18\u79c0\u6821\u53cb\u5206\u4eab\u521b\u4e1a\u7ecf\u5386\uff0c\u5305\u62ec\u9879\u76ee\u7b79\u5907\u3001\u56e2\u961f\u7ec4\u5efa\u3001\u878d\u8d44\u7b49\u65b9\u9762\u7684\u5b9e\u6218\u7ecf\u9a8c\u3002',
            'organizer': '\u4e0a\u6d77\u4ea4\u901a\u5927\u5b66\u5927\u521b\u4e2d\u5fc3', 'credit_info': '',
            'tags': ['\u521b\u4e1a', '\u5206\u4eab', '\u6821\u53cb'], 'max_team_size': 1,
        },
        {
            'title': '\u6821\u56ed\u793e\u56e2\u62db\u65b0\u8054\u5408\u5c55\u793a\u6d3b\u52a8',
            'category': '\u6587\u4f53\u6d3b\u52a8', 'level': '\u6821\u7ea7',
            'description': '\u5404\u5927\u793e\u56e2\u8054\u5408\u62db\u65b0\uff0c\u73b0\u573a\u5c55\u793a\u793e\u56e2\u7279\u8272\uff0c\u5b66\u751f\u53ef\u73b0\u573a\u62a5\u540d\u52a0\u5165\u611f\u5174\u8da3\u7684\u793e\u56e2\u3002',
            'organizer': '\u4e0a\u6d77\u4ea4\u901a\u5927\u5b66\u793e\u56e2\u8054\u5408\u4f1a', 'credit_info': '',
            'tags': ['\u793e\u56e2', '\u62db\u65b0', '\u5c55\u793a'], 'max_team_size': 1,
        },
    ]

    for ad in activities:
        dl = now + timedelta(days=15 + len(activities) * 7)
        activity = Competition(
            title=ad['title'], category=ad['category'], level=ad['level'],
            description=ad['description'], organizer=ad['organizer'],
            credit_info=ad['credit_info'], tags=ad['tags'],
            max_team_size=ad['max_team_size'], ai_confidence=0.9,
            registration_deadline=dl,
            publisher_type='user', publisher_name='\u5f20\u540c\u5b66',
            approval_status='approved', is_competition=False,
            source_site='\u7528\u6237\u53d1\u5e03',
        )
        db.session.add(activity)
    db.session.commit()

    credit_logs_data = [
        ('zhang', 5, '\u5b8c\u6210\u7ec4\u961f', '\u6210\u529f\u7ec4\u5efa\u201c\u6570\u6a21\u51b2\u950b\u961f\u201d'),
        ('zhang', -2, '\u4efb\u52a1\u903e\u671f\u672a\u4ea4', '\u5b50\u4efb\u52a1\u201c\u6570\u636e\u5206\u6790\u62a5\u544a\u201d\u903e\u671f2\u5929'),
        ('li', 10, '\u9996\u6b21\u5b8c\u6210\u7ec4\u961f', '\u6210\u4e3a\u201cACM\u96c6\u8bad\u961f\u201d\u961f\u957f'),
        ('li', 2, '\u6309\u65f6\u4ea4\u4ed8', '\u6309\u622a\u6b62\u65f6\u95f4\u63d0\u4ea4\u4ea4\u4ed8\u7269'),
        ('wang', 3, '\u5b8c\u6210\u7ec4\u961f', '\u52a0\u5165\u201c\u4e92\u8054\u7f51+\u68a6\u4e4b\u961f\u201d'),
    ]
    for uname, change, reason, detail in credit_logs_data:
        u = User.query.filter_by(username=uname).first()
        if u:
            cl = CreditLog(user_id=u.id, change=change, reason=reason, detail=detail)
            db.session.add(cl)
    db.session.commit()
    print(f'\u79cd\u5b50\u6570\u636e\u5df2\u521b\u5efa\uff1a{len(users_data)} \u7528\u6237, {len(activities)} \u4e2a\u6d3b\u52a8')


# ═══════════════════════════════════════════════════════
#  开发者管理面板
# ═══════════════════════════════════════════════════════

# 所有表名到模型的映射
TABLE_MAP = {
    'users': User,
    'competitions': Competition,
    'user_activities': UserActivity,
    'teams': Team,
    'team_members': TeamMember,
    'scrape_logs': ScrapeLog,
    'credit_logs': CreditLog,
    'team_tasks': TeamTask,
    'task_assignments': TaskAssignment,
    'team_documents': TeamDocument,
    'work_submissions': WorkSubmission,
    'chat_messages': ChatMessage,
    'task_progress': TaskProgress,
}

# 安全的列白名单：每张表允许返回给前端的列
TABLE_COLUMNS = {
    'users': ['id', 'username', 'real_name', 'avatar_url', 'skill_tags', 'credit_score', 'created_at'],
    'competitions': ['id', 'title', 'category', 'level', 'description', 'organizer', 'max_team_size', 'min_team_size',
                     'registration_deadline', 'status', 'approval_status', 'publisher_type', 'publisher_name',
                     'is_competition', 'tags', 'source_url', 'source_site', 'ai_confidence', 'scraped_at', 'created_at'],
    'teams': ['id', 'competition_id', 'leader_id', 'name', 'slogan', 'description', 'status', 'created_at'],
    'team_members': ['id', 'team_id', 'user_id', 'role', 'joined_at'],
    'team_tasks': ['id', 'team_id', 'title', 'description', 'required_roles', 'deadline', 'status', 'created_by', 'created_at'],
    'task_assignments': ['id', 'task_id', 'user_id', 'role', 'status', 'match_score', 'applied_at', 'resolved_at'],
    'scrape_logs': ['id', 'source_url', 'status', 'items_found', 'ai_filtered', 'error_msg', 'created_at'],
    'credit_logs': ['id', 'user_id', 'change', 'reason', 'detail', 'created_at'],
    'user_activities': ['id', 'user_id', 'activity_id', 'status', 'created_at'],
    'team_documents': ['id', 'team_id', 'title', 'content', 'task_type', 'ai_suggestions', 'created_by', 'created_at'],
    'work_submissions': ['id', 'document_id', 'team_id', 'user_id', 'file_path', 'file_name', 'description', 'created_at'],
    'chat_messages': ['id', 'team_id', 'user_id', 'chat_type', 'content', 'image_url', 'created_at'],
    'task_progress': ['id', 'team_id', 'document_id', 'total_tasks', 'completed_tasks', 'progress_pct', 'ai_comment', 'updated_at'],
}


def _serialize_row(row, table_name):
    """将 ORM 行对象转为安全字典，只暴露白名单列"""
    allowed = TABLE_COLUMNS.get(table_name, [])
    data = {}
    for col in allowed:
        val = getattr(row, col, None)
        if isinstance(val, datetime):
            data[col] = val.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(val, (list, dict)):
            data[col] = str(val)
        else:
            data[col] = val
    return data


@app.route('/dev')
def dev_panel():
    """开发者管理面板"""
    counts = {}
    for name, model in TABLE_MAP.items():
        counts[name] = db.session.query(model).count()
    return render_template('dev.html', table_names=list(TABLE_MAP.keys()), counts=counts)


@app.route('/dev/api/tables/<table_name>')
def dev_table_data(table_name):
    """获取表数据（支持分页）"""
    model = TABLE_MAP.get(table_name)
    if not model:
        return jsonify({'error': '无效的表名'}), 404

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    order_by = request.args.get('order_by', '')
    order_dir = request.args.get('order_dir', 'desc')

    query = model.query

    # 搜索（在所有字符串列中模糊匹配）
    if search:
        allowed = TABLE_COLUMNS.get(table_name, [])
        conditions = []
        for col_name in allowed:
            col = getattr(model, col_name, None)
            if col is not None and hasattr(col, 'type'):
                col_type = str(col.type).lower()
                if any(t in col_type for t in ('string', 'text', 'varchar')):
                    conditions.append(col.ilike(f'%{search}%'))
        if conditions:
            from sqlalchemy import or_
            query = query.filter(or_(*conditions))

    # 排序
    if order_by and order_by in TABLE_COLUMNS.get(table_name, []):
        col = getattr(model, order_by)
        if col is not None:
            col = col.desc() if order_dir == 'desc' else col.asc()
            query = query.order_by(col)
    else:
        # 默认按创建时间倒序
        if hasattr(model, 'created_at'):
            query = query.order_by(model.created_at.desc())

    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'table_name': table_name,
        'columns': TABLE_COLUMNS.get(table_name, []),
        'rows': [_serialize_row(r, table_name) for r in rows],
        'total': total,
        'page': page,
        'per_page': per_page,
    })


@app.route('/dev/api/tables/<table_name>/<row_id>', methods=['DELETE'])
def dev_delete_row(table_name, row_id):
    """删除单行记录"""
    model = TABLE_MAP.get(table_name)
    if not model:
        return jsonify({'error': '无效的表名'}), 404

    row = db.session.query(model).get(row_id)
    if not row:
        return jsonify({'error': '记录不存在'}), 404

    try:
        db.session.delete(row)
        db.session.commit()
        return jsonify({'ok': True, 'deleted_id': row_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/dev/api/restart', methods=['POST'])
def dev_restart_server():
    """重启 Flask 服务器"""
    try:
        import subprocess
        # 后台启动新进程
        args = [sys.executable] + sys.argv
        subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
        # 关闭当前进程
        os._exit(0)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/dev/api/truncate/<table_name>', methods=['POST'])
def dev_truncate_table(table_name):
    """清空整张表"""
    model = TABLE_MAP.get(table_name)
    if not model:
        return jsonify({'error': '无效的表名'}), 404

    try:
        count = db.session.query(model).delete()
        db.session.commit()
        return jsonify({'ok': True, 'deleted_count': count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=3002, use_reloader=False)
