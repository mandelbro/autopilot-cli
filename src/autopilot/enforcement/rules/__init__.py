"""Enforcement rules package for Autopilot CLI.

Each rule implements the EnforcementRule protocol defined in base.py and
returns a CheckResult containing zero or more Violation objects.
"""

from autopilot.enforcement.rules.base import EnforcementRule, RuleConfig

__all__ = ["EnforcementRule", "RuleConfig"]
