# Security and Functional Testing Framework for Digital Learning Applications

An enterprise-grade, centralized, web-based quality assurance and security baseline testing framework designed specifically for Digital Learning Applications (LMS). Built with Python Flask, SQLAlchemy, OpenCV, scikit-image, Selenium WebDriver, ReportLab, and openpyxl.

---

## 📌 Executive Summary

Digital learning platforms handle sensitive student credentials, academic records, and interactive course materials. Ensuring their visual stability across deployments, functional reliability, and baseline cybersecurity posture is critical.

This framework provides an end-to-end testing platform with **four dedicated primary modules**, automated reporting, an integrated target Digital Learning Platform (LMS), and real database-driven analytics. It operates without hardcoded placeholders or mock data—every test, scan, and metric is computed dynamically.

---

## 🏛️ System Architecture & Four Core Modules

```
+-----------------------------------------------------------------------------------------+
|                  Enterprise Web UI (Bootstrap 5, Chart.js, Vanilla JS)                   |
+-----------------------------------------------------------------------------------------+
                                             |
+-----------------------------------------------------------------------------------------+
|                         Flask Core & Role-Based Access Control                          |
|             (Admin / Lead QA / Tester / Security Auditor / Student Roles)               |
+-----------------------------------------------------------------------------------------+
     |                           |                            |                        |
     v                           v                            v                        v
+------------------+   +--------------------+   +-----------------------+   +------------------+
|   MODULE 1       |   |    MODULE 2        |   |      MODULE 3         |   |    MODULE 4      |
|  Test Planning   |   | Image Comparison   |   |   Automated Testing   |   |    Threshold     |
|   & Management   |   |      Engine        |   |     & Security        |   |     Analyzer     |
|                  |   |  (Computer Vision) |   | (Selenium + OWASP)    |   | (Decision Engine)|
+------------------+   +--------------------+   +-----------------------+   +------------------+
     |                           |                            |                        |
     |                           +-------------+--------------+                        |
     |                                         |                                       |
     v                                         v                                       v
+-----------------------------------------------------------------------------------------+
|                               Composite Quality Evaluator                               |
|        Decision: PASS / REVIEW REQUIRED / FAIL (Weighted Multi-Metric Quality Score)    |
+-----------------------------------------------------------------------------------------+
                                             |
             +-------------------------------+-------------------------------+
             v                                                               v
+----------------------------+                                 +---------------------------+
|    Executive PDF Reports   |                                 |    Excel Data Workbooks   |
|         (ReportLab)        |                                 |         (openpyxl)        |
+----------------------------+                                 +---------------------------+
```

### Module 1: Test Planning & Case Management
- **Project Hierarchy:** Multi-project workspace with staging, development, and production environments.
- **Test Plans:** Objectives, scope, strategy, entry/exit criteria, and milestone tracking.
- **Comprehensive Test Cases:** Categorized across Functional, Security, UI, Validation, Authentication, Authorization, and Image Comparison.
- **Execution Tracking:** Dynamic status updating (`Not Run`, `Passed`, `Failed`, `Blocked`, `Needs Review`), execution comments, duration, and defect linking.
- **Bulk Operations:** CSV test case import and Excel export.

### Module 2: Image Comparison Engine (Computer Vision Pipeline)
Implemented as modular, decoupled Python components under `modules/image_processing/`:
1. **Validator (`validator.py`):** MIME-type, dimension, format, and image header integrity checks.
2. **Preprocessing (`preprocessing.py`):** Grayscale conversion, aspect-ratio-preserving normalization with letterbox padding, and optional Gaussian denoising.
3. **Alignment (`alignment.py`):** Feature detection and homography estimation (ORB keypoints + RANSAC) to correct minor translations without hiding genuine layout changes.
4. **Pixel-Level Comparison (`pixel_comparison.py`):** OpenCV `absdiff` computing changed pixel count, difference percentage, and pixel similarity.
5. **Structural Similarity (`ssim_analysis.py`):** Multi-channel Structural Similarity Index (SSIM) via `scikit-image`, extracting perceptual difference maps.
6. **Edge Detection (`edge_detection.py`):** Canny edge detection comparing structural wireframe shifts.
7. **Region Detection (`region_detection.py`):** Morphological dilation, contour tracing, and bounding-box coordinates for detected UI defects.
8. **Visualization (`visualization.py`):** Side-by-side overlays, heatmaps, binary difference masks, and annotated bounding boxes (Red = Changed, Yellow = Review).
9. **Metrics (`metrics.py` & `engine.py`):** Consolidated calculation of visual similarity percentage, changed area, and execution time.

### Module 3: Automated Testing & Security Baseline
- **15 Selenium Functional Scenarios (`modules/automated_testing/scenarios.py`):**
  1. Homepage & navigation verification
  2. User registration workflow
  3. Valid student authentication
  4. Invalid login error handling
  5. Session logout
  6. Authenticated dashboard access
  7. Unauthorized access prevention (RBAC check)
  8. Course catalog listing
  9. Course syllabus details
  10. Course enrollment workflow
  11. Form validation & error indicators
  12. Required input fields validation
  13. Header & footer navigation links
  14. Profile information updates
  15. Administrative portal controls
- **Headless Chrome Automation:** Configurable timeouts, background execution runner with live thread status polling, step logs, and automatic failure screenshot capture.
- **OWASP Security Baseline Checks (`modules/security_testing/scanner.py`):**
  - **Security Headers:** Strict-Transport-Security (HSTS), Content-Security-Policy (CSP), X-Frame-Options (Clickjacking), X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
  - **Cookie Security:** Missing `HttpOnly`, missing `Secure`, missing `SameSite` flags.
  - **Authentication Hardening:** Brute-force rate limiting, password complexity enforcement, credential exposure in URL parameters.
  - **Canary Input Validation:** Safe parameter reflection checks for SQLi and XSS vulnerabilities.
  - **Risk Classification:** Critical, High, Medium, Low, and Informational severity levels with detailed remediation advice.

### Module 4: Threshold Analyzer & Quality Decision Engine
- **Configurable Threshold Profiles:** Tailored profiles (Strict, Standard, Permissive, Custom) based on deployment risk.
- **Multi-Metric Decision Matrix (`modules/threshold_analysis/analyzer.py`):**
  - Minimum SSIM structural threshold (e.g., 95.0%)
  - Maximum allowed pixel difference (e.g., 2.0%)
  - Maximum critical/high security vulnerability tolerance (typically 0)
  - Minimum functional pass rate (e.g., 95.0%)
- **Composite Quality Score:** Weighted composite formula evaluating Functional (40%), Visual (35%), and Security (25%) metrics.
- **Formal Status Output:** `PASS`, `REVIEW REQUIRED`, or `FAIL` with explicit failure reasons.

---

## 🎓 Integrated Target Application: EduLearn LMS

The framework includes an embedded, fully functional target Digital Learning Platform accessible at `/lms`:
- **Public Portal:** Responsive Landing page, About Us, Contact Us, and Course Catalog.
- **Student Authentication:** Registration, Login, Session Management, and Role separation.
- **Student Dashboard:** Enrolled courses, course progress tracking, and profile settings.
- **Course System:** Database-driven courses (Python for AI, Web Development Bootcamp, Cyber Defense, Cloud Architecture) with full syllabus details and interactive enrollment.
- **Admin Portal:** Course creation, student roster management, and enrollment statistics.
- **Testing Endpoints:** Built-in endpoints demonstrating proper security controls alongside configurable test cases for validation checks.

---

## 💻 Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Chart.js 4.4, Lucide Icons |
| **Backend** | Python 3.11 / 3.13, Flask 3.1, Flask-SQLAlchemy, Flask-Login, Flask-WTF |
| **Database** | SQLite (development) with SQLAlchemy ORM (PostgreSQL-ready schema) |
| **Computer Vision** | OpenCV (`opencv-python-headless` 4.10), NumPy, Pillow, scikit-image |
| **Automation** | Selenium 4.29+ with Chrome Headless Driver |
| **Reports** | ReportLab 4.4 (PDF) and openpyxl 3.1 (Excel) |
| **Testing** | pytest, pytest-cov |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.11 or later installed on your system.
- Google Chrome installed (for Selenium browser automation).

### 2. Setup Virtual Environment (Recommended)

```bash
# Clone or navigate to the project directory
cd "c:\Users\Dell\Desktop\Security Based ST"

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

> **Windows Application Control / WDAC Note:**  
> On machines with Windows Defender Application Control (WDAC) or strict AppLocker policies, invoke CLI tools via Python module syntax (e.g., `python -m pip` and `python -m pytest`) rather than running standalone `.exe` wrappers.

### 4. Initialize and Seed Database

Run the seed script to create all tables and populate realistic projects, LMS courses, test plans, 18 detailed test cases, threshold profiles, and execution history:

```bash
python seed.py
```

### 5. Launch the Framework

```bash
python app.py
```

The application will start at:
- **Framework Dashboard:** `http://127.0.0.1:5000`
- **Target LMS Application:** `http://127.0.0.1:5000/lms`

---

## 🔑 Demo Credentials

| Role | Username | Password | Purpose |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Full access: User management, threshold configuration, report generation, project administration. |
| **QA Tester** | `tester` | `tester123` | Test management: Create plans, execute automated tests, upload screenshots for visual diffing. |
| **Student** | `student` | `student123` | Target LMS account: Test course enrollment, profile editing, and student dashboard flows. |

---

## 🧪 Running Automated Unit & Integration Tests

The project includes an automated test suite verifying all 4 modules, image processing algorithms, security scanners, and reporting:

```bash
python -m pytest tests/ -v
```

### Test Coverage Highlights:
- **Module 1:** Project creation, editing, deletion, test plan creation, test case lifecycle, and execution status tracking.
- **Module 2:** Exact image match (100% SSIM), shifted element detection, background color change, layout modification, aspect ratio handling, bounding box generation, and noise tolerance.
- **Module 3:** Security scanner header checks, cookie attribute validation, canary input validation, and execution timeout handling.
- **Module 4:** Pass threshold evaluation, visual failure triggers, security failure triggers, and composite score calculation.
- **Reporting:** PDF report generation and multi-tab Excel export integrity.

---

## 📂 Project Directory Structure

```
Security Based ST/
│
├── app.py                      # Application factory and server entry point
├── config.py                   # Environment configuration (Dev, Test, Prod)
├── extensions.py               # Flask extensions (SQLAlchemy, LoginManager, CSRF)
├── models.py                   # Complete relational database models
├── utils.py                    # Role decorators, file validators, helper utilities
├── seed.py                     # Database seeder with realistic test data
├── requirements.txt            # Locked production dependencies
├── pytest.ini                  # Pytest configuration
├── README.md                   # Complete documentation
│
├── modules/                    # Four Primary Core Modules
│   ├── image_processing/       # Module 2: Computer Vision Visual Regression
│   │   ├── __init__.py
│   │   ├── validator.py        # Image format & header validation
│   │   ├── preprocessing.py    # Grayscale, resize with padding, denoising
│   │   ├── alignment.py        # ORB feature detection & homography alignment
│   │   ├── pixel_comparison.py # OpenCV absdiff pixel difference calculations
│   │   ├── ssim_analysis.py    # Structural similarity index map & score
│   │   ├── edge_detection.py   # Canny edge detection & wireframe difference
│   │   ├── region_detection.py # Morphological operations & bounding boxes
│   │   ├── visualization.py    # Difference overlays, heatmaps, annotations
│   │   ├── metrics.py          # Summary metrics calculations
│   │   └── engine.py           # Unified image processing orchestration service
│   │
│   ├── automated_testing/      # Module 3: Selenium Functional Automation
│   │   ├── __init__.py
│   │   ├── scenarios.py        # 15 real executable Selenium LMS test scenarios
│   │   └── runner.py           # Asynchronous execution thread runner & polling
│   │
│   ├── security_testing/       # Module 3 (Sec): Baseline Cybersecurity Scanner
│   │   ├── __init__.py
│   │   └── scanner.py          # OWASP headers, cookie flags, canary validation
│   │
│   ├── threshold_analysis/     # Module 4: Quality Gate Decision Engine
│   │   ├── __init__.py
│   │   └── analyzer.py         # Pass/Fail rules & composite scoring engine
│   │
│   └── reporting/              # Multi-Format Report Generation
│       ├── __init__.py
│       ├── pdf_report.py       # ReportLab PDF executive report builder
│       └── excel_report.py     # openpyxl multi-sheet Excel data export
│
├── routes/                     # Application Blueprints
│   ├── __init__.py
│   ├── auth.py                 # Login, register, logout, session handling
│   ├── dashboard.py            # Real-time metrics, Chart.js trend feeds
│   ├── projects.py             # Project CRUD and environment tracking
│   ├── test_planning.py        # Test plans, test cases, CSV/Excel import-export
│   ├── image_comparison.py     # Visual regression upload & execution workspace
│   ├── automated_testing.py    # Selenium test runner configuration & live polling
│   ├── security.py             # OWASP security scan runner & finding details
│   ├── thresholds.py           # Threshold profile configuration & audit
│   ├── reports.py              # PDF/Excel report generation & downloads
│   ├── history.py              # Consolidated audit trail & execution history
│   ├── users.py                # Admin user management & role assignment
│   ├── settings.py             # System settings & environment configuration
│   └── lms.py                  # Integrated Target EduLearn LMS application
│
├── templates/                  # Jinja2 Templates (Bootstrap 5.3 + Custom CSS)
│   ├── base.html               # Master layout with responsive dark navy sidebar
│   ├── auth/                   # Login & registration views
│   ├── dashboard/              # Executive analytics dashboard
│   ├── projects/               # Project listing, creation, and details
│   ├── test_planning/          # Plans, test cases, details, and forms
│   ├── image_comparison/       # Upload workspace, side-by-side results, history
│   ├── automated_testing/      # Launch modal, live terminal execution, results
│   ├── security/               # Scan launcher, vulnerability table, remediations
│   ├── thresholds/             # Threshold profiles and decision analyzer
│   ├── reports/                # Report generation and export hub
│   ├── history/                # Unified timeline and audit logs
│   ├── users/                  # User accounts table and role modal
│   ├── settings/               # System information and global parameters
│   └── lms/                    # Target LMS (Landing, Catalog, Dashboard, Admin)
│
├── static/                     # Static Assets
│   ├── css/
│   │   └── style.css           # Custom enterprise theme & component styling
│   └── js/                     # Client-side scripts
│
├── instance/                   # Runtime SQLite database
│   └── testing_framework.db
│
├── uploads/                    # Staged screenshots & diff outputs
│   ├── reference/
│   ├── actual/
│   └── processed/
│
├── reports/                    # Generated PDF & Excel deliverables
│
└── tests/                      # Automated Verification Test Suite
    ├── __init__.py
    ├── conftest.py             # Test fixtures & test DB setup
    └── test_all.py             # 23 comprehensive integration tests
```

---

## 📊 Live Metrics & Reporting Features

### Executive PDF Report Includes:
- System & Target Information, Execution Timestamps, Lead Tester details.
- Overall Compliance Status badge (`PASS`, `REVIEW REQUIRED`, or `FAIL`).
- Composite Quality Score bar chart and percentage breakdown.
- Visual Regression summary (SSIM, Pixel Similarity, Changed Pixels).
- Functional Automation breakdown (Pass/Fail count, execution duration).
- OWASP Security Findings table with vulnerability severities and remediations.

### Detailed Excel Export Includes:
- **Sheet 1:** Executive Summary & Overall Decision.
- **Sheet 2:** Functional Automation Test Case Results (Step-by-step logs).
- **Sheet 3:** Visual Regression Image Comparison Metrics.
- **Sheet 4:** Security Baseline Findings & OWASP Details.
- **Sheet 5:** Test Planning Cases (Categorized test inventory).

---

## 🔮 Future Enhancements

1. **AI-Driven Visual Flakiness Detection:** Machine learning classification to ignore dynamic content (e.g., timestamps, video carousels) without manual region masking.
2. **Distributed Cloud Execution:** Celery and Redis integration for distributed parallel Selenium workers across Docker containers.
3. **CI/CD Integration:** Official GitHub Actions and GitLab CI plugins to execute quality gates automatically upon pull request creation.
4. **Active DAST Scanner:** Integration with OWASP ZAP for automated active security penetration testing alongside the baseline scanner.
5. **PostgreSQL / Enterprise SSO:** SAML 2.0 and OAuth2 / OpenID Connect single sign-on integration for enterprise deployments.

---

## 📜 License & Academic Integrity

Developed for academic demonstration and enterprise QA automation. Free to use and extend for educational and professional testing purposes.
