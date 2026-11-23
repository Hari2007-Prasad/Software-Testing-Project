import cv2
import numpy as np
from typing import Tuple, Dict, Any

class PixelComparator:
    """Computes exact pixel-level differences, binary difference masks, and similarity scores."""

    @staticmethod
    def compare(
        ref_gray: np.ndarray,
        act_gray: np.ndarray,
        intensity_threshold: int = 25,
        noise_filter_level: int = 1
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Calculates pixel difference using cv2.absdiff and threshold filtering.
        
        Args:
            ref_gray: Reference grayscale image
            act_gray: Actual grayscale image
            intensity_threshold: Minimum intensity difference to consider a pixel changed (1-255)
            noise_filter_level: 0=none, 1=mild 3x3 opening, 2=stronger 5x5 opening
            
        Returns:
            diff_image: Grayscale absolute difference
            diff_mask: Binary threshold mask (0 or 255)
            metrics: Dictionary of pixel similarity metrics
        """
        # Ensure identical shape
        assert ref_gray.shape == act_gray.shape, "Images must have identical dimensions for pixel diff"

        h, w = ref_gray.shape[:2]
        total_pixels = h * w

        # OpenCV absdiff
        diff_image = cv2.absdiff(ref_gray, act_gray)

        # Thresholding to binary mask
        _, diff_mask = cv2.threshold(diff_image, intensity_threshold, 255, cv2.THRESH_BINARY)

        # Optional noise filtering to prevent sub-pixel font anti-aliasing from counting as defects
        if noise_filter_level > 0:
            k_size = 3 if noise_filter_level == 1 else 5
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
            diff_mask = cv2.morphologyEx(diff_mask, cv2.MORPH_OPEN, kernel)

        # Count changed pixels
        changed_pixels = int(cv2.countNonZero(diff_mask))

        # Calculate exact percentages per project formula:
        # Difference Percentage = (Changed Pixels / Total Pixels) * 100
        # Pixel Similarity = 100 - Difference Percentage
        if total_pixels > 0:
            diff_percentage = (changed_pixels / total_pixels) * 100.0
        else:
            diff_percentage = 0.0

        diff_percentage = min(100.0, max(0.0, diff_percentage))
        pixel_similarity = max(0.0, 100.0 - diff_percentage)

        metrics = {
            'total_pixels': total_pixels,
            'changed_pixels': changed_pixels,
            'difference_percentage': round(diff_percentage, 4),
            'pixel_similarity': round(pixel_similarity, 4),
            'intensity_threshold': intensity_threshold,
            'noise_filter_level': noise_filter_level
        }

        return diff_image, diff_mask, metrics
