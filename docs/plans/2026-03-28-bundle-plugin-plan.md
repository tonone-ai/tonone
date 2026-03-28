# Bundle Plugin + Discoverable Names Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add discoverable hyphenated plugin names and a one-command bundle installer for all 13 agents.

**Architecture:** Rename `name` field in each agent's `plugin.json` to `<agent>-<role>`, update `marketplace.json` keys to match, and create a `bundle/engineering-team/` meta-plugin whose post-install hook runs `claude plugin install` for each agent.

**Tech Stack:** Claude Code Plugin System, Bash

**Design:** `docs/plans/2026-03-28-bundle-plugin-design.md`

---

### Task 1: Rename plugin names in all 13 plugin.json files

**Files:**

- Modify: `team/apex/.claude-plugin/plugin.json` — `"name": "apex"` → `"name": "apex-lead"`
- Modify: `team/forge/.claude-plugin/plugin.json` — `"name": "forge"` → `"name": "forge-infra"`
- Modify: `team/relay/.claude-plugin/plugin.json` — `"name": "relay"` → `"name": "relay-devops"`
- Modify: `team/spine/.claude-plugin/plugin.json` — `"name": "spine"` → `"name": "spine-backend"`
- Modify: `team/flux/.claude-plugin/plugin.json` — `"name": "flux"` → `"name": "flux-data"`
- Modify: `team/warden/.claude-plugin/plugin.json` — `"name": "warden"` → `"name": "warden-security"`
- Modify: `team/vigil/.claude-plugin/plugin.json` — `"name": "vigil"` → `"name": "vigil-sre"`
- Modify: `team/prism/.claude-plugin/plugin.json` — `"name": "prism"` → `"name": "prism-frontend"`
- Modify: `team/cortex/.claude-plugin/plugin.json` — `"name": "cortex"` → `"name": "cortex-ml"`
- Modify: `team/touch/.claude-plugin/plugin.json` — `"name": "touch"` → `"name": "touch-mobile"`
- Modify: `team/volt/.claude-plugin/plugin.json` — `"name": "volt"` → `"name": "volt-embedded"`
- Modify: `team/atlas/.claude-plugin/plugin.json` — `"name": "atlas"` → `"name": "atlas-docs"`
- Modify: `team/lens/.claude-plugin/plugin.json` — `"name": "lens"` → `"name": "lens-analytics"`

**Step 1: Update each plugin.json**

In each file, change only the `"name"` field on line 2. The mapping:

```
apex     → apex-lead
forge    → forge-infra
relay    → relay-devops
spine    → spine-backend
flux     → flux-data
warden   → warden-security
vigil    → vigil-sre
prism    → prism-frontend
cortex   → cortex-ml
touch    → touch-mobile
volt     → volt-embedded
atlas    → atlas-docs
lens     → lens-analytics
```

**Step 2: Verify all 13 files are valid JSON**

Run: `for d in team/*/; do python3 -c "import json; d=json.load(open('${d}.claude-plugin/plugin.json')); print(f\"{d['name']:20s} OK\")"; done`

Expected: All 13 print `<name>  OK` with hyphenated names.

**Step 3: Commit**

```bash
git add team/*/.claude-plugin/plugin.json
git commit -m "feat: rename plugins to discoverable <agent>-<role> names"
```

---

### Task 2: Update marketplace.json keys

**Files:**

- Modify: `marketplace.json`

**Step 1: Update plugin keys**

Change each key in the `"plugins"` object to match the new plugin names. The `"path"` values stay the same (directories are not renamed).

New `marketplace.json`:

```json
{
  "name": "tonone-ai",
  "description": "Engineering Team - Claude Code agents that work as specialized engineers",
  "plugins": {
    "engineering-team": {
      "path": "bundle/engineering-team",
      "description": "Install all 13 Engineering Team agents at once"
    },
    "apex-lead": {
      "path": "team/apex",
      "description": "Engineering lead — orchestrates the team, scopes work, controls depth and budget",
      "team": "lead"
    },
    "forge-infra": {
      "path": "team/forge",
      "description": "Infrastructure engineer — cloud services, networking, IaC, cost optimization",
      "team": "infrastructure"
    },
    "relay-devops": {
      "path": "team/relay",
      "description": "DevOps engineer — CI/CD, deployments, GitOps, developer experience",
      "team": "devops"
    },
    "spine-backend": {
      "path": "team/spine",
      "description": "Backend engineer — APIs, system design, performance, distributed systems",
      "team": "backend"
    },
    "flux-data": {
      "path": "team/flux",
      "description": "Data engineer — databases, migrations, pipelines, data modeling",
      "team": "data"
    },
    "warden-security": {
      "path": "team/warden",
      "description": "Security engineer — IAM, secrets, compliance, threat modeling",
      "team": "security"
    },
    "vigil-sre": {
      "path": "team/vigil",
      "description": "Observability & reliability engineer — monitoring, alerting, SRE, incident response, SLOs",
      "team": "observability-reliability"
    },
    "prism-frontend": {
      "path": "team/prism",
      "description": "Frontend & DX engineer — UI, internal tools, developer portals",
      "team": "frontend"
    },
    "cortex-ml": {
      "path": "team/cortex",
      "description": "ML/AI engineer — model training, MLOps, feature engineering, LLM integration",
      "team": "ml"
    },
    "touch-mobile": {
      "path": "team/touch",
      "description": "Mobile engineer — native iOS/Android, cross-platform, app stores, mobile performance",
      "team": "mobile"
    },
    "volt-embedded": {
      "path": "team/volt",
      "description": "Embedded & IoT engineer — firmware, microcontrollers, edge computing, device protocols",
      "team": "embedded"
    },
    "atlas-docs": {
      "path": "team/atlas",
      "description": "Knowledge engineer — architecture docs, ADRs, API specs, system diagrams, onboarding",
      "team": "knowledge"
    },
    "lens-analytics": {
      "path": "team/lens",
      "description": "Data analytics & BI engineer — dashboards, metrics design, reporting, data storytelling",
      "team": "analytics"
    }
  }
}
```

**Step 2: Verify valid JSON**

Run: `python3 -c "import json; d=json.load(open('marketplace.json')); print(f\"{len(d['plugins'])} plugins OK\")"`

Expected: `14 plugins OK`

**Step 3: Commit**

```bash
git add marketplace.json
git commit -m "feat: update marketplace keys to discoverable names + add engineering-team bundle"
```

---

### Task 3: Create bundle plugin manifest

**Files:**

- Create: `bundle/engineering-team/.claude-plugin/plugin.json`

**Step 1: Create directory**

Run: `mkdir -p bundle/engineering-team/.claude-plugin`

**Step 2: Write plugin.json**

Create `bundle/engineering-team/.claude-plugin/plugin.json`:

```json
{
  "name": "engineering-team",
  "version": "0.1.0",
  "description": "Install all 13 Engineering Team agents at once",
  "author": {
    "name": "tonone-ai",
    "url": "https://tonone.ai"
  },
  "repository": "https://github.com/tonone-ai/tonone",
  "license": "MIT",
  "keywords": ["bundle", "installer", "engineering-team", "all-agents"]
}
```

**Step 3: Commit**

```bash
git add bundle/engineering-team/.claude-plugin/plugin.json
git commit -m "feat: add engineering-team bundle plugin manifest"
```

---

### Task 4: Create post-install hook

**Files:**

- Create: `bundle/engineering-team/hooks/hooks.json`

**Step 1: Create directory**

Run: `mkdir -p bundle/engineering-team/hooks`

**Step 2: Write hooks.json**

Create `bundle/engineering-team/hooks/hooks.json`:

```json
{
  "hooks": [
    {
      "event": "post_install",
      "command": "bash scripts/install-all.sh",
      "description": "Install all Engineering Team agent plugins"
    }
  ]
}
```

**Step 3: Commit**

```bash
git add bundle/engineering-team/hooks/hooks.json
git commit -m "feat: add post-install hook for bundle plugin"
```

---

### Task 5: Create install-all script

**Files:**

- Create: `bundle/engineering-team/scripts/install-all.sh`

**Step 1: Create directory**

Run: `mkdir -p bundle/engineering-team/scripts`

**Step 2: Write install-all.sh**

Create `bundle/engineering-team/scripts/install-all.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

MARKETPLACE="tonone-ai"

PLUGINS=(
  "apex-lead"
  "forge-infra"
  "relay-devops"
  "spine-backend"
  "flux-data"
  "warden-security"
  "vigil-sre"
  "prism-frontend"
  "cortex-ml"
  "touch-mobile"
  "volt-embedded"
  "atlas-docs"
  "lens-analytics"
)

echo ""
echo "=== tonone — Installing ${#PLUGINS[@]} agent(s) ==="
echo ""

if command -v claude &>/dev/null; then
  for plugin in "${PLUGINS[@]}"; do
    echo "  Installing ${plugin}..."
    claude plugin install "${plugin}@${MARKETPLACE}" || echo "  WARNING: Failed to install ${plugin}, skipping"
  done
  echo ""
  echo "Done! All agents installed."
else
  echo "Run these commands to install each agent:"
  echo ""
  for plugin in "${PLUGINS[@]}"; do
    echo "  /plugin install ${plugin}@${MARKETPLACE}"
  done
  echo ""
fi
```

**Step 3: Make executable**

Run: `chmod +x bundle/engineering-team/scripts/install-all.sh`

**Step 4: Dry-run (should fall back to printing commands)**

Run: `cd bundle/engineering-team && bash scripts/install-all.sh`

Expected: Prints list of `/plugin install` commands (since `claude` CLI isn't in PATH in this context).

**Step 5: Commit**

```bash
git add bundle/engineering-team/scripts/install-all.sh
git commit -m "feat: add install-all script for bundle plugin"
```

---

### Task 6: Verify everything

**Step 1: Check bundle directory structure**

Run: `find bundle/ -type f | sort`

Expected:

```
bundle/engineering-team/.claude-plugin/plugin.json
bundle/engineering-team/hooks/hooks.json
bundle/engineering-team/scripts/install-all.sh
```

**Step 2: Verify all JSON files are valid**

Run: `python3 -c "import json, glob; [print(f'{f}: OK') for f in sorted(glob.glob('**/plugin.json', recursive=True)) if json.load(open(f))]"`

Expected: All plugin.json files print OK.

**Step 3: Verify marketplace has 14 entries**

Run: `python3 -c "import json; d=json.load(open('marketplace.json')); print(f\"{len(d['plugins'])} plugins\"); [print(f'  {k}') for k in d['plugins']]"`

Expected: 14 plugins listed (engineering-team + 13 agents with hyphenated names).
