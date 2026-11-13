"""Code diff scanning and analysis."""


from __future__ import annotations

import hashlib
import json
from pathlib import Path

from git import InvalidGitRepositoryError, NoSuchPathError, Repo

from ai_git_hooks.config import Config
from ai_git_hooks.providers import LLMProvider


class DiffScanner:
    """Scan staged/unstaged diffs using LLM."""
    
    def __init__(self, config: Config, provider: LLMProvider) -> None:
        self.config = config
        self.provider = provider
        self.cache_dir = Path.home() / ".cache" / "ai-git-hooks"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def scan(self, staged_only: bool = True) -> list[dict]:
        """Scan current changes and return findings."""
        try:
            repo = Repo(search_parent_directories=True)
        except (InvalidGitRepositoryError, NoSuchPathError):
            raise RuntimeError("Not in a git repository")
        
        # Get diff
        if staged_only:
            diff = repo.git.diff("--staged")
        else:
            diff = repo.git.diff()
        
        if not diff.strip():
            return []
        
        # Check cache
        diff_hash = hashlib.sha256(diff.encode()).hexdigest()[:16]
        cache_file = self.cache_dir / f"{diff_hash}.json"
        
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        
        # Run LLM review
        findings = self.provider.review(diff)
        
        # Cache results
        with open(cache_file, "w") as f:
            json.dump(findings, f)
        
        return findings
    
    def scan_file(self, file_path: str, staged_only: bool = True) -> list[dict]:
        """Scan a specific file."""
        try:
            repo = Repo(search_parent_directories=True)
        except (InvalidGitRepositoryError, NoSuchPathError):
            raise RuntimeError("Not in a git repository")
        
        if staged_only:
            diff = repo.git.diff("--staged", "--", file_path)
        else:
            diff = repo.git.diff("--", file_path)
        
        if not diff.strip():
            return []
        
        return self.provider.review(diff)
