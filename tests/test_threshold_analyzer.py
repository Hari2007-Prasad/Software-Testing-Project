import pytest
from modules.threshold_analysis.analyzer import ThresholdAnalyzer

def test_visual_metrics_evaluation_pass():
    metrics = {
        'difference_percentage': 0.4,
        'pixel_similarity': 99.6,
        'ssim_score': 0.98,
        'structural_similarity_pct': 98.0,
        'changed_regions_count': 1
    }
    thresholds = {
        'max_pixel_diff_pct': 1.5,
        'min_pixel_similarity_pct': 98.5,
        'min_ssim_score': 0.92,
        'max_changed_regions': 2
    }
    res = ThresholdAnalyzer.evaluate_visual_metrics(metrics, thresholds)
    assert res['status'] == 'PASS'
    assert len(res['violations']) == 0
    assert res['score'] > 95.0

def test_visual_metrics_evaluation_fail():
    metrics = {
        'difference_percentage': 8.5,
        'pixel_similarity': 91.5,
        'ssim_score': 0.81,
        'structural_similarity_pct': 81.0,
        'changed_regions_count': 6
    }
    thresholds = {
        'max_pixel_diff_pct': 1.5,
        'min_pixel_similarity_pct': 98.5,
        'min_ssim_score': 0.92,
        'max_changed_regions': 2
    }
    res = ThresholdAnalyzer.evaluate_visual_metrics(metrics, thresholds)
    assert res['status'] == 'FAIL'
    assert len(res['violations']) >= 3

def test_functional_metrics_evaluation():
    exec_data = {
        'total_tests': 15,
        'passed_tests': 15,
        'failed_tests': 0,
        'blocked_tests': 0
    }
    thresholds = {
        'min_pass_rate': 90.0,
        'max_failed_tests': 1,
        'max_blocked_tests': 0
    }
    res = ThresholdAnalyzer.evaluate_functional_metrics(exec_data, thresholds)
    assert res['status'] == 'PASS'
    assert res['score'] == 100.0

def test_security_metrics_evaluation():
    findings = [
        {'severity': 'Medium'},
        {'severity': 'Low'}
    ]
    thresholds = {
        'max_critical_findings': 0,
        'max_high_findings': 1
    }
    res = ThresholdAnalyzer.evaluate_security_metrics(findings, thresholds)
    assert res['status'] in ('PASS', 'REVIEW')
    assert res['score'] > 85.0

def test_combined_weighted_evaluation():
    v_metrics = {'difference_percentage': 0.0, 'pixel_similarity': 100.0, 'ssim_score': 1.0, 'changed_regions_count': 0}
    f_data = {'total_tests': 10, 'passed_tests': 10, 'failed_tests': 0, 'blocked_tests': 0}
    s_findings = []
    config = {
        'max_pixel_diff_pct': 1.5,
        'min_pixel_similarity_pct': 98.5,
        'min_ssim_score': 0.92,
        'max_changed_regions': 2,
        'min_pass_rate': 90.0,
        'max_failed_tests': 1,
        'max_blocked_tests': 0,
        'max_critical_findings': 0,
        'max_high_findings': 1,
        'visual_weight': 0.30,
        'functional_weight': 0.40,
        'security_weight': 0.30
    }
    res = ThresholdAnalyzer.evaluate_combined(v_metrics, f_data, s_findings, config)
    assert res['overall_status'] == 'PASS'
    assert res['overall_score'] == 100.0
