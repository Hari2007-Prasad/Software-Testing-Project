import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class ExcelReportGenerator:
    """
    Generates professional multi-sheet Excel reports (.xlsx) containing:
    1. Overview & Summary
    2. Test Cases Specification
    3. Automated Functional Execution Results
    4. Security Findings & Baseline Audit
    5. Image Comparison Metrics
    6. Threshold Acceptance Analysis
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, project, test_cases, executions, findings, comparisons, analyses) -> str:
        wb = Workbook()
        
        # Styles
        primary_header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid") # Dark Slate
        sub_header_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
        accent_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid") # Royal Blue
        pass_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # Light Green
        fail_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Light Red
        review_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid") # Light Yellow

        white_bold_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=16, bold=True, color="1E293B")
        bold_font = Font(name="Calibri", size=11, bold=True)
        regular_font = Font(name="Calibri", size=10)

        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        # -------------------------------------------------------------
        # SHEET 1: OVERVIEW & EXECUTIVE SUMMARY
        # -------------------------------------------------------------
        ws_overview = wb.active
        ws_overview.title = "Executive Summary"
        ws_overview.views.sheetView[0].showGridLines = True

        ws_overview.append(["SECURITY & FUNCTIONAL TESTING PLATFORM - PROJECT REPORT"])
        ws_overview["A1"].font = title_font
        ws_overview.append([])

        metadata_rows = [
            ["Project Name", project.name],
            ["Target Application URL", project.app_url],
            ["Environment", project.environment],
            ["Project Type", project.project_type],
            ["Status", project.status],
            ["Report Generated At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")]
        ]
        for row in metadata_rows:
            ws_overview.append(row)
            ws_overview.cell(row=ws_overview.max_row, column=1).font = bold_font
            ws_overview.cell(row=ws_overview.max_row, column=2).font = regular_font

        ws_overview.append([])
        ws_overview.append(["KEY TESTING METRICS"])
        ws_overview.cell(row=ws_overview.max_row, column=1).font = Font(size=13, bold=True, color="2563EB")

        metrics_headers = ["Metric Category", "Total Count", "Passed / Met", "Failed / Issues", "Success Rate / Score"]
        ws_overview.append(metrics_headers)
        for col_num in range(1, len(metrics_headers) + 1):
            cell = ws_overview.cell(row=ws_overview.max_row, column=col_num)
            cell.fill = primary_header_fill
            cell.font = white_bold_font
            cell.alignment = Alignment(horizontal="center")

        # Metric summary counts
        total_tc = len(test_cases)
        passed_tc = sum(1 for tc in test_cases if tc.execution_status == 'Passed')
        failed_tc = sum(1 for tc in test_cases if tc.execution_status == 'Failed')
        tc_rate = f"{(passed_tc / total_tc * 100):.1f}%" if total_tc > 0 else "N/A"

        total_exec = sum(e.total_tests for e in executions)
        passed_exec = sum(e.passed_tests for e in executions)
        failed_exec = sum(e.failed_tests for e in executions)
        exec_rate = f"{(passed_exec / total_exec * 100):.1f}%" if total_exec > 0 else "N/A"

        total_findings = len(findings)
        critical_findings = sum(1 for f in findings if f.severity.lower() == 'critical')
        high_findings = sum(1 for f in findings if f.severity.lower() == 'high')
        sec_issues = f"{critical_findings} Crit, {high_findings} High"

        total_img = len(comparisons)
        clean_img = sum(1 for c in comparisons if c.metric and c.metric.pixel_similarity >= 99.0)
        flagged_img = total_img - clean_img

        summary_rows = [
            ["Planned Test Cases", total_tc, passed_tc, failed_tc, tc_rate],
            ["Automated Test Runs", total_exec, passed_exec, failed_exec, exec_rate],
            ["Security Baseline Audit", total_findings, total_findings - (critical_findings + high_findings), sec_issues, "Evaluated"],
            ["Visual Image Comparisons", total_img, clean_img, flagged_img, f"{(clean_img/total_img*100):.1f}%" if total_img > 0 else "N/A"]
        ]
        for row in summary_rows:
            ws_overview.append(row)
            for c_idx in range(1, len(row) + 1):
                cell = ws_overview.cell(row=ws_overview.max_row, column=c_idx)
                cell.font = regular_font
                cell.border = thin_border
                if c_idx > 1:
                    cell.alignment = Alignment(horizontal="center")

        # -------------------------------------------------------------
        # SHEET 2: TEST CASES SPECIFICATION
        # -------------------------------------------------------------
        ws_tc = wb.create_sheet(title="Test Cases")
        tc_headers = ["Case ID", "Title", "Module", "Category", "Priority", "Severity", "Status", "Expected Result", "Actual Result"]
        ws_tc.append(tc_headers)
        for c in range(1, len(tc_headers) + 1):
            cell = ws_tc.cell(row=1, column=c)
            cell.fill = primary_header_fill
            cell.font = white_bold_font
            cell.alignment = Alignment(horizontal="center")

        for tc in test_cases:
            row_data = [
                tc.custom_id, tc.title, tc.module, tc.category, tc.priority, tc.severity,
                tc.execution_status, tc.expected_result, tc.actual_result or ''
            ]
            ws_tc.append(row_data)
            row_num = ws_tc.max_row
            for c in range(1, len(row_data) + 1):
                cell = ws_tc.cell(row=row_num, column=c)
                cell.font = regular_font
                cell.border = thin_border
                if c == 7: # Status
                    if tc.execution_status == 'Passed':
                        cell.fill = pass_fill
                    elif tc.execution_status == 'Failed':
                        cell.fill = fail_fill
                    elif tc.execution_status == 'Blocked':
                        cell.fill = review_fill

        # -------------------------------------------------------------
        # SHEET 3: FUNCTIONAL EXECUTION RESULTS
        # -------------------------------------------------------------
        ws_exec = wb.create_sheet(title="Functional Execution")
        exec_headers = ["Run ID", "Suite Name", "Execution Type", "Total Tests", "Passed", "Failed", "Blocked", "Duration (s)", "Timestamp"]
        ws_exec.append(exec_headers)
        for c in range(1, len(exec_headers) + 1):
            cell = ws_exec.cell(row=1, column=c)
            cell.fill = primary_header_fill
            cell.font = white_bold_font
            cell.alignment = Alignment(horizontal="center")

        for ex in executions:
            row_data = [
                ex.id, ex.test_suite_name, ex.execution_type, ex.total_tests, ex.passed_tests,
                ex.failed_tests, ex.blocked_tests, f"{ex.duration:.2f}",
                ex.start_time.strftime("%Y-%m-%d %H:%M") if ex.start_time else ''
            ]
            ws_exec.append(row_data)
            row_num = ws_exec.max_row
            for c in range(1, len(row_data) + 1):
                cell = ws_exec.cell(row=row_num, column=c)
                cell.font = regular_font
                cell.border = thin_border

        # -------------------------------------------------------------
        # SHEET 4: SECURITY FINDINGS
        # -------------------------------------------------------------
        ws_sec = wb.create_sheet(title="Security Findings")
        sec_headers = ["Finding Code", "Title", "Severity", "Affected URL", "Description", "Evidence", "Recommendation", "Status"]
        ws_sec.append(sec_headers)
        for c in range(1, len(sec_headers) + 1):
            cell = ws_sec.cell(row=1, column=c)
            cell.fill = primary_header_fill
            cell.font = white_bold_font
            cell.alignment = Alignment(horizontal="center")

        for f in findings:
            row_data = [
                f.finding_code, f.title, f.severity, f.affected_url,
                f.description, f.evidence or '', f.recommendation, f.status
            ]
            ws_sec.append(row_data)
            row_num = ws_sec.max_row
            for c in range(1, len(row_data) + 1):
                cell = ws_sec.cell(row=row_num, column=c)
                cell.font = regular_font
                cell.border = thin_border
                if c == 3: # Severity
                    if f.severity.lower() == 'critical':
                        cell.fill = fail_fill
                    elif f.severity.lower() == 'high':
                        cell.fill = fail_fill
                    elif f.severity.lower() == 'medium':
                        cell.fill = review_fill

        # -------------------------------------------------------------
        # SHEET 5: IMAGE COMPARISON METRICS
        # -------------------------------------------------------------
        ws_img = wb.create_sheet(title="Image Comparison Metrics")
        img_headers = ["Comparison ID", "Name", "Pixel Similarity %", "Difference %", "SSIM Score", "Changed Pixels", "Regions Detected", "Duration", "Status"]
        ws_img.append(img_headers)
        for c in range(1, len(img_headers) + 1):
            cell = ws_img.cell(row=1, column=c)
            cell.fill = primary_header_fill
            cell.font = white_bold_font
            cell.alignment = Alignment(horizontal="center")

        for cmp in comparisons:
            m = cmp.metric
            row_data = [
                cmp.id, cmp.name,
                f"{m.pixel_similarity:.2f}%" if m else 'N/A',
                f"{m.difference_percentage:.2f}%" if m else 'N/A',
                f"{m.ssim_score:.4f}" if m else 'N/A',
                m.changed_pixels if m else 0,
                m.changed_regions_count if m else 0,
                f"{m.processing_duration:.2f}s" if m else 'N/A',
                cmp.status
            ]
            ws_img.append(row_data)
            row_num = ws_img.max_row
            for c in range(1, len(row_data) + 1):
                cell = ws_img.cell(row=row_num, column=c)
                cell.font = regular_font
                cell.border = thin_border

        # -------------------------------------------------------------
        # SHEET 6: THRESHOLD ACCEPTANCE ANALYSIS
        # -------------------------------------------------------------
        ws_th = wb.create_sheet(title="Threshold Analysis")
        th_headers = ["Analysis ID", "Visual Status", "Visual Score", "Functional Status", "Functional Score", "Security Status", "Security Score", "Overall Status", "Overall Score", "Evaluated At"]
        ws_th.append(th_headers)
        for c in range(1, len(th_headers) + 1):
            cell = ws_th.cell(row=1, column=c)
            cell.fill = primary_header_fill
            cell.font = white_bold_font
            cell.alignment = Alignment(horizontal="center")

        for a in analyses:
            row_data = [
                a.id, a.visual_status, f"{a.visual_score:.1f}",
                a.functional_status, f"{a.functional_score:.1f}",
                a.security_status, f"{a.security_score:.1f}",
                a.overall_status, f"{a.overall_score:.1f}",
                a.analyzed_at.strftime("%Y-%m-%d %H:%M") if a.analyzed_at else ''
            ]
            ws_th.append(row_data)
            row_num = ws_th.max_row
            for c in range(1, len(row_data) + 1):
                cell = ws_th.cell(row=row_num, column=c)
                cell.font = regular_font
                cell.border = thin_border
                if c == 8: # Overall status
                    if a.overall_status == 'PASS':
                        cell.fill = pass_fill
                    elif a.overall_status == 'FAIL':
                        cell.fill = fail_fill
                    else:
                        cell.fill = review_fill

        # Auto-adjust column widths across all sheets
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or '')
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        filename = f"Project_Report_{project.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path = os.path.join(self.output_dir, filename)
        wb.save(file_path)
        return filename
