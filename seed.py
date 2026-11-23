import os
import shutil
from datetime import datetime, date, timedelta
import numpy as np
import cv2

from app import create_app
from extensions import db
from models import (
    User, Project, TestPlan, TestCase, Course, Enrollment,
    ThresholdConfiguration, ImageComparison, ImageMetric, TestExecution,
    TestExecutionResult, SecurityFinding, ThresholdAnalysis, ActivityLog
)
from modules.image_processing.preprocessing import ImagePreprocessor
from modules.image_processing.engine import ImageComparisonEngine
from modules.automated_testing.scenarios import FunctionalScenarios

def seed_database():
    app = create_app()
    with app.app_context():
        print("[Seed] Dropping and recreating all tables...")
        db.create_all()

        # Check if users already exist
        if User.query.filter_by(username='admin').first():
            print("[Seed] Database already seeded. Skipping initial seed.")
            return

        print("[Seed] Creating system user roles: Admin, Tester, Student...")
        # 1. Users
        admin = User(
            username='admin',
            email='admin@secplatform.local',
            full_name='Security Lead Architect',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')

        tester = User(
            username='tester',
            email='tester@secplatform.local',
            full_name='Senior QA Automation Engineer',
            role='tester',
            is_active=True
        )
        tester.set_password('tester123')

        student = User(
            username='student',
            email='student@digitallearn.edu',
            full_name='Alex Rivera (Student)',
            role='student',
            is_active=True
        )
        student.set_password('student123')

        db.session.add_all([admin, tester, student])
        db.session.commit()

        print("[Seed] Creating sample Digital Learning Application Courses...")
        # 2. LMS Courses
        courses = [
            Course(
                title='Web Application Security & OWASP Top 10',
                code='SEC-101',
                description='Master defensive engineering, secure coding standards, authentication flaws, and vulnerability auditing for modern web applications.',
                category='Cybersecurity',
                instructor='Dr. Alan Turing',
                duration='8 Weeks',
                level='Intermediate',
                lessons_count=16,
                is_published=True
            ),
            Course(
                title='Full-Stack Python & Flask Architecture',
                code='DEV-201',
                description='Build production-ready, RESTful enterprise applications utilizing Flask, SQLAlchemy, background queues, and clean design patterns.',
                category='Software Engineering',
                instructor='Prof. Guido Rossum',
                duration='10 Weeks',
                level='Intermediate',
                lessons_count=20,
                is_published=True
            ),
            Course(
                title='Automated QA & Continuous Testing with Selenium',
                code='QA-301',
                description='End-to-end browser automation, test suite design, visual regression verification, and integration into modern DevOps pipelines.',
                category='Quality Assurance',
                instructor='Elena Rostova, QA Lead',
                duration='6 Weeks',
                level='Advanced',
                lessons_count=12,
                is_published=True
            ),
            Course(
                title='Computer Vision with OpenCV & Image Processing',
                code='CV-401',
                description='Practical visual inspection algorithms: structural similarity, edge detection, feature alignment, and defect localization.',
                category='Computer Vision',
                instructor='Dr. Fei-Fei Li',
                duration='8 Weeks',
                level='Advanced',
                lessons_count=14,
                is_published=True
            )
        ]
        db.session.add_all(courses)
        db.session.commit()

        # Seed initial enrollment for student
        enrollment = Enrollment(
            user_id=student.id,
            course_id=courses[0].id,
            progress=45,
            status='Active'
        )
        db.session.add(enrollment)
        db.session.commit()

        print("[Seed] Creating Default Testing Project...")
        # 3. Project
        project = Project(
            name='Digital Learning LMS - Core Platform',
            description='Comprehensive visual regression, functional automation, and security baseline verification for the Digital Learning LMS portal.',
            app_url='http://127.0.0.1:5000/lms',
            project_type='Digital Learning Platform',
            environment='Staging',
            status='Active',
            user_id=admin.id
        )
        db.session.add(project)
        db.session.commit()

        # 4. Threshold Configuration
        threshold = ThresholdConfiguration(
            project_id=project.id,
            name='LMS Enterprise Acceptance Criteria',
            max_pixel_diff_pct=1.5,
            min_pixel_similarity_pct=98.5,
            min_ssim_score=0.92,
            min_region_size=25,
            max_changed_regions=2,
            min_pass_rate=90.0,
            max_failed_tests=1,
            max_blocked_tests=0,
            max_critical_findings=0,
            max_high_findings=1,
            severity_policy='Strict',
            visual_weight=0.30,
            functional_weight=0.40,
            security_weight=0.30,
            is_active=True
        )
        db.session.add(threshold)
        db.session.commit()

        print("[Seed] Creating Test Plan and Test Cases...")
        # 5. Test Plan
        plan = TestPlan(
            project_id=project.id,
            name='Release 2.4 Comprehensive Regression & Security Plan',
            description='Verification of authentication flows, course catalog interactions, student enrollment, and security posture ahead of academic term release.',
            objectives='Ensure visual pixel fidelity, zero critical security baseline regressions, and 95%+ functional test pass rate.',
            scope='All public LMS pages, student authentication, course dashboard, contact form, and administrative boundaries.',
            environment='Staging',
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() + timedelta(days=15),
            assigned_tester_id=tester.id,
            test_strategy='Automated Selenium regression suite supplemented by OpenCV visual comparison and automated OWASP baseline scans.',
            entry_criteria='Staging environment deployed; all test accounts seeded; database migrations applied.',
            exit_criteria='Zero blocker defects; visual regression diff <= 1.5%; zero critical security findings.',
            status='In Progress'
        )
        db.session.add(plan)
        db.session.commit()

        # 6. Test Cases (Populate all 15 scenarios + security cases)
        scenarios = FunctionalScenarios.get_all_scenarios()
        for idx, (tc_code, data) in enumerate(scenarios.items(), start=1):
            tc = TestCase(
                custom_id=tc_code,
                test_plan_id=plan.id,
                title=data['name'],
                module='Student Portal' if 'student' in data['name'].lower() or 'course' in data['name'].lower() else 'Authentication',
                category=data['category'],
                preconditions=data['preconditions'],
                steps=data['steps'],
                test_data='student / student123',
                expected_result=data['expected'],
                actual_result=data['expected'] if idx <= 13 else 'Pending automated run',
                priority='High' if idx in (1, 2, 3, 7) else 'Medium',
                severity='Critical' if idx in (3, 7) else 'Major',
                execution_status='Passed' if idx <= 12 else ('Needs Review' if idx == 13 else 'Not Run'),
                tester_id=tester.id
            )
            db.session.add(tc)

        # Add 3 security-specific test cases
        sec_cases = [
            TestCase(
                custom_id='TC-SEC-001',
                test_plan_id=plan.id,
                title='Content Security Policy (CSP) Response Header Audit',
                module='Security Architecture',
                category='Security Testing',
                preconditions='Application accessible via HTTP/HTTPS.',
                steps='1. Issue GET request to application root.\n2. Inspect response headers for Content-Security-Policy.\n3. Assert policy directive restrictions.',
                test_data='GET /lms',
                expected_result='CSP header is present with restrictive script-src and object-src directives.',
                actual_result='Header missing on staging root.',
                priority='Critical',
                severity='Critical',
                execution_status='Failed',
                tester_id=tester.id
            ),
            TestCase(
                custom_id='TC-SEC-002',
                test_plan_id=plan.id,
                title='Session Cookie HttpOnly and SameSite Attributes Verification',
                module='Session Security',
                category='Security Testing',
                preconditions='User initiates login.',
                steps='1. Authenticate user.\n2. Inspect Set-Cookie header for session token.\n3. Verify HttpOnly, Secure, and SameSite flags.',
                test_data='POST /lms/login',
                expected_result='Session cookie includes HttpOnly and SameSite=Lax flags.',
                actual_result='HttpOnly flag verified.',
                priority='High',
                severity='Major',
                execution_status='Passed',
                tester_id=tester.id
            ),
            TestCase(
                custom_id='TC-SEC-003',
                test_plan_id=plan.id,
                title='Administrative Route Broken Access Control Check',
                module='Authorization',
                category='Authorization Testing',
                preconditions='Student session or anonymous session.',
                steps='1. Send GET request to /lms/admin with student credentials.\n2. Assert HTTP 403 Forbidden is returned.',
                test_data='GET /lms/admin',
                expected_result='Access denied; non-admin cannot access administrative dashboard.',
                actual_result='Access denied as expected (HTTP 403).',
                priority='Critical',
                severity='Blocker',
                execution_status='Passed',
                tester_id=tester.id
            )
        ]
        db.session.add_all(sec_cases)
        db.session.commit()

        print("[Seed] Creating sample Visual Regression baseline images & comparison run...")
        # 7. Generate Reference and Actual Images for Demonstration
        ref_dir = os.path.join(app.root_path, 'uploads', 'reference')
        act_dir = os.path.join(app.root_path, 'uploads', 'actual')
        proc_dir = os.path.join(app.root_path, 'uploads', 'processed')
        os.makedirs(ref_dir, exist_ok=True)
        os.makedirs(act_dir, exist_ok=True)
        os.makedirs(proc_dir, exist_ok=True)

        # Create Reference Image (LMS Dashboard mock)
        ref_img = np.full((600, 900, 3), (248, 250, 252), dtype=np.uint8) # Slate 50 background
        # Top Nav Bar
        cv2.rectangle(ref_img, (0, 0), (900, 60), (30, 41, 59), -1) # Dark Slate 800
        cv2.putText(ref_img, "DIGITAL LEARNING PLATFORM", (24, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(ref_img, "Dashboard   Courses   Profile", (520, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (203, 213, 225), 1)
        # Dashboard Title
        cv2.putText(ref_img, "Student Learning Dashboard", (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (15, 23, 42), 2)
        # Cards
        cv2.rectangle(ref_img, (30, 140), (280, 240), (255, 255, 255), -1)
        cv2.rectangle(ref_img, (30, 140), (280, 240), (226, 232, 240), 1)
        cv2.putText(ref_img, "Active Courses", (50, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 116, 139), 1)
        cv2.putText(ref_img, "3 Enrolled", (50, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (37, 99, 235), 2)

        cv2.rectangle(ref_img, (310, 140), (560, 240), (255, 255, 255), -1)
        cv2.rectangle(ref_img, (310, 140), (560, 240), (226, 232, 240), 1)
        cv2.putText(ref_img, "Average Completion", (330, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 116, 139), 1)
        cv2.putText(ref_img, "78.4%", (330, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (16, 185, 129), 2)

        # Course Table
        cv2.rectangle(ref_img, (30, 270), (870, 560), (255, 255, 255), -1)
        cv2.rectangle(ref_img, (30, 270), (870, 560), (226, 232, 240), 1)
        cv2.rectangle(ref_img, (30, 270), (870, 310), (241, 245, 249), -1)
        cv2.putText(ref_img, "Enrolled Courses", (50, 298), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 41, 59), 2)

        ref_file_path = os.path.join(ref_dir, "ref_lms_dashboard.png")
        ImagePreprocessor.save_image(ref_file_path, ref_img)

        # Create Actual Image with a visual regression defect (modified button and status badge)
        act_img = ref_img.copy()
        # Visual Defect 1: Miscolored alert card
        cv2.rectangle(act_img, (30, 140), (280, 240), (254, 242, 242), -1) # Light Red
        cv2.rectangle(act_img, (30, 140), (280, 240), (248, 113, 113), 2) # Red border
        cv2.putText(act_img, "Active Courses", (50, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (185, 28, 28), 1)
        cv2.putText(act_img, "Attention Required", (50, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 38, 38), 2)

        # Visual Defect 2: Additional notification badge
        cv2.circle(act_img, (830, 38), 14, (59, 130, 246), -1)
        cv2.putText(act_img, "3", (826, 43), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        act_file_path = os.path.join(act_dir, "act_lms_dashboard.png")
        ImagePreprocessor.save_image(act_file_path, act_img)

        # Execute comparison engine on seeded images
        engine = ImageComparisonEngine(processed_dir=proc_dir)
        cmp_result = engine.run_comparison(ref_file_path, act_file_path)

        comparison = ImageComparison(
            project_id=project.id,
            name='Dashboard Visual Regression Baseline',
            reference_path='ref_lms_dashboard.png',
            actual_path='act_lms_dashboard.png',
            diff_image_path=cmp_result['paths']['diff_image'],
            mask_path=cmp_result['paths']['mask'],
            overlay_path=cmp_result['paths']['overlay'],
            bbox_path=cmp_result['paths']['bbox'],
            edge_path=cmp_result['paths']['edge'],
            config_json=str(cmp_result['config']),
            status='Completed',
            created_by_id=tester.id
        )
        db.session.add(comparison)
        db.session.flush()

        metrics_data = cmp_result['metrics']
        metric = ImageMetric(
            image_comparison_id=comparison.id,
            pixel_similarity=metrics_data['pixel_similarity'],
            difference_percentage=metrics_data['difference_percentage'],
            changed_pixels=metrics_data['changed_pixels'],
            total_pixels=metrics_data['total_pixels'],
            ssim_score=metrics_data['ssim_score'],
            structural_similarity_pct=metrics_data['structural_similarity_pct'],
            changed_regions_count=metrics_data['changed_regions_count'],
            regions_data=str(metrics_data['regions']),
            processing_duration=metrics_data['processing_duration'],
            alignment_applied=metrics_data['alignment_applied']
        )
        db.session.add(metric)
        db.session.commit()

        print("[Seed] Seeding sample Security Baseline Findings...")
        # 8. Seed Sample Security Findings
        seed_findings = [
            SecurityFinding(
                project_id=project.id,
                finding_code='SEC-FIND-001',
                title='Missing Content Security Policy (CSP) Header',
                description='The HTTP Content-Security-Policy response header is missing from the application root and portal endpoints.',
                severity='Medium',
                affected_url='http://127.0.0.1:5000/lms',
                evidence='Header Content-Security-Policy was absent in response to GET /lms.',
                recommendation='Implement restrictive Content-Security-Policy header enforcing default-src self.',
                status='Open',
                discovered_at=datetime.utcnow() - timedelta(hours=3)
            ),
            SecurityFinding(
                project_id=project.id,
                finding_code='SEC-FIND-002',
                title='Missing X-Frame-Options Clickjacking Protection',
                description='The web application response does not define X-Frame-Options or CSP frame-ancestors.',
                severity='Medium',
                affected_url='http://127.0.0.1:5000/lms/login',
                evidence='X-Frame-Options header not returned.',
                recommendation='Add "X-Frame-Options: SAMEORIGIN" to prevent embedding in malicious iframes.',
                status='Open',
                discovered_at=datetime.utcnow() - timedelta(hours=3)
            ),
            SecurityFinding(
                project_id=project.id,
                finding_code='SEC-FIND-003',
                title='X-Content-Type-Options Header Absent',
                description='MIME-type sniffing protection is not explicitly declared.',
                severity='Low',
                affected_url='http://127.0.0.1:5000/lms',
                evidence='X-Content-Type-Options header not present in HTTP response.',
                recommendation='Set "X-Content-Type-Options: nosniff".',
                status='Acknowledged',
                discovered_at=datetime.utcnow() - timedelta(hours=3)
            )
        ]
        db.session.add_all(seed_findings)
        db.session.commit()

        print("[Seed] Creating sample Automated Execution History...")
        # 9. Seed Sample Test Execution Run
        execution = TestExecution(
            project_id=project.id,
            test_suite_name='Pre-Release Full LMS Functional Suite',
            execution_type='Automated Selenium',
            status='Completed',
            start_time=datetime.utcnow() - timedelta(minutes=45),
            end_time=datetime.utcnow() - timedelta(minutes=43),
            duration=128.45,
            total_tests=15,
            passed_tests=14,
            failed_tests=1,
            blocked_tests=0,
            logs="[14:15:00] Initialized Chrome WebDriver headless.\n[14:15:05] Running TC-AUTO-001 -> PASSED\n[14:15:20] Running TC-AUTO-002 -> PASSED\n[14:15:35] Running TC-AUTO-003 -> PASSED\n[14:15:48] Running TC-AUTO-004 -> PASSED\n[14:16:02] Running TC-AUTO-005 -> PASSED\n[14:16:15] Running TC-AUTO-006 -> PASSED\n[14:16:29] Running TC-AUTO-007 -> PASSED\n[14:16:42] Running TC-AUTO-008 -> PASSED\n[14:16:55] Running TC-AUTO-009 -> PASSED\n[14:17:08] Running TC-AUTO-010 -> PASSED\n[14:17:21] Running TC-AUTO-011 -> PASSED\n[14:17:34] Running TC-AUTO-012 -> PASSED\n[14:17:47] Running TC-AUTO-013 -> PASSED\n[14:18:00] Running TC-AUTO-014 -> PASSED\n[14:18:12] Running TC-AUTO-015 -> PASSED\n[14:18:25] Suite finished with 100% pass rate.",
            created_by_id=tester.id
        )
        db.session.add(execution)
        db.session.flush()

        for idx, (tc_id, s_data) in enumerate(scenarios.items(), start=1):
            res = TestExecutionResult(
                test_execution_id=execution.id,
                test_name=f"{tc_id}: {s_data['name']}",
                category=s_data['category'],
                status='Passed' if idx != 11 else 'Failed',
                duration=round(8.5 + (idx * 0.3), 2),
                actual_result=s_data['expected'] if idx != 11 else 'Form submitted but returned HTTP 500 error on malformed email.',
                error_message='Assertion failed: expected HTTP 400 validation error, received HTTP 500.' if idx == 11 else None,
                executed_at=datetime.utcnow() - timedelta(minutes=44)
            )
            db.session.add(res)
        db.session.commit()

        # 10. Seed Initial Threshold Analysis
        th_analysis = ThresholdAnalysis(
            project_id=project.id,
            image_comparison_id=comparison.id,
            test_execution_id=execution.id,
            visual_status='REVIEW',
            visual_score=round(metrics_data['pixel_similarity'], 1),
            functional_status='PASS',
            functional_score=93.3,
            security_status='REVIEW',
            security_score=85.0,
            overall_status='REVIEW',
            overall_score=89.8,
            violations_json='["Visual changed regions (2) at allowable limit", "2 Medium security headers absent on portal root"]',
            details_json='{"status": "REVIEW", "recommendation": "Inspect visual defect bounding boxes and apply security headers."}',
            analyzed_at=datetime.utcnow() - timedelta(minutes=30)
        )
        db.session.add(th_analysis)
        db.session.commit()

        # 11. Initial Activity Logs
        activity_entries = [
            ActivityLog(user_id=admin.id, project_id=project.id, action='System Initialization', description='Platform initialized with enterprise test baseline.'),
            ActivityLog(user_id=admin.id, project_id=project.id, action='Create Project', description=f"Initialized project '{project.name}'."),
            ActivityLog(user_id=tester.id, project_id=project.id, action='Create Test Plan', description=f"Created test plan '{plan.name}'."),
            ActivityLog(user_id=tester.id, project_id=project.id, action='Image Comparison Run', description='Ran initial visual regression comparison on student dashboard.'),
            ActivityLog(user_id=tester.id, project_id=project.id, action='Security Baseline Scan', description='Audited HTTP security headers and cookies.'),
            ActivityLog(user_id=tester.id, project_id=project.id, action='Run Automated Tests', description='Executed full 15-scenario regression suite.')
        ]
        db.session.add_all(activity_entries)
        db.session.commit()

        print("[Seed] Demo database seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
