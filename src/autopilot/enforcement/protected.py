"""Layer 5: Hash-based protected code regions (Task 064, RFC Section 3.5.2).

Detects #@protected markers in source files, validates hash integrity,
and alerts when protected code regions are modified without authorization.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)

_MARKER_RE = re.compile(r"^#@protected\s+(\d+)\s+([0-9a-fA-F]+)\s*$")


@dataclass(frozen=True)
class ProtectedRegion:
    """A hash-protected code region within a source file."""

    file_path: str
    start_line: int
    line_count: int
    hash_value: str
    region_id: str


@dataclass(frozen=True)
class ProtectionViolation:
    """A detected hash mismatch in a protected region."""

    region: ProtectedRegion
    expected_hash: str
    actual_hash: str
    message: str


def _hash_lines(lines: list[str]) -> str:
    """Compute the sha256 hex digest of joined *lines*."""
    return hashlib.sha256("".join(lines).encode()).hexdigest()


class ProtectedRegionManager:
    """Manages ``#@protected`` markers in source files.

    Marker format::

        #@protected <line_count> <sha256_hex>

    The marker declares that the *line_count* lines immediately following it
    are protected and must hash to *sha256_hex*.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self, file_path: Path) -> list[ProtectedRegion]:
        """Parse *file_path* and return all :class:`ProtectedRegion` entries."""
        lines = self._read_lines(file_path)
        regions: list[ProtectedRegion] = []

        idx = 0
        while idx < len(lines):
            match = _MARKER_RE.match(lines[idx])
            if match:
                line_count = int(match.group(1))
                hash_value = match.group(2)
                # start_line is the 1-indexed line of the first protected line
                start_line = idx + 2  # marker is idx (0-based), so +1 for 1-index, +1 for next line
                protected_lines = lines[idx + 1 : idx + 1 + line_count]
                actual_hash = _hash_lines(protected_lines)
                region = ProtectedRegion(
                    file_path=str(file_path),
                    start_line=start_line,
                    line_count=line_count,
                    hash_value=hash_value,
                    region_id=f"{file_path}:{start_line}",
                )
                regions.append(region)
                _log.debug(
                    "found protected region",
                    extra={
                        "region_id": region.region_id,
                        "hash_match": actual_hash == hash_value,
                    },
                )
                idx += 1 + line_count
            else:
                idx += 1

        return regions

    def validate(self, file_path: Path) -> list[ProtectionViolation]:
        """Return violations for regions whose hash no longer matches."""
        lines = self._read_lines(file_path)
        violations: list[ProtectionViolation] = []

        idx = 0
        while idx < len(lines):
            match = _MARKER_RE.match(lines[idx])
            if match:
                line_count = int(match.group(1))
                expected_hash = match.group(2)
                start_line = idx + 2
                protected_lines = lines[idx + 1 : idx + 1 + line_count]
                actual_hash = _hash_lines(protected_lines)

                if actual_hash != expected_hash:
                    region = ProtectedRegion(
                        file_path=str(file_path),
                        start_line=start_line,
                        line_count=line_count,
                        hash_value=expected_hash,
                        region_id=f"{file_path}:{start_line}",
                    )
                    violations.append(
                        ProtectionViolation(
                            region=region,
                            expected_hash=expected_hash,
                            actual_hash=actual_hash,
                            message=(
                                f"Protected region {region.region_id} hash mismatch: "
                                f"expected {expected_hash[:12]}... got {actual_hash[:12]}..."
                            ),
                        )
                    )
                idx += 1 + line_count
            else:
                idx += 1

        return violations

    def protect(self, file_path: Path, start_line: int, line_count: int) -> ProtectedRegion:
        """Add a ``#@protected`` marker before *start_line* (1-indexed).

        Reads *line_count* lines starting at *start_line*, computes their
        sha256 hash, and inserts a marker comment on the line before them.
        Returns the resulting :class:`ProtectedRegion`.
        """
        lines = self._read_lines(file_path)
        # start_line is 1-indexed
        start_idx = start_line - 1
        protected_lines = lines[start_idx : start_idx + line_count]
        hash_value = _hash_lines(protected_lines)

        marker = f"#@protected {line_count} {hash_value}\n"
        lines.insert(start_idx, marker)
        file_path.write_text("".join(lines))

        # After insertion the protected lines start one line later
        new_start_line = start_line + 1
        region = ProtectedRegion(
            file_path=str(file_path),
            start_line=new_start_line,
            line_count=line_count,
            hash_value=hash_value,
            region_id=f"{file_path}:{new_start_line}",
        )
        _log.info("protected region created", extra={"region_id": region.region_id})
        return region

    def update_hash(self, file_path: Path, region_id: str) -> ProtectedRegion | None:
        """Recompute and update the hash for *region_id*.

        Returns the updated :class:`ProtectedRegion`, or ``None`` if the
        *region_id* was not found in the file.
        """
        lines = self._read_lines(file_path)

        idx = 0
        while idx < len(lines):
            match = _MARKER_RE.match(lines[idx])
            if match:
                line_count = int(match.group(1))
                start_line = idx + 2
                candidate_id = f"{file_path}:{start_line}"

                if candidate_id == region_id:
                    protected_lines = lines[idx + 1 : idx + 1 + line_count]
                    new_hash = _hash_lines(protected_lines)
                    lines[idx] = f"#@protected {line_count} {new_hash}\n"
                    file_path.write_text("".join(lines))

                    region = ProtectedRegion(
                        file_path=str(file_path),
                        start_line=start_line,
                        line_count=line_count,
                        hash_value=new_hash,
                        region_id=region_id,
                    )
                    _log.info(
                        "protected region hash updated",
                        extra={"region_id": region_id},
                    )
                    return region

                idx += 1 + line_count
            else:
                idx += 1

        _log.warning("region not found", extra={"region_id": region_id})
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_lines(file_path: Path) -> list[str]:
        """Read *file_path* and return its lines (with newlines preserved)."""
        with open(file_path) as fh:
            return fh.readlines()
