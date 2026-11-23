from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from extensions import db
from models import (
    Project, TestCase, TestPlan, TestExecution, TestExecutionResult,
    ImageComparison, ImageMetric, SecurityFinding, ThresholdAnalysis, ActivityLog
)
from utils import tester_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
@tester_required
def index():
    # 1. Total testing projects
    total_projects = Project.query.count()

    # 2. Total test cases
    total_test_cases = TestCase.query.count()

    # 3. Test execution aggregates
    total_executions = TestExecution.query.count()
    exec_aggregates = db.session.query(
        func.sum(TestExecution.total_tests),
        func.sum(TestExecution.passed_tests),
        func.sum(TestExecution.failed_tests),
        func.sum(TestExecution.blocked_tests)
    ).first()

    total_executed_tests = int(exec_aggregates[0] or 0)
    passed_tests = int(exec_aggregates[1] or 0)
    failed_tests = int(exec_aggregates[2] or 0)
    blocked_tests = int(exec_aggregates[3] or 0)

    # Calculate overall pass rate
    if total_executed_tests > 0:
        overall_pass_rate = round((passed_tests / total_executed_tests) * 100.0, 1)
    else:
        overall_pass_rate = 0.0

    # 4. Security findings count and breakdown
    total_security_findings = SecurityFinding.query.count()
    critical_findings = SecurityFinding.query.filter_by(severity='Critical').count()
    high_findings = SecurityFinding.query.filter_by(severity='High').count()
    medium_findings = SecurityFinding.query.filter_by(severity='Medium').count()
    low_findings = SecurityFinding.query.filter_by(severity='Low').count()

    # 5. Image comparison metrics
    total_comparisons = ImageComparison.query.count()
    avg_similarity_query = db.session.query(func.avg(ImageMetric.pixel_similarity)).scalar()
    avg_visual_similarity = round(float(avg_similarity_query), 2) if avg_similarity_query is not None else 100.0

    # 6. Recent records for tables
    recent_executions = TestExecution.query.order_by(TestExecution.start_time.desc()).limit(5).all()
    recent_findings = SecurityFinding.query.order_by(SecurityFinding.discovered_at.desc()).limit(5).all()
    recent_comparisons = ImageComparison.query.order_by(ImageComparison.created_at.desc()).limit(5).all()
    recent_activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(8).all()
    all_projects = Project.query.order_by(Project.created_at.desc()).all()

    # 7. Trend chart data: Last 7 executions
    trend_execs = TestExecution.query.order_by(TestExecution.start_time.asc()).limit(7).all()
    trend_labels = [e.start_time.strftime('%b %d') if e.start_time else f"Run #{e.id}" for e in trend_execs]
    trend_passed = [e.passed_tests for e in trend_execs]
    trend_failed = [e.failed_tests for e in trend_execs]

    stats = {
        'total_projects': total_projects,
        'total_test_cases': total_test_cases,
        'total_executions': total_executions,
        'total_executed_tests': total_executed_tests,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'blocked_tests': blocked_tests,
        'overall_pass_rate': overall_pass_rate,
        'total_security_findings': total_security_findings,
        'critical_findings': critical_findings,
        'high_findings': high_findings,
        'medium_findings': medium_findings,
        'low_findings': low_findings,
        'total_comparisons': total_comparisons,
        'avg_visual_similarity': avg_visual_similarity
    }

    chart_data = {
        'trend_labels': trend_labels,
        'trend_passed': trend_passed,
        'trend_failed': trend_failed,
        'distribution': [passed_tests, failed_tests, blocked_tests],
        'security_dist': [critical_findings, high_findings, medium_findings, low_findings]
    }

    return render_template(
        'dashboard/index.html',
        stats=stats,
        chart_data=chart_data,
        recent_executions=recent_executions,
        recent_findings=recent_findings,
        recent_comparisons=recent_comparisons,
        recent_activities=recent_activities,
        projects=all_projects
    )
