import pytest
from models import Project, TestPlan, TestCase

def login(client, username='test_tester', password='tester123'):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)

def test_project_crud(client, app):
    """Test project creation, inspection, and update."""
    login(client)

    # 1. Create project
    resp = client.post('/projects/create', data={
        'name': 'Canvas LMS Mobile Audit',
        'description': 'Mobile responsive audit',
        'app_url': 'http://127.0.0.1:5000/lms',
        'project_type': 'Digital Learning Platform',
        'environment': 'Staging',
        'status': 'Active'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Canvas LMS Mobile Audit' in resp.data

    with app.app_context():
        p = Project.query.filter_by(name='Canvas LMS Mobile Audit').first()
        assert p is not None
        p_id = p.id

    # 2. View details
    resp = client.get(f'/projects/{p_id}')
    assert resp.status_code == 200
    assert b'Canvas LMS Mobile Audit' in resp.data

    # 3. Edit project
    resp = client.post(f'/projects/{p_id}/edit', data={
        'name': 'Canvas LMS Mobile Audit Updated',
        'description': 'Updated description',
        'app_url': 'http://127.0.0.1:5000/lms',
        'project_type': 'Digital Learning Platform',
        'environment': 'Production',
        'status': 'Active'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Canvas LMS Mobile Audit Updated' in resp.data

def test_test_plan_and_case_lifecycle(client, app):
    """Test creating a test plan, adding a test case, and updating execution status."""
    login(client)

    with app.app_context():
        project = Project.query.first()
        p_id = project.id

    # 1. Create Test Plan
    resp = client.post('/test-planning/plans/create', data={
        'project_id': p_id,
        'name': 'Core Authentication Test Plan',
        'description': 'Security and sanity checks for login',
        'environment': 'Staging',
        'status': 'In Progress'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Core Authentication Test Plan' in resp.data

    with app.app_context():
        plan = TestPlan.query.filter_by(name='Core Authentication Test Plan').first()
        assert plan is not None
        plan_id = plan.id

    # 2. Create Test Case
    resp = client.post(f'/test-planning/plans/{plan_id}/cases/create', data={
        'custom_id': 'TC-TEST-001',
        'title': 'Verify Dashboard Redirect upon Valid Credentials',
        'module': 'Authentication',
        'category': 'Functional Testing',
        'preconditions': 'Student exists',
        'steps': '1. POST credentials\n2. Inspect redirect',
        'test_data': 'student/student123',
        'expected_result': 'Redirect to /lms/dashboard',
        'priority': 'High',
        'severity': 'Critical'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'TC-TEST-001' in resp.data

    with app.app_context():
        tc = TestCase.query.filter_by(custom_id='TC-TEST-001').first()
        assert tc is not None
        assert tc.execution_status == 'Not Run'
        case_id = tc.id

    # 3. Record Execution Status
    resp = client.post(f'/test-planning/cases/{case_id}/execute', data={
        'execution_status': 'Passed',
        'actual_result': 'Navigated to dashboard with HTTP 302/200.',
        'comments': 'Verified cleanly in automated run.'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Passed' in resp.data

    with app.app_context():
        tc = TestCase.query.get(case_id)
        assert tc.execution_status == 'Passed'
