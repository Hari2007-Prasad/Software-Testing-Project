import os
import pytest
import numpy as np
import cv2

from modules.image_processing.engine import ImageComparisonEngine
from modules.image_processing.validator import ImageValidator
from modules.image_processing.preprocessing import ImagePreprocessor
from modules.threshold_analysis.analyzer import ThresholdAnalyzer

@pytest.fixture
def image_env(tmp_path):
    proc_dir = str(tmp_path / 'processed')
    os.makedirs(proc_dir, exist_ok=True)
    engine = ImageComparisonEngine(processed_dir=proc_dir)
    return {'engine': engine, 'tmp': tmp_path}

def test_1_identical_images_zero_difference(image_env):
    """Case 1: Identical images should report zero pixel difference and SSIM=1.0."""
    tmp = image_env['tmp']
    engine = image_env['engine']

    img = np.full((200, 300, 3), (240, 240, 240), dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (280, 60), (37, 99, 235), -1)

    ref_path = str(tmp / 'ref_ident.png')
    act_path = str(tmp / 'act_ident.png')
    ImagePreprocessor.save_image(ref_path, img)
    ImagePreprocessor.save_image(act_path, img)

    result = engine.run_comparison(ref_path, act_path)
    metrics = result['metrics']

    assert metrics['pixel_similarity'] == 100.0
    assert metrics['difference_percentage'] == 0.0
    assert metrics['changed_pixels'] == 0
    assert metrics['ssim_score'] >= 0.999
    assert metrics['changed_regions_count'] == 0

def test_2_changed_button_creates_difference_region(image_env):
    """Case 2: A changed button should create a difference region."""
    tmp = image_env['tmp']
    engine = image_env['engine']

    ref = np.full((300, 400, 3), (250, 250, 250), dtype=np.uint8)
    # Blue Button on Reference
    cv2.rectangle(ref, (50, 50), (180, 100), (37, 99, 235), -1)

    act = ref.copy()
    # Changed Button (Red) on Actual
    cv2.rectangle(act, (50, 50), (180, 100), (220, 38, 38), -1)

    ref_path = str(tmp / 'ref_btn.png')
    act_path = str(tmp / 'act_btn.png')
    ImagePreprocessor.save_image(ref_path, ref)
    ImagePreprocessor.save_image(act_path, act)

    result = engine.run_comparison(ref_path, act_path)
    metrics = result['metrics']

    assert metrics['difference_percentage'] > 0.0
    assert metrics['changed_regions_count'] >= 1
    # Check that region bounding box covers the button
    regions = metrics['regions']
    btn_region = regions[0]
    assert abs(btn_region['x'] - 50) < 15
    assert abs(btn_region['y'] - 50) < 15

def test_3_missing_ui_element_detected(image_env):
    """Case 3: A missing UI element should be detected."""
    tmp = image_env['tmp']
    engine = image_env['engine']

    ref = np.full((300, 400, 3), (255, 255, 255), dtype=np.uint8)
    # UI Card Element present in Ref
    cv2.rectangle(ref, (100, 120), (250, 220), (100, 100, 100), -1)

    # Actual is blank (missing UI card)
    act = np.full((300, 400, 3), (255, 255, 255), dtype=np.uint8)

    ref_path = str(tmp / 'ref_missing.png')
    act_path = str(tmp / 'act_missing.png')
    ImagePreprocessor.save_image(ref_path, ref)
    ImagePreprocessor.save_image(act_path, act)

    result = engine.run_comparison(ref_path, act_path)
    metrics = result['metrics']

    assert metrics['changed_regions_count'] >= 1
    assert metrics['difference_percentage'] > 0.0

def test_4_different_resolutions_handled_correctly(image_env):
    """Case 4: Different resolutions should be normalized without distortion."""
    tmp = image_env['tmp']
    engine = image_env['engine']

    # Reference at 300x400
    ref = np.full((300, 400, 3), (240, 240, 240), dtype=np.uint8)
    # Actual at 450x600 (different resolution)
    act = np.full((450, 600, 3), (240, 240, 240), dtype=np.uint8)

    ref_path = str(tmp / 'ref_res.png')
    act_path = str(tmp / 'act_res.png')
    ImagePreprocessor.save_image(ref_path, ref)
    ImagePreprocessor.save_image(act_path, act)

    result = engine.run_comparison(ref_path, act_path)
    # Should execute cleanly without shape mismatch exceptions
    assert result['dimensions']['width'] == 600
    assert result['dimensions']['height'] == 450
    assert result['metrics']['difference_percentage'] == 0.0

def test_5_invalid_image_extension_rejected():
    """Case 5: Invalid file extensions should be rejected."""
    assert not ImageValidator.is_allowed_file("malicious_script.php")
    assert not ImageValidator.is_allowed_file("exploit.exe")
    assert ImageValidator.is_allowed_file("screenshot.png")
    assert ImageValidator.is_allowed_file("banner.jpg")

def test_6_corrupted_image_rejected(tmp_path):
    """Case 6: Corrupted images should be rejected."""
    corrupt_file = str(tmp_path / "corrupt.png")
    with open(corrupt_file, "wb") as f:
        f.write(b"NOT_A_REAL_PNG_HEADER_GARBAGE_BYTES_1234567890")

    is_valid, err_msg, meta = ImageValidator.validate_and_inspect(corrupt_file)
    assert not is_valid
    assert "Corrupted or invalid" in err_msg

def test_7_minor_pixel_noise_evaluated_according_to_thresholds(image_env):
    """Case 7: Minor pixel noise should be evaluated according to configured thresholds."""
    tmp = image_env['tmp']
    engine = image_env['engine']

    base = np.full((200, 200, 3), 128, dtype=np.uint8)
    # Add subtle sub-threshold anti-aliasing variations (intensity shift of 5, below default threshold 25)
    noisy = base.copy()
    noisy[10:30, 10:30] = 133

    ref_path = str(tmp / 'ref_noise.png')
    act_path = str(tmp / 'act_noise.png')
    ImagePreprocessor.save_image(ref_path, base)
    ImagePreprocessor.save_image(act_path, noisy)

    result = engine.run_comparison(ref_path, act_path, intensity_threshold=20)
    # Diff should be 0 because intensity shift 5 is below threshold 20
    assert result['metrics']['difference_percentage'] == 0.0

def test_8_significant_layout_changes_identified(image_env):
    """Case 8: Significant layout changes should be identified."""
    tmp = image_env['tmp']
    engine = image_env['engine']

    ref = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.rectangle(ref, (50, 50), (350, 350), (255, 255, 255), -1)

    act = np.zeros((400, 400, 3), dtype=np.uint8)
    # Inverted layout
    cv2.circle(act, (200, 200), 100, (255, 255, 255), -1)

    ref_path = str(tmp / 'ref_layout.png')
    act_path = str(tmp / 'act_layout.png')
    ImagePreprocessor.save_image(ref_path, ref)
    ImagePreprocessor.save_image(act_path, act)

    result = engine.run_comparison(ref_path, act_path)
    assert result['metrics']['difference_percentage'] > 15.0
    assert result['metrics']['status'] == 'MAJOR_DIFFERENCE'

def test_9_missing_metrics_does_not_pass_threshold_analysis():
    """Case 9: Missing metrics should not automatically pass threshold analysis."""
    thresholds = {'max_pixel_diff_pct': 1.5, 'min_pixel_similarity_pct': 98.5}
    # Pass None for metrics
    result = ThresholdAnalyzer.evaluate_visual_metrics(None, thresholds)
    assert result['status'] == 'REVIEW'
    assert result['score'] == 0.0
    assert len(result['violations']) > 0
