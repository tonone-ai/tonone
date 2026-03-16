# Cloud Architecture

Agents specialized in Google Cloud infrastructure - auditing, right-sizing, security hardening, and cost optimization.

## Agents

| Agent                                         | Status    | Description                                       |
| --------------------------------------------- | --------- | ------------------------------------------------- |
| [cloud-run-specialist](cloud-run-specialist/) | Available | Fleet-wide Cloud Run analysis across 6 dimensions |
| gke-specialist                                | Planned   | GKE cluster and workload analysis                 |
| cloud-sql-specialist                          | Planned   | Database performance and cost optimization        |

## Philosophy

These agents operate as senior cloud architects. They don't just report metrics - they interpret them, prioritize findings by business impact, and give you the specific fix.

Each agent follows the same pattern:

1. **Discover** - find all resources in scope
2. **Collect** - fetch config + live metrics via `gcloud`
3. **Analyze** - run domain-specific checks against best practices
4. **Report** - visual dashboard + categorized findings + historical comparison
