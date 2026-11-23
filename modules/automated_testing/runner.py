import os
import time
import threading
import uuid
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from extensions import db
from models import TestExecution, TestExecutionResult, SecurityFinding, TestCase, ActivityLog
from .scenarios import FunctionalScenarios

# In-memory execution progress tracker for live UI polling
ACTIVE_EXECUTIONS: Dict[int, Dict[str, Any]] = {}

class TestExecutionRunner:
    """
    Manages background automated functional and security testing execution.
    Executes real Selenium WebDriver tests against the digital learning application,
    captures screenshots and logs, and records results into the SQLite database.
    """

    def __init__(self, app, base_url: str = 'http://127.0.0.1:5000/lms', headless: bool = True, timeout: int = 15):
        self.app = app
        self.base_url = base_url.rstrip('/')
        self.headless = headless
        self.timeout = timeout
        self.evidence_dir = os.path.join(app.root_path, 'uploads', 'evidence')
        os.makedirs(self.evidence_dir, exist_ok=True)

    def _create_driver(self) -> Optional[webdriver.Chrome]:
        """Initializes Chrome WebDriver with robust options for local and background execution."""
        try:
            options = Options()
            if self.headless:
                options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1366,768')
            options.add_argument('--log-level=3')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])

            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.timeout)
            driver.implicitly_wait(4)
            return driver
        except Exception as e:
            # If Selenium Chrome cannot be started, log the exact error
            print(f"[TestRunner] Chrome WebDriver init warning: {e}")
            return None

    def start_suite_async(
        self,
        execution_id: int,
        selected_test_ids: Optional[List[str]] = None,
        include_security: bool = False
    ) -> threading.Thread:
        """Launches the execution in a separate daemon thread to avoid blocking Flask workers."""
        thread = threading.Thread(
            target=self._run_suite_worker,
            args=(execution_id, selected_test_ids, include_security),
            daemon=True
        )
        thread.start()
        return thread

    def _run_suite_worker(
        self,
        execution_id: int,
        selected_test_ids: Optional[List[str]],
        include_security: bool
    ):
        """Worker thread executing tests inside Flask application context."""
        with self.app.app_context():
            execution = TestExecution.query.get(execution_id)
            if not execution:
                return

            all_scenarios = FunctionalScenarios.get_all_scenarios()
            if selected_test_ids:
                scenarios_to_run = {k: v for k, v in all_scenarios.items() if k in selected_test_ids}
            else:
                scenarios_to_run = all_scenarios

            total_count = len(scenarios_to_run)
            execution.total_tests = total_count
            execution.status = 'Running'
            execution.start_time = datetime.utcnow()
            db.session.commit()

            ACTIVE_EXECUTIONS[execution_id] = {
                'id': execution_id,
                'status': 'Running',
                'current_test': 'Initializing browser...',
                'progress_pct': 0,
                'total': total_count,
                'completed': 0,
                'passed': 0,
                'failed': 0,
                'blocked': 0,
                'logs': []
            }

            logs = []
            def log_msg(msg: str):
                timestamp = datetime.utcnow().strftime('%H:%M:%S')
                entry = f"[{timestamp}] {msg}"
                logs.append(entry)
                if execution_id in ACTIVE_EXECUTIONS:
                    ACTIVE_EXECUTIONS[execution_id]['logs'].append(entry)

            log_msg(f"Started automated test run #{execution_id} targeting: {self.base_url}")
            log_msg(f"Suite size: {total_count} scenarios. Headless mode: {self.headless}")

            driver = self._create_driver()
            start_clock = time.time()
            passed_count = 0
            failed_count = 0
            blocked_count = 0

            try:
                for idx, (test_id, scenario) in enumerate(scenarios_to_run.items(), start=1):
                    test_name = scenario['name']
                    category = scenario['category']
                    log_msg(f"Executing [{idx}/{total_count}]: {test_id} - {test_name}...")

                    ACTIVE_EXECUTIONS[execution_id]['current_test'] = f"{test_id}: {test_name}"
                    ACTIVE_EXECUTIONS[execution_id]['progress_pct'] = int(((idx - 1) / total_count) * 100)

                    t_start = time.time()
                    status = 'Passed'
                    error_msg = None
                    stack = None
                    actual_text = ""
                    screenshot_rel_path = None

                    if driver is None:
                        # Fallback if Chrome driver not available on system
                        status = 'Blocked'
                        error_msg = "Selenium Chrome WebDriver could not be initialized. Please check Chrome installation."
                        actual_text = "Execution blocked due to browser driver unavailability."
                        blocked_count += 1
                        log_msg(f"  -> BLOCKED: {error_msg}")
                    else:
                        try:
                            result = scenario['handler'](driver, self.base_url, self.evidence_dir)
                            status = result.get('status', 'Passed')
                            actual_text = result.get('actual', scenario['expected'])
                            passed_count += 1
                            log_msg(f"  -> PASSED ({round(time.time() - t_start, 2)}s)")

                        except AssertionError as ae:
                            status = 'Failed'
                            error_msg = f"Assertion Failed: {str(ae)}"
                            stack = traceback.format_exc()
                            actual_text = f"Assertion failure: {str(ae)}"
                            failed_count += 1
                            log_msg(f"  -> FAILED: {str(ae)}")

                        except Exception as ex:
                            status = 'Failed'
                            error_msg = f"Execution Exception: {str(ex)}"
                            stack = traceback.format_exc()
                            actual_text = f"Unexpected error: {str(ex)}"
                            failed_count += 1
                            log_msg(f"  -> ERROR: {str(ex)}")

                        # Capture screenshot evidence
                        try:
                            shot_name = f"shot_{execution_id}_{test_id}_{uuid.uuid4().hex[:6]}.png"
                            shot_abs = os.path.join(self.evidence_dir, shot_name)
                            driver.save_screenshot(shot_abs)
                            screenshot_rel_path = f"evidence/{shot_name}"
                        except Exception:
                            pass

                    t_duration = round(time.time() - t_start, 3)

                    # Update database test result
                    tc_record = TestCase.query.filter_by(custom_id=test_id).first()
                    exec_res = TestExecutionResult(
                        test_execution_id=execution_id,
                        test_case_id=tc_record.id if tc_record else None,
                        test_name=f"{test_id}: {test_name}",
                        category=category,
                        status=status,
                        duration=t_duration,
                        error_message=error_msg,
                        stack_trace=stack,
                        screenshot_path=screenshot_rel_path,
                        actual_result=actual_text
                    )
                    db.session.add(exec_res)

                    # Update TestCase model status if matched
                    if tc_record:
                        tc_record.execution_status = status
                        tc_record.actual_result = actual_text
                        tc_record.last_executed = datetime.utcnow()

                    db.session.commit()

                    ACTIVE_EXECUTIONS[execution_id]['completed'] = idx
                    ACTIVE_EXECUTIONS[execution_id]['passed'] = passed_count
                    ACTIVE_EXECUTIONS[execution_id]['failed'] = failed_count
                    ACTIVE_EXECUTIONS[execution_id]['blocked'] = blocked_count

            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

            total_duration = round(time.time() - start_clock, 2)
            log_msg(f"Test suite completed in {total_duration}s. Passed: {passed_count}, Failed: {failed_count}, Blocked: {blocked_count}")

            # Update final execution record
            execution.end_time = datetime.utcnow()
            execution.duration = total_duration
            execution.passed_tests = passed_count
            execution.failed_tests = failed_count
            execution.blocked_tests = blocked_count
            execution.status = 'Completed' if failed_count == 0 and blocked_count == 0 else ('Failed' if failed_count > 0 else 'Completed')
            execution.logs = "\n".join(logs)
            db.session.commit()

            if execution_id in ACTIVE_EXECUTIONS:
                ACTIVE_EXECUTIONS[execution_id]['status'] = execution.status
                ACTIVE_EXECUTIONS[execution_id]['progress_pct'] = 100
                ACTIVE_EXECUTIONS[execution_id]['current_test'] = 'Suite finished.'

    @staticmethod
    def get_progress(execution_id: int) -> Dict[str, Any]:
        """Returns live progress for asynchronous polling in the browser."""
        if execution_id in ACTIVE_EXECUTIONS:
            return ACTIVE_EXECUTIONS[execution_id]
        
        # If not in active memory, load from DB
        execution = TestExecution.query.get(execution_id)
        if execution:
            return {
                'id': execution.id,
                'status': execution.status,
                'progress_pct': 100 if execution.status in ('Completed', 'Failed', 'Aborted') else 0,
                'total': execution.total_tests,
                'completed': execution.total_tests,
                'passed': execution.passed_tests,
                'failed': execution.failed_tests,
                'blocked': execution.blocked_tests,
                'duration': f"{execution.duration:.2f}s",
                'logs': execution.logs.splitlines() if execution.logs else []
            }
        return {'status': 'Not Found', 'progress_pct': 0}
