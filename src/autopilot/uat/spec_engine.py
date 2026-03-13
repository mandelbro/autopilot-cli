"""UAT specification cross-reference engine.

Parses explicit specification references from task context and builds
traceability matrices mapping tasks to RFC sections, discovery requirements,
and UX design elements per UAT Discovery specification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from autopilot.uat.task_context import SpecReference, TaskContext  # noqa: TC001

# ---------------------------------------------------------------------------
# Regex patterns for explicit reference matching
# ---------------------------------------------------------------------------

# "RFC Section 3.4.1" or "RFC 3.4.1"
_RFC_RE = re.compile(r"RFC\s+(?:Section\s+)?([\d]+(?:\.[\d]+)*)", re.IGNORECASE)

# "UX Design Section 4.1"
_UX_RE = re.compile(r"UX\s+Design\s+Section\s+([\d]+(?:\.[\d]+)*)", re.IGNORECASE)

# "Discovery ADR-5", "Discovery: Task Management", "Discovery ADR-026"
_DISCOVERY_RE = re.compile(r"Discovery\s+(?::?\s*)?([\w][\w-]*)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceabilityMatrix:
    """Maps a task to its specification references with coverage scoring."""

    task_id: str
    rfc_sections: list[str] = field(default_factory=list)
    discovery_requirements: list[str] = field(default_factory=list)
    ux_elements: list[str] = field(default_factory=list)
    coverage_score: float = 0.0
    unmapped_specs: list[str] = field(default_factory=list)
    unmapped_tasks: list[str] = field(default_factory=list)

    def __hash__(self) -> int:  # pragma: no cover
        return hash(self.task_id)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class SpecCrossReferenceEngine:
    """Matches explicit specification references from task context."""

    def match_explicit_references(self, context: TaskContext) -> list[SpecReference]:
        """Extract all explicit spec references from a task context.

        Scans both ``spec_references`` and ``prompt_text`` for patterns
        like ``RFC Section 3.4.1``, ``UX Design Section 4.1``, and
        ``Discovery ADR-5``.
        """
        refs: list[SpecReference] = []
        seen: set[tuple[str, str]] = set()

        # Scan existing spec_references for additional regex matches
        for ref in context.spec_references:
            key = (ref.document, ref.section)
            if key not in seen:
                refs.append(ref)
                seen.add(key)

        # Scan prompt text for explicit references
        text = context.prompt_text
        if text:
            refs.extend(self._scan_text(text, seen))

        # Also scan user_story and outcome
        for extra_text in (context.user_story, context.outcome):
            if extra_text:
                refs.extend(self._scan_text(extra_text, seen))

        return refs

    def _scan_text(self, text: str, seen: set[tuple[str, str]]) -> list[SpecReference]:
        """Scan free text for explicit spec reference patterns."""
        refs: list[SpecReference] = []

        for m in _RFC_RE.finditer(text):
            section = m.group(1)
            key = ("RFC", section)
            if key not in seen:
                seen.add(key)
                refs.append(
                    SpecReference(
                        document="RFC",
                        section=section,
                        verification_type="automated",
                    )
                )

        for m in _UX_RE.finditer(text):
            section = m.group(1)
            key = ("UX Design", section)
            if key not in seen:
                seen.add(key)
                refs.append(
                    SpecReference(
                        document="UX Design",
                        section=section,
                        verification_type="visual",
                    )
                )

        for m in _DISCOVERY_RE.finditer(text):
            requirement = m.group(1)
            key = ("Discovery", requirement)
            if key not in seen:
                seen.add(key)
                refs.append(
                    SpecReference(
                        document="Discovery",
                        section="",
                        requirement=requirement,
                        verification_type="manual",
                    )
                )

        return refs


# ---------------------------------------------------------------------------
# Traceability matrix builder
# ---------------------------------------------------------------------------


def build_traceability_matrix(context: TaskContext) -> TraceabilityMatrix:
    """Build a traceability matrix from a task context's explicit references.

    Coverage score is computed as the fraction of specification categories
    (RFC, Discovery, UX Design) that have at least one reference, yielding
    a value between 0.0 and 1.0.
    """
    engine = SpecCrossReferenceEngine()
    refs = engine.match_explicit_references(context)

    rfc_sections: list[str] = []
    discovery_requirements: list[str] = []
    ux_elements: list[str] = []
    unmapped: list[str] = []

    seen_rfc: set[str] = set()
    seen_disc: set[str] = set()
    seen_ux: set[str] = set()

    for ref in refs:
        doc_lower = ref.document.lower()
        if "rfc" in doc_lower:
            label = f"Section {ref.section}" if ref.section else ref.requirement
            if label and label not in seen_rfc:
                rfc_sections.append(label)
                seen_rfc.add(label)
        elif "discovery" in doc_lower:
            label = ref.requirement or ref.section
            if label and label not in seen_disc:
                discovery_requirements.append(label)
                seen_disc.add(label)
        elif "ux" in doc_lower:
            label = f"Section {ref.section}" if ref.section else ref.requirement
            if label and label not in seen_ux:
                ux_elements.append(label)
                seen_ux.add(label)
        else:
            desc = f"{ref.document}"
            if ref.section:
                desc += f" Section {ref.section}"
            if ref.requirement:
                desc += f": {ref.requirement}"
            unmapped.append(desc)

    # Coverage score: fraction of 3 categories with at least one reference
    categories_covered = sum(
        1 for bucket in (rfc_sections, discovery_requirements, ux_elements) if bucket
    )
    coverage_score = round(categories_covered / 3.0, 2)

    return TraceabilityMatrix(
        task_id=context.task_id,
        rfc_sections=rfc_sections,
        discovery_requirements=discovery_requirements,
        ux_elements=ux_elements,
        coverage_score=coverage_score,
        unmapped_specs=unmapped,
    )
