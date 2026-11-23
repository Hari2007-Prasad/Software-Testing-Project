import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, Response
from flask_login import login_required, current_user
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from extensions import db
from models import Project, TestPlan, TestCase, User
from utils import tester_required, log_activity

test_planning_bp = Blueprint('test_planning', __name__, url_prefix='/test-planning')

@test_planning_bp.route('/')
@login_required
@tester_required
def index():
    project_id = request.args.get('project_id', type=int)
    projects = Project.query.order_by(Project.name).all()

    query = TestPlan.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    test_plans = query.order_by(TestPlan.created_at.desc()).all()

    # Metrics for Test Planning Dashboard
    total_plans = TestPlan.query.count()
    total_cases = TestCase.query.count()
    executed_cases = TestCase.query.filter(TestCase.execution_status.in_(['Passed', 'Failed', 'Blocked', 'Needs Review'])).count()
    pending_cases = TestCase.query.filter_by(execution_status='Not Run').count()
    passed_cases = TestCase.query.filter_by(execution_status='Passed').count()
    failed_cases = TestCase.query.filter_by(execution_status='Failed').count()

    pass_rate = round((passed_cases / executed_cases * 100.0), 1) if executed_cases > 0 else 0.0
    failure_rate = round((failed_cases / executed_cases * 100.0), 1) if executed_cases > 0 else 0.0

    stats = {
        'total_plans': total_plans,
        'total_cases': total_cases,
        'executed_cases': executed_cases,
        'pending_cases': pending_cases,
        'passed_cases': passed_cases,
        'failed_cases': failed_cases,
        'pass_rate': pass_rate,
        'failure_rate': failure_rate
    }

    return render_template(
        'test_planning/index.html',
        test_plans=test_plans,
        projects=projects,
        selected_project_id=project_id,
        stats=stats
    )

@test_planning_bp.route('/plans/create', methods=['GET', 'POST'])
@login_required
@tester_required
def create_plan():
    projects = Project.query.filter_by(status='Active').all()
    testers = User.query.filter(User.role.in_(['admin', 'tester'])).all()

    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        objectives = request.form.get('objectives', '').strip()
        scope = request.form.get('scope', '').strip()
        environment = request.form.get('environment', 'Staging')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        assigned_tester_id = request.form.get('assigned_tester_id', type=int)
        test_strategy = request.form.get('test_strategy', '').strip()
        entry_criteria = request.form.get('entry_criteria', '').strip()
        exit_criteria = request.form.get('exit_criteria', '').strip()
        status = request.form.get('status', 'Draft')

        if not project_id or not name:
            flash('Project and Test Plan Name are mandatory.', 'warning')
            return render_template('test_planning/create_plan.html', projects=projects, testers=testers)

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        plan = TestPlan(
            project_id=project_id,
            name=name,
            description=description,
            objectives=objectives,
            scope=scope,
            environment=environment,
            start_date=start_date,
            end_date=end_date,
            assigned_tester_id=assigned_tester_id,
            test_strategy=test_strategy,
            entry_criteria=entry_criteria,
            exit_criteria=exit_criteria,
            status=status
        )
        db.session.add(plan)
        db.session.commit()

        log_activity(action='Create Test Plan', description=f"Created test plan '{name}' in project ID {project_id}.", project_id=project_id)
        flash(f"Test Plan '{name}' created successfully!", 'success')
        return redirect(url_for('test_planning.plan_details', plan_id=plan.id))

    return render_template('test_planning/create_plan.html', projects=projects, testers=testers)

@test_planning_bp.route('/plans/<int:plan_id>')
@login_required
@tester_required
def plan_details(plan_id):
    plan = TestPlan.query.get_or_404(plan_id)
    
    # Filters
    search_q = request.args.get('q', '').strip()
    module_filter = request.args.get('module', '').strip()
    category_filter = request.args.get('category', '').strip()
    priority_filter = request.args.get('priority', '').strip()
    status_filter = request.args.get('status', '').strip()

    tc_query = plan.test_cases
    if search_q:
        tc_query = tc_query.filter(TestCase.title.ilike(f"%{search_q}%") | TestCase.custom_id.ilike(f"%{search_q}%"))
    if module_filter:
        tc_query = tc_query.filter_by(module=module_filter)
    if category_filter:
        tc_query = tc_query.filter_by(category=category_filter)
    if priority_filter:
        tc_query = tc_query.filter_by(priority=priority_filter)
    if status_filter:
        tc_query = tc_query.filter_by(execution_status=status_filter)

    test_cases = tc_query.order_by(TestCase.id.asc()).all()

    # Distinct modules for filter dropdown
    modules = [m[0] for m in db.session.query(TestCase.module).filter_by(test_plan_id=plan_id).distinct().all()]

    return render_template(
        'test_planning/plan_details.html',
        plan=plan,
        test_cases=test_cases,
        modules=modules,
        search_q=search_q,
        module_filter=module_filter,
        category_filter=category_filter,
        priority_filter=priority_filter,
        status_filter=status_filter
    )

@test_planning_bp.route('/plans/<int:plan_id>/cases/create', methods=['GET', 'POST'])
@login_required
@tester_required
def create_case(plan_id):
    plan = TestPlan.query.get_or_404(plan_id)
    testers = User.query.filter(User.role.in_(['admin', 'tester'])).all()

    if request.method == 'POST':
        custom_id = request.form.get('custom_id', '').strip()
        title = request.form.get('title', '').strip()
        module = request.form.get('module', 'Authentication').strip()
        category = request.form.get('category', 'Functional Testing')
        preconditions = request.form.get('preconditions', '').strip()
        steps = request.form.get('steps', '').strip()
        test_data = request.form.get('test_data', '').strip()
        expected_result = request.form.get('expected_result', '').strip()
        priority = request.form.get('priority', 'Medium')
        severity = request.form.get('severity', 'Major')
        tester_id = request.form.get('tester_id', type=int)

        if not custom_id or not title or not steps or not expected_result:
            flash('Case ID, Title, Steps, and Expected Result are mandatory fields.', 'warning')
            return render_template('test_planning/create_case.html', plan=plan, testers=testers)

        # Check unique custom_id
        if TestCase.query.filter_by(custom_id=custom_id).first():
            flash(f"Test Case ID '{custom_id}' is already registered. Please use a unique identifier.", 'danger')
            return render_template('test_planning/create_case.html', plan=plan, testers=testers)

        tc = TestCase(
            custom_id=custom_id,
            test_plan_id=plan.id,
            title=title,
            module=module,
            category=category,
            preconditions=preconditions,
            steps=steps,
            test_data=test_data,
            expected_result=expected_result,
            priority=priority,
            severity=severity,
            execution_status='Not Run',
            tester_id=tester_id or current_user.id
        )
        db.session.add(tc)
        db.session.commit()

        log_activity(action='Create Test Case', description=f"Added test case {custom_id}: '{title}'.", project_id=plan.project_id)
        flash(f"Test case '{custom_id}' created successfully!", 'success')
        return redirect(url_for('test_planning.plan_details', plan_id=plan.id))

    # Auto-generate next ID proposal
    count = plan.test_cases.count() + 1
    suggested_id = f"TC-{count:03d}"

    return render_template('test_planning/create_case.html', plan=plan, testers=testers, suggested_id=suggested_id)

@test_planning_bp.route('/cases/<int:case_id>')
@login_required
@tester_required
def case_details(case_id):
    case = TestCase.query.get_or_404(case_id)
    return render_template('test_planning/case_details.html', case=case)

@test_planning_bp.route('/cases/<int:case_id>/edit', methods=['GET', 'POST'])
@login_required
@tester_required
def edit_case(case_id):
    case = TestCase.query.get_or_404(case_id)
    testers = User.query.filter(User.role.in_(['admin', 'tester'])).all()

    if request.method == 'POST':
        case.title = request.form.get('title', case.title).strip()
        case.module = request.form.get('module', case.module).strip()
        case.category = request.form.get('category', case.category)
        case.preconditions = request.form.get('preconditions', case.preconditions).strip()
        case.steps = request.form.get('steps', case.steps).strip()
        case.test_data = request.form.get('test_data', case.test_data).strip()
        case.expected_result = request.form.get('expected_result', case.expected_result).strip()
        case.priority = request.form.get('priority', case.priority)
        case.severity = request.form.get('severity', case.severity)
        case.tester_id = request.form.get('tester_id', type=int)

        db.session.commit()
        log_activity(action='Edit Test Case', description=f"Updated test case {case.custom_id}.", project_id=case.test_plan.project_id)
        flash(f"Test case '{case.custom_id}' updated successfully.", 'success')
        return redirect(url_for('test_planning.case_details', case_id=case.id))

    return render_template('test_planning/edit_case.html', case=case, testers=testers)

@test_planning_bp.route('/cases/<int:case_id>/execute', methods=['POST'])
@login_required
@tester_required
def record_case_execution(case_id):
    case = TestCase.query.get_or_404(case_id)
    execution_status = request.form.get('execution_status', 'Passed')
    actual_result = request.form.get('actual_result', '').strip()
    comments = request.form.get('comments', '').strip()

    case.execution_status = execution_status
    case.actual_result = actual_result
    case.comments = comments
    case.last_executed = datetime.utcnow()
    case.tester_id = current_user.id

    db.session.commit()
    log_activity(action='Execute Test Case', description=f"Recorded '{execution_status}' for {case.custom_id}.", project_id=case.test_plan.project_id)
    flash(f"Execution status for {case.custom_id} recorded as {execution_status}.", 'success')
    return redirect(url_for('test_planning.case_details', case_id=case.id))

@test_planning_bp.route('/cases/<int:case_id>/delete', methods=['POST'])
@login_required
@tester_required
def delete_case(case_id):
    case = TestCase.query.get_or_404(case_id)
    plan_id = case.test_plan_id
    custom_id = case.custom_id
    db.session.delete(case)
    db.session.commit()

    flash(f"Test case '{custom_id}' was removed.", 'info')
    return redirect(url_for('test_planning.plan_details', plan_id=plan_id))

@test_planning_bp.route('/plans/<int:plan_id>/export-excel')
@login_required
@tester_required
def export_cases_excel(plan_id):
    plan = TestPlan.query.get_or_404(plan_id)
    cases = plan.test_cases.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Test Cases"

    headers = [
        "Test Case ID", "Title", "Module", "Category", "Preconditions",
        "Test Steps", "Test Data", "Expected Result", "Actual Result",
        "Priority", "Severity", "Execution Status", "Assigned Tester"
    ]
    ws.append(headers)

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")

    for tc in cases:
        ws.append([
            tc.custom_id, tc.title, tc.module, tc.category, tc.preconditions or '',
            tc.steps, tc.test_data or '', tc.expected_result, tc.actual_result or '',
            tc.priority, tc.severity, tc.execution_status,
            tc.tester.username if tc.tester else 'Unassigned'
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"TestCases_{plan.name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@test_planning_bp.route('/plans/<int:plan_id>/import-csv', methods=['POST'])
@login_required
@tester_required
def import_cases_csv(plan_id):
    plan = TestPlan.query.get_or_404(plan_id)
    if 'csv_file' not in request.files:
        flash('No file was uploaded.', 'warning')
        return redirect(url_for('test_planning.plan_details', plan_id=plan.id))

    file = request.files['csv_file']
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file.', 'danger')
        return redirect(url_for('test_planning.plan_details', plan_id=plan.id))

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
        reader = csv.DictReader(stream)

        imported_count = 0
        skipped_count = 0

        for row in reader:
            custom_id = row.get('custom_id') or row.get('Test Case ID') or row.get('id')
            title = row.get('title') or row.get('Title')
            module = row.get('module') or row.get('Module') or 'General'
            category = row.get('category') or row.get('Category') or 'Functional Testing'
            steps = row.get('steps') or row.get('Test Steps') or 'N/A'
            expected = row.get('expected_result') or row.get('Expected Result') or 'N/A'

            if not custom_id or not title:
                continue

            existing = TestCase.query.filter_by(custom_id=custom_id).first()
            if existing:
                skipped_count += 1
                continue

            tc = TestCase(
                custom_id=custom_id.strip(),
                test_plan_id=plan.id,
                title=title.strip(),
                module=module.strip(),
                category=category.strip(),
                preconditions=row.get('preconditions') or row.get('Preconditions'),
                steps=steps.strip(),
                test_data=row.get('test_data') or row.get('Test Data'),
                expected_result=expected.strip(),
                priority=row.get('priority') or 'Medium',
                severity=row.get('severity') or 'Major',
                execution_status='Not Run',
                tester_id=current_user.id
            )
            db.session.add(tc)
            imported_count += 1

        db.session.commit()
        log_activity(action='Import Test Cases CSV', description=f"Imported {imported_count} cases into plan ID {plan_id}.", project_id=plan.project_id)
        flash(f"Successfully imported {imported_count} test cases ({skipped_count} skipped duplicates).", 'success')

    except Exception as e:
        db.session.rollback()
        flash(f"Error parsing CSV file: {str(e)}", 'danger')

    return redirect(url_for('test_planning.plan_details', plan_id=plan.id))
