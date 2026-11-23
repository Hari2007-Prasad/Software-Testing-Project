from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    """User account model for Admin, Tester, and Student roles."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='tester')  # 'admin', 'tester', 'student'
    full_name = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    projects = db.relationship('Project', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    assigned_plans = db.relationship('TestPlan', backref='assigned_tester', foreign_keys='TestPlan.assigned_tester_id', lazy='dynamic')
    assigned_cases = db.relationship('TestCase', backref='tester', foreign_keys='TestCase.tester_id', lazy='dynamic')
    executions = db.relationship('TestExecution', backref='executor', lazy='dynamic')
    image_comparisons = db.relationship('ImageComparison', backref='creator', lazy='dynamic')
    enrollments = db.relationship('Enrollment', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_tester(self):
        return self.role in ('admin', 'tester')

    def is_student(self):
        return self.role == 'student'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'full_name': self.full_name or self.username,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Project(db.Model):
    """Testing project containing test plans, test runs, comparisons, and security findings."""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    app_url = db.Column(db.String(255), nullable=False, default='http://127.0.0.1:5000/lms')
    project_type = db.Column(db.String(50), default='Digital Learning Platform')
    environment = db.Column(db.String(50), default='Staging')  # Development, Staging, Production
    status = db.Column(db.String(30), default='Active')        # Active, Archived, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Relationships
    test_plans = db.relationship('TestPlan', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    test_executions = db.relationship('TestExecution', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    image_comparisons = db.relationship('ImageComparison', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    security_findings = db.relationship('SecurityFinding', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    threshold_config = db.relationship('ThresholdConfiguration', backref='project', uselist=False, cascade='all, delete-orphan')
    threshold_analyses = db.relationship('ThresholdAnalysis', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='project', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'app_url': self.app_url,
            'project_type': self.project_type,
            'environment': self.environment,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'owner': self.owner.username if self.owner else None
        }


class TestPlan(db.Model):
    """High-level test plan grouping test cases and defining strategy & scope."""
    __tablename__ = 'test_plans'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    objectives = db.Column(db.Text, nullable=True)
    scope = db.Column(db.Text, nullable=True)
    environment = db.Column(db.String(50), default='Staging')
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    assigned_tester_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    test_strategy = db.Column(db.Text, nullable=True)
    entry_criteria = db.Column(db.Text, nullable=True)
    exit_criteria = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='Draft')  # Draft, In Progress, Completed, Approved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    test_cases = db.relationship('TestCase', backref='test_plan', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'objectives': self.objectives,
            'scope': self.scope,
            'environment': self.environment,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'assigned_tester': self.assigned_tester.username if self.assigned_tester else 'Unassigned',
            'status': self.status,
            'total_cases': self.test_cases.count()
        }


class TestCase(db.Model):
    """Individual test case with detailed steps, expectations, and execution tracking."""
    __tablename__ = 'test_cases'

    id = db.Column(db.Integer, primary_key=True)
    custom_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    test_plan_id = db.Column(db.Integer, db.ForeignKey('test_plans.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    module = db.Column(db.String(100), default='Authentication')
    category = db.Column(db.String(50), default='Functional Testing')
    preconditions = db.Column(db.Text, nullable=True)
    steps = db.Column(db.Text, nullable=False)
    test_data = db.Column(db.Text, nullable=True)
    expected_result = db.Column(db.Text, nullable=False)
    actual_result = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), default='Medium')  # Low, Medium, High, Critical
    severity = db.Column(db.String(20), default='Major')    # Minor, Major, Critical, Blocker
    execution_status = db.Column(db.String(30), default='Not Run')  # Not Run, Passed, Failed, Blocked, Needs Review
    tester_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    comments = db.Column(db.Text, nullable=True)
    evidence_path = db.Column(db.String(255), nullable=True)
    last_executed = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'custom_id': self.custom_id,
            'test_plan_id': self.test_plan_id,
            'title': self.title,
            'module': self.module,
            'category': self.category,
            'preconditions': self.preconditions,
            'steps': self.steps,
            'test_data': self.test_data,
            'expected_result': self.expected_result,
            'actual_result': self.actual_result,
            'priority': self.priority,
            'severity': self.severity,
            'execution_status': self.execution_status,
            'tester': self.tester.username if self.tester else 'Unassigned',
            'last_executed': self.last_executed.strftime('%Y-%m-%d %H:%M') if self.last_executed else 'Never',
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None
        }


class TestExecution(db.Model):
    """Execution session for automated functional or security test runs."""
    __tablename__ = 'test_executions'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    test_suite_name = db.Column(db.String(120), default='Regression Test Suite')
    execution_type = db.Column(db.String(50), default='Automated')  # Automated, Security Baseline, Manual
    status = db.Column(db.String(30), default='Running')  # Running, Completed, Failed, Aborted
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Float, default=0.0)
    total_tests = db.Column(db.Integer, default=0)
    passed_tests = db.Column(db.Integer, default=0)
    failed_tests = db.Column(db.Integer, default=0)
    blocked_tests = db.Column(db.Integer, default=0)
    logs = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    results = db.relationship('TestExecutionResult', backref='execution', lazy='dynamic', cascade='all, delete-orphan')
    security_findings = db.relationship('SecurityFinding', backref='execution', lazy='dynamic')
    threshold_analyses = db.relationship('ThresholdAnalysis', backref='execution', lazy='dynamic')

    @property
    def pass_percentage(self):
        if self.total_tests > 0:
            return round((self.passed_tests / self.total_tests) * 100.0, 2)
        return 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'test_suite_name': self.test_suite_name,
            'execution_type': self.execution_type,
            'status': self.status,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'duration': f"{self.duration:.2f}s",
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'blocked_tests': self.blocked_tests,
            'pass_percentage': self.pass_percentage,
            'executor': self.executor.username if self.executor else 'System'
        }


class TestExecutionResult(db.Model):
    """Detailed result for each individual test case executed in an automated run."""
    __tablename__ = 'test_execution_results'

    id = db.Column(db.Integer, primary_key=True)
    test_execution_id = db.Column(db.Integer, db.ForeignKey('test_executions.id', ondelete='CASCADE'), nullable=False, index=True)
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_cases.id', ondelete='SET NULL'), nullable=True)
    test_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='Functional')
    status = db.Column(db.String(20), default='Passed')  # Passed, Failed, Blocked
    duration = db.Column(db.Float, default=0.0)
    error_message = db.Column(db.Text, nullable=True)
    stack_trace = db.Column(db.Text, nullable=True)
    screenshot_path = db.Column(db.String(255), nullable=True)
    actual_result = db.Column(db.Text, nullable=True)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'test_name': self.test_name,
            'category': self.category,
            'status': self.status,
            'duration': f"{self.duration:.2f}s",
            'error_message': self.error_message,
            'screenshot_path': self.screenshot_path,
            'actual_result': self.actual_result,
            'executed_at': self.executed_at.strftime('%Y-%m-%d %H:%M:%S') if self.executed_at else None
        }


class ImageComparison(db.Model):
    """Record of reference vs actual image comparison run."""
    __tablename__ = 'image_comparisons'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    reference_path = db.Column(db.String(255), nullable=False)
    actual_path = db.Column(db.String(255), nullable=False)
    diff_image_path = db.Column(db.String(255), nullable=True)
    mask_path = db.Column(db.String(255), nullable=True)
    overlay_path = db.Column(db.String(255), nullable=True)
    bbox_path = db.Column(db.String(255), nullable=True)
    edge_path = db.Column(db.String(255), nullable=True)
    config_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='Completed')  # Processing, Completed, Failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # One-to-one relationship with ImageMetric
    metric = db.relationship('ImageMetric', backref='comparison', uselist=False, cascade='all, delete-orphan')
    threshold_analyses = db.relationship('ThresholdAnalysis', backref='image_comparison', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'reference_path': self.reference_path,
            'actual_path': self.actual_path,
            'diff_image_path': self.diff_image_path,
            'mask_path': self.mask_path,
            'overlay_path': self.overlay_path,
            'bbox_path': self.bbox_path,
            'edge_path': self.edge_path,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'metrics': self.metric.to_dict() if self.metric else None
        }


class ImageMetric(db.Model):
    """Calculated computer vision metrics for an image comparison."""
    __tablename__ = 'image_metrics'

    id = db.Column(db.Integer, primary_key=True)
    image_comparison_id = db.Column(db.Integer, db.ForeignKey('image_comparisons.id', ondelete='CASCADE'), unique=True, nullable=False)
    pixel_similarity = db.Column(db.Float, default=100.0)      # 100 - difference_percentage
    difference_percentage = db.Column(db.Float, default=0.0)   # (changed / total) * 100
    changed_pixels = db.Column(db.Integer, default=0)
    total_pixels = db.Column(db.Integer, default=0)
    ssim_score = db.Column(db.Float, default=1.0)              # scikit-image SSIM (-1 to 1)
    structural_similarity_pct = db.Column(db.Float, default=100.0)
    changed_regions_count = db.Column(db.Integer, default=0)
    regions_data = db.Column(db.Text, nullable=True)           # JSON string of bounding boxes
    processing_duration = db.Column(db.Float, default=0.0)
    alignment_applied = db.Column(db.Boolean, default=False)
    transform_matrix_json = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'pixel_similarity': round(self.pixel_similarity, 2),
            'difference_percentage': round(self.difference_percentage, 2),
            'changed_pixels': self.changed_pixels,
            'total_pixels': self.total_pixels,
            'ssim_score': round(self.ssim_score, 4),
            'structural_similarity_pct': round(self.structural_similarity_pct, 2),
            'changed_regions_count': self.changed_regions_count,
            'processing_duration': f"{self.processing_duration:.3f}s",
            'alignment_applied': self.alignment_applied
        }


class SecurityFinding(db.Model):
    """Authorized baseline security finding generated during testing."""
    __tablename__ = 'security_findings'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    test_execution_id = db.Column(db.Integer, db.ForeignKey('test_executions.id', ondelete='SET NULL'), nullable=True)
    finding_code = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='Medium')  # Critical, High, Medium, Low, Info
    affected_url = db.Column(db.String(255), nullable=False)
    evidence = db.Column(db.Text, nullable=True)
    recommendation = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='Open')  # Open, Acknowledged, Resolved, False Positive
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'finding_code': self.finding_code,
            'title': self.title,
            'description': self.description,
            'severity': self.severity,
            'affected_url': self.affected_url,
            'evidence': self.evidence,
            'recommendation': self.recommendation,
            'status': self.status,
            'discovered_at': self.discovered_at.strftime('%Y-%m-%d %H:%M:%S') if self.discovered_at else None
        }


class ThresholdConfiguration(db.Model):
    """Acceptance criteria and weights for a project or global baseline."""
    __tablename__ = 'threshold_configurations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True, unique=True)
    name = db.Column(db.String(100), default='Strict Quality & Security Policy')
    
    # Image comparison thresholds
    max_pixel_diff_pct = db.Column(db.Float, default=1.5)        # Max allowed pixel diff %
    min_pixel_similarity_pct = db.Column(db.Float, default=98.5) # Min pixel similarity %
    min_ssim_score = db.Column(db.Float, default=0.92)           # Min SSIM score (0-1.0)
    min_region_size = db.Column(db.Integer, default=25)          # Minimum region size in px
    max_changed_regions = db.Column(db.Integer, default=2)       # Max allowed changed regions

    # Functional testing thresholds
    min_pass_rate = db.Column(db.Float, default=90.0)            # Minimum test pass rate %
    max_failed_tests = db.Column(db.Integer, default=1)          # Max allowable failed tests
    max_blocked_tests = db.Column(db.Integer, default=0)         # Max allowable blocked tests

    # Security thresholds
    max_critical_findings = db.Column(db.Integer, default=0)     # Max critical findings allowed
    max_high_findings = db.Column(db.Integer, default=1)         # Max high findings allowed
    severity_policy = db.Column(db.String(50), default='Strict') # Strict, Moderate, Relaxed

    # Overall project assessment weights (must sum to 1.0)
    visual_weight = db.Column(db.Float, default=0.30)
    functional_weight = db.Column(db.Float, default=0.40)
    security_weight = db.Column(db.Float, default=0.30)
    
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'max_pixel_diff_pct': self.max_pixel_diff_pct,
            'min_pixel_similarity_pct': self.min_pixel_similarity_pct,
            'min_ssim_score': self.min_ssim_score,
            'min_region_size': self.min_region_size,
            'max_changed_regions': self.max_changed_regions,
            'min_pass_rate': self.min_pass_rate,
            'max_failed_tests': self.max_failed_tests,
            'max_blocked_tests': self.max_blocked_tests,
            'max_critical_findings': self.max_critical_findings,
            'max_high_findings': self.max_high_findings,
            'severity_policy': self.severity_policy,
            'visual_weight': self.visual_weight,
            'functional_weight': self.functional_weight,
            'security_weight': self.security_weight,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class ThresholdAnalysis(db.Model):
    """Evaluation result of actual metrics tested against threshold criteria."""
    __tablename__ = 'threshold_analyses'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    image_comparison_id = db.Column(db.Integer, db.ForeignKey('image_comparisons.id', ondelete='SET NULL'), nullable=True)
    test_execution_id = db.Column(db.Integer, db.ForeignKey('test_executions.id', ondelete='SET NULL'), nullable=True)
    
    # Pillar evaluations
    visual_status = db.Column(db.String(20), default='PASS')      # PASS, FAIL, REVIEW
    visual_score = db.Column(db.Float, default=100.0)
    functional_status = db.Column(db.String(20), default='PASS')
    functional_score = db.Column(db.Float, default=100.0)
    security_status = db.Column(db.String(20), default='PASS')
    security_score = db.Column(db.Float, default=100.0)
    
    # Combined score and final status
    overall_status = db.Column(db.String(20), default='PASS')    # PASS, FAIL, REVIEW
    overall_score = db.Column(db.Float, default=100.0)
    
    violations_json = db.Column(db.Text, nullable=True)  # List of violation strings
    details_json = db.Column(db.Text, nullable=True)     # Detailed breakdown
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_violations(self):
        if self.violations_json:
            try:
                return json.loads(self.violations_json)
            except Exception:
                return []
        return []

    def get_details(self):
        if self.details_json:
            try:
                return json.loads(self.details_json)
            except Exception:
                return {}
        return {}

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'visual_status': self.visual_status,
            'visual_score': round(self.visual_score, 1),
            'functional_status': self.functional_status,
            'functional_score': round(self.functional_score, 1),
            'security_status': self.security_status,
            'security_score': round(self.security_score, 1),
            'overall_status': self.overall_status,
            'overall_score': round(self.overall_score, 1),
            'violations': self.get_violations(),
            'analyzed_at': self.analyzed_at.strftime('%Y-%m-%d %H:%M:%S') if self.analyzed_at else None
        }


class ActivityLog(db.Model):
    """Audit trail for key user actions and testing events."""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), default='127.0.0.1')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.username if self.user else 'System',
            'action': self.action,
            'description': self.description,
            'project': self.project.name if self.project else None,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }


class Course(db.Model):
    """Sample LMS Course."""
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='Cybersecurity')
    instructor = db.Column(db.String(100), default='Dr. Alan Turing')
    duration = db.Column(db.String(50), default='6 Weeks')
    level = db.Column(db.String(30), default='Intermediate')
    image_url = db.Column(db.String(255), nullable=True)
    lessons_count = db.Column(db.Integer, default=10)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship('Enrollment', backref='course', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'code': self.code,
            'description': self.description,
            'category': self.category,
            'instructor': self.instructor,
            'duration': self.duration,
            'level': self.level,
            'lessons_count': self.lessons_count,
            'is_published': self.is_published
        }


class Enrollment(db.Model):
    """Sample LMS student course enrollment."""
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Integer, default=0)  # 0 to 100%
    status = db.Column(db.String(30), default='Active')  # Active, Completed, Dropped

    __table_args__ = (db.UniqueConstraint('user_id', 'course_id', name='_user_course_uc'),)
