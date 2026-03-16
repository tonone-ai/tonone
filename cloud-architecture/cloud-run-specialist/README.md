# cloudrun-agent

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) agent that analyzes your Google Cloud Run services and generates a visual dashboard with actionable findings.

Analyzes **6 dimensions**: resource waste, performance bottlenecks, pricing, traffic & latency, security posture, and recommendations.

Part of [Engineering Team](https://github.com/thisisfatih/eng-team) - your engineering team on call.

## Quick Start

```bash
pip install cloudrun-agent
cloudrun-agent install
```

This installs the agent definition and skills into `~/.claude/` so they're available in every Claude Code session.

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- Python 3.10+
- GCP permissions: Cloud Run Viewer, Monitoring Viewer

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## Usage

### In Claude Code (recommended)

Just ask Claude:

```
> analyze my cloud run services
> show me a dashboard of my cloud run fleet
> which services are wasting resources?
> are there security issues in my cloud run setup?
```

Claude will use the `cloudrun-analyzer` agent automatically.

### Slash Commands

After install, these slash commands are available in Claude Code:

| Command               | What it does                      |
| --------------------- | --------------------------------- |
| `/cloudrun-dashboard` | Visual fleet report in browser    |
| `/cloudrun-check`     | Quick health check in terminal    |
| `/cloudrun-inspect`   | Deep dive into a specific service |
| `/cloudrun-history`   | Compare changes over time         |

### Standalone CLI

```bash
# HTML dashboard (opens in browser)
cloudrun-agent analyze --html

# JSON output
cloudrun-agent analyze

# Single service deep dive
cloudrun-agent analyze --service my-api --region us-central1

# Filter by project/region
cloudrun-agent analyze --html --project my-project --region europe-west1

# Skip metrics (faster, config-only analysis)
cloudrun-agent analyze --no-metrics

# View snapshot history
cloudrun-agent analyze --history

# Troubleshooting
cloudrun-agent analyze --verbose
```

## What It Analyzes

### Dashboard

The HTML dashboard includes:

- **Health score** - weighted 0-100 score based on finding severity
- **KPI cards** - service count, estimated monthly cost, daily requests, finding counts
- **Services table** - per-service CPU, memory, utilization, latency, cost, health status
- **Findings by category** - collapsible groups for Security, Resources, Performance, Traffic, Pricing
- **Historical charts** - time-series for request count, CPU utilization, latency (P50/P99), instance count
- **Interactive filtering** - click any service row to filter all charts
- **Snapshot comparison** - delta banner showing changes since last analysis

### Finding Categories

| Category        | What it checks                                                                                        |
| --------------- | ----------------------------------------------------------------------------------------------------- |
| **Security**    | Plaintext secrets in env vars, default service accounts, public ingress, IAM policies, VPC connectors |
| **Resources**   | CPU/memory over-provisioning, utilization rates, min-instance idle costs                              |
| **Performance** | Cold start risk, concurrency settings, latency percentiles, error rates                               |
| **Traffic**     | Request volume patterns, scaling behavior, billable instance time, traffic splits                     |
| **Pricing**     | Cost breakdown (CPU, memory, requests, idle), optimization opportunities                              |

### Severity Levels

- **Critical** - security risks or significant waste requiring immediate action
- **Warning** - optimization opportunities or potential issues
- **Info** - informational findings, architectural observations

## How It Works

1. **Discovery** - lists all Cloud Run services via `gcloud run services list`
2. **Configuration** - fetches detailed config for each service (CPU, memory, scaling, IAM, env vars)
3. **Metrics** - queries Cloud Monitoring API for the last 24h (requests, CPU, memory, latency, instances)
4. **Analysis** - runs 5 analyzers against config + metrics to produce findings
5. **Dashboard** - generates a self-contained HTML file with Chart.js visualizations

No data leaves your machine. All analysis runs locally using your `gcloud` credentials.

## Development

```bash
git clone https://github.com/thisisfatih/eng-team
cd eng-team/cloud-architecture/cloud-run-specialist
uv sync

# Run tests
uv run pytest

# Run directly
uv run python -m cloudrun_agent.cli --html
```

## License

MIT
