from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from typing import Any


FENCE_INFO = "fixdrift"

_FENCE_RE = re.compile(
    r"```(?P<info>fixdrift)\s*\n(?P<body>.*?)\n```",
    re.DOTALL,
)


def extract_fixdrift_spec(description: str) -> str | None:
    m = _FENCE_RE.search(description or "")
    if not m:
        return None
    return m.group("body").strip()


def parse_fixdrift_spec(text: str) -> dict[str, Any]:
    data = tomllib.loads(text)
    if not isinstance(data, dict):
        raise ValueError("fixdrift block must parse to a TOML table/object.")
    return data


@dataclass(frozen=True)
class FixdriftSpec:
    schema: int
    min_open_fix_followups: int
    followup_prefixes: list[str]
    require_repro_log: bool
    repro_markers: list[str]
    require_root_cause_log: bool
    root_cause_markers: list[str]
    require_regression_signal: bool
    regression_markers: list[str]
    regression_test_globs: list[str]
    ignore_log_prefixes: list[str]
    ignore_paths: list[str]

    @staticmethod
    def from_raw(raw: dict[str, Any]) -> "FixdriftSpec":
        schema = int(raw.get("schema", 1))

        min_open_fix_followups = int(raw.get("min_open_fix_followups", 2))
        if min_open_fix_followups < 1:
            min_open_fix_followups = 1

        followup_prefixes = [
            str(x)
            for x in (
                raw.get("followup_prefixes")
                or ["drift-harden-", "drift-scope-", "drift-therapy-", "drift-fix-"]
            )
        ]

        require_repro_log = bool(raw.get("require_repro_log", True))
        repro_markers = [
            str(x)
            for x in (
                raw.get("repro_markers")
                or ["Repro:", "Reproduction:"]
            )
        ]

        require_root_cause_log = bool(raw.get("require_root_cause_log", True))
        root_cause_markers = [
            str(x)
            for x in (
                raw.get("root_cause_markers")
                or ["RootCause:", "RCA:"]
            )
        ]

        require_regression_signal = bool(raw.get("require_regression_signal", True))
        regression_markers = [
            str(x)
            for x in (
                raw.get("regression_markers")
                or ["RegressionTest:", "Added regression test:"]
            )
        ]
        regression_test_globs = [
            str(x)
            for x in (
                raw.get("regression_test_globs")
                or ["tests/**", "**/*test*.py", "**/*.test.*", "**/*.spec.*"]
            )
        ]

        ignore_log_prefixes = [str(x) for x in (raw.get("ignore_log_prefixes") or ["Fixdrift:"])]

        ignore_paths = [str(x) for x in (raw.get("ignore_paths") or [])]
        ignore_paths = [*ignore_paths, ".workgraph/**", ".git/**"]

        return FixdriftSpec(
            schema=schema,
            min_open_fix_followups=min_open_fix_followups,
            followup_prefixes=followup_prefixes,
            require_repro_log=require_repro_log,
            repro_markers=repro_markers,
            require_root_cause_log=require_root_cause_log,
            root_cause_markers=root_cause_markers,
            require_regression_signal=require_regression_signal,
            regression_markers=regression_markers,
            regression_test_globs=regression_test_globs,
            ignore_log_prefixes=ignore_log_prefixes,
            ignore_paths=ignore_paths,
        )
