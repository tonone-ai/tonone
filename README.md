# Engineering Team

Your engineering team on call — [Claude Code](https://docs.anthropic.com/en/docs/claude-code) agents that work as specialized engineers.

Each agent is a senior specialist who audits, analyzes, and recommends. They integrate directly into Claude Code as agents and slash commands.

Everything runs locally. No data leaves your machine.

## Quick Start

Install the Cloud Run Specialist directly:

```bash
pip install cloudrun-agent
cloudrun-agent install
```

Then in Claude Code:
```
> analyze my cloud run services
```

Or install via the marketplace to browse all agents:

```bash
pip install engteam
engteam list
engteam install cloud-run-specialist
```

## Available Agents

### Cloud Architecture

| Agent | What it does | Install |
|-------|-------------|---------|
| **[cloud-run-specialist](cloud-architecture/cloud-run-specialist/)** | Audit Cloud Run fleet: waste, performance, pricing, traffic, security | `pip install cloudrun-agent` |

### Coming Soon

- **gke-specialist** — GKE cluster auditing
- **cloud-sql-specialist** — Cloud SQL performance and cost
- **iam-auditor** — IAM policy analysis and least-privilege recommendations
- **ci-cd-engineer** — Pipeline optimization and reliability

## How It Works

Each agent:
1. Connects to your infrastructure using your existing CLI credentials
2. Fetches configuration and live metrics
3. Runs specialized analyzers against best practices
4. Generates findings with severity, scope, and actionable fixes
5. Produces a visual dashboard you can share with your team

## Marketplace Commands

```bash
engteam list                              # browse all agents
engteam list --team cloud-architecture    # filter by team
engteam install cloud-run-specialist      # install one agent
engteam install cloud-architecture        # install a whole team
engteam install --all                     # install everything
engteam run cloud-run-specialist -- --html  # run an agent directly
engteam update                            # update all agents
```

## For Contributors

See [CLAUDE.md](CLAUDE.md) for development setup and how to add new agents.

## License

MIT
