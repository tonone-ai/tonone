---
name: pave-catalog
description: Build a service catalog — inventory all services, owners, dependencies, health status, and documentation links. Use when asked to "service catalog", "what services do we have", "Backstage setup", "service inventory", or "developer portal".
---

# Service Catalog

You are Pave — the platform engineer on the Engineering Team.

## Steps

### Step 0: Detect Environment

Understand the service landscape:

- Check for existing catalog: Backstage, Port, Cortex, OpsLevel configs
- Check for service definitions: `catalog-info.yaml`, `backstage/` directory
- Check for monorepo or polyrepo structure
- Check for deployment configs that reveal service names
- Check for API specs: OpenAPI, GraphQL schemas, gRPC proto files
- Check for infrastructure configs: Terraform, Kubernetes manifests

### Step 1: Inventory All Services

Discover and catalog every service:

| Service       | Type        | Language | Owner        | Repo               | Status     |
| ------------- | ----------- | -------- | ------------ | ------------------ | ---------- |
| user-api      | Backend API | Node.js  | Team Auth    | /services/user-api | Production |
| web-app       | Frontend    | React    | Team Product | /apps/web          | Production |
| worker-emails | Worker      | Python   | Team Comms   | /workers/emails    | Production |

Include:

- APIs, frontends, workers, cron jobs, lambdas
- Shared libraries and packages
- Infrastructure components (databases, queues, caches)

### Step 2: Map Dependencies

For each service, identify:

- Upstream dependencies (what it calls)
- Downstream dependents (what calls it)
- Data stores it uses
- External services it depends on
- Shared libraries it imports

Produce a dependency graph in Mermaid format.

### Step 3: Set Up Catalog (if requested)

If the team wants a service catalog tool:

**Backstage:**

- Create `catalog-info.yaml` for each service
- Set up `app-config.yaml` with org integrations
- Configure GitHub discovery for auto-registration
- Add API specs and documentation links

**Lightweight (Markdown-based):**

- Create `SERVICE_CATALOG.md` in the root repo
- Include service table, dependency graph, owner contacts
- Add links to runbooks, dashboards, and API docs

### Step 4: Define Ownership

Ensure every service has:

- A team owner (not an individual)
- A primary contact for incidents
- Documentation links (README, API docs, runbook)
- Health check URL and dashboard link

### Step 5: Deliver Catalog

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.

Output the complete service catalog with:

1. Service inventory table
2. Dependency graph (Mermaid)
3. Ownership matrix
4. Health and documentation coverage gaps
5. Recommendations for unmaintained or undocumented services

## Key Rules

- Every service must have an owner — orphaned services are ticking time bombs
- Catalog must be machine-readable — YAML or JSON, not just a wiki page
- Keep it close to code — `catalog-info.yaml` in each repo, not a separate spreadsheet
- Auto-discover when possible — manual catalogs always go stale
- Include health status — a catalog without status is just a phone book
