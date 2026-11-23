import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Project, SecurityFinding, ThresholdConfiguration, ThresholdAnalysis
from modules.security_testing.scanner import SecurityBaselineScanner
from modules.threshold_analysis.analyzer import ThresholdAnalyzer
from utils import tester_required, log_activity

security_bp = Blueprint('security', __name__, url_prefix='/security')

@security_bp.route('/')
@login_required
@tester_required
def index():
    project_id = request.args.get('project_id', type=int)
    severity_filter = request.args.get('severity', '').strip()
    status_filter = request.args.get('status', '').strip()
    projects = Project.query.filter_by(status='Active').all()

    query = SecurityFinding.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    if severity_filter:
        query = query.filter_by(severity=severity_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    findings = query.order_by(SecurityFinding.discovered_at.desc()).all()

    # Metrics
    total_findings = len(findings)
    critical_count = sum(1 for f in findings if f.severity.lower() == 'critical')
    high_count = sum(1 for f in findings if f.severity.lower() == 'high')
    medium_count = sum(1 for f in findings if f.severity.lower() == 'medium')
    low_count = sum(1 for f in findings if f.severity.lower() == 'low')
    info_count = sum(1 for f in findings if f.severity.lower() == 'info')

    stats = {
        'total': total_findings,
        'critical': critical_count,
        'high': high_count,
        'medium': medium_count,
        'low': low_count,
        'info': info_count
    }

    return render_template(
        'security/index.html',
        findings=findings,
        projects=projects,
        selected_project_id=project_id,
        severity_filter=severity_filter,
        status_filter=status_filter,
        stats=stats
    )

@security_bp.route('/scan', methods=['POST'])
@login_required
@tester_required
def run_scan():
    project_id = request.form.get('project_id', type=int)
    if not project_id:
        flash('Please select a project to scan.', 'warning')
        return redirect(url_for('security.index'))

    project = Project.query.get_or_404(project_id)
    target_url = request.form.get('target_url', project.app_url).strip() or project.app_url

    try:
        scanner = SecurityBaselineScanner(target_base_url=target_url, timeout=10)
        discovered_findings = scanner.run_all_checks()

        # Save findings to database
        saved_count = 0
        for item in discovered_findings:
            # Avoid duplicate findings by code & affected_url
            existing = SecurityFinding.query.filter_by(
                project_id=project.id,
                title=item['title'],
                affected_url=item['affected_url']
            ).first()

            if not existing:
                finding = SecurityFinding(
                    project_id=project.id,
                    finding_code=item['finding_code'],
                    title=item['title'],
                    description=item['description'],
                    severity=item['severity'],
                    affected_url=item['affected_url'],
                    evidence=item['evidence'],
                    recommendation=item['recommendation'],
                    status='Open',
                    discovered_at=datetime.utcnow()
                )
                db.session.add(finding)
                saved_count += 1

        db.session.commit()

        # Update or run Threshold Analysis for security
        threshold_cfg = ThresholdConfiguration.query.filter_by(project_id=project.id, is_active=True).first()
        if threshold_cfg:
            all_project_findings = [f.to_dict() for f in project.security_findings.all()]
            sec_eval = ThresholdAnalyzer.evaluate_security_metrics(all_project_findings, threshold_cfg.to_dict())
            analysis = ThresholdAnalysis(
                project_id=project.id,
                security_status=sec_eval['status'],
                security_score=sec_eval['score'],
                overall_status=sec_eval['status'],
                overall_score=sec_eval['score'],
                violations_json=json.dumps(sec_eval['violations']),
                details_json=json.dumps(sec_eval['details'])
            )
            db.session.add(analysis)
            db.session.commit()

        log_activity(
            action='Security Baseline Scan',
            description=f"Scanned {target_url} for project '{project.name}'. Discovered {len(discovered_findings)} baseline issues.",
            project_id=project.id
        )
        flash(f"Security baseline audit completed! {len(discovered_findings)} checks evaluated ({saved_count} new findings saved).", 'success')

    except Exception as e:
        db.session.rollback()
        flash(f"Security Audit error: {str(e)}", 'danger')

    return redirect(url_for('security.index', project_id=project.id))

@security_bp.route('/findings/<int:finding_id>')
@login_required
@tester_required
def finding_details(finding_id):
    finding = SecurityFinding.query.get_or_404(finding_id)
    return render_template('security/details.html', finding=finding)

@security_bp.route('/findings/<int:finding_id>/update-status', methods=['POST'])
@login_required
@tester_required
def update_status(finding_id):
    finding = SecurityFinding.query.get_or_404(finding_id)
    new_status = request.form.get('status', 'Open')
    if new_status in ('Open', 'Acknowledged', 'Resolved', 'False Positive'):
        finding.status = new_status
        db.session.commit()
        log_activity(action='Update Security Finding', description=f"Updated finding {finding.finding_code} status to '{new_status}'.", project_id=finding.project_id)
        flash(f"Finding {finding.finding_code} updated to '{new_status}'.", 'success')
    return redirect(url_for('security.finding_details', finding_id=finding.id))
