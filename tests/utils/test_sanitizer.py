"""Tests for autopilot.utils.sanitizer."""

from __future__ import annotations

from autopilot.utils.sanitizer import sanitize


class TestSanitize:
    def test_anthropic_key(self) -> None:
        text = "key is sk-ant-api03-abcdefghijklmnopqrstuvwx"
        assert "sk-ant-" not in sanitize(text)
        assert "[REDACTED_API_KEY]" in sanitize(text)

    def test_openai_key(self) -> None:
        text = "key is sk-1234567890abcdefghijklmn"
        assert "sk-1234567890" not in sanitize(text)
        assert "[REDACTED_API_KEY]" in sanitize(text)

    def test_aws_key(self) -> None:
        text = "AKIAIOSFODNN7EXAMPLE"
        assert "AKIA" not in sanitize(text)
        assert "[REDACTED_AWS_KEY]" in sanitize(text)

    def test_bearer_token(self) -> None:
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        result = sanitize(text)
        assert "eyJhbG" not in result
        assert "Bearer [REDACTED_TOKEN]" in result

    def test_generic_key_assignment(self) -> None:
        text = "api_key=abcdefghijklmnop"
        result = sanitize(text)
        assert "abcdefghijklmnop" not in result
        assert "[REDACTED]" in result

    def test_github_pat(self) -> None:
        text = "using ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij here"  # 36 after ghp_
        result = sanitize(text)
        assert "ghp_ABCDEF" not in result
        assert "[REDACTED_GH_TOKEN]" in result

    def test_github_oauth(self) -> None:
        text = "using gho_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij here"  # 36 chars after gho_
        result = sanitize(text)
        assert "gho_ABCDEF" not in result

    def test_github_fine_grained(self) -> None:
        text = "github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZab"
        result = sanitize(text)
        assert "github_pat_" not in result

    def test_safe_text_unchanged(self) -> None:
        text = "Hello, this is a normal log message with no secrets."
        assert sanitize(text) == text

    def test_empty_string(self) -> None:
        assert sanitize("") == ""

    def test_password_in_config(self) -> None:
        text = 'password="SuperSecret123!"'
        result = sanitize(text)
        assert "SuperSecret123" not in result
