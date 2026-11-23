from functools import wraps
from flask import flash, redirect, url_for, request, abort
from flask_login import current_user
from extensions import db
from models import ActivityLog

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role != 'admin':
            flash("Administrator privileges are required for this action.", "danger")
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def tester_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role not in ('admin', 'tester'):
            flash("Tester or Administrator privileges are required to access testing modules.", "danger")
            return redirect(url_for('lms.student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_activity(action: str, description: str = '', project_id: int = None, user_id: int = None):
    """Utility to record system and audit activity logs to the database."""
    try:
        uid = user_id if user_id is not None else (current_user.id if current_user and current_user.is_authenticated else None)
        ip = request.remote_addr if request else '127.0.0.1'
        log_entry = ActivityLog(
            user_id=uid,
            project_id=project_id,
            action=action,
            description=description,
            ip_address=ip
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
