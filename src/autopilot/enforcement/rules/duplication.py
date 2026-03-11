"""Category 1 enforcement rule: Infrastructure Duplication detection.

Detects structurally similar code blocks (≥ min_lines lines, ≥ similarity_threshold
structural similarity) across the scanned Python files using Python's ``ast``
module.  No third-party dependencies are required.

Detection strategy
------------------
1. Parse each file into an AST.
2. Extract top-level and class-level function definitions as candidate blocks.
3. Normalise each AST block by replacing all Name/identifier tokens with a
   canonical placeholder — this makes two functions that differ only in
   variable names appear structurally identical.
4. Compare every cross-file pair of blocks whose line span meets min_lines.
5. Compute similarity as:
     len(common_nodes) / max(len(a_nodes), len(b_nodes))
   where nodes are the sequence of AST node *type names* in depth-first order.
6. Pairs whose similarity ≥ threshold yield a Violation for the file that
   appears first alphabetically (deterministic ordering).

Test files (name starts with ``test_`` or ends with ``_test.py``) are
excluded from analysis to avoid false positives from test fixtures.
"""

from __future__ import annotations

import ast
import os
import time
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

from autopilot.core.models import CheckResult, Violation
from autopilot.enforcement.rules.base import RuleConfig

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_test_file(path: Path) -> bool:
    """Return True if *path* looks like a test file that should be excluded."""
    name = os.path.basename(os.fspath(path))
    return name.startswith("test_") or name.endswith("_test.py")


def _node_type_sequence(node: ast.AST) -> list[str]:
    """Return a depth-first sequence of AST node type names for *node*.

    All ``ast.Name`` ids and ``ast.arg`` annotations are replaced with the
    canonical placeholder ``"_ID_"`` so that functions differing only in
    identifier names are seen as structurally identical.
    """
    tokens: list[str] = []
    for child in ast.walk(node):
        type_name = type(child).__name__
        # Normalise identifiers so name differences don't affect similarity.
        if isinstance(child, ast.Name):
            tokens.append("Name:_ID_")
        elif isinstance(child, ast.arg):
            tokens.append("arg:_ID_")
        elif isinstance(child, ast.Attribute):
            tokens.append("Attribute:_ID_")
        else:
            tokens.append(type_name)
    return tokens


def _block_line_span(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Return the number of source lines covered by *node*."""
    end = getattr(node, "end_lineno", node.lineno)
    return end - node.lineno + 1


def _similarity(seq_a: list[str], seq_b: list[str]) -> float:
    """Return structural similarity ratio in [0.0, 1.0] between two sequences."""
    if not seq_a or not seq_b:
        return 0.0
    matcher = SequenceMatcher(None, seq_a, seq_b, autojunk=False)
    return matcher.ratio()


def _extract_functions(
    tree: ast.AST,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Extract all top-level and class-level function/async-function defs."""
    funcs: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(node)
    return funcs


def _make_suggestion(func_name: str, other_file: str) -> str:
    basename = os.path.basename(other_file)
    return (
        f"Extract '{func_name}' into a shared utility module instead of "
        f"duplicating it in '{basename}'. "
        "See docs/development-standards/ for guidance on shared libraries."
    )


def _make_message(func_name: str, other_file: str, similarity: float, line: int) -> str:
    pct = int(similarity * 100)
    basename = os.path.basename(other_file)
    return (
        f"Duplicate code block: function '{func_name}' at line {line} is "
        f"{pct}% structurally similar to a block in '{basename}'."
    )


# ---------------------------------------------------------------------------
# Public rule
# ---------------------------------------------------------------------------


class DuplicationRule:
    """Enforcement rule that detects duplicate code blocks across Python files.

    Satisfies the ``EnforcementRule`` protocol.

    Args:
        config: Optional ``RuleConfig`` overriding defaults (min_lines,
            similarity_threshold, severity).
    """

    def __init__(self, config: RuleConfig | None = None) -> None:
        self._config = config or RuleConfig()

    # -- EnforcementRule protocol --

    @property
    def category(self) -> str:
        return "duplication"

    @property
    def name(self) -> str:
        return "duplicate-code-blocks"

    def check(self, files: Sequence[Path]) -> CheckResult:
        """Analyse *files* for structurally similar code blocks.

        Test files are excluded.  Files that do not exist or contain syntax
        errors are silently skipped.

        Returns:
            A ``CheckResult`` with category ``"duplication"``.
        """
        start = time.monotonic()

        # Filter to parseable, non-test Python files
        parsed: list[tuple[Path, list[ast.FunctionDef | ast.AsyncFunctionDef]]] = []
        for path in files:
            if _is_test_file(path):
                continue
            tree = _parse_safe(path)
            if tree is None:
                continue
            funcs = _extract_functions(tree)
            parsed.append((path, funcs))

        violations: list[Violation] = []
        seen_pairs: set[frozenset[str]] = set()

        cfg = self._config
        for i, (path_a, funcs_a) in enumerate(parsed):
            for path_b, funcs_b in parsed[i + 1 :]:
                for func_a in funcs_a:
                    if _block_line_span(func_a) < cfg.min_lines:
                        continue
                    seq_a = _node_type_sequence(func_a)
                    for func_b in funcs_b:
                        if _block_line_span(func_b) < cfg.min_lines:
                            continue
                        # Deduplicate: same pair of (file:line) only once
                        pair_key = frozenset(
                            [
                                f"{path_a}:{func_a.lineno}",
                                f"{path_b}:{func_b.lineno}",
                            ]
                        )
                        if pair_key in seen_pairs:
                            continue

                        seq_b = _node_type_sequence(func_b)
                        sim = _similarity(seq_a, seq_b)
                        if sim >= cfg.similarity_threshold:
                            seen_pairs.add(pair_key)
                            violations.append(
                                Violation(
                                    category=self.category,
                                    rule=self.name,
                                    file=str(path_a),
                                    line=func_a.lineno,
                                    message=_make_message(
                                        func_a.name,
                                        str(path_b),
                                        sim,
                                        func_a.lineno,
                                    ),
                                    severity=cfg.severity,
                                    suggestion=_make_suggestion(func_a.name, str(path_b)),
                                )
                            )

        elapsed = time.monotonic() - start
        return CheckResult(
            category=self.category,
            violations=tuple(violations),
            files_scanned=len(parsed),
            duration_seconds=elapsed,
        )


# ---------------------------------------------------------------------------
# Private utilities
# ---------------------------------------------------------------------------


def _parse_safe(path: Path) -> ast.AST | None:
    """Parse *path* into an AST, returning None on any error."""
    try:
        filepath = os.fspath(path)
        with open(filepath, encoding="utf-8", errors="replace") as fh:
            source = fh.read()
        return ast.parse(source, filename=filepath)
    except (OSError, SyntaxError, ValueError):
        return None
