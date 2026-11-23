import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Project, ThresholdConfiguration, ThresholdAnalysis, ImageComparison, TestExecution, SecurityFinding
from modules.threshold_analysis.analyzer import ThresholdAnalyzer
from utils import tester_required, admin_required, log_activity

thresholds_bp = Blueprint('thresholds', __name__, url_prefix='/thresholds')

@thresholds_bp.route('/')
@login_required
@tester_required
def index():
    project_id = request.args.get('project_id', type=int)
    projects = Project.query.filter_by(status='Active').all()

    if not project_id and projects:
        project_id = projects[0].id

    selected_project = Project.query.get(project_id) if project_id else None
    config = selected_project.threshold_config if selected_project else None

    # Load threshold analyses history
    analyses_query = ThresholdAnalysis.query
    if project_id:
        analyses_query = analyses_query.filter_by(project_id=project_id)
    analyses = analyses_query.order_by(ThresholdAnalysis.analyzed_at.desc()).all()

    latest_analysis = analyses[0] if analyses else None

    return render_template(
        'thresholds/index.html',
        projects=projects,
        selected_project=selected_project,
        config=config,
        analyses=analyses,
        latest_analysis=latest_analysis
    )

@thresholds_bp.route('/save-config', methods=['POST'])
@login_required
@tester_required
def save_config():
    project_id = request.form.get('project_id', type=int)
    project = Project.query.get_or_404(project_id)

    config = project.threshold_config
    if not config:
        config = ThresholdConfiguration(project_id=project.id)
        db.session.add(config)

    config.name = request.form.get('name', config.name).strip()
    config.max_pixel_diff_pct = float(request.form.get('max_pixel_diff_pct', 1.5))
    config.min_pixel_similarity_pct = float(request.form.get('min_pixel_similarity_pct', 98.5))
    config.min_ssim_score = float(request.form.get('min_ssim_score', 0.92))
    config.min_region_size = int(request.form.get('min_region_size', 25))
    config.max_changed_regions = int(request.form.get('max_changed_regions', 2))

    config.min_pass_rate = float(request.form.get('min_pass_rate', 90.0))
    config.max_failed_tests = int(request.form.get('max_failed_tests', 1))
    config.max_blocked_tests = int(request.form.get('max_blocked_tests', 0))

    config.max_critical_findings = int(request.form.get('max_critical_findings', 0))
    config.max_high_findings = int(request.form.get('max_high_findings', 1))
    config.severity_policy = request.form.get('severity_policy', 'Strict')

    config.visual_weight = float(request.form.get('visual_weight', 0.30))
    config.functional_weight = float(request.form.get('functional_weight', 0.40))
    config.security_weight = float(request.form.get('security_weight', 0.30))
    config.updated_at = datetime.utcnow()

    db.session.commit()
    log_activity(action='Update Threshold Policy', description=f"Updated thresholds policy for project '{project.name}'.", project_id=project.id)
    flash(f"Threshold policy for '{project.name}' successfully updated!", 'success')
    return redirect(url_for('thresholds.index', project_id=project.id))

@thresholds_bp.route('/evaluate/<int:project_id>', methods=['POST'])
@login_required
@tester_required
def evaluate(project_id):
    project = Project.query.get_or_404(project_id)
    config = project.threshold_config

    if not config:
        flash("No threshold policy configured for this project.", "warning")
        return redirect(url_for('thresholds.index', project_id=project.id))

    # Collect latest visual comparison metrics
    latest_cmp = project.image_comparisons.order_by(ImageComparison.created_at.desc()).first()
    visual_metrics = latest_cmp.metric.to_dict() if (latest_cmp and latest_cmp.metric) else None

    # Collect latest functional execution metrics
    latest_exec = project.test_executions.order_by(TestExecution.start_time.desc()).first()
    functional_data = {
        'total_tests': latest_exec.total_tests,
        'passed_tests': latest_exec.passed_tests,
        'failed_tests': latest_exec.failed_tests,
        'blocked_tests': latest_exec.blocked_tests
    } if latest_exec else None

    # Collect security findings
    findings = [f.to_dict() for f in project.security_findings.all()]

    # Run Combined Quality Assessment
    result = ThresholdAnalyzer.evaluate_combined(
        visual_metrics=visual_metrics,
        functional_data=functional_data,
        security_findings=findings,
        threshold_config=config.to_dict()
    )

    analysis = ThresholdAnalysis(
        project_id=project.id,
        image_comparison_id=latest_cmp.id if latest_cmp else None,
        test_execution_id=latest_exec.id if latest_exec else None,
        visual_status=result['visual']['status'],
        visual_score=result['visual']['score'],
        functional_status=result['functional']['status'],
        functional_score=result['functional']['score'],
        security_status=result['security']['status'],
        security_score=result['security']['score'],
        overall_status=result['overall_status'],
        overall_score=result['overall_score'],
        violations_json=json.dumps(result['violations']),
        details_json=json.dumps(result)
    )
    db.session.add(analysis)
    db.session.commit()

    log_activity(
        action='Run Threshold Analysis',
        description=f"Evaluated project '{project.name}': Verdict={result['overall_status']}, Score={result['overall_score']}.",
        project_id=project.id
    )
    flash(f"Threshold Analysis generated: {result['overall_status']} (Composite Score: {result['overall_score']}%)", 'success' if result['overall_status'] == 'PASS' else 'warning')
    return redirect(url_for('thresholds.analysis_details', analysis_id=analysis.id))

@thresholds_bp.route('/analyses/<int:analysis_id>')
@login_required
@tester_required
def analysis_details(analysis_id):
    analysis = ThresholdAnalysis.query.get_or_404(analysis_id)
    details = analysis.get_details()
    violations = analysis.get_violations()
    return render_template('thresholds/details.html', analysis=analysis, details=details, violations=violations)
