import numpy as np
from skimage.metrics import structural_similarity as ssim
from typing import Tuple, Dict, Any

class SSIMAnalyzer:
    """Calculates Structural Similarity Index (SSIM) and difference maps using scikit-image."""

    @staticmethod
    def analyze(ref_gray: np.ndarray, act_gray: np.ndarray) -> Tuple[float, np.ndarray, Dict[str, Any]]:
        """
        Calculates SSIM score between reference and actual grayscale images.
        
        Returns:
            score: SSIM value in range [-1.0, 1.0]
            diff_map_uint8: Visual 8-bit difference map (0-255)
            metrics: Dictionary of SSIM metrics
        """
        assert ref_gray.shape == act_gray.shape, "Images must have identical dimensions for SSIM"

        # Calculate SSIM with full difference map
        score, diff_map = ssim(ref_gray, act_gray, full=True, data_range=255)

        # diff_map has values in [-1, 1], where 1 is identical.
        # Convert to uint8 where 255 = identical, 0 = completely inverted:
        # Or more intuitively for difference: (1.0 - diff) * 255
        diff_inverted = ((1.0 - diff_map) / 2.0) * 255.0
        diff_map_uint8 = np.clip(diff_inverted, 0, 255).astype(np.uint8)

        # Structural similarity percentage: map [-1, 1] to [0%, 100%]
        # For standard images, score is usually between 0 and 1
        ssim_pct = max(0.0, min(100.0, float(score) * 100.0))

        metrics = {
            'ssim_score': round(float(score), 4),
            'structural_similarity_pct': round(ssim_pct, 2)
        }

        return float(score), diff_map_uint8, metrics
