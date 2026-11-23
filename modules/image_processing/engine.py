import os
import time
import uuid
import json
from typing import Dict, Any, Optional

from .validator import ImageValidator
from .preprocessing import ImagePreprocessor
from .alignment import ImageAligner
from .pixel_comparison import PixelComparator
from .ssim_analysis import SSIMAnalyzer
from .edge_detection import EdgeDetector
from .region_detection import RegionDetector
from .visualization import Visualizer
from .metrics import ImageMetrics

class ImageComparisonEngine:
    """
    Central Image Comparison Engine coordinating the complete CV visual regression pipeline.
    """

    def __init__(self, processed_dir: str):
        self.processed_dir = processed_dir
        os.makedirs(self.processed_dir, exist_ok=True)

    def run_comparison(
        self,
        ref_path: str,
        act_path: str,
        intensity_threshold: int = 25,
        min_region_size: int = 25,
        noise_filter_level: int = 1,
        enable_alignment: bool = False,
        lower_edge_thresh: int = 50,
        upper_edge_thresh: int = 150
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end computer-vision comparison pipeline:
        1. Validate reference and actual images.
        2. Preprocess & aspect-ratio-normalize images.
        3. Optional feature-based alignment (ORB).
        4. Absolute pixel difference & threshold filtering.
        5. Structural Similarity Analysis (SSIM).
        6. Canny edge detection & structural difference map.
        7. Morphological contour & region detection.
        8. Highlighting, bounding-box overlays, and montage visualization.
        9. Save all artifacts to disk and return metrics.
        """
        start_time = time.time()
        run_id = uuid.uuid4().hex[:10]

        # Stage 1: Validation
        ref_valid, ref_err, ref_meta = ImageValidator.validate_and_inspect(ref_path)
        if not ref_valid:
            raise ValueError(f"Reference image error: {ref_err}")

        act_valid, act_err, act_meta = ImageValidator.validate_and_inspect(act_path)
        if not act_valid:
            raise ValueError(f"Actual image error: {act_err}")

        # Stage 2: Preprocessing & Resolution Normalization
        ref_bgr = ImagePreprocessor.load_image(ref_path)
        act_bgr = ImagePreprocessor.load_image(act_path)

        if ref_bgr is None or act_bgr is None:
            raise RuntimeError("Failed to decode image data into NumPy array.")

        # Normalize resolution using aspect-ratio-preserving letterboxing
        ref_norm, act_norm, dimensions = ImagePreprocessor.normalize_resolution(ref_bgr, act_bgr)

        ref_gray = ImagePreprocessor.to_grayscale(ref_norm)
        act_gray = ImagePreprocessor.to_grayscale(act_norm)

        # Stage 3: Optional Alignment
        alignment_applied = False
        alignment_info = {'attempted': enable_alignment, 'applied': False}
        if enable_alignment:
            act_norm, act_gray, alignment_applied, alignment_info = ImageAligner.align_images(
                ref_gray, act_norm, act_gray
            )

        # Stage 4: Pixel-Level Difference
        diff_image, diff_mask, pixel_metrics = PixelComparator.compare(
            ref_gray, act_gray,
            intensity_threshold=intensity_threshold,
            noise_filter_level=noise_filter_level
        )

        # Stage 5: Structural Similarity Analysis (SSIM)
        ssim_score, ssim_diff_map, ssim_metrics = SSIMAnalyzer.analyze(ref_gray, act_gray)

        # Stage 6: Canny Edge Detection
        ref_edges, act_edges, edge_vis, edge_metrics = EdgeDetector.detect_and_compare(
            ref_gray, act_gray,
            lower_threshold=lower_edge_thresh,
            upper_threshold=upper_edge_thresh
        )

        # Stage 7: Region Detection & Contours
        regions, grouped_mask = RegionDetector.detect_regions(
            diff_mask,
            min_region_size=min_region_size
        )

        # Stage 8: Visual Artifact Generation
        overlay_bgr = Visualizer.create_diff_overlay(act_norm, diff_mask)
        bbox_bgr = Visualizer.create_bbox_visualization(act_norm, regions)
        montage_bgr = Visualizer.create_side_by_side_montage(ref_norm, act_norm, overlay_bgr)

        # Save all generated artifacts
        diff_filename = f"diff_{run_id}.png"
        mask_filename = f"mask_{run_id}.png"
        overlay_filename = f"overlay_{run_id}.png"
        bbox_filename = f"bbox_{run_id}.png"
        edge_filename = f"edge_{run_id}.png"
        montage_filename = f"montage_{run_id}.png"

        diff_path = os.path.join(self.processed_dir, diff_filename)
        mask_path = os.path.join(self.processed_dir, mask_filename)
        overlay_path = os.path.join(self.processed_dir, overlay_filename)
        bbox_path = os.path.join(self.processed_dir, bbox_filename)
        edge_path = os.path.join(self.processed_dir, edge_filename)
        montage_path = os.path.join(self.processed_dir, montage_filename)

        ImagePreprocessor.save_image(diff_path, diff_image)
        ImagePreprocessor.save_image(mask_path, diff_mask)
        ImagePreprocessor.save_image(overlay_path, overlay_bgr)
        ImagePreprocessor.save_image(bbox_path, bbox_bgr)
        ImagePreprocessor.save_image(edge_path, edge_vis)
        ImagePreprocessor.save_image(montage_path, montage_bgr)

        duration = time.time() - start_time

        # Stage 9: Consolidate Metrics
        metrics = ImageMetrics.aggregate_metrics(
            pixel_metrics=pixel_metrics,
            ssim_metrics=ssim_metrics,
            edge_metrics=edge_metrics,
            regions=regions,
            duration_sec=duration,
            alignment_applied=alignment_applied,
            alignment_info=alignment_info
        )

        return {
            'run_id': run_id,
            'dimensions': {'width': dimensions[0], 'height': dimensions[1]},
            'paths': {
                'diff_image': diff_filename,
                'mask': mask_filename,
                'overlay': overlay_filename,
                'bbox': bbox_filename,
                'edge': edge_filename,
                'montage': montage_filename
            },
            'metrics': metrics,
            'config': {
                'intensity_threshold': intensity_threshold,
                'min_region_size': min_region_size,
                'noise_filter_level': noise_filter_level,
                'enable_alignment': enable_alignment,
                'lower_edge_thresh': lower_edge_thresh,
                'upper_edge_thresh': upper_edge_thresh
            }
        }
