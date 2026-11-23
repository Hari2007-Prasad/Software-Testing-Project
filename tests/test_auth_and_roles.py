import pytest
from models import User

def test_user_registration(client, app):
    """Test user registration workflow."""
    resp = client.post('/auth/register', data={
        'username': 'newuser',
        'email': 'newuser@org.edu',
        'full_name': 'New Student',
        'role': 'student',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.check_password('Password123!')
        assert user.role == 'student'

def test_login_valid_credentials(client):
    """Test successful login with valid credentials."""
    resp = client.post('/auth/login', data={
        'username': 'test_admin',
        'password': 'admin123'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Testing &amp; Security Operations Center' in resp.data or b'Overview Dashboard' in resp.data

def test_login_invalid_credentials(client):
    """Test rejection of invalid credentials."""
    resp = client.post('/auth/login', data={
        'username': 'test_admin',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Invalid username or password' in resp.data

def test_student_restricted_from_admin_areas(client):
    """Test that student role cannot access tester/admin dashboard or user management."""
    # Login as student
    client.post('/auth/login', data={'username': 'test_student', 'password': 'student123'}, follow_redirects=True)
    
    # Try accessing admin users endpoint
    resp = client.get('/users/', follow_redirects=True)
    assert resp.status_code == 200
    # Should be redirected away or flash error
    assert b'Administrator privileges are required' in resp.data or b'Student Learning Dashboard' in resp.data
