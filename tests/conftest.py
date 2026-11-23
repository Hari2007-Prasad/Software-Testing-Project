import os
import pytest
from app import create_app
from extensions import db
from models import User, Project, ThresholdConfiguration

@pytest.fixture
def app():
    os.environ['FLASK_ENV'] = 'testing'
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Create base test users
        admin = User(username='test_admin', email='admin@test.org', role='admin')
        admin.set_password('admin123')

        tester = User(username='test_tester', email='tester@test.org', role='tester')
        tester.set_password('tester123')

        student = User(username='test_student', email='student@test.org', role='student')
        student.set_password('student123')

        db.session.add_all([admin, tester, student])
        db.session.flush()

        # Create base project
        project = Project(
            name='Test Project LMS',
            description='Test environment LMS project',
            app_url='http://127.0.0.1:5000/lms',
            user_id=admin.id
        )
        db.session.add(project)
        db.session.flush()

        th = ThresholdConfiguration(
            project_id=project.id,
            max_pixel_diff_pct=1.5,
            min_pixel_similarity_pct=98.5,
            min_ssim_score=0.92,
            min_pass_rate=90.0,
            max_failed_tests=1,
            max_blocked_tests=0,
            max_critical_findings=0,
            max_high_findings=1
        )
        db.session.add(th)

        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
