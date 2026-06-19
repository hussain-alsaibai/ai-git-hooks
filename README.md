# AI Git Hooks

> 🤖 AI-powered Git hooks for automated code review, security scanning, and quality checks — runs entirely local or via your preferred LLM provider.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Why?

Every commit is an opportunity to catch issues before they hit CI/CD. AI Git Hooks analyzes your staged changes locally using LLMs (Ollama, OpenAI, Claude, etc.) and provides instant feedback on:

- 🔒 **Security issues** — secrets, SQL injection, XSS, insecure patterns
- 🐛 **Logic errors** — null pointer risks, race conditions, off-by-one errors  
- 📋 **Code quality** — complexity, duplication, style violations
- 📖 **Documentation** — missing docstrings, unclear naming
- 🧪 **Test coverage** — untested code paths

## Quick Start

```bash
# Install
pip install ai-git-hooks

# Configure (uses Ollama by default for privacy)
aigh configure --provider ollama --model codellama

# Install hooks into your repo
cd my-project
aigh install

# Now every commit gets AI review!
git commit -m "Add new feature"
# [AI Review] ⚠️  Potential SQL injection in login() — see line 42
```

## Features

| Feature | Description |
|---------|-------------|
| **Local-First** | Default to Ollama/LM Studio — no data leaves your machine |
| **Multi-Provider** | OpenAI, Anthropic, Gemini, Groq, Ollama, custom endpoints |
| **Fast Caching** | Skip re-analyzing unchanged files via content hash cache |
| **Custom Rules** | `.aigh.yml` — define team-specific patterns to catch |
| **CI/CD Ready** | Run as GitHub Action / pre-commit hook / standalone CLI |
| **Smart Batching** | Groups small changes, splits large ones — optimal token usage |

## Supported Hooks

- `pre-commit` — Block commits with critical issues
- `commit-msg` — Validate commit messages follow conventions
- `prepare-commit-msg` — Auto-generate commit messages from diff
- `post-checkout` — Warn on large/suspicious file changes
- `pre-push` — Full security scan before push

## Configuration

Create `.aigh.yml` in your repo root:

```yaml
provider: ollama
model: codellama:13b

# Security rules
rules:
  secrets:
    enabled: true
    patterns:
      - "AKIA[0-9A-Z]{16}"  # AWS keys
      - "ghp_[a-zA-Z0-9]{36}"  # GitHub PAT
  
  sql_injection:
    enabled: true
    severity: critical

# Quality thresholds
quality:
  max_complexity: 15
  min_test_coverage: 80

# Custom prompts
prompts:
  review: |
    Review this code change for security, logic, and quality issues.
    Be concise. Format: [SEVERITY] Issue — suggestion
  
  commit_msg: |
    Write a conventional commit message for this diff.
    Format: type(scope): description
```

## Providers

| Provider | Setup | Speed | Cost |
|----------|-------|-------|------|
| **Ollama** | Local install | Fast (GPU) | Free |
| **LM Studio** | Local GUI | Fast (GPU) | Free |
| **OpenAI** | `OPENAI_API_KEY` | Fast | Pay-per-use |
| **Anthropic** | `ANTHROPIC_API_KEY` | Fast | Pay-per-use |
| **Groq** | `GROQ_API_KEY` | Very fast | Pay-per-use |

## Architecture

```
┌─────────────────────────────────────────────┐
│  git commit                                 │
│      ↓                                      │
│  pre-commit hook → aigh-cli                 │
│      ↓                                      │
│  ┌─────────────┐   ┌─────────────────────┐│
│  │ Staged Diff │ → │ Chunk & Filter      ││
│  │ Extractor   │   │ (skip vendor/lock)  ││
│  └─────────────┘   └─────────────────────┘│
│      ↓                                      │
│  ┌────────────────────────────────────────┐│
│  │ Cache Check (content hash)             ││
│  │ Skip if analyzed in last N commits     ││
│  └────────────────────────────────────────┘│
│      ↓                                      │
│  ┌────────────────────────────────────────┐│
│  │ LLM Review (batched prompts)           ││
│  │ - Security scan                        ││
│  │ - Logic review                         ││
│  │ - Quality check                        ││
│  └────────────────────────────────────────┘│
│      ↓                                      │
│  ┌────────────────────────────────────────┐│
│  │ Output Formatter                       ││
│  │ - Inline comments                      ││
│  │ - Summary table                        ││
│  │ - Exit code (block/pass/warn)          ││
│  └────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

## Performance

| Project Size | Cold | Cached |
|-------------|------|--------|
| Small (<10 files) | ~3s | ~0.5s |
| Medium (50 files) | ~8s | ~1s |
| Large (200+ files) | ~20s | ~2s |

*With Ollama on RTX 4090. Remote APIs: ~1-3s regardless of size.*

## Comparison

| Tool | Local | Custom Rules | Commit Hook | CI/CD | Cost |
|------|-------|------------|-------------|-------|------|
| **AI Git Hooks** | ✅ | ✅ | ✅ | ✅ | Free-$ |
| GitHub Copilot | ❌ | ❌ | ❌ | ❌ | $10/mo |
| CodeRabbit | ❌ | ✅ | ❌ | ✅ | $15/mo |
| Snyk Code | ❌ | ❌ | ❌ | ✅ | Free-$ |
| pre-commit | ✅ | ✅ | ✅ | ✅ | Free (no AI) |

## Roadmap

- [ ] VS Code extension for real-time analysis
- [ ] PR review bot (GitHub/GitLab)
- [ ] Custom model fine-tuning on your codebase
- [ ] Team dashboard (shared rule enforcement)
- [ ] SARIF output for security tool integration

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We welcome security rule contributions!

## License

MIT — see [LICENSE](LICENSE)
