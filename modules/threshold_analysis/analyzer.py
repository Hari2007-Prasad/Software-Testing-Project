from typing import Dict, Any, List, Optional
from datetime import datetime

class ThresholdAnalyzer:
    """
    Evaluates visual, functional, and security metrics against acceptance criteria.
    Produces deterministic PASS / FAIL / REVIEW verdicts and weighted project health scores.
    """

    @staticmethod
    def evaluate_visual_metrics(
        metrics: Optional[Dict[str, Any]],
        thresholds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates visual comparison metrics against acceptance criteria.
        Returns visual status (PASS/FAIL/REVIEW), visual score (0-100), and violations.
        """
        if not metrics:
            return {
                'status': 'REVIEW',
                'score': 0.0,
                'violations': ['No image comparison metrics available for evaluation.'],
                'details': {'reason': 'Missing visual metrics'}
            }

        violations = []
        max_diff_pct = float(thresholds.get('max_pixel_diff_pct', 1.5))
        min_pixel_sim = float(thresholds.get('min_pixel_similarity_pct', 98.5))
        min_ssim = float(thresholds.get('min_ssim_score', 0.92))
        max_regions = int(thresholds.get('max_changed_regions', 2))

        actual_diff_pct = float(metrics.get('difference_percentage', 0.0))
        actual_pixel_sim = float(metrics.get('pixel_similarity', 100.0))
        actual_ssim = float(metrics.get('ssim_score', 1.0))
        actual_regions = int(metrics.get('changed_regions_count', 0))

        # Check thresholds
        if actual_diff_pct > max_diff_pct:
            violations.append(
                f"Pixel difference ({actual_diff_pct:.2f}%) exceeds maximum allowable threshold ({max_diff_pct:.2f}%)."
            )

        if actual_pixel_sim < min_pixel_sim:
            violations.append(
                f"Pixel similarity ({actual_pixel_sim:.2f}%) is below minimum requirement ({min_pixel_sim:.2f}%)."
            )

        if actual_ssim < min_ssim:
            violations.append(
                f"SSIM score ({actual_ssim:.4f}) is below minimum acceptable threshold ({min_ssim:.4f})."
            )

        if actual_regions > max_regions:
            violations.append(
                f"Changed regions count ({actual_regions}) exceeds maximum allowed regions ({max_regions})."
            )

        # Calculate visual quality score (0-100):
        # 50% weighted on pixel similarity + 50% weighted on SSIM percentage
        ssim_pct = float(metrics.get('structural_similarity_pct', actual_ssim * 100.0))
        visual_score = (actual_pixel_sim * 0.5) + (ssim_pct * 0.5)
        visual_score = round(max(0.0, min(100.0, visual_score)), 2)

        # Status determination:
        if len(violations) == 0:
            status = 'PASS'
        elif actual_diff_pct <= (max_diff_pct * 2.0) and actual_ssim >= (min_ssim - 0.05):
            status = 'REVIEW'
        else:
            status = 'FAIL'

        return {
            'status': status,
            'score': visual_score,
            'violations': violations,
            'details': {
                'actual_diff_pct': actual_diff_pct,
                'max_diff_pct': max_diff_pct,
                'actual_pixel_sim': actual_pixel_sim,
                'min_pixel_sim': min_pixel_sim,
                'actual_ssim': actual_ssim,
                'min_ssim': min_ssim,
                'actual_regions': actual_regions,
                'max_regions': max_regions
            }
        }

    @staticmethod
    def evaluate_functional_metrics(
        execution_data: Optional[Dict[str, Any]],
        thresholds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates automated functional test execution results.
        Returns functional status (PASS/FAIL/REVIEW), score (0-100), and violations.
        """
        if not execution_data or execution_data.get('total_tests', 0) == 0:
            return {
                'status': 'REVIEW',
                'score': 0.0,
                'violations': ['No automated functional test executions recorded.'],
                'details': {'reason': 'Missing functional test runs'}
            }

        violations = []
        min_pass_rate = float(thresholds.get('min_pass_rate', 90.0))
        max_failed = int(thresholds.get('max_failed_tests', 1))
        max_blocked = int(thresholds.get('max_blocked_tests', 0))

        total_tests = int(execution_data.get('total_tests', 0))
        passed_tests = int(execution_data.get('passed_tests', 0))
        failed_tests = int(execution_data.get('failed_tests', 0))
        blocked_tests = int(execution_data.get('blocked_tests', 0))

        pass_rate = round((passed_tests / total_tests) * 100.0, 2) if total_tests > 0 else 0.0

        if pass_rate < min_pass_rate:
            violations.append(
                f"Functional pass rate ({pass_rate}%) is below minimum required threshold ({min_pass_rate}%)."
            )

        if failed_tests > max_failed:
            violations.append(
                f"Failed tests count ({failed_tests}) exceeds allowable ceiling ({max_failed})."
            )

        if blocked_tests > max_blocked:
            violations.append(
                f"Blocked tests count ({blocked_tests}) exceeds allowable ceiling ({max_blocked})."
            )

        functional_score = pass_rate

        if len(violations) == 0:
            status = 'PASS'
        elif failed_tests <= max_failed + 1 and pass_rate >= (min_pass_rate - 15.0):
            status = 'REVIEW'
        else:
            status = 'FAIL'

        return {
            'status': status,
            'score': functional_score,
            'violations': violations,
            'details': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'blocked_tests': blocked_tests,
                'pass_rate': pass_rate,
                'min_pass_rate': min_pass_rate,
                'max_failed': max_failed,
                'max_blocked': max_blocked
            }
        }

    @staticmethod
    def evaluate_security_metrics(
        findings: List[Dict[str, Any]],
        thresholds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates security baseline findings against policy thresholds.
        Returns security status (PASS/FAIL/REVIEW), score (0-100), and violations.
        """
        violations = []
        max_critical = int(thresholds.get('max_critical_findings', 0))
        max_high = int(thresholds.get('max_high_findings', 1))

        critical_count = sum(1 for f in findings if f.get('severity', '').lower() == 'critical')
        high_count = sum(1 for f in findings if f.get('severity', '').lower() == 'high')
        medium_count = sum(1 for f in findings if f.get('severity', '').lower() == 'medium')
        low_count = sum(1 for f in findings if f.get('severity', '').lower() == 'low')

        if critical_count > max_critical:
            violations.append(
                f"Critical security findings ({critical_count}) exceed allowable policy ({max_critical})."
            )

        if high_count > max_high:
            violations.append(
                f"High-severity security findings ({high_count}) exceed allowable policy ({max_high})."
            )

        # Deductive scoring from 100:
        # Critical = -30 each, High = -15 each, Medium = -5 each, Low = -2 each
        penalty = (critical_count * 30) + (high_count * 15) + (medium_count * 5) + (low_count * 2)
        security_score = max(0.0, 100.0 - penalty)

        if critical_count > max_critical or high_count > max_high + 2:
            status = 'FAIL'
        elif high_count > max_high or medium_count > 3:
            status = 'REVIEW'
        else:
            status = 'PASS'

        return {
            'status': status,
            'score': security_score,
            'violations': violations,
            'details': {
                'critical_count': critical_count,
                'high_count': high_count,
                'medium_count': medium_count,
                'low_count': low_count,
                'max_critical': max_critical,
                'max_high': max_high
            }
        }

    @classmethod
    def evaluate_combined(
        cls,
        visual_metrics: Optional[Dict[str, Any]],
        functional_data: Optional[Dict[str, Any]],
        security_findings: List[Dict[str, Any]],
        threshold_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Computes composite project health using configurable weights:
        Overall Score = (Visual Score * W_v) + (Functional Score * W_f) + (Security Score * W_s)
        Overall Status = FAIL if any pillar FAILs, REVIEW if any REVIEWs, else PASS.
        """
        w_v = float(threshold_config.get('visual_weight', 0.30))
        w_f = float(threshold_config.get('functional_weight', 0.40))
        w_s = float(threshold_config.get('security_weight', 0.30))

        # Normalize weights if sum != 1.0
        total_w = w_v + w_f + w_s
        if total_w > 0:
            w_v /= total_w
            w_f /= total_w
            w_s /= total_w

        visual_eval = cls.evaluate_visual_metrics(visual_metrics, threshold_config)
        functional_eval = cls.evaluate_functional_metrics(functional_data, threshold_config)
        security_eval = cls.evaluate_security_metrics(security_findings, threshold_config)

        all_violations = visual_eval['violations'] + functional_eval['violations'] + security_eval['violations']

        statuses = [visual_eval['status'], functional_eval['status'], security_eval['status']]
        if 'FAIL' in statuses:
            overall_status = 'FAIL'
        elif 'REVIEW' in statuses:
            overall_status = 'REVIEW'
        else:
            overall_status = 'PASS'

        overall_score = (visual_eval['score'] * w_v) + (functional_eval['score'] * w_f) + (security_eval['score'] * w_s)
        overall_score = round(overall_score, 2)

        return {
            'visual': visual_eval,
            'functional': functional_eval,
            'security': security_eval,
            'weights': {'visual': round(w_v, 2), 'functional': round(w_f, 2), 'security': round(w_s, 2)},
            'overall_status': overall_status,
            'overall_score': overall_score,
            'violations': all_violations,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
