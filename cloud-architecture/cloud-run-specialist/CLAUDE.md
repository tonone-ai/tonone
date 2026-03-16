# Cloud Run Analyzer Agent

Claude Code agent that analyzes Google Cloud Run instances across 6 dimensions:
resource waste, performance, pricing, traffic/latency, security, and recommendations.

## Quick Start

```bash
# Prerequisites: gcloud CLI authenticated
gcloud auth login && gcloud config set project YOUR_PROJECT

# Visual dashboard (opens in browser)
uv run python -m cloudrun_agent.cli --html

# JSON output
uv run python -m cloudrun_agent.cli

# Single service deep dive
uv run python -m cloudrun_agent.cli --service NAME --region REGION

# In Claude Code: use the cloudrun-analyzer agent
```

## Project Structure

```
src/cloudrun_agent/
  models/service.py    — Immutable dataclasses for service config and metrics
  tools/gcloud.py      — gcloud CLI wrapper + Cloud Monitoring REST API
  tools/parser.py      — Parse gcloud JSON into typed models
  tools/metrics.py     — Fetch and aggregate Cloud Monitoring time-series
  analyzers/
    resources.py       — Hardware waste detection
    performance.py     — Bottleneck analysis
    pricing.py         — Cost estimation
    security.py        — Security posture
    traffic.py         — Traffic and latency patterns
  overview.py          — Fleet-level overview with time-series
  dashboard.py         — Self-contained HTML dashboard generator
  runner.py            — Single-service analysis orchestrator
  cli.py               — CLI entry point
```

## Development

- Python 3.13+ with uv
- All data models are frozen dataclasses (immutable)
- No external Python dependencies — uses gcloud CLI + curl for GCP APIs
- Chart.js loaded from CDN for dashboard charts
- Tests: `uv run pytest`
