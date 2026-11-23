import cv2
import numpy as np
from typing import List, Dict, Any, Tuple

class RegionDetector:
    """Detects coherent changed regions, contours, and bounding boxes from binary masks."""

    @staticmethod
    def detect_regions(
        diff_mask: np.ndarray,
        min_region_size: int = 25,
        dilation_iterations: int = 2
    ) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """
        Groups adjacent changed pixels into distinct defect/change regions using
        morphological dilation and contour analysis.

        Args:
            diff_mask: Binary difference mask (single channel, 0 or 255)
            min_region_size: Minimum bounding box area in pixels to be reported
            dilation_iterations: How much to dilate adjacent changed pixels to bridge gaps

        Returns:
            regions: List of dicts with region metadata:
                     [{id, x, y, width, height, area, severity, aspect_ratio}, ...]
            grouped_mask: Mask after morphological grouping
        """
        # Morphological dilation to bridge anti-aliasing gaps and button borders
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        grouped_mask = cv2.dilate(diff_mask, kernel, iterations=dilation_iterations)
        grouped_mask = cv2.morphologyEx(grouped_mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(grouped_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions = []
        region_id = 1

        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            x, y, w, h = cv2.boundingRect(cnt)
            bbox_area = w * h

            # Filter out tiny noise specks smaller than min_region_size
            if bbox_area < min_region_size and area < min_region_size:
                continue

            aspect_ratio = round(w / float(h), 2) if h > 0 else 1.0

            # Categorize visual impact based on bbox dimensions
            if bbox_area > 15000:
                severity = 'High'
            elif bbox_area > 3000:
                severity = 'Medium'
            else:
                severity = 'Low'

            regions.append({
                'id': region_id,
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
                'area': int(bbox_area),
                'contour_area': round(area, 1),
                'aspect_ratio': aspect_ratio,
                'severity': severity
            })
            region_id += 1

        # Sort regions by area descending (largest defects first)
        regions.sort(key=lambda r: r['area'], reverse=True)
        # Re-number IDs for clean presentation
        for idx, r in enumerate(regions, start=1):
            r['id'] = idx

        return regions, grouped_mask
