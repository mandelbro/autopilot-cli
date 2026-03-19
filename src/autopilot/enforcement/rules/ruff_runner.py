"""Shared ruff output parser for enforcement rules.

Runs ``ruff check`` with specific rule codes and converts JSON output
into Violation objects.  Used by Categories 2-11 to avoid duplicating
the ruff invocation and parsing logic.
"""

from __future__ import annotations

import json
import subprocess
import time
from typing import TYPE_CHECKING, cast

from autopilot.core.models import CheckResult, Violation, ViolationSeverity

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def run_ruff_check(
    files: Sequence[Path],
    *,
    select_codes: list[str],
    category: str,
    rule_name: str,
    severity: ViolationSeverity = ViolationSeverity.WARNING,
) -> CheckResult:
    """Run ``ruff check --select <codes>`` and return a CheckResult.

    Falls back to an empty result if ruff is not installed or fails.
    """
    start = time.monotonic()
    existing = [str(f) for f in files if f.exists()]
    if not existing:
        return CheckResult(category=category, files_scanned=0)

    select_arg = ",".join(select_codes)
    cmd = [
        "ruff",
        "check",
        "--select",
        select_arg,
        "--output-format",
        "json",
        "--no-fix",
        *existing,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        elapsed = time.monotonic() - start
        return CheckResult(
            category=category,
            files_scanned=len(existing),
            duration_seconds=elapsed,
        )

    violations = _parse_ruff_json(
        result.stdout,
        category=category,
        rule_name=rule_name,
        severity=severity,
    )
    elapsed = time.monotonic() - start
    return CheckResult(
        category=category,
        violations=tuple(violations),
        files_scanned=len(existing),
        duration_seconds=elapsed,
    )


def _parse_ruff_json(
    raw: str,
    *,
    category: str,
    rule_name: str,
    severity: ViolationSeverity,
) -> list[Violation]:
    """Parse ruff JSON output into Violation objects."""
    if not raw.strip():
        return []
    try:
        entries: object = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(entries, list):
        return []

    violations: list[Violation] = []
    for entry_raw in cast("list[object]", entries):
        if not isinstance(entry_raw, dict):
            continue
        entry = cast("dict[str, object]", entry_raw)
        code = str(entry.get("code", ""))
        message = str(entry.get("message", ""))
        filename = str(entry.get("filename", ""))
        raw_location = entry.get("location", {})
        location = cast("dict[str, object]", raw_location) if isinstance(raw_location, dict) else {}
        line_val = location.get("row", 0)
        line = int(line_val) if isinstance(line_val, int | float) else 0

        violations.append(
            Violation(
                category=category,
                rule=f"{rule_name}:{code}",
                file=filename,
                line=line,
                message=f"[{code}] {message}",
                severity=severity,
            )
        )
    return violations
