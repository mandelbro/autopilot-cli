"""Layer 4: Agent guardrails for Claude Code sessions (Task 063, RFC Section 3.5.2).

Generates PreToolUse/PostToolUse hook rules with progressive trust and
circuit breaker to prevent agent lockup. Security rules are exempt from
progressive trust (always error). Target < 10ms evaluation per rule.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class GuardrailRule:
    """A single guardrail rule for a Claude Code hook."""

    name: str
    hook_type: str  # "PreToolUse" or "PostToolUse"
    pattern: str  # regex pattern to match
    action: str  # "block" or "warn"
    message: str
    is_security: bool = False  # exempt from progressive trust
    trigger_count: int = 0  # for progressive trust tracking


class GuardrailsGenerator:
    """Generates and manages PreToolUse/PostToolUse guardrail rules."""

    def generate_pretooluse_rules(self) -> list[GuardrailRule]:
        """Generate PreToolUse rules that block dangerous operations.

        Returns rules blocking: git commit --no-verify, deleting protected
        files (.env, config), and installing unauthorized dependencies.
        """
        return [
            GuardrailRule(
                name="block_no_verify_commit",
                hook_type="PreToolUse",
                pattern=r"git\s+commit\s+.*--no-verify",
                action="block",
                message="Blocked: git commit --no-verify bypasses safety hooks",
                is_security=True,
            ),
            GuardrailRule(
                name="block_protected_file_deletion",
                hook_type="PreToolUse",
                pattern=r"rm\s+.*\.(env|config|credentials|key|pem)",
                action="block",
                message="Blocked: deletion of protected file (.env, config, credentials)",
                is_security=True,
            ),
            GuardrailRule(
                name="block_unauthorized_pip_install",
                hook_type="PreToolUse",
                pattern=r"pip\s+install\s+.*--index-url\s+(?!https://pypi\.org)",
                action="block",
                message="Blocked: pip install from unauthorized source",
                is_security=True,
            ),
            GuardrailRule(
                name="block_force_push",
                hook_type="PreToolUse",
                pattern=r"git\s+push\s+.*--force",
                action="block",
                message="Blocked: git push --force can destroy remote history",
                is_security=True,
            ),
        ]

    def generate_posttooluse_rules(self) -> list[GuardrailRule]:
        """Generate PostToolUse rules that warn on risky outcomes.

        Returns rules warning on: large file modifications (>500 lines
        changed) and dependency additions.
        """
        return [
            GuardrailRule(
                name="warn_large_file_modification",
                hook_type="PostToolUse",
                pattern=r"(?:insertions|deletions).{0,20}(?:[5-9]\d{2}|\d{4,})",
                action="warn",
                message="Warning: large file modification detected (>500 lines changed)",
            ),
            GuardrailRule(
                name="warn_dependency_addition",
                hook_type="PostToolUse",
                pattern=r"(?:pip\s+install|poetry\s+add|npm\s+install)\s+\S+",
                action="warn",
                message="Warning: new dependency added — verify it is approved",
            ),
        ]

    def generate_settings_json(self, rules: list[GuardrailRule]) -> dict[str, Any]:
        """Produce a dict for ``.claude/settings.json`` from guardrail rules.

        Groups rules by hook_type into the ``hooks`` key.
        """
        hooks: dict[str, list[dict[str, str]]] = {
            "PreToolUse": [],
            "PostToolUse": [],
        }

        for rule in rules:
            entry = {
                "pattern": rule.pattern,
                "action": rule.action,
                "message": rule.message,
            }
            hooks[rule.hook_type].append(entry)

        return {"hooks": hooks}

    def apply_progressive_trust(
        self,
        rule: GuardrailRule,
        consecutive_triggers: int,
        threshold: int = 3,
    ) -> GuardrailRule:
        """Downgrade a non-security rule after repeated triggers.

        If *is_security* is ``True`` the rule is returned unchanged regardless
        of how many times it has triggered.  Otherwise, when
        *consecutive_triggers* >= *threshold* the action is downgraded from
        ``"block"`` to ``"warn"``.
        """
        if rule.is_security:
            return rule

        if consecutive_triggers >= threshold and rule.action == "block":
            return replace(
                rule,
                action="warn",
                trigger_count=consecutive_triggers,
            )

        return replace(rule, trigger_count=consecutive_triggers)

    def write_settings(self, project_root: Path, settings: dict[str, Any]) -> Path:
        """Write *settings* to ``.claude/settings.json`` under *project_root*.

        Creates the ``.claude`` directory if it does not exist.  Returns the
        path to the written file.
        """
        settings_dir = project_root / ".claude"
        settings_dir.mkdir(parents=True, exist_ok=True)

        settings_path = settings_dir / "settings.json"
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")

        return settings_path
