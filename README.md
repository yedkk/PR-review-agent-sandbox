# PR Review Agent

Multi-agent PR review bot powered by E2B Sandbox. Runs as a GitHub Actions workflow — no server needed.

When a PR is opened or updated, the agent spins up an isolated E2B sandbox, runs linters and tests, then dispatches 5 specialized LLM agents to analyze the code in parallel across different facets. A summarizer converges the results into a single review comment posted directly on the PR.

## Architecture

```
PR Event → GitHub Actions → E2B Sandbox (clone, lint, test)
                                 ↓
                          ┌──────┴──────┐
                    Security  Quality  Logic  Testing  Performance
                          └──────┬──────┘
                             Summarizer
                                 ↓
                         PR Review Comment
```

**Sandbox lifecycle**: On first PR, a sandbox is created and paused after review. On subsequent commits, the same sandbox is resumed (no re-clone, no re-install). On PR close, the sandbox is killed. No external database — E2B metadata is the registry.

## Setup

### 1. Install E2B CLI and build the template

```bash
pip install e2b-cli
e2b login

cd e2b-templates/python-reviewer
e2b template build --name python-reviewer
```

### 2. Configure GitHub Secrets

Go to your repo **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|--------|-------------|
| `E2B_API_KEY` | From [e2b.dev](https://e2b.dev) dashboard |
| `KIMI_API_KEY` | Moonshot API key for Kimi 2.5 |

`GITHUB_TOKEN` is automatically provided by Actions.

### 3. Push and open a PR

```bash
git push -u origin main
```

The workflow triggers automatically on `pull_request` events (opened, synchronize, reopened, closed). You can also trigger manually from the Actions tab with a language override.

## Configuration

**`config.yaml`** — LLM models and language profiles:

```yaml
agents:
  security:
    model: "kimi-k2.5"
    provider: "kimi"
  # Each agent can use a different model/provider

languages:
  python:
    template: "python-reviewer"
    lint_cmd: "ruff check . --output-format=json"
    test_cmd: "pytest --tb=short --timeout=60 -q"
    # ...
```

**`.pr-review.yaml`** (optional, per-repo) — Override language detection:

```yaml
language: python
```

## Adding a new LLM provider

Any OpenAI-compatible API can be added to `PROVIDER_REGISTRY` in `pr_review_agent/agents/base.py`:

```python
PROVIDER_REGISTRY = {
    # ...
    "your-provider": {
        "base_url": "https://api.example.com/v1",
        "api_key_env": "YOUR_PROVIDER_API_KEY",
    },
}
```

Then use `provider: "your-provider"` in `config.yaml`.

## Project Structure

```
pr-review-agent/
├── .github/workflows/review.yml   # GitHub Actions workflow
├── config.yaml                    # Agent + language profile config
├── e2b-templates/                 # Dockerfiles for E2B sandbox templates
├── pr_review_agent/
│   ├── __main__.py                # Entry point (reads env vars, routes events)
│   ├── config.py                  # Config loading
│   ├── sandbox/                   # E2B lifecycle + context collection
│   ├── agents/                    # 5 facet agents + summarizer + orchestrator
│   └── github/                    # GitHub API client + review formatter
└── tests/
```

## License

MIT
