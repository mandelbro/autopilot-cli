"""Tests for orchestration hooks (Task 088)."""

from __future__ import annotations

from autopilot.orchestration.hooks import HookConfig, HookResult, HookRunner


class TestHookRunnerRunHooks:
    """Tests for HookRunner.run_hooks execution."""

    def test_executes_matching_hooks_only(self) -> None:
        hooks = [
            HookConfig(hook_point="pre_cycle", command="echo pre"),
            HookConfig(hook_point="post_cycle", command="echo post"),
        ]
        runner = HookRunner(hooks)

        results = runner.run_hooks("pre_cycle")

        assert len(results) == 1
        assert results[0].hook_point == "pre_cycle"
        assert results[0].exit_code == 0

    def test_executes_multiple_hooks_for_same_point(self) -> None:
        hooks = [
            HookConfig(hook_point="pre_cycle", command="echo first"),
            HookConfig(hook_point="pre_cycle", command="echo second"),
        ]
        runner = HookRunner(hooks)

        results = runner.run_hooks("pre_cycle")

        assert len(results) == 2
        assert all(r.exit_code == 0 for r in results)

    def test_successful_hook_returns_exit_code_zero(self) -> None:
        runner = HookRunner([HookConfig(hook_point="pre_cycle", command="exit 0")])

        results = runner.run_hooks("pre_cycle")

        assert len(results) == 1
        assert results[0].exit_code == 0
        assert results[0].timed_out is False

    def test_successful_hook_captures_stdout(self) -> None:
        runner = HookRunner([HookConfig(hook_point="pre_cycle", command="echo hello")])

        results = runner.run_hooks("pre_cycle")

        assert results[0].stdout.strip() == "hello"

    def test_failed_hook_logs_warning_but_continues(self) -> None:
        hooks = [
            HookConfig(hook_point="pre_cycle", command="exit 1"),
            HookConfig(hook_point="pre_cycle", command="echo continued"),
        ]
        runner = HookRunner(hooks)

        results = runner.run_hooks("pre_cycle")

        assert len(results) == 2
        assert results[0].exit_code == 1
        assert results[1].exit_code == 0
        assert results[1].stdout.strip() == "continued"

    def test_records_duration(self) -> None:
        runner = HookRunner([HookConfig(hook_point="pre_cycle", command="exit 0")])

        results = runner.run_hooks("pre_cycle")

        assert results[0].duration_seconds >= 0.0

    def test_empty_hooks_returns_empty(self) -> None:
        runner = HookRunner([])

        results = runner.run_hooks("pre_cycle")

        assert results == []

    def test_no_matching_hooks_returns_empty(self) -> None:
        runner = HookRunner([HookConfig(hook_point="post_cycle", command="echo post")])

        results = runner.run_hooks("pre_cycle")

        assert results == []


class TestVariableSubstitution:
    """Tests for variable substitution in hook commands."""

    def test_substitutes_agent_variable(self) -> None:
        runner = HookRunner([HookConfig(hook_point="pre_dispatch", command="echo {agent}")])

        results = runner.run_hooks("pre_dispatch", context={"agent": "coder"})

        assert results[0].stdout.strip() == "coder"

    def test_substitutes_project_variable(self) -> None:
        runner = HookRunner([HookConfig(hook_point="pre_cycle", command="echo {project}")])

        results = runner.run_hooks("pre_cycle", context={"project": "myapp"})

        assert results[0].stdout.strip() == "myapp"

    def test_substitutes_cycle_id_variable(self) -> None:
        runner = HookRunner([HookConfig(hook_point="pre_cycle", command="echo {cycle_id}")])

        results = runner.run_hooks("pre_cycle", context={"cycle_id": "abc-123"})

        assert results[0].stdout.strip() == "abc-123"

    def test_substitutes_multiple_variables(self) -> None:
        runner = HookRunner(
            [
                HookConfig(
                    hook_point="post_dispatch",
                    command="echo {agent} {action} {project}",
                )
            ]
        )

        results = runner.run_hooks(
            "post_dispatch",
            context={"agent": "coder", "action": "fix-bug", "project": "myapp"},
        )

        assert results[0].stdout.strip() == "coder fix-bug myapp"

    def test_unmatched_variables_left_as_is(self) -> None:
        runner = HookRunner([HookConfig(hook_point="pre_cycle", command="echo {unknown}")])

        results = runner.run_hooks("pre_cycle", context={})

        assert results[0].stdout.strip() == "{unknown}"


class TestHookTimeout:
    """Tests for hook timeout handling."""

    def test_timeout_returns_timed_out_true(self) -> None:
        runner = HookRunner([HookConfig(hook_point="pre_cycle", command="sleep 10", timeout=1)])

        results = runner.run_hooks("pre_cycle")

        assert len(results) == 1
        assert results[0].timed_out is True
        assert results[0].exit_code == -1
        assert "Timed out" in results[0].stderr


class TestAbortOnFailure:
    """Tests for abort_on_failure behavior."""

    def test_abort_on_exit_code_2_stops_remaining_hooks(self) -> None:
        hooks = [
            HookConfig(
                hook_point="pre_cycle",
                command="exit 2",
                abort_on_failure=True,
            ),
            HookConfig(hook_point="pre_cycle", command="echo should-not-run"),
        ]
        runner = HookRunner(hooks)

        results = runner.run_hooks("pre_cycle")

        assert len(results) == 1
        assert results[0].exit_code == 2

    def test_exit_code_1_does_not_abort_even_with_flag(self) -> None:
        hooks = [
            HookConfig(
                hook_point="pre_cycle",
                command="exit 1",
                abort_on_failure=True,
            ),
            HookConfig(hook_point="pre_cycle", command="echo runs"),
        ]
        runner = HookRunner(hooks)

        results = runner.run_hooks("pre_cycle")

        assert len(results) == 2
        assert results[0].exit_code == 1
        assert results[1].exit_code == 0

    def test_exit_code_2_without_abort_flag_continues(self) -> None:
        hooks = [
            HookConfig(
                hook_point="pre_cycle",
                command="exit 2",
                abort_on_failure=False,
            ),
            HookConfig(hook_point="pre_cycle", command="echo runs"),
        ]
        runner = HookRunner(hooks)

        results = runner.run_hooks("pre_cycle")

        assert len(results) == 2


class TestShouldAbort:
    """Tests for should_abort logic."""

    def test_returns_true_for_abort_condition(self) -> None:
        hooks = [
            HookConfig(
                hook_point="pre_cycle",
                command="exit 2",
                abort_on_failure=True,
            ),
        ]
        runner = HookRunner(hooks)
        result = HookResult(hook_point="pre_cycle", command="exit 2", exit_code=2)

        assert runner.should_abort([result]) is True

    def test_returns_false_for_success(self) -> None:
        hooks = [
            HookConfig(
                hook_point="pre_cycle",
                command="echo ok",
                abort_on_failure=True,
            ),
        ]
        runner = HookRunner(hooks)
        result = HookResult(hook_point="pre_cycle", command="echo ok", exit_code=0)

        assert runner.should_abort([result]) is False

    def test_returns_false_for_empty_results(self) -> None:
        runner = HookRunner([])

        assert runner.should_abort([]) is False


class TestFromConfig:
    """Tests for HookRunner.from_config factory method."""

    def test_creates_hooks_from_config_dicts(self) -> None:
        config = [
            {"hook_point": "pre_cycle", "command": "git fetch", "timeout": 60},
            {
                "hook_point": "post_dispatch",
                "command": "echo {agent} done",
                "abort_on_failure": True,
            },
        ]

        runner = HookRunner.from_config(config)

        assert len(runner._hooks) == 2
        assert runner._hooks[0].hook_point == "pre_cycle"
        assert runner._hooks[0].command == "git fetch"
        assert runner._hooks[0].timeout == 60
        assert runner._hooks[0].abort_on_failure is False
        assert runner._hooks[1].hook_point == "post_dispatch"
        assert runner._hooks[1].abort_on_failure is True

    def test_uses_defaults_for_missing_fields(self) -> None:
        config = [{"hook_point": "pre_cycle", "command": "echo hi"}]

        runner = HookRunner.from_config(config)

        assert runner._hooks[0].timeout == 30
        assert runner._hooks[0].abort_on_failure is False

    def test_empty_config_creates_empty_runner(self) -> None:
        runner = HookRunner.from_config([])

        assert runner._hooks == []
