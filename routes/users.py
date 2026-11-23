from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import User
from utils import admin_required, log_activity

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@login_required
@admin_required
def index():
    users = User.query.order_by(User.id.asc()).all()
    return render_template('users/index.html', users=users)

@users_bp.route('/create', methods=['POST'])
@login_required
@admin_required
def create():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', 'tester')
    password = request.form.get('password', '')

    if not username or not email or not password:
        flash('All user fields are mandatory.', 'warning')
        return redirect(url_for('users.index'))

    if User.query.filter_by(username=username).first():
        flash('Username is already taken.', 'danger')
        return redirect(url_for('users.index'))

    if User.query.filter_by(email=email).first():
        flash('Email is already registered.', 'danger')
        return redirect(url_for('users.index'))

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

    log_activity(action='Admin Create User', description=f"Admin created user {username} with role {role}.")
    flash(f"User '{username}' created successfully!", 'success')
    return redirect(url_for('users.index'))

@users_bp.route('/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_status(user_id):
    if user_id == current_user.id:
        flash('You cannot deactivate your own administrative account.', 'warning')
        return redirect(url_for('users.index'))

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()

    action_label = "activated" if user.is_active else "deactivated"
    log_activity(action='Toggle User Status', description=f"User {user.username} was {action_label}.")
    flash(f"User '{user.username}' {action_label}.", 'info')
    return redirect(url_for('users.index'))

@users_bp.route('/<int:user_id>/update-role', methods=['POST'])
@login_required
@admin_required
def update_role(user_id):
    if user_id == current_user.id:
        flash('You cannot change your own role.', 'warning')
        return redirect(url_for('users.index'))

    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', 'tester')
    if new_role in ('admin', 'tester', 'student'):
        user.role = new_role
        db.session.commit()
        log_activity(action='Update User Role', description=f"Changed user {user.username} role to {new_role}.")
        flash(f"Role for '{user.username}' updated to '{new_role}'.", 'success')
    return redirect(url_for('users.index'))
