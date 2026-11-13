"""Tests for LLM response parsing and provider selection.

The regex in _parse_response was written as r\'...\' -- an escaped quote inside
a raw string -- so the module did not even import. After the syntax fix it
parsed but could not match anything, because the first group was a literal "(" instead of a word class.
These tests pin the behaviour so neither can come back.
"""

import pytest

from ai_git_hooks.config import Config
from ai_git_hooks.providers import (
    AnthropicProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
    get_provider,
)


class TestParseResponse:
    def _parse(self, text):
        return OllamaProvider(Config())._parse_response(text)

    def test_structured_line_is_parsed(self):
        out = self._parse("[HIGH] security: SQL injection in login")
        assert len(out) == 1
        assert out[0]["severity"] == "high"
        assert out[0]["category"] == "security"
        assert out[0]["message"] == "SQL injection in login"

    def test_severity_and_category_are_lowercased(self):
        out = self._parse("[CRITICAL] SECURITY: boom")
        assert out[0]["severity"] == "critical"
        assert out[0]["category"] == "security"

    def test_trailing_whitespace_in_message_is_stripped(self):
        out = self._parse("[low] quality:   spacing   ")
        assert out[0]["message"] == "spacing"

    def test_empty_brackets_fall_through_to_info(self):
        # "[not a finding]" does not match the structured pattern, and because
        # the line starts with "[" it must not be silently dropped either.
        out = self._parse("[nope]")
        assert out == []

    def test_unstructured_line_becomes_info(self):
        out = self._parse("some free text review")
        assert out[0]["severity"] == "info"
        assert out[0]["category"] == "general"
        assert out[0]["message"] == "some free text review"

    def test_blank_lines_and_comments_are_skipped(self):
        out = self._parse("\n\n# a comment\n")
        assert out == []

    def test_mixed_content(self):
        out = self._parse(
            "# header\n[CRITICAL] security: hardcoded secret\nlooks fine otherwise\n"
        )
        assert len(out) == 2
        assert out[0]["severity"] == "critical"
        assert out[1]["severity"] == "info"

    def test_findings_carry_file_and_line_defaults(self):
        out = self._parse("[INFO] testing: add a test")
        assert out[0]["file"] == "unknown"
        assert out[0]["line"] == 0

    def test_empty_string_returns_empty_list(self):
        assert self._parse("") == []


class TestGetProvider:
    def test_defaults_to_ollama(self):
        assert isinstance(get_provider(Config()), OllamaProvider)

    def test_known_providers_need_their_key(self):
        # OpenAI and Anthropic refuse to construct without a key. That is
        # deliberate: a provider that silently no-ops would review nothing.
        for name, exc in [
            ("openai", "OPENAI_API_KEY"),
            ("anthropic", "ANTHROPIC_API_KEY"),
        ]:
            cfg = Config()
            cfg.provider = name
            with pytest.raises(ValueError, match=exc):
                get_provider(cfg)

    @pytest.mark.parametrize(
        "name,cls", [("openai", OpenAIProvider), ("anthropic", AnthropicProvider)]
    )
    def test_known_providers_with_a_key(self, name, cls):
        cfg = Config()
        cfg.provider = name
        cfg.api_key = "test-key-not-real"
        assert isinstance(get_provider(cfg), cls)

    def test_claude_is_an_alias_for_anthropic(self):
        cfg = Config()
        cfg.provider = "claude"
        cfg.api_key = "test-key-not-real"
        assert isinstance(get_provider(cfg), AnthropicProvider)

    def test_unknown_provider_raises(self):
        cfg = Config()
        cfg.provider = "nope"
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider(cfg)

    def test_provider_names_are_case_insensitive(self):
        cfg = Config()
        cfg.provider = "OpenAI"
        cfg.api_key = "test-key-not-real"
        assert isinstance(get_provider(cfg), OpenAIProvider)


class TestProviderContract:
    @pytest.mark.parametrize("cls", [OllamaProvider, OpenAIProvider, AnthropicProvider])
    def test_every_provider_implements_the_interface(self, cls):
        assert issubclass(cls, LLMProvider)

    @pytest.mark.parametrize("cls", [OllamaProvider, OpenAIProvider, AnthropicProvider])
    def test_every_provider_can_parse_a_response(self, cls):
        cfg = Config()
        cfg.api_key = "test-key-not-real"
        out = cls(cfg)._parse_response("[MEDIUM] logic: off by one")
        assert out[0]["severity"] == "medium"
