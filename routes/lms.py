from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime

from extensions import db
from models import User, Course, Enrollment, ActivityLog
from utils import log_activity

lms_bp = Blueprint('lms', __name__, url_prefix='/lms')

# -----------------------------------------------------------------------------
# PUBLIC PAGES
# -----------------------------------------------------------------------------

@lms_bp.route('/')
def home():
    featured_courses = Course.query.filter_by(is_published=True).limit(6).all()
    return render_template('lms/home.html', courses=featured_courses)

@lms_bp.route('/about')
def about():
    return render_template('lms/about.html')

@lms_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not email or not message or '@' not in email:
            flash('Please enter a valid name, email address, and message.', 'warning')
            return render_template('lms/contact.html')

        flash('Thank you for contacting us! Your inquiry has been dispatched to our instructional support team.', 'success')
        return redirect(url_for('lms.contact'))

    return render_template('lms/contact.html')

@lms_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('lms.student_dashboard'))
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter your username and password.', 'warning')
            return render_template('lms/login.html')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('This account is disabled. Contact campus support.', 'danger')
                return render_template('lms/login.html')

            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            log_activity(action='LMS Login', description=f"Student {user.username} logged into LMS portal.", user_id=user.id)
            flash(f"Welcome to Digital Learning Portal, {user.full_name or user.username}!", 'success')
            return redirect(url_for('lms.student_dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('lms/login.html')

@lms_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('lms.student_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password or not full_name:
            flash('All registration fields are required.', 'warning')
            return render_template('lms/register.html')

        if password != confirm_password:
            flash('Password confirmation does not match.', 'danger')
            return render_template('lms/register.html')

        if User.query.filter_by(username=username).first():
            flash('This username is already taken. Please choose another.', 'danger')
            return render_template('lms/register.html')

        if User.query.filter_by(email=email).first():
            flash('An account with this email address already exists.', 'danger')
            return render_template('lms/register.html')

        new_student = User(
            username=username,
            email=email,
            full_name=full_name,
            role='student',
            is_active=True
        )
        new_student.set_password(password)
        db.session.add(new_student)
        db.session.commit()

        log_activity(action='LMS Student Registration', description=f"Registered student {username}.", user_id=new_student.id)
        flash('Registration successful! Please log in with your new student account.', 'success')
        return redirect(url_for('lms.login'))

    return render_template('lms/register.html')

@lms_bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    uid = current_user.id
    logout_user()
    log_activity(action='LMS Logout', description=f"User {username} logged out from LMS.", user_id=uid)
    flash('You have been logged out of the learning platform.', 'info')
    return redirect(url_for('lms.login'))

# -----------------------------------------------------------------------------
# AUTHENTICATED STUDENT PAGES
# -----------------------------------------------------------------------------

@lms_bp.route('/dashboard')
@login_required
def student_dashboard():
    # If admin or tester visits, they can still view or switch
    enrollments = current_user.enrollments.all()
    available_courses = Course.query.filter_by(is_published=True).limit(4).all()
    return render_template('lms/dashboard.html', enrollments=enrollments, available_courses=available_courses)

@lms_bp.route('/courses')
def course_listing():
    query_str = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()

    query = Course.query.filter_by(is_published=True)
    if query_str:
        query = query.filter(Course.title.ilike(f"%{query_str}%") | Course.description.ilike(f"%{query_str}%"))
    if category:
        query = query.filter_by(category=category)

    courses = query.order_by(Course.title).all()
    categories = [c[0] for c in db.session.query(Course.category).distinct().all()]

    return render_template('lms/courses.html', courses=courses, categories=categories, query_str=query_str, selected_category=category)

@lms_bp.route('/courses/<int:course_id>')
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    is_enrolled = False
    enrollment = None
    if current_user.is_authenticated:
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
        is_enrolled = enrollment is not None

    return render_template('lms/course_details.html', course=course, is_enrolled=is_enrolled, enrollment=enrollment)

@lms_bp.route('/courses/<int:course_id>/enroll', methods=['GET', 'POST'])
@login_required
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    existing = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()

    if existing:
        flash(f"You are already actively enrolled in '{course.title}'.", 'info')
        return redirect(url_for('lms.course_details', course_id=course.id))

    enrollment = Enrollment(
        user_id=current_user.id,
        course_id=course.id,
        progress=15, # Starting milestone
        status='Active'
    )
    db.session.add(enrollment)
    db.session.commit()

    log_activity(action='Course Enrollment', description=f"Student {current_user.username} enrolled in {course.code}: {course.title}.", user_id=current_user.id)
    flash(f"Congratulations! You have successfully enrolled in '{course.title}'.", 'success')
    return redirect(url_for('lms.student_dashboard'))

@lms_bp.route('/profile')
@login_required
def student_profile():
    enrollments = current_user.enrollments.all()
    return render_template('lms/profile.html', user=current_user, enrollments=enrollments)

# -----------------------------------------------------------------------------
# ADMIN MANAGEMENT PAGES
# -----------------------------------------------------------------------------

@lms_bp.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        abort(403)
    total_students = User.query.filter_by(role='student').count()
    total_courses = Course.query.count()
    total_enrollments = Enrollment.query.count()
    recent_enrollments = Enrollment.query.order_by(Enrollment.enrolled_at.desc()).limit(8).all()

    return render_template(
        'lms/admin_dashboard.html',
        total_students=total_students,
        total_courses=total_courses,
        total_enrollments=total_enrollments,
        recent_enrollments=recent_enrollments
    )

@lms_bp.route('/admin/courses', methods=['GET', 'POST'])
@login_required
def admin_courses():
    if current_user.role != 'admin':
        abort(403)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'Computer Science')
        instructor = request.form.get('instructor', 'Staff Instructor').strip()
        duration = request.form.get('duration', '6 Weeks').strip()
        level = request.form.get('level', 'Beginner')

        if not title or not code or not description:
            flash('Course Code, Title, and Description are mandatory.', 'warning')
        elif Course.query.filter_by(code=code).first():
            flash(f"Course code '{code}' already exists.", 'danger')
        else:
            new_course = Course(
                title=title,
                code=code,
                description=description,
                category=category,
                instructor=instructor,
                duration=duration,
                level=level,
                lessons_count=10,
                is_published=True
            )
            db.session.add(new_course)
            db.session.commit()
            flash(f"Course '{code} - {title}' created successfully!", 'success')
            return redirect(url_for('lms.admin_courses'))

    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('lms/admin_courses.html', courses=courses)

@lms_bp.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        abort(403)
    users = User.query.order_by(User.id.asc()).all()
    return render_template('lms/admin_users.html', users=users)
