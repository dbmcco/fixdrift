from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fixdrift.git_tools import WorkingChanges
from fixdrift.globmatch import match_any
from fixdrift.specs import FixdriftSpec


@dataclass(frozen=True)
class Finding:
    kind: str
    severity: str
    summary: str
    details: dict[str, Any] | None = None


def _task_status(task: dict[str, Any]) -> str:
    return str(task.get("status") or "")


def _blocked_by(task: dict[str, Any]) -> list[str]:
    return [str(x) for x in (task.get("blocked_by") or [])]


def _contains_marker(message: str, markers: list[str]) -> bool:
    low = message.lower()
    return any(str(marker).lower() in low for marker in markers if str(marker).strip())


def compute_fix_drift(
    *,
    task_id: str,
    task_title: str,
    spec: FixdriftSpec,
    task: dict[str, Any],
    tasks: dict[str, dict[str, Any]],
    git_root: str | None,
    changes: WorkingChanges | None,
) -> dict[str, Any]:
    findings: list[Finding] = []

    logs = task.get("log") or []
    log_messages: list[str] = []
    ignored_log_messages = 0
    for e in logs:
        if not isinstance(e, dict):
            continue
        message = str(e.get("message") or "").strip()
        if not message:
            continue
        if any(message.startswith(prefix) for prefix in spec.ignore_log_prefixes):
            ignored_log_messages += 1
            continue
        log_messages.append(message)

    open_fix_followups: list[str] = []
    for t in tasks.values():
        tid = str(t.get("id") or "")
        if not tid or tid == task_id:
            continue
        if _task_status(t) not in {"open", "in-progress"}:
            continue
        if task_id not in _blocked_by(t):
            continue
        if any(tid.startswith(prefix) for prefix in spec.followup_prefixes):
            open_fix_followups.append(tid)
    open_fix_followups = sorted(set(open_fix_followups))

    changed_files: list[str] = []
    if changes:
        changed_files = [
            p
            for p in changes.changed_files
            if not (p.startswith(".workgraph/") or p.startswith(".git/") or match_any(p, spec.ignore_paths))
        ]
    changed_test_files = [p for p in changed_files if match_any(p, spec.regression_test_globs)]

    has_repro_log = any(_contains_marker(message, spec.repro_markers) for message in log_messages)
    has_root_cause_log = any(_contains_marker(message, spec.root_cause_markers) for message in log_messages)
    has_regression_log = any(_contains_marker(message, spec.regression_markers) for message in log_messages)
    has_regression_signal = bool(has_regression_log or changed_test_files)

    telemetry: dict[str, Any] = {
        "logs_scanned": len(log_messages),
        "ignored_log_messages": ignored_log_messages,
        "open_fix_followups": len(open_fix_followups),
        "open_fix_followup_ids": open_fix_followups[:50],
        "changed_files": len(changed_files),
        "changed_test_files": len(changed_test_files),
        "changed_test_file_ids": changed_test_files[:50],
        "has_repro_log": has_repro_log,
        "has_root_cause_log": has_root_cause_log,
        "has_regression_log": has_regression_log,
        "has_regression_signal": has_regression_signal,
    }

    if spec.schema != 1:
        findings.append(
            Finding(
                kind="unsupported_schema",
                severity="warn",
                summary=f"Unsupported fixdrift schema: {spec.schema} (expected 1)",
            )
        )

    if open_fix_followups:
        findings.append(
            Finding(
                kind="unresolved_fix_followups",
                severity="warn",
                summary=f"Task has unresolved fix-related follow-up tasks ({len(open_fix_followups)})",
                details={"tasks": open_fix_followups[:20]},
            )
        )

    if len(open_fix_followups) >= spec.min_open_fix_followups:
        findings.append(
            Finding(
                kind="repeated_fix_attempts",
                severity="warn",
                summary=(
                    "Task appears to be accumulating patch-on-patch remediation "
                    f"({len(open_fix_followups)} open follow-ups >= {spec.min_open_fix_followups})"
                ),
                details={"tasks": open_fix_followups[:20]},
            )
        )

    if spec.require_repro_log and not has_repro_log:
        findings.append(
            Finding(
                kind="missing_repro_evidence",
                severity="warn",
                summary="No explicit reproduction evidence found in task logs",
                details={"expected_markers": spec.repro_markers},
            )
        )

    if spec.require_root_cause_log and not has_root_cause_log:
        findings.append(
            Finding(
                kind="missing_root_cause_evidence",
                severity="warn",
                summary="No explicit root-cause evidence found in task logs",
                details={"expected_markers": spec.root_cause_markers},
            )
        )

    if spec.require_regression_signal and not has_regression_signal:
        findings.append(
            Finding(
                kind="missing_regression_evidence",
                severity="warn",
                summary="No regression evidence found (log marker or changed test file)",
                details={
                    "expected_markers": spec.regression_markers,
                    "test_globs": spec.regression_test_globs,
                },
            )
        )

    score = "green"
    if any(f.severity == "warn" for f in findings):
        score = "yellow"
    if any(f.severity == "error" for f in findings):
        score = "red"

    recommendations: list[dict[str, Any]] = []
    for f in findings:
        if f.kind == "unresolved_fix_followups":
            recommendations.append(
                {
                    "priority": "high",
                    "action": "Resolve or re-scope open fix follow-up tasks before adding new fixes",
                    "rationale": "Stacked open remediation tasks are a strong leading indicator of fix churn.",
                }
            )
        elif f.kind == "repeated_fix_attempts":
            recommendations.append(
                {
                    "priority": "high",
                    "action": "Pause patching and run a bounded RCA pass to converge one durable fix path",
                    "rationale": "Repeated partial fixes usually indicate unresolved causal understanding.",
                }
            )
        elif f.kind == "missing_repro_evidence":
            recommendations.append(
                {
                    "priority": "high",
                    "action": "Log a concrete reproduction note (for example `Repro: ...`) before finalizing",
                    "rationale": "Without a reproducible symptom, fixes drift into guesswork.",
                }
            )
        elif f.kind == "missing_root_cause_evidence":
            recommendations.append(
                {
                    "priority": "high",
                    "action": "Log an explicit causal statement (for example `RootCause: ...` or `RCA: ...`)",
                    "rationale": "A causal explanation reduces repeated symptom-level patching.",
                }
            )
        elif f.kind == "missing_regression_evidence":
            recommendations.append(
                {
                    "priority": "high",
                    "action": "Add regression evidence via changed tests or a `RegressionTest:` log note",
                    "rationale": "Regression proof is the minimum confidence boundary for defect fixes.",
                }
            )
        elif f.kind == "unsupported_schema":
            recommendations.append(
                {
                    "priority": "high",
                    "action": "Set fixdrift schema = 1",
                    "rationale": "Only schema v1 is currently supported.",
                }
            )

    seen_actions: set[str] = set()
    recommendations = [r for r in recommendations if not (r["action"] in seen_actions or seen_actions.add(r["action"]))]  # type: ignore[arg-type]

    return {
        "task_id": task_id,
        "task_title": task_title,
        "git_root": git_root,
        "score": score,
        "spec": asdict(spec),
        "telemetry": telemetry,
        "findings": [asdict(f) for f in findings],
        "recommendations": recommendations,
    }
