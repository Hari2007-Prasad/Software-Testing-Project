from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from extensions import db
from models import User
from utils import log_activity

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('lms.student_dashboard'))
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not username or not password:
            flash('Please enter both username and password.', 'warning')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            log_activity(action='User Login', description=f"User {user.username} ({user.role}) logged in successfully.", user_id=user.id)
            flash(f"Welcome back, {user.full_name or user.username}!", "success")

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            if user.role == 'student':
                return redirect(url_for('lms.student_dashboard'))
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid username or password. Please verify your credentials.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'tester')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic validations
        if not username or not email or not password:
            flash('All mandatory fields must be completed.', 'warning')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must contain at least 6 characters.', 'warning')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email address is already registered. Please login.', 'danger')
            return render_template('auth/register.html')

        # Restrict role assignment from open registration (admin can only be created by admin or seeds)
        if role not in ('tester', 'student'):
            role = 'tester'

        new_user = User(
            username=username,
            email=email,
            full_name=full_name or username,
            role=role,
            is_active=True
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        log_activity(action='User Registration', description=f"New user {username} ({role}) registered.", user_id=new_user.id)
        flash('Account successfully created! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    uid = current_user.id
    logout_user()
    log_activity(action='User Logout', description=f"User {username} logged out.", user_id=uid)
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))
