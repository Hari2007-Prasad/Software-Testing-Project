import cv2
import numpy as np
from typing import List, Dict, Any, Tuple

class Visualizer:
    """Generates visual artifacts: difference images, masks, overlays, and bounding boxes."""

    @staticmethod
    def create_diff_overlay(
        actual_bgr: np.ndarray,
        diff_mask: np.ndarray,
        alpha: float = 0.45
    ) -> np.ndarray:
        """
        Creates a semi-transparent highlighted overlay on the actual image.
        Changed pixels are colored bold red (#E53E3E / BGR [62, 62, 229]).
        """
        overlay = actual_bgr.copy()
        h, w = actual_bgr.shape[:2]

        # Red tint layer
        red_tint = np.zeros_like(actual_bgr)
        red_tint[:, :] = [40, 40, 235]  # Bold red in BGR

        # Where diff_mask is non-zero, blend red_tint with actual image
        mask_indices = diff_mask > 0
        if np.any(mask_indices):
            blended = cv2.addWeighted(actual_bgr, 1.0 - alpha, red_tint, alpha, 0)
            overlay[mask_indices] = blended[mask_indices]

        return overlay

    @staticmethod
    def create_bbox_visualization(
        actual_bgr: np.ndarray,
        regions: List[Dict[str, Any]],
        color_scheme: str = 'standard'
    ) -> np.ndarray:
        """
        Draws clear bounding boxes, badges, and region coordinates on the actual screenshot.
        Colors:
            Red [50, 50, 225] for High impact changes
            Yellow/Orange [30, 165, 245] for Medium
            Blue/Teal [230, 160, 40] for Minor
        """
        vis = actual_bgr.copy()

        for r in regions:
            x, y, w, h = r['x'], r['y'], r['width'], r['height']
            severity = r.get('severity', 'Medium')

            if severity == 'High':
                color = (45, 45, 230)      # Vivid Red
            elif severity == 'Medium':
                color = (30, 165, 245)     # Amber/Yellow
            else:
                color = (220, 160, 40)     # Teal/Blue

            # Draw outer rectangle
            cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)

            # Badge background for label
            label = f"#{r['id']} ({w}x{h})"
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 0.45
            thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(label, font, scale, thickness)
            
            badge_y1 = max(0, y - text_h - 6)
            badge_y2 = y
            badge_x1 = x
            badge_x2 = x + text_w + 8

            cv2.rectangle(vis, (badge_x1, badge_y1), (badge_x2, badge_y2), color, -1)
            cv2.putText(vis, label, (x + 4, y - 4), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

        return vis

    @staticmethod
    def create_side_by_side_montage(
        ref_bgr: np.ndarray,
        act_bgr: np.ndarray,
        overlay_bgr: np.ndarray,
        max_width: int = 1400
    ) -> np.ndarray:
        """Generates a 3-panel comparative montage: [Reference] | [Actual] | [Differences]."""
        h_ref, w_ref = ref_bgr.shape[:2]
        h_act, w_act = act_bgr.shape[:2]
        h_ov, w_ov = overlay_bgr.shape[:2]

        common_h = min(h_ref, h_act, h_ov, 600)
        scale_ref = common_h / float(h_ref)
        scale_act = common_h / float(h_act)
        scale_ov = common_h / float(h_ov)

        ref_thumb = cv2.resize(ref_bgr, (int(w_ref * scale_ref), common_h))
        act_thumb = cv2.resize(act_bgr, (int(w_act * scale_act), common_h))
        ov_thumb = cv2.resize(overlay_bgr, (int(w_ov * scale_ov), common_h))

        # Add top banner headers to each thumbnail
        header_h = 32
        def add_header(img, title, color):
            w = img.shape[1]
            header = np.full((header_h, w, 3), color, dtype=np.uint8)
            cv2.putText(header, title, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
            return np.vstack([header, img])

        panel1 = add_header(ref_thumb, "1. REFERENCE BASELINE", (60, 60, 60))
        panel2 = add_header(act_thumb, "2. ACTUAL CANDIDATE", (60, 60, 60))
        panel3 = add_header(ov_thumb, "3. DETECTED DIFFERENCES", (40, 40, 180))

        montage = np.hstack([panel1, panel2, panel3])

        # Resize montage if too wide
        if montage.shape[1] > max_width:
            factor = max_width / float(montage.shape[1])
            montage = cv2.resize(montage, (max_width, int(montage.shape[0] * factor)))

        return montage
