"""Tests for Layer 4 agent guardrails (Task 063)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.enforcement.guardrails import GuardrailRule, GuardrailsGenerator


class TestPreToolUseRules:
    def setup_method(self) -> None:
        self.gen = GuardrailsGenerator()
        self.rules = self.gen.generate_pretooluse_rules()

    def test_returns_at_least_three_rules(self) -> None:
        assert len(self.rules) >= 3

    def test_all_rules_are_pretooluse(self) -> None:
        for rule in self.rules:
            assert rule.hook_type == "PreToolUse"

    def test_blocks_no_verify_commit(self) -> None:
        names = [r.name for r in self.rules]
        assert "block_no_verify_commit" in names
        rule = next(r for r in self.rules if r.name == "block_no_verify_commit")
        assert rule.action == "block"
        assert rule.is_security is True

    def test_blocks_protected_file_deletion(self) -> None:
        names = [r.name for r in self.rules]
        assert "block_protected_file_deletion" in names
        rule = next(r for r in self.rules if r.name == "block_protected_file_deletion")
        assert rule.action == "block"
        assert rule.is_security is True

    def test_blocks_unauthorized_pip_install(self) -> None:
        names = [r.name for r in self.rules]
        assert "block_unauthorized_pip_install" in names
        rule = next(r for r in self.rules if r.name == "block_unauthorized_pip_install")
        assert rule.action == "block"
        assert rule.is_security is True

    def test_all_pretooluse_rules_have_block_action(self) -> None:
        for rule in self.rules:
            assert rule.action == "block"

    def test_all_pretooluse_rules_are_security(self) -> None:
        for rule in self.rules:
            assert rule.is_security is True


class TestPostToolUseRules:
    def setup_method(self) -> None:
        self.gen = GuardrailsGenerator()
        self.rules = self.gen.generate_posttooluse_rules()

    def test_returns_at_least_two_rules(self) -> None:
        assert len(self.rules) >= 2

    def test_all_rules_are_posttooluse(self) -> None:
        for rule in self.rules:
            assert rule.hook_type == "PostToolUse"

    def test_warns_on_large_file_modification(self) -> None:
        names = [r.name for r in self.rules]
        assert "warn_large_file_modification" in names
        rule = next(r for r in self.rules if r.name == "warn_large_file_modification")
        assert rule.action == "warn"

    def test_warns_on_dependency_addition(self) -> None:
        names = [r.name for r in self.rules]
        assert "warn_dependency_addition" in names
        rule = next(r for r in self.rules if r.name == "warn_dependency_addition")
        assert rule.action == "warn"

    def test_posttooluse_rules_are_not_security(self) -> None:
        for rule in self.rules:
            assert rule.is_security is False


class TestProgressiveTrust:
    def setup_method(self) -> None:
        self.gen = GuardrailsGenerator()

    def test_downgrades_non_security_rule_after_threshold(self) -> None:
        rule = GuardrailRule(
            name="test_rule",
            hook_type="PreToolUse",
            pattern=r"test",
            action="block",
            message="test message",
            is_security=False,
        )
        result = self.gen.apply_progressive_trust(rule, consecutive_triggers=3)
        assert result.action == "warn"
        assert result.trigger_count == 3

    def test_does_not_downgrade_below_threshold(self) -> None:
        rule = GuardrailRule(
            name="test_rule",
            hook_type="PreToolUse",
            pattern=r"test",
            action="block",
            message="test message",
            is_security=False,
        )
        result = self.gen.apply_progressive_trust(rule, consecutive_triggers=2)
        assert result.action == "block"
        assert result.trigger_count == 2

    def test_security_rules_never_downgraded(self) -> None:
        rule = GuardrailRule(
            name="security_rule",
            hook_type="PreToolUse",
            pattern=r"test",
            action="block",
            message="security message",
            is_security=True,
        )
        result = self.gen.apply_progressive_trust(rule, consecutive_triggers=100)
        assert result.action == "block"
        assert result.is_security is True

    def test_custom_threshold(self) -> None:
        rule = GuardrailRule(
            name="test_rule",
            hook_type="PreToolUse",
            pattern=r"test",
            action="block",
            message="test message",
            is_security=False,
        )
        result = self.gen.apply_progressive_trust(rule, consecutive_triggers=5, threshold=5)
        assert result.action == "warn"

    def test_warn_action_stays_warn(self) -> None:
        rule = GuardrailRule(
            name="test_rule",
            hook_type="PostToolUse",
            pattern=r"test",
            action="warn",
            message="test message",
            is_security=False,
        )
        result = self.gen.apply_progressive_trust(rule, consecutive_triggers=10)
        assert result.action == "warn"


class TestSettingsJson:
    def setup_method(self) -> None:
        self.gen = GuardrailsGenerator()

    def test_settings_is_valid_dict(self) -> None:
        rules = self.gen.generate_pretooluse_rules() + self.gen.generate_posttooluse_rules()
        settings = self.gen.generate_settings_json(rules)
        assert isinstance(settings, dict)

    def test_settings_has_hooks_key(self) -> None:
        rules = self.gen.generate_pretooluse_rules()
        settings = self.gen.generate_settings_json(rules)
        assert "hooks" in settings

    def test_settings_has_pretooluse_and_posttooluse(self) -> None:
        rules = self.gen.generate_pretooluse_rules() + self.gen.generate_posttooluse_rules()
        settings = self.gen.generate_settings_json(rules)
        assert "PreToolUse" in settings["hooks"]
        assert "PostToolUse" in settings["hooks"]

    def test_pretooluse_entries_have_required_keys(self) -> None:
        rules = self.gen.generate_pretooluse_rules()
        settings = self.gen.generate_settings_json(rules)
        for entry in settings["hooks"]["PreToolUse"]:
            assert "pattern" in entry
            assert "action" in entry
            assert "message" in entry

    def test_posttooluse_entries_have_required_keys(self) -> None:
        rules = self.gen.generate_posttooluse_rules()
        settings = self.gen.generate_settings_json(rules)
        for entry in settings["hooks"]["PostToolUse"]:
            assert "pattern" in entry
            assert "action" in entry
            assert "message" in entry

    def test_settings_is_json_serializable(self) -> None:
        rules = self.gen.generate_pretooluse_rules() + self.gen.generate_posttooluse_rules()
        settings = self.gen.generate_settings_json(rules)
        serialized = json.dumps(settings)
        assert isinstance(serialized, str)


class TestWriteSettings:
    def test_creates_settings_file(self, tmp_path: Path) -> None:
        gen = GuardrailsGenerator()
        rules = gen.generate_pretooluse_rules() + gen.generate_posttooluse_rules()
        settings = gen.generate_settings_json(rules)
        result_path = gen.write_settings(tmp_path, settings)

        assert result_path.exists()
        assert result_path.name == "settings.json"
        assert result_path.parent.name == ".claude"

    def test_written_file_is_valid_json(self, tmp_path: Path) -> None:
        gen = GuardrailsGenerator()
        rules = gen.generate_pretooluse_rules()
        settings = gen.generate_settings_json(rules)
        result_path = gen.write_settings(tmp_path, settings)

        content = json.loads(result_path.read_text())
        assert "hooks" in content

    def test_creates_claude_directory(self, tmp_path: Path) -> None:
        gen = GuardrailsGenerator()
        settings = gen.generate_settings_json([])
        gen.write_settings(tmp_path, settings)

        assert (tmp_path / ".claude").is_dir()


class TestGuardrailRuleDataclass:
    def test_frozen(self) -> None:
        rule = GuardrailRule(
            name="test",
            hook_type="PreToolUse",
            pattern="test",
            action="block",
            message="msg",
        )
        try:
            rule.name = "changed"  # type: ignore[misc]
            raised = False
        except AttributeError:
            raised = True
        assert raised, "GuardrailRule should be frozen"

    def test_default_values(self) -> None:
        rule = GuardrailRule(
            name="test",
            hook_type="PreToolUse",
            pattern="test",
            action="block",
            message="msg",
        )
        assert rule.is_security is False
        assert rule.trigger_count == 0
