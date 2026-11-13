"""Configuration management for AI Git Hooks."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Config:
    """AI Git Hooks configuration."""
    
    provider: str = "ollama"
    model: str = "codellama"
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    
    # Security rules
    rules: dict = field(default_factory=lambda: {
        "secrets": {"enabled": True},
        "sql_injection": {"enabled": True, "severity": "critical"},
        "xss": {"enabled": True, "severity": "high"},
    })
    
    # Quality thresholds
    quality: dict = field(default_factory=lambda: {
        "max_complexity": 15,
        "min_test_coverage": 80,
    })
    
    # Hooks configuration
    hooks: dict = field(default_factory=lambda: {
        "pre-commit": {"enabled": True, "block_critical": True},
        "commit-msg": {"enabled": True, "conventional_commits": True},
        "prepare-commit-msg": {"enabled": False},
        "post-checkout": {"enabled": True, "max_file_size_mb": 10},
        "pre-push": {"enabled": True, "full_scan": True},
    })
    
    # Custom prompts
    prompts: dict = field(default_factory=lambda: {
        "review": """Review the following code changes for security vulnerabilities, 
logic errors, and quality issues. Be concise and actionable.

Format each finding as:
[SEVERITY] CATEGORY: Description (File:Line)

Severity levels: critical, high, medium, low, info
Categories: security, logic, quality, documentation, testing

Code changes:
{diff}
""",
        "commit_msg": """Write a conventional commit message for these changes.
Format: type(scope): description

Types: feat, fix, docs, style, refactor, test, chore

Changes:
{diff}
""",
    })
    
    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary."""
        return cls(
            provider=data.get("provider", "ollama"),
            model=data.get("model", "codellama"),
            api_key=data.get("api_key"),
            api_url=data.get("api_url"),
            rules=data.get("rules", {}),
            quality=data.get("quality", {}),
            hooks=data.get("hooks", {}),
            prompts=data.get("prompts", {}),
        )


def load_config() -> Config:
    """Load configuration from file or environment."""
    # Try local config first
    local_config = Path.cwd() / ".aigh.yml"
    global_config = Path.home() / ".aigh.yml"
    
    config_data = {}
    
    # Load global config if exists
    if global_config.exists():
        with open(global_config) as f:
            config_data = yaml.safe_load(f) or {}
    
    # Local config overrides global
    if local_config.exists():
        with open(local_config) as f:
            local_data = yaml.safe_load(f) or {}
            config_data.update(local_data)
    
    # Environment variables override file config
    env_mappings = {
        "AIGH_PROVIDER": "provider",
        "AIGH_MODEL": "model",
        "AIGH_API_KEY": "api_key",
        "AIGH_API_URL": "api_url",
    }
    
    for env_var, config_key in env_mappings.items():
        if os.environ.get(env_var):
            config_data[config_key] = os.environ[env_var]
    
    return Config.from_dict(config_data)
