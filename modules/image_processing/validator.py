import os
import uuid
from typing import Tuple, Dict, Any, Optional
from PIL import Image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB

class ImageValidator:
    """Validates image uploads, file types, sizes, and integrity."""

    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        if '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in ALLOWED_EXTENSIONS

    @staticmethod
    def validate_and_inspect(file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates that the file exists, is non-empty, does not exceed size limits,
        and is a genuine, uncorrupted image. Returns (is_valid, error_msg, metadata).
        """
        if not os.path.exists(file_path):
            return False, f"File does not exist: {file_path}", {}

        size_bytes = os.path.getsize(file_path)
        if size_bytes == 0:
            return False, "File is empty (0 bytes).", {}

        if size_bytes > MAX_FILE_SIZE:
            return False, f"File size ({size_bytes / (1024*1024):.2f} MB) exceeds maximum 16 MB.", {}

        # Verify actual image integrity using Pillow
        try:
            with Image.open(file_path) as img:
                img.verify()  # Verifies file integrity
            
            # Reopen to get dimensions and format (verify() closes/invalidates the file object)
            with Image.open(file_path) as img:
                width, height = img.size
                img_format = img.format or "UNKNOWN"
                mode = img.mode

            metadata = {
                'width': width,
                'height': height,
                'format': img_format.lower(),
                'mode': mode,
                'size_bytes': size_bytes,
                'size_formatted': f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / (1024*1024):.2f} MB"
            }
            return True, "", metadata

        except Exception as e:
            return False, f"Corrupted or invalid image file: {str(e)}", {}

    @staticmethod
    def generate_safe_filename(original_filename: str, prefix: str = 'img') -> str:
        """Generates a secure, unique filename preserving valid extension."""
        ext = 'png'
        if '.' in original_filename:
            candidate_ext = original_filename.rsplit('.', 1)[1].lower()
            if candidate_ext in ALLOWED_EXTENSIONS:
                ext = candidate_ext
        unique_id = uuid.uuid4().hex[:12]
        return f"{prefix}_{unique_id}.{ext}"
