import os
import cv2
import numpy as np
from typing import Tuple, Optional

class ImagePreprocessor:
    """Handles safe image loading, color space conversion, aspect-ratio-aware normalization, and filtering."""

    @staticmethod
    def load_image(file_path: str) -> Optional[np.ndarray]:
        """Loads an image safely on Windows even with special characters or spaces in path."""
        if not os.path.exists(file_path):
            return None
        try:
            # Use np.fromfile to avoid Windows path encoding issues
            data = np.fromfile(file_path, dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            return img
        except Exception:
            return None

    @staticmethod
    def save_image(file_path: str, img: np.ndarray) -> bool:
        """Saves an image safely to disk on Windows using imencode + tofile."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            ext = os.path.splitext(file_path)[1]
            if not ext:
                ext = '.png'
            success, encoded_img = cv2.imencode(ext, img)
            if success:
                encoded_img.tofile(file_path)
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def to_rgb(bgr_img: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)

    @staticmethod
    def to_grayscale(img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 2:
            return img
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def normalize_resolution(
        ref_img: np.ndarray,
        act_img: np.ndarray,
        target_size: Optional[Tuple[int, int]] = None,
        padding_color: Tuple[int, int, int] = (240, 240, 240)
    ) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int]]:
        """
        Normalizes two images to identical dimensions without distortion.
        Uses aspect-ratio-preserving scaling and centered letterboxing/padding.
        If target_size is not provided, defaults to the larger bounding dimension of ref and act.
        """
        h_ref, w_ref = ref_img.shape[:2]
        h_act, w_act = act_img.shape[:2]

        if (w_ref, h_ref) == (w_act, h_act) and target_size is None:
            return ref_img.copy(), act_img.copy(), (w_ref, h_ref)

        if target_size is None:
            target_w = max(w_ref, w_act)
            target_h = max(h_ref, h_act)
        else:
            target_w, target_h = target_size

        ref_normalized = ImagePreprocessor.letterbox_resize(ref_img, target_w, target_h, padding_color)
        act_normalized = ImagePreprocessor.letterbox_resize(act_img, target_w, target_h, padding_color)

        return ref_normalized, act_normalized, (target_w, target_h)

    @staticmethod
    def letterbox_resize(
        img: np.ndarray,
        target_w: int,
        target_h: int,
        padding_color: Tuple[int, int, int] = (240, 240, 240)
    ) -> np.ndarray:
        """Scales image maintaining aspect ratio and pads to target_w, target_h."""
        h, w = img.shape[:2]
        scale = min(target_w / w, target_h / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR)

        # Create padded background
        if len(img.shape) == 3:
            padded = np.full((target_h, target_w, img.shape[2]), padding_color, dtype=np.uint8)
        else:
            padded = np.full((target_h, target_w), padding_color[0], dtype=np.uint8)

        # Center the resized image
        x_offset = (target_w - new_w) // 2
        y_offset = (target_h - new_h) // 2
        padded[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return padded

    @staticmethod
    def reduce_noise(gray_img: np.ndarray, kernel_size: int = 3, sigma: float = 0.8) -> np.ndarray:
        """Applies Gaussian blur to reduce high-frequency noise and minor anti-aliasing artifacts."""
        if kernel_size % 2 == 0:
            kernel_size += 1
        return cv2.GaussianBlur(gray_img, (kernel_size, kernel_size), sigma)
