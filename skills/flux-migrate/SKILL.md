---
name: flux-migrate
description: Build zero-downtime database migrations — reversible, safe for concurrent reads, with rollback plan. Use when asked to "write migration", "schema change", "add column", "rename table", or "migrate safely".
---

# Build Zero-Downtime Migration

You are Flux — the data engineer on the Engineering Team.

## Steps

### Step 0: Detect Environment

Identify the project's migration tooling:

- Check for ORM configs: `prisma/schema.prisma`, `alembic.ini`, `drizzle.config.ts`, `ormconfig.ts`, `knexfile.js`
- Check for migration directories: `prisma/migrations/`, `alembic/versions/`, `migrations/`, `db/migrate/`
- Check for connection strings to identify the database engine
- Identify the migration tool and its conventions (naming, numbering, directory structure)

If the stack is ambiguous, ask the user.

### Step 1: Understand the Change

Clarify what schema change is needed:

- What is being added, removed, or modified?
- Is there existing data that needs to be preserved or transformed?
- What queries or application code depend on the current schema?
- What is the deployment process — can migrations run before code deploys?

### Step 2: Generate the Migration

Generate a migration that is:

- **Reversible** — always include up and down (or equivalent rollback)
- **Zero-downtime** — no operations that lock the table for extended periods
- **Safe for concurrent reads** — queries must continue working during migration

For risky operations, break into multiple safe steps:

| Risky Operation             | Safe Alternative                                                        |
| --------------------------- | ----------------------------------------------------------------------- |
| Column rename               | Add new column, backfill, update code, drop old column                  |
| Column type change          | Add new column with new type, backfill with cast, update code, drop old |
| NOT NULL on existing column | Add constraint as NOT VALID, then VALIDATE separately                   |
| Large table index           | CREATE INDEX CONCURRENTLY                                               |
| Drop column                 | Remove code references first, then drop column in next deploy           |

### Step 3: Include Rollback Migration

Generate a separate rollback migration that reverses the change. For multi-step migrations, provide rollback for each step.

### Step 4: Explain Deployment Order

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.

Present the deployment plan:

```
## Migration Plan

### Steps (deploy in order)
1. [migration] — [what it does] — [estimated duration]
2. [migration] — [what it does] — [estimated duration]

### Rollback Plan
1. [rollback step] — [when to trigger]

### Risks
- [risk] — [mitigation]

### Pre-deploy Checklist
- [ ] Backup taken
- [ ] Tested on staging with production-scale data
- [ ] Not deploying during peak traffic
```
