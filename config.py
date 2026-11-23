import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sec-st-platform-secure-token-v1-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'testing_framework.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload and File Paths
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    REFERENCE_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'reference')
    ACTUAL_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'actual')
    PROCESSED_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'processed')
    EVIDENCE_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'evidence')
    REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
    LOGS_FOLDER = os.path.join(BASE_DIR, 'logs')
    
    # Upload limits
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max limit
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    ALLOWED_DATA_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    # Automated Testing
    SELENIUM_HEADLESS = os.environ.get('SELENIUM_HEADLESS', 'true').lower() == 'true'
    SELENIUM_TIMEOUT = int(os.environ.get('SELENIUM_TIMEOUT', '15'))
    DEFAULT_TARGET_APP_URL = os.environ.get('TARGET_APP_URL', 'http://127.0.0.1:5000/lms')
    
    # Security Baseline Checks
    AUTHORIZED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0']
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # SESSION_COOKIE_SECURE can be enabled in production with HTTPS
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config_by_name = {
    'default': Config,
    'development': Config,
    'testing': TestingConfig
}
