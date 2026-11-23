import os
import pytest
from types import SimpleNamespace
from datetime import datetime

from modules.security_testing.scanner import SecurityBaselineScanner
from modules.reporting.excel_report import ExcelReportGenerator
from modules.reporting.pdf_report import PDFReportGenerator

def test_security_scanner_checks():
    """Test safe baseline security scanner checks structure."""
    scanner = SecurityBaselineScanner(target_base_url='http://127.0.0.1:5000/lms')
    transport_findings = scanner._check_transport_protocol()
    assert len(transport_findings) == 1
    assert transport_findings[0]['title'] == 'Unencrypted HTTP Transport In Use'

def test_pdf_report_generation(tmp_path):
    """Test PDF report generation produces a valid non-empty PDF file."""
    proj = SimpleNamespace(id=1, name='Demo Project', app_url='http://127.0.0.1:5000/lms', environment='Staging', project_type='LMS', status='Active')
    generator = PDFReportGenerator(output_dir=str(tmp_path))
    pdf_filename = generator.generate(
        project=proj,
        test_plans=[],
        test_cases=[],
        executions=[],
        findings=[],
        comparisons=[],
        analyses=[],
        uploads_dir=str(tmp_path)
    )
    assert pdf_filename.endswith('.pdf')
    target = os.path.join(str(tmp_path), pdf_filename)
    assert os.path.exists(target)
    assert os.path.getsize(target) > 1000

def test_excel_report_generation(tmp_path):
    """Test Excel report generation produces a valid workbook."""
    proj = SimpleNamespace(id=1, name='Demo Project', app_url='http://127.0.0.1:5000/lms', environment='Staging', project_type='LMS', status='Active')
    generator = ExcelReportGenerator(output_dir=str(tmp_path))
    xl_filename = generator.generate(
        project=proj,
        test_cases=[],
        executions=[],
        findings=[],
        comparisons=[],
        analyses=[]
    )
    assert xl_filename.endswith('.xlsx')
    target = os.path.join(str(tmp_path), xl_filename)
    assert os.path.exists(target)
    assert os.path.getsize(target) > 1000
