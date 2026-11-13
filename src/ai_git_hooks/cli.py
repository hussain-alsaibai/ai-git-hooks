#!/usr/bin/env python3
"""AI Git Hooks - CLI entry point."""

import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from ai_git_hooks.config import load_config
from ai_git_hooks.hooks import install_hooks, uninstall_hooks
from ai_git_hooks.providers import get_provider
from ai_git_hooks.scanner import DiffScanner

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """AI-powered Git hooks for automated code review and security scanning."""
    pass


@cli.command()
@click.option("--provider", type=click.Choice(["ollama", "openai", "anthropic", "groq", "custom"]))
@click.option("--model", help="Model name (e.g., codellama:13b, gpt-4)")
@click.option("--api-key", help="API key for remote providers")
@click.option("--api-url", help="Custom API endpoint URL")
@click.option("--global", "global_config", is_flag=True, help="Write to global config (~/.aigh.yml)")
def configure(provider: str, model: str, api_key: str, api_url: str, global_config: bool) -> None:
    """Configure AI Git Hooks."""
    config_path = Path.home() / ".aigh.yml" if global_config else Path.cwd() / ".aigh.yml"
    
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
    
    if provider:
        config["provider"] = provider
    if model:
        config["model"] = model
    if api_key:
        config["api_key"] = api_key
    if api_url:
        config["api_url"] = api_url
    
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    console.print(f"[green]Configuration saved to {config_path}[/green]")


@cli.command()
@click.option("--force", is_flag=True, help="Overwrite existing hooks")
@click.option("--hooks", multiple=True, default=["pre-commit", "commit-msg"], 
              type=click.Choice(["pre-commit", "commit-msg", "prepare-commit-msg", 
                               "post-checkout", "pre-push", "all"]))
def install(force: bool, hooks: tuple) -> None:
    """Install AI-powered Git hooks into the current repository."""
    try:
        install_hooks(list(hooks), force=force)
        console.print("[green]Hooks installed successfully![/green]")
        
        table = Table(title="Installed Hooks")
        table.add_column("Hook", style="cyan")
        table.add_column("Purpose", style="magenta")
        
        hook_info = {
            "pre-commit": "Block commits with critical security issues",
            "commit-msg": "Validate commit message format and content",
            "prepare-commit-msg": "Auto-generate commit messages",
            "post-checkout": "Warn on large or suspicious file changes",
            "pre-push": "Full security scan before push",
        }
        
        for hook in hooks:
            if hook == "all":
                continue
            table.add_row(hook, hook_info.get(hook, "AI review"))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error installing hooks: {e}[/red]")
        sys.exit(1)


@cli.command()
def uninstall() -> None:
    """Remove AI Git hooks from the current repository."""
    try:
        uninstall_hooks()
        console.print("[green]Hooks uninstalled.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--staged-only", is_flag=True, default=True, help="Only review staged changes")
@click.option("--output", type=click.Choice(["console", "json", "sarif"]), default="console")
def review(staged_only: bool, output: str) -> None:
    """Manually trigger AI review of current changes."""
    try:
        config = load_config()
        provider = get_provider(config)
        scanner = DiffScanner(config, provider)
        
        findings = scanner.scan(staged_only=staged_only)
        
        if output == "json":
            import json
            print(json.dumps(findings, indent=2))
        elif output == "sarif":
            console.print("[yellow]SARIF output coming in v0.2.0[/yellow]")
        else:
            _display_findings(findings)
            
    except Exception as e:
        console.print(f"[red]Error during review: {e}[/red]")
        sys.exit(1)


def _display_findings(findings: list) -> None:
    """Display findings in a rich table format."""
    if not findings:
        console.print("[green]No issues found! ✨[/green]")
        return
    
    table = Table(title="AI Code Review Findings")
    table.add_column("Severity", style="red", width=10)
    table.add_column("Category", style="cyan", width=12)
    table.add_column("File", style="green")
    table.add_column("Line", style="yellow", width=6)
    table.add_column("Issue", style="white")
    
    severity_colors = {
        "critical": "red",
        "high": "bright_red",
        "medium": "yellow",
        "low": "blue",
        "info": "dim",
    }
    
    for finding in findings:
        severity = finding.get("severity", "info").lower()
        color = severity_colors.get(severity, "white")
        table.add_row(
            f"[{color}]{severity.upper()}[/{color}]",
            finding.get("category", "general"),
            finding.get("file", "unknown"),
            str(finding.get("line", "-")),
            finding.get("message", "No details"),
        )
    
    console.print(table)
    
    critical = sum(1 for f in findings if f.get("severity", "").lower() == "critical")
    if critical > 0:
        console.print(f"[red]Found {critical} critical issue(s). Commit blocked.[/red]")
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
