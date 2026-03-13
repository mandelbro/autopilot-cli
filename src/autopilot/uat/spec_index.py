"""UAT specification index builder.

Parses RFC and specification markdown documents to build a structured index
of requirements with section hierarchy, enabling traceability from tasks
to specific specification sections.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 — used at runtime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from typing import TextIO

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

# Patterns that indicate a requirement (MUST, SHALL, SHOULD, etc.)
_REQUIREMENT_RE = re.compile(
    r"\b(MUST|SHALL|SHOULD|WILL|REQUIRED|RECOMMENDED)\b",
    re.IGNORECASE,
)

# Verification type hints in text
_VERIFICATION_HINTS: dict[str, str] = {
    "api": "automated",
    "endpoint": "automated",
    "function": "automated",
    "interface": "automated",
    "test": "automated",
    "cli": "automated",
    "command": "automated",
    "design": "visual",
    "ux": "visual",
    "layout": "visual",
    "display": "visual",
}


@dataclass(frozen=True)
class SpecEntry:
    """A single requirement extracted from a specification document."""

    spec_id: str
    document: str
    section: str
    requirement_text: str
    verification_type: str = "manual"


@dataclass(frozen=True)
class SpecIndex:
    """Index of all requirements extracted from a specification document."""

    entries: list[SpecEntry] = field(default_factory=list)
    generated_at: str = ""
    total_requirements: int = 0
    testable_count: int = 0


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _infer_verification_type(text: str) -> str:
    """Infer the verification type from requirement text."""
    lower = text.lower()
    for keyword, vtype in _VERIFICATION_HINTS.items():
        if keyword in lower:
            return vtype
    return "manual"


def _is_testable(text: str) -> bool:
    """Determine if a requirement is testable (has a concrete assertion)."""
    lower = text.lower()
    testable_indicators = [
        "must",
        "shall",
        "should",
        "will",
        "required",
        "returns",
        "produces",
        "generates",
        "validates",
        "accepts",
        "rejects",
        "supports",
    ]
    return any(ind in lower for ind in testable_indicators)


class SpecIndexBuilder:
    """Builds a structured index from RFC/specification markdown files."""

    def build_rfc_index(self, rfc_path: Path) -> SpecIndex:
        """Parse an RFC markdown file and extract a structured requirement index.

        Extracts sections by heading hierarchy (##, ###) and identifies
        requirement-like sentences within each section.
        """
        if not rfc_path.exists():
            logger.warning("rfc_file_not_found", path=str(rfc_path))
            return SpecIndex(generated_at=_now_iso())

        text = rfc_path.read_text(encoding="utf-8")
        document = rfc_path.stem
        entries = self._extract_entries(text, document)

        testable = sum(1 for e in entries if _is_testable(e.requirement_text))

        return SpecIndex(
            entries=entries,
            generated_at=_now_iso(),
            total_requirements=len(entries),
            testable_count=testable,
        )

    def save_index(self, index: SpecIndex, output: Path | TextIO) -> None:
        """Serialize a SpecIndex to JSON."""
        data = asdict(index)
        if isinstance(output, Path):
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        else:
            json.dump(data, output, indent=2)

    def load_index(self, path: Path) -> SpecIndex:
        """Deserialize a SpecIndex from JSON."""
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = [SpecEntry(**e) for e in data.get("entries", [])]
        return SpecIndex(
            entries=entries,
            generated_at=data.get("generated_at", ""),
            total_requirements=data.get("total_requirements", 0),
            testable_count=data.get("testable_count", 0),
        )

    # -- private helpers ----------------------------------------------------

    def _extract_entries(self, text: str, document: str) -> list[SpecEntry]:
        """Extract requirement entries from markdown text."""
        entries: list[SpecEntry] = []
        lines = text.split("\n")

        # Track the current section hierarchy
        section_stack: list[str] = []
        section_number_stack: list[int] = []
        counter = 0

        for line in lines:
            heading_match = _HEADING_RE.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                # Only track ## and deeper (skip top-level #)
                if level < 2:
                    continue

                effective_level = level - 1  # ## is level 1 in our stack

                # Pop back to parent level
                while len(section_stack) >= effective_level:
                    section_stack.pop()
                    if section_number_stack:
                        section_number_stack.pop()

                section_stack.append(title)
                section_number_stack.append(level)
                continue

            # Check for requirement-like content in non-heading lines
            stripped = line.strip()
            if not stripped or not section_stack:
                continue

            if _REQUIREMENT_RE.search(stripped):
                counter += 1
                section_path = " > ".join(section_stack)
                spec_id = f"{document}-R{counter:03d}"
                verification_type = _infer_verification_type(stripped)

                entries.append(
                    SpecEntry(
                        spec_id=spec_id,
                        document=document,
                        section=section_path,
                        requirement_text=stripped,
                        verification_type=verification_type,
                    )
                )

        return entries


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(UTC).isoformat()
