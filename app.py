
import os
from datetime import datetime

from flask import Flask, render_template
from config import config_by_name
from extensions import db, login_manager, csrf


def create_app(config_name=None):

    # --------------------------------------------------
    # 1. Detect environment
    # --------------------------------------------------

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    is_vercel = os.environ.get("VERCEL") == "1"

    # --------------------------------------------------
    # 2. Create Flask application
    # --------------------------------------------------

    if is_vercel:
        runtime_root = "/tmp/security_testing"

        instance_folder = os.path.join(
            runtime_root, "instance"
        )

        os.makedirs(instance_folder, exist_ok=True)

        app = Flask(
            __name__,
            instance_path=instance_folder
        )

    else:
        app = Flask(__name__)

    # Load application configuration
    app.config.from_object(
        config_by_name.get(
            config_name,
            config_by_name["default"]
        )
    )

    # --------------------------------------------------
    # 3. Configure writable folders
    # --------------------------------------------------

    if is_vercel:

        runtime_root = "/tmp/security_testing"

        app.config["UPLOAD_FOLDER"] = os.path.join(
            runtime_root, "uploads"
        )

        app.config["REFERENCE_UPLOAD_FOLDER"] = os.path.join(
            runtime_root, "uploads", "reference"
        )

        app.config["ACTUAL_UPLOAD_FOLDER"] = os.path.join(
            runtime_root, "uploads", "actual"
        )

        app.config["PROCESSED_UPLOAD_FOLDER"] = os.path.join(
            runtime_root, "uploads", "processed"
        )

        app.config["EVIDENCE_UPLOAD_FOLDER"] = os.path.join(
            runtime_root, "uploads", "evidence"
        )

        app.config["REPORTS_FOLDER"] = os.path.join(
            runtime_root, "reports"
        )

        app.config["LOGS_FOLDER"] = os.path.join(
            runtime_root, "logs"
        )

    # --------------------------------------------------
    # 4. Create required directories
    # --------------------------------------------------

    folder_keys = [
        "UPLOAD_FOLDER",
        "REFERENCE_UPLOAD_FOLDER",
        "ACTUAL_UPLOAD_FOLDER",
        "PROCESSED_UPLOAD_FOLDER",
        "EVIDENCE_UPLOAD_FOLDER",
        "REPORTS_FOLDER",
        "LOGS_FOLDER"
    ]

    for key in folder_keys:

        folder = app.config.get(key)

        if folder:
            os.makedirs(folder, exist_ok=True)

    # Create instance directory
    os.makedirs(app.instance_path, exist_ok=True)

    # --------------------------------------------------
    # 5. Initialize extensions
    # --------------------------------------------------

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # --------------------------------------------------
    # 6. Import blueprints
    # --------------------------------------------------

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.projects import projects_bp
    from routes.test_planning import test_planning_bp
    from routes.image_comparison import image_comparison_bp
    from routes.automated_testing import automated_testing_bp
    from routes.security import security_bp
    from routes.thresholds import thresholds_bp
    from routes.reports import reports_bp
    from routes.history import history_bp
    from routes.users import users_bp
    from routes.settings import settings_bp
    from routes.lms import lms_bp

    # --------------------------------------------------
    # 7. Register blueprints
    # --------------------------------------------------

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(test_planning_bp)
    app.register_blueprint(image_comparison_bp)
    app.register_blueprint(automated_testing_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(thresholds_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(lms_bp)

    # --------------------------------------------------
    # 8. Global template context
    # --------------------------------------------------

    @app.context_processor
    def inject_global_data():

        from models import Project

        all_projects = []

        try:
            all_projects = Project.query.filter_by(
                status="Active"
            ).all()

        except Exception:
            app.logger.exception(
                "Could not load global project data"
            )

        return {
            "global_projects": all_projects,
            "current_year": datetime.utcnow().year,
            "platform_version": "v2.4.0 Enterprise"
        }

    # --------------------------------------------------
    # 9. Custom template filters
    # --------------------------------------------------

    @app.template_filter("datetime_format")
    def datetime_format_filter(
        value,
        format="%b %d, %Y %H:%M"
    ):

        if value is None:
            return "N/A"

        if isinstance(value, str):

            try:
                value = datetime.strptime(
                    value,
                    "%Y-%m-%d %H:%M:%S"
                )

            except Exception:
                return value

        return value.strftime(format)

    @app.template_filter("status_badge")
    def status_badge_filter(status):

        status_map = {
            "Passed": "bg-success",
            "PASS": "bg-success",
            "Completed": "bg-success",
            "Active": "bg-success",
            "Approved": "bg-success",

            "Failed": "bg-danger",
            "FAIL": "bg-danger",
            "Critical": "bg-danger",
            "High": "bg-danger",
            "Blocked": "bg-danger",

            "Needs Review": "bg-warning text-dark",
            "REVIEW": "bg-warning text-dark",
            "Medium": "bg-warning text-dark",

            "In Progress": "bg-info text-dark",
            "Running": "bg-info text-dark",
            "Low": "bg-info text-dark",

            "Not Run": "bg-secondary",
            "Draft": "bg-secondary",
            "Archived": "bg-secondary",
            "Info": "bg-secondary"
        }

        return status_map.get(
            status,
            "bg-primary"
        )

    # --------------------------------------------------
    # 10. Error handlers
    # --------------------------------------------------

    @app.errorhandler(403)
    def forbidden(e):

        return render_template(
            "base.html",
            error_code=403,
            error_message=(
                "Access Forbidden. "
                "You do not possess the required role permissions."
            )
        ), 403

    @app.errorhandler(404)
    def page_not_found(e):

        return render_template(
            "base.html",
            error_code=404,
            error_message=(
                "The requested resource or page was not found."
            )
        ), 404

    @app.errorhandler(500)
    def internal_server_error(e):

        return render_template(
            "base.html",
            error_code=500,
            error_message=(
                "An unexpected internal server error occurred."
            )
        ), 500

    # --------------------------------------------------
    # 11. Database initialization command
    # --------------------------------------------------

    @app.cli.command("init-db")
    def init_db_command():

        """Creates database schema and tables."""

        with app.app_context():

            db.create_all()

            print(
                "Database schema successfully created."
            )

    # --------------------------------------------------
    # 12. Demo data command
    # --------------------------------------------------

    @app.cli.command("seed-demo")
    def seed_demo_command():

        """Seeds demo users, courses, test cases and images."""

        from seed import seed_database

        with app.app_context():
            seed_database()

    return app


# ------------------------------------------------------
# 13. Create application instance
# ------------------------------------------------------

app = create_app()


# ------------------------------------------------------
# 14. Local development startup
# ------------------------------------------------------

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

        from models import User

        if not User.query.filter_by(
            username="admin"
        ).first():

            from seed import seed_database

            seed_database()

    print("=" * 65)

    print(
        "SECURITY & FUNCTIONAL TESTING PLATFORM FOR DIGITAL LEARNING LMS"
    )

    print("Active: http://127.0.0.1:5000")
    print("Target LMS: http://127.0.0.1:5000/lms")

    print("Admin Login: admin / admin123")
    print("Tester Login: tester / tester123")
    print("Student Login: student / student123")

    print("=" * 65)

    debug_mode = (
        os.environ.get(
            "FLASK_DEBUG", "false"
        ).lower() == "true"
    )

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=debug_mode
    )
