import unittest

from fixdrift.drift import compute_fix_drift
from fixdrift.git_tools import WorkingChanges
from fixdrift.specs import FixdriftSpec


class TestFixDrift(unittest.TestCase):
    def test_green_with_root_cause_evidence(self) -> None:
        spec = FixdriftSpec.from_raw({"schema": 1})
        task = {
            "id": "task-1",
            "status": "in-progress",
            "log": [
                {"message": "Repro: upload fails for 413 payloads"},
                {"message": "RootCause: nginx body limit lower than service expectation"},
                {"message": "RegressionTest: added test_upload_rejects_oversized_payload"},
            ],
        }
        tasks = {"task-1": task}
        changes = WorkingChanges(changed_files=["tests/test_upload.py"], new_files=["tests/test_upload.py"])

        report = compute_fix_drift(
            task_id="task-1",
            task_title="Fix upload failure",
            spec=spec,
            task=task,
            tasks=tasks,
            git_root="/tmp/project",
            changes=changes,
        )
        self.assertEqual("green", report["score"])
        self.assertEqual([], report["findings"])

    def test_flags_patch_on_patch_patterns(self) -> None:
        spec = FixdriftSpec.from_raw({"schema": 1, "min_open_fix_followups": 2})
        task = {"id": "task-1", "status": "in-progress", "log": []}
        tasks = {
            "task-1": task,
            "drift-harden-task-1": {"id": "drift-harden-task-1", "status": "open", "blocked_by": ["task-1"]},
            "drift-scope-task-1": {"id": "drift-scope-task-1", "status": "in-progress", "blocked_by": ["task-1"]},
        }
        changes = WorkingChanges(changed_files=["src/service.py"], new_files=[])

        report = compute_fix_drift(
            task_id="task-1",
            task_title="Fix flaky auth refresh",
            spec=spec,
            task=task,
            tasks=tasks,
            git_root="/tmp/project",
            changes=changes,
        )
        kinds = {f["kind"] for f in report["findings"]}
        self.assertIn("unresolved_fix_followups", kinds)
        self.assertIn("repeated_fix_attempts", kinds)
        self.assertIn("missing_repro_evidence", kinds)
        self.assertIn("missing_root_cause_evidence", kinds)
        self.assertIn("missing_regression_evidence", kinds)
        self.assertEqual("yellow", report["score"])


if __name__ == "__main__":
    unittest.main()
