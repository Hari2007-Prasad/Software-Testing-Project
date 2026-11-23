import cv2
import numpy as np
import json
from typing import Tuple, Dict, Any, Optional

class ImageAligner:
    """Feature-based image registration with strict safety bounds to prevent masking layout shifts."""

    @staticmethod
    def align_images(
        ref_gray: np.ndarray,
        act_bgr: np.ndarray,
        act_gray: np.ndarray,
        max_features: int = 1500,
        good_match_ratio: float = 0.75,
        max_translation_px: float = 50.0,
        max_rotation_deg: float = 5.0
    ) -> Tuple[np.ndarray, np.ndarray, bool, Dict[str, Any]]:
        """
        Attempts feature matching (ORB) and controlled partial affine alignment.
        Rejects extreme transforms to prevent masking genuine layout alterations.
        Returns:
            aligned_bgr: aligned actual color image
            aligned_gray: aligned actual gray image
            alignment_applied: boolean
            transform_info: metadata dict
        """
        transform_info = {
            'attempted': True,
            'applied': False,
            'keypoints_ref': 0,
            'keypoints_act': 0,
            'matches_found': 0,
            'reason': 'No alignment necessary'
        }

        try:
            orb = cv2.ORB_create(nfeatures=max_features)
            kp1, des1 = orb.detectAndCompute(ref_gray, None)
            kp2, des2 = orb.detectAndCompute(act_gray, None)

            transform_info['keypoints_ref'] = len(kp1) if kp1 else 0
            transform_info['keypoints_act'] = len(kp2) if kp2 else 0

            if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
                transform_info['reason'] = 'Insufficient features for registration'
                return act_bgr, act_gray, False, transform_info

            # Match descriptors using Brute-Force Matcher with Hamming distance
            matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = matcher.knnMatch(des1, des2, k=2)

            # Apply Lowe's ratio test
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < good_match_ratio * n.distance:
                        good_matches.append(m)

            transform_info['matches_found'] = len(good_matches)

            if len(good_matches) < 8:
                transform_info['reason'] = 'Insufficient robust matches (< 8)'
                return act_bgr, act_gray, False, transform_info

            # Extract location of good matches
            pts_ref = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            pts_act = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

            # Estimate partial affine matrix (translation, rotation, uniform scale)
            matrix, inliers = cv2.estimateAffinePartial2D(pts_act, pts_ref, method=cv2.RANSAC, ransacReprojThreshold=3.0)

            if matrix is None:
                transform_info['reason'] = 'Could not estimate stable affine transformation'
                return act_bgr, act_gray, False, transform_info

            # Analyze transformation bounds to avoid warping UI structure
            dx = matrix[0, 2]
            dy = matrix[1, 2]
            scale = np.sqrt(matrix[0, 0]**2 + matrix[1, 0]**2)
            angle = np.degrees(np.arctan2(matrix[1, 0], matrix[0, 0]))

            transform_info['translation_x'] = float(dx)
            transform_info['translation_y'] = float(dy)
            transform_info['scale'] = float(scale)
            transform_info['rotation_deg'] = float(angle)

            # Reject drastic shifts (likely actual UI changes rather than camera/rendering jitter)
            if abs(dx) > max_translation_px or abs(dy) > max_translation_px:
                transform_info['reason'] = f'Translation exceeds safety limit: dx={dx:.1f}, dy={dy:.1f}'
                return act_bgr, act_gray, False, transform_info

            if abs(angle) > max_rotation_deg:
                transform_info['reason'] = f'Rotation exceeds safety limit: {angle:.1f} deg'
                return act_bgr, act_gray, False, transform_info

            if abs(scale - 1.0) > 0.08:
                transform_info['reason'] = f'Scale distortion exceeds safety limit: {scale:.2f}'
                return act_bgr, act_gray, False, transform_info

            # Apply warpAffine to actual image
            h, w = ref_gray.shape[:2]
            aligned_bgr = cv2.warpAffine(act_bgr, matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)
            aligned_gray = cv2.warpAffine(act_gray, matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)

            transform_info['applied'] = True
            transform_info['reason'] = 'Alignment applied successfully within safety bounds'
            transform_info['matrix'] = matrix.tolist()

            return aligned_bgr, aligned_gray, True, transform_info

        except Exception as e:
            transform_info['reason'] = f'Alignment error: {str(e)}'
            return act_bgr, act_gray, False, transform_info
