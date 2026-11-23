import os
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import Project, ImageComparison, ImageMetric, ThresholdConfiguration, ThresholdAnalysis
from modules.image_processing.engine import ImageComparisonEngine
from modules.image_processing.validator import ImageValidator
from modules.threshold_analysis.analyzer import ThresholdAnalyzer
from utils import tester_required, log_activity

image_comparison_bp = Blueprint('image_comparison', __name__, url_prefix='/image-comparison')

@image_comparison_bp.route('/')
@login_required
@tester_required
def index():
    project_id = request.args.get('project_id', type=int)
    projects = Project.query.filter_by(status='Active').all()

    query = ImageComparison.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    comparisons = query.order_by(ImageComparison.created_at.desc()).all()

    return render_template(
        'image_comparison/index.html',
        comparisons=comparisons,
        projects=projects,
        selected_project_id=project_id
    )

@image_comparison_bp.route('/workspace', methods=['GET', 'POST'])
@login_required
@tester_required
def workspace():
    projects = Project.query.filter_by(status='Active').all()

    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        name = request.form.get('name', '').strip()
        intensity_threshold = int(request.form.get('intensity_threshold', 25))
        min_region_size = int(request.form.get('min_region_size', 25))
        noise_filter_level = int(request.form.get('noise_filter_level', 1))
        enable_alignment = bool(request.form.get('enable_alignment'))
        lower_edge_thresh = int(request.form.get('lower_edge_thresh', 50))
        upper_edge_thresh = int(request.form.get('upper_edge_thresh', 150))

        if not project_id or not name:
            flash('Project and Comparison Name are mandatory.', 'warning')
            return render_template('image_comparison/workspace.html', projects=projects)

        if 'reference_image' not in request.files or 'actual_image' not in request.files:
            flash('Both Reference and Actual screenshots must be uploaded.', 'warning')
            return render_template('image_comparison/workspace.html', projects=projects)

        ref_file = request.files['reference_image']
        act_file = request.files['actual_image']

        if not ref_file.filename or not act_file.filename:
            flash('Please select files for both reference and actual images.', 'warning')
            return render_template('image_comparison/workspace.html', projects=projects)

        # Validate file extensions
        if not ImageValidator.is_allowed_file(ref_file.filename) or not ImageValidator.is_allowed_file(act_file.filename):
            flash('Invalid file extension. Only PNG, JPG, and JPEG files are supported.', 'danger')
            return render_template('image_comparison/workspace.html', projects=projects)

        ref_dir = os.path.join(current_app.root_path, 'uploads', 'reference')
        act_dir = os.path.join(current_app.root_path, 'uploads', 'actual')
        proc_dir = os.path.join(current_app.root_path, 'uploads', 'processed')

        os.makedirs(ref_dir, exist_ok=True)
        os.makedirs(act_dir, exist_ok=True)
        os.makedirs(proc_dir, exist_ok=True)

        ref_filename = ImageValidator.generate_safe_filename(ref_file.filename, prefix='ref')
        act_filename = ImageValidator.generate_safe_filename(act_file.filename, prefix='act')

        ref_abs_path = os.path.join(ref_dir, ref_filename)
        act_abs_path = os.path.join(act_dir, act_filename)

        ref_file.save(ref_abs_path)
        act_file.save(act_abs_path)

        # Run Image Comparison Engine
        try:
            engine = ImageComparisonEngine(processed_dir=proc_dir)
            result = engine.run_comparison(
                ref_path=ref_abs_path,
                act_path=act_abs_path,
                intensity_threshold=intensity_threshold,
                min_region_size=min_region_size,
                noise_filter_level=noise_filter_level,
                enable_alignment=enable_alignment,
                lower_edge_thresh=lower_edge_thresh,
                upper_edge_thresh=upper_edge_thresh
            )

            metrics_data = result['metrics']
            paths = result['paths']

            # Create Database Record
            comparison = ImageComparison(
                project_id=project_id,
                name=name,
                reference_path=ref_filename,
                actual_path=act_filename,
                diff_image_path=paths['diff_image'],
                mask_path=paths['mask'],
                overlay_path=paths['overlay'],
                bbox_path=paths['bbox'],
                edge_path=paths['edge'],
                config_json=json.dumps(result['config']),
                status='Completed',
                created_by_id=current_user.id
            )
            db.session.add(comparison)
            db.session.flush()

            metric_record = ImageMetric(
                image_comparison_id=comparison.id,
                pixel_similarity=metrics_data['pixel_similarity'],
                difference_percentage=metrics_data['difference_percentage'],
                changed_pixels=metrics_data['changed_pixels'],
                total_pixels=metrics_data['total_pixels'],
                ssim_score=metrics_data['ssim_score'],
                structural_similarity_pct=metrics_data['structural_similarity_pct'],
                changed_regions_count=metrics_data['changed_regions_count'],
                regions_data=json.dumps(metrics_data['regions']),
                processing_duration=metrics_data['processing_duration'],
                alignment_applied=metrics_data['alignment_applied'],
                transform_matrix_json=json.dumps(metrics_data['alignment_info'])
            )
            db.session.add(metric_record)

            # Automatically run Threshold Analysis against project policy
            threshold_cfg = ThresholdConfiguration.query.filter_by(project_id=project_id, is_active=True).first()
            if threshold_cfg:
                th_eval = ThresholdAnalyzer.evaluate_visual_metrics(metrics_data, threshold_cfg.to_dict())
                analysis = ThresholdAnalysis(
                    project_id=project_id,
                    image_comparison_id=comparison.id,
                    visual_status=th_eval['status'],
                    visual_score=th_eval['score'],
                    overall_status=th_eval['status'],
                    overall_score=th_eval['score'],
                    violations_json=json.dumps(th_eval['violations']),
                    details_json=json.dumps(th_eval['details'])
                )
                db.session.add(analysis)

            db.session.commit()

            log_activity(
                action='Image Comparison Run',
                description=f"Compared '{name}': Sim={metrics_data['pixel_similarity']}%, SSIM={metrics_data['ssim_score']}, Regions={metrics_data['changed_regions_count']}.",
                project_id=project_id
            )
            flash(f"Image comparison '{name}' completed successfully in {metrics_data['processing_duration']:.2f}s!", 'success')
            return redirect(url_for('image_comparison.results', comparison_id=comparison.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Computer Vision Comparison Failed: {str(e)}", 'danger')

    return render_template('image_comparison/workspace.html', projects=projects)

@image_comparison_bp.route('/results/<int:comparison_id>')
@login_required
@tester_required
def results(comparison_id):
    comparison = ImageComparison.query.get_or_404(comparison_id)
    metric = comparison.metric
    regions = json.loads(metric.regions_data) if (metric and metric.regions_data) else []
    config = json.loads(comparison.config_json) if comparison.config_json else {}
    analysis = comparison.threshold_analyses.first()

    return render_template(
        'image_comparison/results.html',
        comparison=comparison,
        metric=metric,
        regions=regions,
        config=config,
        analysis=analysis
    )

@image_comparison_bp.route('/history')
@login_required
@tester_required
def history():
    comparisons = ImageComparison.query.order_by(ImageComparison.created_at.desc()).all()
    return render_template('image_comparison/history.html', comparisons=comparisons)

@image_comparison_bp.route('/view-image/<folder>/<filename>')
@login_required
def view_image(folder, filename):
    """Securely serves image files from uploads directories."""
    allowed_folders = {'reference', 'actual', 'processed', 'evidence'}
    if folder not in allowed_folders:
        flash("Invalid image category.", "danger")
        return redirect(url_for('dashboard.index'))

    safe_folder = os.path.join(current_app.root_path, 'uploads', folder)
    return send_from_directory(safe_folder, secure_filename(filename))
