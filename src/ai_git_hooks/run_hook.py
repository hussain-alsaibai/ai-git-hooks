"""Hook runner - called by Git hooks."""


from __future__ import annotations

import sys

from ai_git_hooks.config import load_config
from ai_git_hooks.providers import get_provider
from ai_git_hooks.scanner import DiffScanner


def run_hook(hook_name: str, args: list[str]) -> int:
    """Run the appropriate hook logic."""
    config = load_config()
    
    hook_config = config.hooks.get(hook_name, {})
    if not hook_config.get("enabled", True):
        return 0
    
    provider = get_provider(config)
    scanner = DiffScanner(config, provider)
    
    if hook_name == "pre-commit":
        findings = scanner.scan(staged_only=True)
        
        # Display findings
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        if not findings:
            console.print("[green]AI review passed! ✨[/green]")
            return 0
        
        table = Table(title="AI Code Review")
        table.add_column("Severity", width=10)
        table.add_column("Issue")
        
        for finding in findings:
            severity = finding.get("severity", "info")
            message = finding.get("message", "")
            table.add_row(severity.upper(), message)
        
        console.print(table)
        
        # Check if we should block
        if hook_config.get("block_critical", True):
            critical = any(
                f.get("severity", "").lower() == "critical"
                for f in findings
            )
            if critical:
                console.print("[red]Critical issues found. Commit blocked.[/red]")
                console.print("[dim]Use --no-verify to bypass (not recommended)[/dim]")
                return 1
        
        return 0
    
    elif hook_name == "commit-msg":
        commit_msg_file = args[0] if args else ".git/COMMIT_EDITMSG"
        
        with open(commit_msg_file) as f:
            msg = f.read().strip()
        
        # Check conventional commits
        if hook_config.get("conventional_commits", True):
            import re
            pattern = r"^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+"
            if not re.match(pattern, msg):
                print("Commit message should follow conventional commits format:")
                print("  type(scope): description")
                print("  Types: feat, fix, docs, style, refactor, test, chore")
                return 1
        
        return 0
    
    elif hook_name == "pre-push":
        if hook_config.get("full_scan", True):
            findings = scanner.scan(staged_only=False)
            
            critical = any(
                f.get("severity", "").lower() == "critical"
                for f in findings
            )
            if critical:
                print("Critical security issues found in repository!")
                return 1
        
        return 0
    
    return 0


if __name__ == "__main__":
    hook_name = sys.argv[1] if len(sys.argv) > 1 else "pre-commit"
    args = sys.argv[2:]
    sys.exit(run_hook(hook_name, args))
