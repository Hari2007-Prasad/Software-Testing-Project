import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user

from extensions import db
from models import Project, TestPlan, TestCase, TestExecution, SecurityFinding, ImageComparison, ThresholdAnalysis
from modules.reporting.pdf_report import PDFReportGenerator
from modules.reporting.excel_report import ExcelReportGenerator
from utils import tester_required, log_activity

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
@tester_required
def index():
    projects = Project.query.filter_by(status='Active').all()
    reports_dir = os.path.join(current_app.root_path, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    # List generated reports on disk
    report_files = []
    for f in os.listdir(reports_dir):
        if f.endswith('.pdf') or f.endswith('.xlsx'):
            f_path = os.path.join(reports_dir, f)
            size_kb = round(os.path.getsize(f_path) / 1024, 1)
            mtime = os.path.getmtime(f_path)
            report_files.append({
                'filename': f,
                'type': 'PDF' if f.endswith('.pdf') else 'Excel',
                'size': f"{size_kb} KB",
                'mtime': mtime
            })
    report_files.sort(key=lambda x: x['mtime'], reverse=True)

    return render_template('reports/index.html', projects=projects, reports=report_files)

@reports_bp.route('/generate-pdf/<int:project_id>', methods=['POST'])
@login_required
@tester_required
def generate_pdf(project_id):
    project = Project.query.get_or_404(project_id)
    reports_dir = os.path.join(current_app.root_path, 'reports')
    uploads_dir = os.path.join(current_app.root_path, 'uploads')

    test_plans = project.test_plans.all()
    test_cases = TestCase.query.join(TestPlan).filter(TestPlan.project_id == project.id).all()
    executions = project.test_executions.order_by(TestExecution.start_time.desc()).all()
    findings = project.security_findings.order_by(SecurityFinding.discovered_at.desc()).all()
    comparisons = project.image_comparisons.order_by(ImageComparison.created_at.desc()).all()
    analyses = project.threshold_analyses.order_by(ThresholdAnalysis.analyzed_at.desc()).all()

    try:
        generator = PDFReportGenerator(output_dir=reports_dir)
        filename = generator.generate(
            project=project,
            test_plans=test_plans,
            test_cases=test_cases,
            executions=executions,
            findings=findings,
            comparisons=comparisons,
            analyses=analyses,
            uploads_dir=uploads_dir
        )
        log_activity(action='Generate PDF Report', description=f"Exported PDF audit report for project '{project.name}'.", project_id=project.id)
        flash(f"PDF Report '{filename}' successfully generated!", 'success')
        return redirect(url_for('reports.download', filename=filename))
    except Exception as e:
        flash(f"Error generating PDF report: {str(e)}", 'danger')
        return redirect(url_for('reports.index'))

@reports_bp.route('/generate-excel/<int:project_id>', methods=['POST'])
@login_required
@tester_required
def generate_excel(project_id):
    project = Project.query.get_or_404(project_id)
    reports_dir = os.path.join(current_app.root_path, 'reports')

    test_cases = TestCase.query.join(TestPlan).filter(TestPlan.project_id == project.id).all()
    executions = project.test_executions.order_by(TestExecution.start_time.desc()).all()
    findings = project.security_findings.order_by(SecurityFinding.discovered_at.desc()).all()
    comparisons = project.image_comparisons.order_by(ImageComparison.created_at.desc()).all()
    analyses = project.threshold_analyses.order_by(ThresholdAnalysis.analyzed_at.desc()).all()

    try:
        generator = ExcelReportGenerator(output_dir=reports_dir)
        filename = generator.generate(
            project=project,
            test_cases=test_cases,
            executions=executions,
            findings=findings,
            comparisons=comparisons,
            analyses=analyses
        )
        log_activity(action='Generate Excel Report', description=f"Exported Excel workbook for project '{project.name}'.", project_id=project.id)
        flash(f"Excel Report '{filename}' successfully generated!", 'success')
        return redirect(url_for('reports.download', filename=filename))
    except Exception as e:
        flash(f"Error generating Excel report: {str(e)}", 'danger')
        return redirect(url_for('reports.index'))

@reports_bp.route('/download/<filename>')
@login_required
@tester_required
def download(filename):
    reports_dir = os.path.join(current_app.root_path, 'reports')
    return send_from_directory(reports_dir, filename, as_attachment=True)
