"""DebuggingTool protocol and supporting data models.

Defines the runtime-checkable protocol that all debugging tool adapters must
satisfy, along with frozen dataclasses for interaction results, diagnostic
evidence, UX observations, and provisioning status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable

PROTOCOL_VERSION: int = 1


# -- Enums --


class ToolCapability(StrEnum):
    """Capabilities a debugging tool may advertise."""

    INTERACTIVE_TEST = "interactive_test"
    CONSOLE_CAPTURE = "console_capture"
    NETWORK_CAPTURE = "network_capture"
    SCREENSHOT = "screenshot"
    UX_REVIEW = "ux_review"


# -- Frozen dataclasses --


@dataclass(frozen=True)
class InteractionResult:
    """Outcome of a single tool interaction step."""

    success: bool
    screenshot_path: str = ""
    console_output: str = ""
    network_log: str = ""
    observation: str = ""
    error: str = ""


@dataclass(frozen=True)
class DiagnosticEvidence:
    """Collected diagnostic artefacts from a debugging session."""

    screenshots: tuple[str, ...] = ()
    console_errors: tuple[str, ...] = ()
    network_failures: tuple[str, ...] = ()
    state_dumps: tuple[str, ...] = ()
    observations: str = ""


@dataclass(frozen=True)
class UXObservation:
    """A single UX quality observation."""

    category: str
    severity: str
    description: str
    screenshot_path: str = ""
    element_reference: str = ""


@dataclass(frozen=True)
class ProvisionResult:
    """Outcome of provisioning a debugging tool environment."""

    success: bool
    components_installed: tuple[str, ...] = ()
    manual_steps: tuple[str, ...] = ()
    error: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class ProvisionStatus:
    """Current provisioning state of a debugging tool."""

    provisioned: bool
    ready: bool
    components: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    message: str = ""


# -- Protocol --


@runtime_checkable
class DebuggingTool(Protocol):
    """Protocol that all debugging tool adapters must satisfy.

    The debugging agent discovers tools via isinstance(obj, DebuggingTool),
    so this protocol is marked @runtime_checkable.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this debugging tool."""
        ...

    @property
    def capabilities(self) -> frozenset[ToolCapability]:
        """Set of capabilities this tool provides."""
        ...

    def provision(self, settings: dict[str, object]) -> ProvisionResult:
        """Install or set up required tool components."""
        ...

    def deprovision(self) -> None:
        """Remove tool components and clean up resources."""
        ...

    def check_provisioned(self) -> ProvisionStatus:
        """Return current provisioning status."""
        ...

    def setup(self, settings: dict[str, object]) -> None:
        """Prepare the tool for a debugging session."""
        ...

    def teardown(self) -> None:
        """Clean up after a debugging session."""
        ...

    def execute_step(
        self,
        action: str,
        target: str,
        *,
        value: str = "",
        expect: str = "",
        timeout_seconds: int = 30,
    ) -> InteractionResult:
        """Execute a single interaction step against the target application."""
        ...

    def capture_diagnostic_evidence(self) -> DiagnosticEvidence:
        """Gather all available diagnostic artefacts."""
        ...

    def capture_screenshot(self, label: str) -> str:
        """Take a labelled screenshot and return its file path."""
        ...

    def evaluate_ux(
        self,
        criteria: tuple[str, ...],
        design_system_ref: str = "",
    ) -> tuple[UXObservation, ...]:
        """Evaluate UX quality against the given criteria."""
        ...
