import os
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime

from extensions import db
from models import Project, TestExecution, TestExecutionResult, TestCase, ThresholdConfiguration, ThresholdAnalysis
from modules.automated_testing.runner import TestExecutionRunner, ACTIVE_EXECUTIONS
from modules.automated_testing.scenarios import FunctionalScenarios
from modules.threshold_analysis.analyzer import ThresholdAnalyzer
from utils import tester_required, log_activity

automated_testing_bp = Blueprint('automated_testing', __name__, url_prefix='/automated-testing')

@automated_testing_bp.route('/')
@login_required
@tester_required
def index():
    project_id = request.args.get('project_id', type=int)
    projects = Project.query.filter_by(status='Active').all()

    query = TestExecution.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    executions = query.order_by(TestExecution.start_time.desc()).all()

    scenarios = FunctionalScenarios.get_all_scenarios()

    return render_template(
        'automated_testing/index.html',
        executions=executions,
        projects=projects,
        scenarios=scenarios,
        selected_project_id=project_id
    )

@automated_testing_bp.route('/launch', methods=['GET', 'POST'])
@login_required
@tester_required
def launch():
    projects = Project.query.filter_by(status='Active').all()
    scenarios = FunctionalScenarios.get_all_scenarios()

    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        suite_name = request.form.get('suite_name', 'Full LMS Functional Regression').strip()
        target_url = request.form.get('target_url', 'http://127.0.0.1:5000/lms').strip()
        headless = request.form.get('headless', 'true').lower() == 'true'
        timeout = int(request.form.get('timeout', 15))
        selected_tests = request.form.getlist('selected_tests')

        if not project_id:
            flash('Please select an active project.', 'warning')
            return render_template('automated_testing/launch.html', projects=projects, scenarios=scenarios)

        project = Project.query.get_or_404(project_id)

        # Create new execution record in database
        execution = TestExecution(
            project_id=project_id,
            test_suite_name=suite_name,
            execution_type='Automated Selenium',
            status='Running',
            start_time=datetime.utcnow(),
            total_tests=len(selected_tests) if selected_tests else len(scenarios),
            created_by_id=current_user.id
        )
        db.session.add(execution)
        db.session.commit()

        # Launch background execution runner
        runner = TestExecutionRunner(
            app=current_app._get_current_object(),
            base_url=target_url or project.app_url,
            headless=headless,
            timeout=timeout
        )
        runner.start_suite_async(
            execution_id=execution.id,
            selected_test_ids=selected_tests if selected_tests else None
        )

        log_activity(action='Start Automated Test Run', description=f"Launched '{suite_name}' (#{execution.id}) targeting {target_url}.", project_id=project_id)
        flash(f"Test run #{execution.id} launched! Monitoring live execution in real time.", 'info')
        return redirect(url_for('automated_testing.live_execution', execution_id=execution.id))

    return render_template('automated_testing/launch.html', projects=projects, scenarios=scenarios)

@automated_testing_bp.route('/live/<int:execution_id>')
@login_required
@tester_required
def live_execution(execution_id):
    execution = TestExecution.query.get_or_404(execution_id)
    return render_template('automated_testing/live.html', execution=execution)

@automated_testing_bp.route('/progress/<int:execution_id>')
@login_required
@tester_required
def get_execution_progress(execution_id):
    data = TestExecutionRunner.get_progress(execution_id)
    return jsonify(data)

@automated_testing_bp.route('/results/<int:execution_id>')
@login_required
@tester_required
def results(execution_id):
    execution = TestExecution.query.get_or_404(execution_id)
    results_list = execution.results.order_by(TestExecutionResult.id.asc()).all()

    # If execution finished and no threshold analysis exists yet, compute it!
    threshold_cfg = ThresholdConfiguration.query.filter_by(project_id=execution.project_id, is_active=True).first()
    analysis = execution.threshold_analyses.first()
    if not analysis and threshold_cfg and execution.status in ('Completed', 'Failed'):
        exec_metrics = {
            'total_tests': execution.total_tests,
            'passed_tests': execution.passed_tests,
            'failed_tests': execution.failed_tests,
            'blocked_tests': execution.blocked_tests
        }
        th_eval = ThresholdAnalyzer.evaluate_functional_metrics(exec_metrics, threshold_cfg.to_dict())
        analysis = ThresholdAnalysis(
            project_id=execution.project_id,
            test_execution_id=execution.id,
            functional_status=th_eval['status'],
            functional_score=th_eval['score'],
            overall_status=th_eval['status'],
            overall_score=th_eval['score'],
            violations_json=json.dumps(th_eval['violations']),
            details_json=json.dumps(th_eval['details'])
        )
        db.session.add(analysis)
        db.session.commit()

    return render_template('automated_testing/results.html', execution=execution, results=results_list, analysis=analysis)
