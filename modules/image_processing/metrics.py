from typing import Dict, Any, List

class ImageMetrics:
    """Aggregates, validates, and packages visual comparison metrics."""

    @staticmethod
    def aggregate_metrics(
        pixel_metrics: Dict[str, Any],
        ssim_metrics: Dict[str, Any],
        edge_metrics: Dict[str, Any],
        regions: List[Dict[str, Any]],
        duration_sec: float,
        alignment_applied: bool,
        alignment_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Consolidates all visual regression testing metrics into a standardized report structure."""
        diff_pct = pixel_metrics.get('difference_percentage', 0.0)
        pixel_sim = pixel_metrics.get('pixel_similarity', 100.0)
        ssim_val = ssim_metrics.get('ssim_score', 1.0)
        ssim_pct = ssim_metrics.get('structural_similarity_pct', 100.0)
        region_count = len(regions)

        # Baseline evaluation (can be overridden by project threshold analyzer)
        if diff_pct == 0.0 and ssim_val >= 0.999:
            status = 'MATCH'
        elif diff_pct <= 2.0 and ssim_val >= 0.92:
            status = 'MINOR_DIFFERENCE'
        elif diff_pct <= 10.0:
            status = 'MODERATE_DIFFERENCE'
        else:
            status = 'MAJOR_DIFFERENCE'

        return {
            'pixel_similarity': pixel_sim,
            'difference_percentage': diff_pct,
            'changed_pixels': pixel_metrics.get('changed_pixels', 0),
            'total_pixels': pixel_metrics.get('total_pixels', 0),
            'ssim_score': ssim_val,
            'structural_similarity_pct': ssim_pct,
            'edge_similarity_pct': edge_metrics.get('edge_similarity_pct', 100.0),
            'changed_regions_count': region_count,
            'regions': regions,
            'processing_duration': round(duration_sec, 4),
            'alignment_applied': alignment_applied,
            'alignment_info': alignment_info,
            'status': status
        }
