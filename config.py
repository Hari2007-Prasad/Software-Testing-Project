
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Detect Vercel deployment
IS_VERCEL = os.environ.get("VERCEL") == "1"

# Runtime storage
if IS_VERCEL:
    RUNTIME_DIR = "/tmp/security_testing"
else:
    RUNTIME_DIR = BASE_DIR

# Database directory
INSTANCE_DIR = os.path.join(RUNTIME_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

# Database configuration
DATABASE_URI = os.environ.get("DATABASE_URI")

if not DATABASE_URI:
    DATABASE_PATH = os.path.join(
        INSTANCE_DIR,
        "testing_framework.db"
    )

    DATABASE_URI = "sqlite:///" + DATABASE_PATH.replace("\\", "/")


class Config:
    """Base application configuration."""

    # Security
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "local-development-key-change-before-production"
    )

    # Database
    SQLALCHEMY_DATABASE_URI = DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload and file paths
    UPLOAD_FOLDER = os.path.join(RUNTIME_DIR, "uploads")

    REFERENCE_UPLOAD_FOLDER = os.path.join(
        UPLOAD_FOLDER, "reference"
    )

    ACTUAL_UPLOAD_FOLDER = os.path.join(
        UPLOAD_FOLDER, "actual"
    )

    PROCESSED_UPLOAD_FOLDER = os.path.join(
        UPLOAD_FOLDER, "processed"
    )

    EVIDENCE_UPLOAD_FOLDER = os.path.join(
        UPLOAD_FOLDER, "evidence"
    )

    REPORTS_FOLDER = os.path.join(RUNTIME_DIR, "reports")

    LOGS_FOLDER = os.path.join(RUNTIME_DIR, "logs")

    # Upload limits
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    ALLOWED_IMAGE_EXTENSIONS = {
        "png", "jpg", "jpeg"
    }

    ALLOWED_DATA_EXTENSIONS = {
        "csv", "xlsx", "xls"
    }

    # Automated testing
    SELENIUM_HEADLESS = (
        os.environ.get(
            "SELENIUM_HEADLESS", "true"
        ).lower() == "true"
    )

    SELENIUM_TIMEOUT = int(
        os.environ.get("SELENIUM_TIMEOUT", "15")
    )

    DEFAULT_TARGET_APP_URL = os.environ.get(
        "TARGET_APP_URL",
        "http://127.0.0.1:5000/lms"
    )

    # Security baseline checks
    AUTHORIZED_HOSTS = [
        "127.0.0.1",
        "localhost",
        "0.0.0.0"
    ]

    # Session security
    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = (
        os.environ.get(
            "SESSION_COOKIE_SECURE",
            "true" if IS_VERCEL else "false"
        ).lower() == "true"
    )


class TestingConfig(Config):
    """Configuration for automated tests."""

    TESTING = True

    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    WTF_CSRF_ENABLED = False


config_by_name = {
    "default": Config,
    "development": Config,
    "testing": TestingConfig
}
