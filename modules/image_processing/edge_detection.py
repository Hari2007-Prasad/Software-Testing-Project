import cv2
import numpy as np
from typing import Tuple, Dict, Any

class EdgeDetector:
    """Canny edge detection and edge-based structural difference evaluation."""

    @staticmethod
    def detect_and_compare(
        ref_gray: np.ndarray,
        act_gray: np.ndarray,
        lower_threshold: int = 50,
        upper_threshold: int = 150
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Extracts Canny edges and creates a composite visualization of structural differences.
        
        Returns:
            ref_edges: Binary edge map of reference
            act_edges: Binary edge map of actual
            edge_diff_vis: 3-channel BGR visualization showing:
                           - Green: Matching edges
                           - Red: Added/changed edges in actual
                           - Blue: Missing edges from reference
            metrics: Edge similarity metrics
        """
        assert ref_gray.shape == act_gray.shape, "Images must have identical dimensions for edge detection"

        ref_edges = cv2.Canny(ref_gray, lower_threshold, upper_threshold)
        act_edges = cv2.Canny(act_gray, lower_threshold, upper_threshold)

        h, w = ref_gray.shape[:2]
        edge_diff_vis = np.zeros((h, w, 3), dtype=np.uint8)

        # Matching edges: both ref and act have edge -> Green
        matching = cv2.bitwise_and(ref_edges, act_edges)
        edge_diff_vis[matching > 0] = [46, 204, 113]  # Soft Green (BGR)

        # Added edges in actual (not in ref) -> Red
        added = cv2.bitwise_and(act_edges, cv2.bitwise_not(ref_edges))
        edge_diff_vis[added > 0] = [60, 60, 235]  # Soft Red (BGR)

        # Missing edges (in ref, but missing in actual) -> Cyan / Blue
        missing = cv2.bitwise_and(ref_edges, cv2.bitwise_not(act_edges))
        edge_diff_vis[missing > 0] = [235, 160, 52]  # Soft Blue/Amber (BGR)

        total_ref_edge_pixels = int(cv2.countNonZero(ref_edges))
        matching_edge_pixels = int(cv2.countNonZero(matching))
        added_edge_pixels = int(cv2.countNonZero(added))
        missing_edge_pixels = int(cv2.countNonZero(missing))

        edge_similarity = 100.0
        if total_ref_edge_pixels > 0:
            edge_similarity = (matching_edge_pixels / total_ref_edge_pixels) * 100.0
            edge_similarity = min(100.0, max(0.0, edge_similarity))

        metrics = {
            'edge_similarity_pct': round(edge_similarity, 2),
            'ref_edge_pixels': total_ref_edge_pixels,
            'matching_edge_pixels': matching_edge_pixels,
            'added_edge_pixels': added_edge_pixels,
            'missing_edge_pixels': missing_edge_pixels,
            'lower_threshold': lower_threshold,
            'upper_threshold': upper_threshold
        }

        return ref_edges, act_edges, edge_diff_vis, metrics
