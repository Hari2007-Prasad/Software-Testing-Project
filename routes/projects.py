from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from extensions import db
from models import Project, ThresholdConfiguration, ActivityLog
from utils import tester_required, log_activity

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

@projects_bp.route('/')
@login_required
@tester_required
def index():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    env_filter = request.args.get('env', '').strip()

    query = Project.query

    if search_query:
        query = query.filter(Project.name.ilike(f"%{search_query}%") | Project.description.ilike(f"%{search_query}%"))
    if status_filter:
        query = query.filter_by(status=status_filter)
    if env_filter:
        query = query.filter_by(environment=env_filter)

    projects = query.order_by(Project.created_at.desc()).all()
    return render_template('projects/index.html', projects=projects, search_query=search_query, status_filter=status_filter, env_filter=env_filter)

@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
@tester_required
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        app_url = request.form.get('app_url', '').strip() or 'http://127.0.0.1:5000/lms'
        project_type = request.form.get('project_type', 'Digital Learning Platform')
        environment = request.form.get('environment', 'Staging')
        status = request.form.get('status', 'Active')

        if not name:
            flash('Project name is mandatory.', 'warning')
            return render_template('projects/create.html')

        project = Project(
            name=name,
            description=description,
            app_url=app_url,
            project_type=project_type,
            environment=environment,
            status=status,
            user_id=current_user.id
        )
        db.session.add(project)
        db.session.flush()

        # Create default ThresholdConfiguration for this project
        default_threshold = ThresholdConfiguration(
            project_id=project.id,
            name=f"Policy for {project.name}",
            max_pixel_diff_pct=1.5,
            min_pixel_similarity_pct=98.5,
            min_ssim_score=0.92,
            min_region_size=25,
            max_changed_regions=2,
            min_pass_rate=90.0,
            max_failed_tests=1,
            max_blocked_tests=0,
            max_critical_findings=0,
            max_high_findings=1,
            visual_weight=0.30,
            functional_weight=0.40,
            security_weight=0.30,
            is_active=True
        )
        db.session.add(default_threshold)
        db.session.commit()

        log_activity(action='Create Project', description=f"Created testing project '{project.name}' (ID: {project.id}).", project_id=project.id)
        flash(f"Project '{project.name}' successfully initialized!", 'success')
        return redirect(url_for('projects.details', project_id=project.id))

    return render_template('projects/create.html')

@projects_bp.route('/<int:project_id>')
@login_required
@tester_required
def details(project_id):
    project = Project.query.get_or_404(project_id)
    test_plans = project.test_plans.order_by(db.desc('created_at')).all()
    executions = project.test_executions.order_by(db.desc('start_time')).limit(5).all()
    comparisons = project.image_comparisons.order_by(db.desc('created_at')).limit(5).all()
    findings = project.security_findings.order_by(db.desc('discovered_at')).limit(5).all()
    threshold = project.threshold_config
    recent_analyses = project.threshold_analyses.order_by(db.desc('analyzed_at')).limit(5).all()

    return render_template(
        'projects/details.html',
        project=project,
        test_plans=test_plans,
        executions=executions,
        comparisons=comparisons,
        findings=findings,
        threshold=threshold,
        recent_analyses=recent_analyses
    )

@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@tester_required
def edit(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        project.name = request.form.get('name', '').strip() or project.name
        project.description = request.form.get('description', '').strip()
        project.app_url = request.form.get('app_url', '').strip() or project.app_url
        project.project_type = request.form.get('project_type', project.project_type)
        project.environment = request.form.get('environment', project.environment)
        project.status = request.form.get('status', project.status)

        db.session.commit()
        log_activity(action='Update Project', description=f"Updated details for project '{project.name}'.", project_id=project.id)
        flash(f"Project '{project.name}' updated successfully.", 'success')
        return redirect(url_for('projects.details', project_id=project.id))

    return render_template('projects/edit.html', project=project)

@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
@tester_required
def delete(project_id):
    project = Project.query.get_or_404(project_id)
    name = project.name
    db.session.delete(project)
    db.session.commit()

    log_activity(action='Delete Project', description=f"Deleted project '{name}' (ID: {project_id}).")
    flash(f"Project '{name}' was deleted permanently.", 'info')
    return redirect(url_for('projects.index'))
