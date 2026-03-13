"""UAT pipeline.

Orchestrates the full UAT flow: load context, cross-reference specs,
generate tests, execute, and report. Errors are handled gracefully
so UAT never blocks implementation.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 — used at runtime

import structlog

from autopilot.uat.reporter import UATReporter
from autopilot.uat.spec_engine import build_traceability_matrix
from autopilot.uat.task_context import load_task_context
from autopilot.uat.test_executor import TestExecutor, UATResult
from autopilot.uat.test_generator import TestGenerator

logger = structlog.get_logger(__name__)


class UATPipeline:
    """Runs the full UAT pipeline for a task.

    Steps:
    1. Load task context
    2. Cross-reference specifications
    3. Generate acceptance tests
    4. Execute tests
    5. Report results

    Errors at any stage are caught and logged; the pipeline returns
    a best-effort ``UATResult`` rather than raising.
    """

    def __init__(
        self,
        *,
        timeout: int = 300,
        max_tests_per_sp: int = 5,
    ) -> None:
        self._timeout = timeout
        self._max_tests_per_sp = max_tests_per_sp

    def run(self, task_id: str, project_dir: Path) -> UATResult:
        """Execute the full UAT pipeline for *task_id*.

        Parameters
        ----------
        task_id:
            The task identifier (e.g. ``"046"``).
        project_dir:
            Root directory of the project containing ``tasks/``.

        Returns
        -------
        UATResult
            Aggregated test results.  On error the result will have
            ``overall_pass=False`` and details in ``raw_output``.
        """
        task_dir = project_dir / "tasks"

        # Step 1: Load task context
        logger.info("uat_pipeline_start", task_id=task_id)
        try:
            context = load_task_context(task_dir, task_id)
        except Exception as exc:
            logger.error("uat_context_load_failed", task_id=task_id, error=str(exc))
            return UATResult(raw_output=f"Failed to load task context: {exc}")

        # Step 2: Cross-reference specs
        try:
            matrix = build_traceability_matrix(context)
            logger.info(
                "uat_spec_coverage",
                task_id=task_id,
                coverage=matrix.coverage_score,
                rfc_sections=len(matrix.rfc_sections),
            )
        except Exception as exc:
            logger.warning("uat_spec_cross_ref_failed", task_id=task_id, error=str(exc))
            # Non-fatal: continue without spec cross-reference

        # Step 3: Generate tests
        try:
            generator = TestGenerator(max_tests_per_sp=self._max_tests_per_sp)
            generated = generator.generate_acceptance_tests(context)
            if generated.test_count == 0:
                logger.warning("uat_no_tests_generated", task_id=task_id)
                return UATResult(raw_output="No acceptance criteria found for test generation.")

            test_path = generator.write_test_file(generated, project_dir)
            logger.info(
                "uat_tests_generated",
                task_id=task_id,
                test_count=generated.test_count,
                path=str(test_path),
            )
        except Exception as exc:
            logger.error("uat_test_generation_failed", task_id=task_id, error=str(exc))
            return UATResult(raw_output=f"Failed to generate tests: {exc}")

        # Step 4: Execute tests
        try:
            executor = TestExecutor(timeout=self._timeout)
            result = executor.run(test_path)
            logger.info(
                "uat_tests_executed",
                task_id=task_id,
                passed=result.passed,
                failed=result.failed,
                skipped=result.skipped,
            )
        except Exception as exc:
            logger.error("uat_test_execution_failed", task_id=task_id, error=str(exc))
            return UATResult(raw_output=f"Failed to execute tests: {exc}")

        # Step 5: Report
        try:
            reporter = UATReporter()
            reporter.render_task_report(result, task_id=task_id)
            reporter.save_report(result, task_id=task_id, project_dir=project_dir)
        except Exception as exc:
            logger.warning("uat_report_failed", task_id=task_id, error=str(exc))
            # Non-fatal: return result even if reporting fails

        return result
