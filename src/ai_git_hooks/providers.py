"""LLM provider abstractions for AI Git Hooks."""


from __future__ import annotations

import os
from abc import ABC, abstractmethod

import requests

from ai_git_hooks.config import Config


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
    
    @abstractmethod
    def review(self, diff: str) -> list[dict]:
        """Review code diff and return findings."""
    
    @abstractmethod
    def generate_commit_message(self, diff: str) -> str:
        """Generate commit message from diff."""
    
    def _parse_response(self, content: str) -> list[dict]:
        """Parse LLM response into structured findings."""
        findings = []
        
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Try to parse structured format: [SEVERITY] CATEGORY: Message
            if line.startswith("["):
                import re
                match = re.match(r"\[(\w+)\]\s*(\w+):\s*(.+)", line)
                if match:
                    severity, category, message = match.groups()
                    findings.append({
                        "severity": severity.lower(),
                        "category": category.lower(),
                        "message": message.strip(),
                        "file": "unknown",
                        "line": 0,
                    })
            elif line:
                # Unstructured line - treat as info
                findings.append({
                    "severity": "info",
                    "category": "general",
                    "message": line,
                    "file": "unknown",
                    "line": 0,
                })
        
        return findings


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.base_url = config.api_url or "http://localhost:11434"
        self.model = config.model or "codellama"
    
    def _call(self, prompt: str) -> str:
        """Call Ollama API."""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2048,
                    }
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is Ollama running? Run: ollama serve"
            )
    
    def review(self, diff: str) -> list[dict]:
        """Review code diff."""
        prompt = self.config.prompts.get("review", "").format(diff=diff)
        response = self._call(prompt)
        return self._parse_response(response)
    
    def generate_commit_message(self, diff: str) -> str:
        """Generate commit message."""
        prompt = self.config.prompts.get("commit_msg", "").format(diff=diff)
        response = self._call(prompt)
        return response.strip().split("\n")[0]


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.api_key = config.api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY or use --api-key")
        self.base_url = config.api_url or "https://api.openai.com/v1"
        self.model = config.model or "gpt-4"
    
    def _call(self, prompt: str) -> str:
        """Call OpenAI API."""
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a code review assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def review(self, diff: str) -> list[dict]:
        """Review code diff."""
        prompt = self.config.prompts.get("review", "").format(diff=diff)
        response = self._call(prompt)
        return self._parse_response(response)
    
    def generate_commit_message(self, diff: str) -> str:
        """Generate commit message."""
        prompt = self.config.prompts.get("commit_msg", "").format(diff=diff)
        response = self._call(prompt)
        return response.strip().split("\n")[0]


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""
    
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY")
        self.model = config.model or "claude-3-sonnet-20240229"
    
    def _call(self, prompt: str) -> str:
        """Call Anthropic API."""
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.model,
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]
    
    def review(self, diff: str) -> list[dict]:
        """Review code diff."""
        prompt = self.config.prompts.get("review", "").format(diff=diff)
        response = self._call(prompt)
        return self._parse_response(response)
    
    def generate_commit_message(self, diff: str) -> str:
        """Generate commit message."""
        prompt = self.config.prompts.get("commit_msg", "").format(diff=diff)
        response = self._call(prompt)
        return response.strip().split("\n")[0]


def get_provider(config: Config) -> LLMProvider:
    """Factory function to get the appropriate provider."""
    providers = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "claude": AnthropicProvider,
    }
    
    provider_class = providers.get(config.provider.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {config.provider}. "
                        f"Supported: {', '.join(providers.keys())}")
    
    return provider_class(config)
