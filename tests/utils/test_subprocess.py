"""Tests for autopilot.utils.subprocess."""

from __future__ import annotations

import os
import subprocess
from unittest.mock import patch

import pytest

from autopilot.utils.subprocess import build_clean_env, run_claude_cli, run_with_timeout


class TestBuildCleanEnv:
    def test_strips_anthropic_keys(self) -> None:
        with patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "secret", "HOME": "/home/me"}, clear=True
        ):
            env = build_clean_env()
            assert "ANTHROPIC_API_KEY" not in env
            assert env["HOME"] == "/home/me"

    def test_strips_openai_keys(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}, clear=True):
            env = build_clean_env()
            assert "OPENAI_API_KEY" not in env

    def test_strips_github_tokens(self) -> None:
        with patch.dict(
            os.environ,
            {"GITHUB_TOKEN": "ghp_xxx", "GH_TOKEN": "gho_xxx"},
            clear=True,
        ):
            env = build_clean_env()
            assert "GITHUB_TOKEN" not in env
            assert "GH_TOKEN" not in env

    def test_strips_password_exact_match(self) -> None:
        with patch.dict(os.environ, {"PASSWORD": "hunter2"}, clear=True):
            env = build_clean_env()
            assert "PASSWORD" not in env

    def test_preserves_safe_vars(self) -> None:
        with patch.dict(os.environ, {"PATH": "/usr/bin", "LANG": "en_US"}, clear=True):
            env = build_clean_env()
            assert env["PATH"] == "/usr/bin"
            assert env["LANG"] == "en_US"

    def test_extra_vars_added(self) -> None:
        with patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
            env = build_clean_env(extra={"MY_VAR": "hello"})
            assert env["MY_VAR"] == "hello"

    def test_extra_vars_override(self) -> None:
        with patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
            env = build_clean_env(extra={"PATH": "/custom"})
            assert env["PATH"] == "/custom"


class TestRunClaudeCli:
    def test_constructs_command_correctly(self) -> None:
        with patch("autopilot.utils.subprocess.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="ok", stderr=""
            )
            run_claude_cli("hello", model="opus", max_turns=5)
            args = mock_run.call_args
            cmd = args[0][0]
            assert cmd[0] == "claude"
            assert "--print" in cmd
            assert "--model" in cmd
            idx = cmd.index("--model")
            assert cmd[idx + 1] == "opus"
            assert "--max-turns" in cmd
            idx = cmd.index("--max-turns")
            assert cmd[idx + 1] == "5"
            assert "--prompt" in cmd
            idx = cmd.index("--prompt")
            assert cmd[idx + 1] == "hello"

    def test_extra_flags_split(self) -> None:
        with patch("autopilot.utils.subprocess.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            run_claude_cli("hi", extra_flags="--verbose --debug")
            cmd = mock_run.call_args[0][0]
            assert "--verbose" in cmd
            assert "--debug" in cmd

    def test_extra_flags_list(self) -> None:
        with patch("autopilot.utils.subprocess.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            run_claude_cli("hi", extra_flags=["--verbose", "--debug"])
            cmd = mock_run.call_args[0][0]
            assert "--verbose" in cmd
            assert "--debug" in cmd

    def test_timeout_propagated(self) -> None:
        with patch("autopilot.utils.subprocess.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            run_claude_cli("hi", timeout_seconds=42)
            assert mock_run.call_args[1]["timeout"] == 42


class TestRunWithTimeout:
    def test_returns_completed_process(self) -> None:
        with patch("autopilot.utils.subprocess.subprocess.run") as mock_run:
            expected = subprocess.CompletedProcess(args=[], returncode=0, stdout="out", stderr="")
            mock_run.return_value = expected
            result = run_with_timeout(["echo", "hi"], timeout_seconds=10)
            assert result is expected

    def test_raises_on_timeout(self) -> None:
        with patch("autopilot.utils.subprocess.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo", timeout=1)
            with pytest.raises(subprocess.TimeoutExpired):
                run_with_timeout(["echo", "hi"], timeout_seconds=1)
