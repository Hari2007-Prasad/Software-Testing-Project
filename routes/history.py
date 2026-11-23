from flask import Blueprint, render_template, request
from flask_login import login_required
from extensions import db
from models import ActivityLog, Project, User
from utils import tester_required

history_bp = Blueprint('history', __name__, url_prefix='/history')

@history_bp.route('/')
@login_required
@tester_required
def index():
    project_id = request.args.get('project_id', type=int)
    action_filter = request.args.get('action', '').strip()
    search_q = request.args.get('q', '').strip()

    projects = Project.query.order_by(Project.name).all()

    query = ActivityLog.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    if action_filter:
        query = query.filter(ActivityLog.action.ilike(f"%{action_filter}%"))
    if search_q:
        query = query.filter(ActivityLog.description.ilike(f"%{search_q}%"))

    logs = query.order_by(ActivityLog.timestamp.desc()).limit(150).all()

    return render_template(
        'history/index.html',
        logs=logs,
        projects=projects,
        selected_project_id=project_id,
        action_filter=action_filter,
        search_q=search_q
    )
