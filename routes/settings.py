from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from utils import admin_required, log_activity

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
@admin_required
def index():
    if request.method == 'POST':
        flash('Platform preferences successfully updated.', 'success')
        log_activity(action='Update Platform Settings', description='Administrator updated platform preferences.')
        return redirect(url_for('settings.index'))

    settings_info = {
        'flask_env': current_app.config.get('ENV', 'development'),
        'database_uri': current_app.config.get('SQLALCHEMY_DATABASE_URI'),
        'upload_folder': current_app.config.get('UPLOAD_FOLDER'),
        'max_content_length': f"{current_app.config.get('MAX_CONTENT_LENGTH', 0) / (1024*1024):.0f} MB",
        'selenium_headless': current_app.config.get('SELENIUM_HEADLESS', True),
        'selenium_timeout': f"{current_app.config.get('SELENIUM_TIMEOUT', 15)} seconds",
        'default_target_url': current_app.config.get('DEFAULT_TARGET_APP_URL', 'http://127.0.0.1:5000/lms'),
        'session_cookie_httponly': current_app.config.get('SESSION_COOKIE_HTTPONLY', True),
        'session_cookie_samesite': current_app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
    }
    return render_template('settings/index.html', settings_info=settings_info)
