#!/usr/bin/env node
"use strict";

// tonone-skill-gate — SessionStart hook
//
// A full tonone install advertises every skill in docs/skill-index.json, and
// Claude Code loads every one of those names and descriptions into the system
// prompt of every session. Measured on this repository: 421 rows, 92,309
// characters, roughly 23,000 tokens spent before the user has typed anything.
// Most of them are irrelevant to the project in front of them — a design system
// repository does not need thirty security-operations skills.
//
// This hook scores the skill catalogue against the current project and writes
// `skillOverrides` into `.claude/settings.local.json` so that irrelevant skills
// stop costing context. It scores in two stages — first the ten teams, then the
// individual skills of the teams that survived — so that a whole team can be
// dropped in one decision instead of thirty.
//
// Three states are used, and only three:
//
//   on                    full name and description in context (the default)
//   name-only             name in context, description dropped
//   user-invocable-only   not in context; the user can still type /skill-name
//
// The state `off` is never written. Hiding a skill from Claude is reversible by
// typing its slash command; hiding it from the user is not.
//
// Everything degrades to doing nothing. No skill index, no decision layer, no
// writable settings file, no project signals, a hostile environment — each of
// those ends in exit code 0 with the session untouched. Set TONONE_GATE=off to
// disable the hook outright.
//
// The hook scores locally and performs no network I/O. An API key exported in
// a shell profile does not change that: the decision layer is told to stay
// offline unless TONONE_GATE_JEV=1 is set, because an unattended SessionStart
// hook must not ship project metadata anywhere on the strength of a key that
// was exported for something else.
//
// Which overrides the hook owns is recorded in .claude/tonone-skill-gate.json,
// beside the settings file it describes, so that --reset keeps working after a
// cache clean, a machine move or a re-clone. `--reset --all` clears every
// override unconditionally if that record is ever lost anyway.
//
// The hook writes settings; it does not reach into the running session. Claude
// Code reads `skillOverrides` when it loads settings, so a decision written at
// SessionStart applies from the moment the harness next reads that file, which
// in the worst case is the next session. That is the reason the decision is
// cached for seven days rather than recomputed per prompt: it is a slow-moving
// property of the project, not of the turn.
//
// Usage outside the hook runner:
//
//   node hooks/tonone-skill-gate.js --dry-run          before/after token count
//   node hooks/tonone-skill-gate.js --dry-run --json   the same, machine-readable
//   node hooks/tonone-skill-gate.js --reset            drop every override it wrote
//   node hooks/tonone-skill-gate.js --reset --all      drop every override, full stop
//   node hooks/tonone-skill-gate.js --cwd /path/to/project --dry-run

const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const { spawnSync } = require("child_process");

// ── Config ────────────────────────────────────────────────────────────────────

const PLUGIN_ROOT =
  process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..");

/** Where the catalogue lives. Resolved per call rather than at load time so a
 *  test (or a checkout in an unusual place) can point it elsewhere. */
function skillIndexPath() {
  return (
    process.env.TONONE_GATE_INDEX ||
    path.join(PLUGIN_ROOT, "docs", "skill-index.json")
  );
}

const STATE_ON = "on";
const STATE_NAME_ONLY = "name-only";
const STATE_USER_ONLY = "user-invocable-only";
const VALID_STATES = [STATE_ON, STATE_NAME_ONLY, STATE_USER_ONLY];

// Skills that stay fully loaded whatever the project looks like. Apex and Helm
// are the two entry points into the roster, and atlas-report is the overflow
// target every other skill points at.
const ALWAYS_ON_PREFIXES = ["apex", "helm"];
const ALWAYS_ON_NAMES = ["atlas-report", "tonone-onboard"];

const CACHE_TTL_MS = readIntEnv("TONONE_GATE_TTL_MS", 7 * 24 * 60 * 60 * 1000);
const DECISION_TIMEOUT_MS = readIntEnv("TONONE_GATE_TIMEOUT_MS", 6000);
const DEADLINE_MS = readIntEnv("TONONE_GATE_DEADLINE_MS", 20000);
// How long to wait for the hook payload on stdin before working with whatever
// has arrived. A runner that keeps the pipe open after writing the payload is
// common, so the wait must end on its own.
const STDIN_TIMEOUT_MS = readIntEnv("TONONE_GATE_STDIN_MS", 2000);

// A choice question with hundreds of options is neither cheap nor accurate, so
// a team's skills are split into groups and ranked within each group.
const MAX_OPTIONS_PER_QUESTION = 45;

// Selection is by rank and by position within the spread of a question's own
// probabilities, never by an absolute probability. Two reasons: the scale of a
// probability depends on how many options competed for it, and the local scorer
// returns a nearly flat distribution — measured on this repository the ten
// teams land within a few percent of each other, so the ordering carries the
// signal and the magnitude carries almost none.
const TEAM_KEEP_Z = 0.75; // position in [min, max] that survives stage one outright
const SKILL_ON_Z = 0.6; // position in [min, max] to keep a description
const MAX_ON_FRACTION = 0.4; // at most this share of a surviving team stays full
const MIN_SPREAD = 0.02; // (max − min) / mean below this is noise, not a ranking

// Teams kept by rank, widened by the breadth question: a single-domain project
// keeps 3, a whole-product one keeps 5. Teams scoring in the top quarter of the
// spread, teams the branch name argues for, and Engineering survive on top of
// that, so the measured range on real projects is 4 to 6 of the ten.
const MIN_TEAMS = 3;

// Engineering is never dropped. It is the team every other team hands work to,
// it is the fallback bucket for a row with no team of its own, and it holds the
// generalist skills (planning, architecture docs, testing, shipping) that a
// project of any shape reaches for. Keeping the team is cheap: stage two still
// cuts the descriptions of the skills inside it. The measured failure this
// guards against is a pure-Terraform repository, where the lexical scorer ranks
// Engineering below Design and would otherwise hide /relay-deploy and
// /warden-iam from a session that plainly needs them.
const ALWAYS_KEEP_TEAMS = ["Engineering"];

const CHARS_PER_TOKEN = 4; // the usual rough estimate; see estimateTokens()

// ── Team descriptors ──────────────────────────────────────────────────────────
//
// The keys match the `team` field of docs/skill-index.json exactly. The
// descriptions are contrastive on purpose: the local scorer builds its IDF
// corpus out of these option texts, so words that appear in every option carry
// no signal and words unique to one team carry all of it.

const TEAMS = {
  Engineering: {
    what:
      "Application and backend code: HTTP APIs, services, databases, schema migrations, " +
      "frontend components, mobile apps, firmware, unit and end-to-end tests, CI pipelines, " +
      "deployments, logging and monitoring, refactoring, performance and bug fixes.",
    not_for: "Company strategy, contracts, marketing copy, model training.",
  },
  Product: {
    what:
      "Product and go-to-market decisions: roadmap, prioritization, user interviews, personas, " +
      "activation and retention funnels, pricing, positioning, launch messaging, sales pipeline, " +
      "customer success, churn, blog and SEO content, community and developer relations.",
    not_for: "Writing code, cloud configuration, legal drafting.",
  },
  Operations: {
    what:
      "Running the company: finance, runway, budgets and unit economics, fundraising, hiring, " +
      "employee onboarding, compensation, org design, vendor management, process design, " +
      "support tickets, SLAs and the customer knowledge base.",
    not_for: "Source code, product design, security tooling.",
  },
  Legal: {
    what:
      "Contracts and regulation: NDAs, MSAs, employment agreements, terms of service, privacy " +
      "policy, GDPR and CCPA, SOC2 and HIPAA compliance, trademarks, patents, open source " +
      "licence obligations, regulatory filings, board resolutions and cap tables.",
    not_for: "Source code, infrastructure, analytics.",
  },
  Design: {
    what:
      "Visual and interaction design: color palettes, typography and type scale, spacing and " +
      "layout grids, responsive breakpoints, design tokens and multi-brand theming, icons, " +
      "illustration, motion and micro-interactions, accessibility (WCAG, ARIA, keyboard, " +
      "screen readers), UX writing and microcopy.",
    not_for: "Backend services, cloud cost, contracts.",
  },
  "Data Science": {
    what:
      "Statistics and modelling: time series forecasting, feature engineering, model training " +
      "and hyperparameter tuning, evaluation metrics, data and concept drift, embeddings and " +
      "vector search, fine-tuning, experiment design and A/B tests, data cleaning and validation, " +
      "exploratory analysis and charts.",
    not_for: "UI styling, contracts, support workflow.",
  },
  "Security Operations": {
    what:
      "Security operations: penetration testing, red and blue team exercises, threat hunting and " +
      "IOCs, CVE triage and patch SLAs, SBOM and dependency scanning, SAST and DAST, SIEM " +
      "detection rules, incident response and forensics, zero trust and microsegmentation, " +
      "phishing simulations.",
    not_for: "Product roadmap, typography, forecasting.",
  },
  "Developer Experience": {
    what:
      "The developer-facing surface of an API: reference documentation, integration guides, " +
      "code samples and quickstarts, SDK design across languages, OpenAPI and GraphQL and gRPC " +
      "schemas, mock servers and contract tests, changelogs, deprecation and semver policy, " +
      "API linting and latency benchmarks.",
    not_for: "Cloud provisioning, legal drafting, model training.",
  },
  "Infrastructure Specialist": {
    what:
      "Cloud infrastructure: Kubernetes clusters and RBAC, Terraform modules and state, cloud " +
      "cost and FinOps, SLOs, error budgets and capacity planning, CDN and edge functions, Redis " +
      "and Memcached caching, Kafka and SQS queues, service mesh and mTLS, multi-cloud " +
      "portability, chaos engineering.",
    not_for: "UI components, copywriting, support tickets.",
  },
  "AI Operations": {
    what:
      "LLM applications in production: model serving and inference endpoints, eval harnesses and " +
      "benchmark suites, LLM tracing and cost attribution, guardrails, PII filters and content " +
      "moderation, token budgets and context window limits, prompt design and versioning, " +
      "embedding pipelines, retrieval reranking.",
    not_for: "Physical infrastructure, contracts, brand design.",
  },
};

// Words that, seen in a branch name, force a team to survive stage one.
const BRANCH_TEAM_HINTS = {
  Engineering: [
    "api",
    "backend",
    "frontend",
    "bug",
    "fix",
    "feat",
    "feature",
    "test",
    "perf",
  ],
  Product: [
    "growth",
    "pricing",
    "launch",
    "onboarding",
    "marketing",
    "landing",
  ],
  Operations: ["finance", "hiring", "support", "vendor", "okr"],
  Legal: [
    "legal",
    "privacy",
    "gdpr",
    "licence",
    "license",
    "terms",
    "compliance",
  ],
  Design: [
    "design",
    "ui",
    "ux",
    "theme",
    "token",
    "brand",
    "a11y",
    "accessibility",
  ],
  "Data Science": [
    "model",
    "ml",
    "forecast",
    "embedding",
    "experiment",
    "dataset",
  ],
  "Security Operations": [
    "security",
    "sec",
    "cve",
    "vuln",
    "pentest",
    "hardening",
  ],
  "Developer Experience": [
    "docs",
    "sdk",
    "openapi",
    "schema",
    "changelog",
    "quickstart",
  ],
  "Infrastructure Specialist": [
    "infra",
    "k8s",
    "kubernetes",
    "terraform",
    "cache",
    "queue",
    "mesh",
  ],
  "AI Operations": ["llm", "prompt", "eval", "guardrail", "inference", "rag"],
};

// ── Small helpers ─────────────────────────────────────────────────────────────

function readIntEnv(name, fallback) {
  const raw = parseInt(process.env[name] || "", 10);
  return isFinite(raw) && raw > 0 ? raw : fallback;
}

function readJsonFile(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

/**
 * Read JSON and say which of the three things happened, because a caller that
 * is about to rewrite the file has to tell "there is no file" (safe to create)
 * from "there is a file I could not read" (never safe to overwrite).
 *
 * Returns { exists, ok, value }:
 *   { exists: false, ok: true,  value: null }  no such file
 *   { exists: true,  ok: true,  value: ... }   parsed
 *   { exists: true,  ok: false, value: null }  unreadable or not valid JSON
 */
function readJsonFileStrict(file) {
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch (err) {
    if (err && (err.code === "ENOENT" || err.code === "ENOTDIR")) {
      return { exists: false, ok: true, value: null };
    }
    return { exists: true, ok: false, value: null };
  }
  try {
    return { exists: true, ok: true, value: JSON.parse(text) };
  } catch {
    return { exists: true, ok: false, value: null };
  }
}

function readTextFile(file, limit) {
  try {
    const text = fs.readFileSync(file, "utf8");
    return limit && text.length > limit ? text.slice(0, limit) : text;
  } catch {
    return "";
  }
}

/** Rough token count. Deliberately the same crude ratio on both sides of the
 *  before/after comparison, so the ratio is honest even though the absolute
 *  number is an estimate. */
function estimateTokens(chars) {
  return Math.ceil(chars / CHARS_PER_TOKEN);
}

/** The only place a state string enters the settings file. `off` can never
 *  survive this function, whatever the caller thought it was asking for. */
function sanitizeState(state) {
  if (VALID_STATES.indexOf(state) !== -1) return state;
  return STATE_NAME_ONLY;
}

function uniq(list) {
  const seen = Object.create(null);
  const out = [];
  for (const item of list) {
    if (!item || seen[item]) continue;
    seen[item] = true;
    out.push(item);
  }
  return out;
}

function git(cwd, args) {
  try {
    const result = spawnSync("git", args, {
      cwd,
      encoding: "utf8",
      timeout: 3000,
      stdio: ["ignore", "pipe", "ignore"],
    });
    if (result.status !== 0 || !result.stdout) return "";
    return result.stdout.trim();
  } catch {
    return "";
  }
}

// ── Skill index ───────────────────────────────────────────────────────────────

/** Read docs/skill-index.json. Returns [] when it is missing or unusable —
 *  the caller treats an empty index as "nothing to gate". */
function readSkillIndex(file) {
  const data = readJsonFile(file || skillIndexPath());
  if (!Array.isArray(data)) return [];
  const rows = [];
  for (const row of data) {
    if (!row || typeof row !== "object") continue;
    if (typeof row.name !== "string" || !row.name) continue;
    rows.push({
      name: row.name,
      agent: typeof row.agent === "string" ? row.agent : "",
      team: typeof row.team === "string" ? row.team : "",
      description: typeof row.description === "string" ? row.description : "",
    });
  }
  return rows;
}

function isAlwaysOn(name) {
  if (ALWAYS_ON_NAMES.indexOf(name) !== -1) return true;
  const prefix = String(name).split("-")[0];
  return ALWAYS_ON_PREFIXES.indexOf(prefix) !== -1;
}

/** Agent entry-point skills are single-word (`/forge`, `/warden`). They are the
 *  door to a whole agent, so even a dropped team keeps its doors visible by
 *  name — the cost is a handful of characters each. */
function isEntrySkill(row) {
  return row.name.indexOf("-") === -1;
}

// ── Project signals ───────────────────────────────────────────────────────────

const SKIP_DIRS = new Set([
  ".git",
  "node_modules",
  ".venv",
  "venv",
  "__pycache__",
  "dist",
  "build",
  "target",
  "vendor",
  ".next",
  ".cache",
  "coverage",
  ".claude",
  ".agent-logs",
]);

const DEP_FILES = [
  "package.json",
  "pyproject.toml",
  "requirements.txt",
  "go.mod",
  "Cargo.toml",
  "Gemfile",
  "composer.json",
];

function collectDependencies(cwd) {
  const deps = [];

  const pkg = readJsonFile(path.join(cwd, "package.json"));
  if (pkg && typeof pkg === "object") {
    for (const field of [
      "dependencies",
      "devDependencies",
      "peerDependencies",
    ]) {
      const block = pkg[field];
      if (block && typeof block === "object") deps.push(...Object.keys(block));
    }
    if (Array.isArray(pkg.keywords)) deps.push(...pkg.keywords.map(String));
  }

  // Everything else is scanned lexically. A dependency list is a bag of names;
  // parsing five manifest grammars correctly would buy nothing here.
  for (const file of [
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
    "Cargo.toml",
    "Gemfile",
  ]) {
    const text = readTextFile(path.join(cwd, file), 40000);
    if (!text) continue;
    const quoted = text.match(/["']([A-Za-z][A-Za-z0-9._/-]{1,48})["']/g) || [];
    for (const token of quoted) deps.push(token.replace(/["']/g, ""));
    const bare = text.match(/^\s*([a-z][a-z0-9._-]{1,40})\s*[=>~<]/gim) || [];
    for (const token of bare)
      deps.push(token.trim().replace(/[\s=><~].*$/, ""));
  }

  return uniq(deps.map((d) => String(d).toLowerCase())).slice(0, 80);
}

function walkProject(cwd) {
  const dirs = [];
  const extCount = Object.create(null);
  let files = 0;
  const queue = [{ dir: cwd, depth: 0 }];

  while (queue.length && files < 4000) {
    const { dir, depth } = queue.shift();
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (entry.name.startsWith(".") && depth === 0 && entry.name !== ".github")
        continue;
      if (SKIP_DIRS.has(entry.name)) continue;
      if (entry.isDirectory()) {
        if (depth === 0) dirs.push(entry.name);
        if (depth < 3)
          queue.push({ dir: path.join(dir, entry.name), depth: depth + 1 });
      } else if (entry.isFile()) {
        files++;
        const ext = path.extname(entry.name).slice(1).toLowerCase();
        if (ext && ext.length <= 5) extCount[ext] = (extCount[ext] || 0) + 1;
      }
    }
  }

  const extensions = Object.keys(extCount)
    .sort((a, b) => extCount[b] - extCount[a])
    .slice(0, 14);

  return { dirs: dirs.slice(0, 30), extensions, files };
}

/** Everything the decision layer gets to see about this project. Bounded in
 *  size: a decision request is small and a huge state would dilute it. */
function gatherSignals(cwd) {
  const tree = walkProject(cwd);
  const deps = collectDependencies(cwd);
  const branch = git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"]);
  const commits = git(cwd, ["log", "-20", "--pretty=%s"])
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 20);

  const manifests = DEP_FILES.filter((f) => {
    try {
      return fs.existsSync(path.join(cwd, f));
    } catch {
      return false;
    }
  });

  const pkg = readJsonFile(path.join(cwd, "package.json"));
  const blurb =
    (pkg && typeof pkg.description === "string" ? pkg.description : "") ||
    readTextFile(path.join(cwd, "README.md"), 600).replace(/\s+/g, " ").trim();

  const parts = {
    project: path.basename(cwd),
    branch: branch,
    blurb: blurb.slice(0, 400),
    manifests: manifests,
    directories: tree.dirs,
    extensions: tree.extensions,
    dependencies: deps,
    commits: commits,
    fileCount: tree.files,
  };

  const text = [
    "Project: " + parts.project,
    parts.branch ? "Branch: " + parts.branch : "",
    parts.blurb ? "About: " + parts.blurb : "",
    parts.manifests.length ? "Manifests: " + parts.manifests.join(", ") : "",
    parts.directories.length
      ? "Top-level directories: " + parts.directories.join(", ")
      : "",
    parts.extensions.length ? "File types: " + parts.extensions.join(", ") : "",
    parts.dependencies.length
      ? "Dependencies: " + parts.dependencies.join(", ")
      : "",
    parts.commits.length ? "Recent commits: " + parts.commits.join(" | ") : "",
  ]
    .filter(Boolean)
    .join("\n")
    .slice(0, 6000);

  // A directory with no manifests, no tracked history and almost no files tells
  // us nothing, and a decision made from nothing is worse than no decision.
  const empty =
    !parts.manifests.length &&
    !parts.commits.length &&
    !parts.dependencies.length &&
    parts.fileCount < 3;

  return { text, parts, empty };
}

/** Teams the branch name argues for, whatever the scores say. */
function branchForcedTeams(branch) {
  const tokens = String(branch || "")
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
  if (!tokens.length) return [];
  const forced = [];
  for (const team of Object.keys(BRANCH_TEAM_HINTS)) {
    const hints = BRANCH_TEAM_HINTS[team];
    if (tokens.some((t) => hints.indexOf(t) !== -1)) forced.push(team);
  }
  return forced;
}

/** Agents the branch name names directly (`fix/warden-iam` → warden). */
function branchForcedAgents(branch, index) {
  const tokens = new Set(
    String(branch || "")
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter(Boolean),
  );
  if (!tokens.size) return [];
  const agents = uniq(index.map((r) => r.agent).filter(Boolean));
  return agents.filter((a) => tokens.has(String(a).toLowerCase()));
}

// ── Decision ──────────────────────────────────────────────────────────────────

/**
 * The environment lib/jev/client.js is allowed to see.
 *
 * The client treats the presence of OPENROUTER_API_KEY, JEV_API_KEY or
 * TYPESAFE_API_KEY as consent to call the hosted decision model. That is a
 * reasonable rule for a command the user typed; it is the wrong rule for an
 * unattended SessionStart hook, because a key exported in a shell profile for
 * some unrelated tool is not an opt-in to shipping this project's name,
 * description, directory names, file extensions, dependency list and recent
 * commit subjects to a third party on every session start.
 *
 * So the gate is offline by default whatever the ambient environment holds.
 * Set TONONE_GATE_JEV=1 to opt this hook in; the local scorer answers
 * otherwise, and the whole feature is designed to work that way.
 */
function jevEnv() {
  if (truthyEnv(process.env.TONONE_GATE_JEV)) return process.env;
  return Object.assign({}, process.env, {
    TONONE_JEV_OFFLINE: "1",
    JEV_API_KEY: "",
    TYPESAFE_API_KEY: "",
    OPENROUTER_API_KEY: "",
  });
}

function truthyEnv(value) {
  if (!value) return false;
  const v = String(value).trim().toLowerCase();
  return v !== "" && v !== "0" && v !== "false" && v !== "no" && v !== "off";
}

function loadJev() {
  try {
    return require(path.join(PLUGIN_ROOT, "lib", "jev", "client.js"));
  } catch {
    return null;
  }
}

function loadCache() {
  try {
    return require(path.join(PLUGIN_ROOT, "lib", "jev", "cache.js"));
  } catch {
    return null;
  }
}

/**
 * Position every option inside the spread of its own question: 1 for the
 * top-scoring option, 0 for the bottom one. `spread` is that range measured
 * against the mean, which is how a flat distribution is told apart from a
 * discriminating one — the probabilities themselves cannot say.
 */
function normalize(probabilities, keys) {
  let max = -Infinity;
  let min = Infinity;
  let sum = 0;
  for (const key of keys) {
    const p = Number(probabilities && probabilities[key]) || 0;
    if (p > max) max = p;
    if (p < min) min = p;
    sum += p;
  }
  if (!isFinite(max) || !isFinite(min) || !keys.length) {
    return { z: Object.create(null), spread: 0, max: 0 };
  }
  const mean = sum / keys.length;
  const range = max - min;
  const z = Object.create(null);
  for (const key of keys) {
    const p = Number(probabilities && probabilities[key]) || 0;
    z[key] = range > 0 ? (p - min) / range : 0;
  }
  return { z, spread: mean > 0 ? range / mean : 0, max };
}

/** Split a list into as few groups as possible, all of them about the same
 *  size. Even groups matter: the share of a group that keeps its description is
 *  a fraction of the group, so a stray group of one would keep that one skill. */
function chunk(list, size) {
  if (list.length <= size) return list.length ? [list.slice()] : [];
  const groups = Math.ceil(list.length / size);
  const each = Math.ceil(list.length / groups);
  const out = [];
  for (let i = 0; i < list.length; i += each) out.push(list.slice(i, i + each));
  return out;
}

/**
 * Stage one: which teams does this project need?
 * One request carrying a choice across the ten teams plus a breadth score, so
 * a broad project keeps more teams than a narrow one.
 */
async function scoreTeams(jev, state, teamsPresent, opts) {
  const options = Object.create(null);
  for (const team of teamsPresent) {
    options[team] = TEAMS[team] || { what: team, not_for: "" };
  }

  const result = await jev.batch(
    state,
    {
      teams: {
        type: "choice",
        question:
          "Which specialist team's skills does the work in this project mainly draw on?",
        options: options,
      },
      breadth: {
        type: "score",
        question: "How many different disciplines does this project span?",
        levels: [
          "One narrow technical domain, worked on by one kind of specialist",
          "A couple of adjacent domains, for example code plus infrastructure",
          "A whole product across engineering, product, design and operations",
        ],
      },
    },
    opts,
  );

  const teams = result.answers.teams || {};
  const breadth = result.answers.breadth || {};
  return {
    probabilities: teams.probabilities || {},
    confidence: Number(teams.confidence) || 0,
    breadth: typeof breadth.answer === "number" ? breadth.answer : 1,
    source: result.source || "local",
  };
}

/**
 * The skills of one group that keep their full description: those in the upper
 * part of the group's own spread, never more than MAX_ON_FRACTION of the group,
 * never fewer than one.
 *
 * When the group's probabilities are flat (`spread < MIN_SPREAD`) the ranking is
 * noise rather than signal, and the cut falls back to plain rank order. That is
 * deliberate and safe: everything not chosen becomes `name-only`, which keeps
 * the skill's name in context and keeps `/skill-name` working, so a wrong guess
 * costs a description, not a capability.
 */
function pickOn(group) {
  const ranked = group.ranked || [];
  if (!ranked.length) return [];
  const cap = Math.max(1, Math.floor(ranked.length * MAX_ON_FRACTION));
  const useZ = group.spread >= MIN_SPREAD;
  const eligible = useZ
    ? ranked.filter((name) => (group.z[name] || 0) >= SKILL_ON_Z)
    : [];
  const chosen = (eligible.length ? eligible : ranked).slice(0, cap);
  return chosen.length ? chosen : ranked.slice(0, 1);
}

/**
 * Stage two: within the surviving teams only, which skills earn a description?
 * One request for all surviving teams; a team with more than
 * MAX_OPTIONS_PER_QUESTION skills is split into groups and ranked within each.
 */
async function scoreSkills(jev, state, survivingTeams, byTeam, opts) {
  const questions = Object.create(null);
  const groups = [];

  for (const team of survivingTeams) {
    const rows = byTeam[team] || [];
    const parts = chunk(rows, MAX_OPTIONS_PER_QUESTION);
    parts.forEach((part, i) => {
      const key = "g" + groups.length;
      const options = Object.create(null);
      for (const row of part) {
        options[row.name] = String(row.description || row.name).slice(0, 260);
      }
      questions[key] = {
        type: "choice",
        question:
          "Which of these " +
          team +
          " skills is most likely to be used on this project" +
          (parts.length > 1
            ? " (group " + (i + 1) + " of " + parts.length + ")"
            : "") +
          "?",
        options: options,
      };
      groups.push({ key, team, names: part.map((r) => r.name) });
    });
  }

  if (!groups.length) return { groups: [], source: "local" };

  const result = await jev.batch(state, questions, opts);

  for (const group of groups) {
    const answer = result.answers[group.key] || {};
    const probabilities = answer.probabilities || {};
    const scored = normalize(probabilities, group.names);
    group.z = scored.z;
    group.spread = scored.spread;
    group.ranked = group.names
      .slice()
      .sort(
        (a, b) =>
          (Number(probabilities[b]) || 0) - (Number(probabilities[a]) || 0),
      );
  }
  return { groups, source: result.source || "local" };
}

/**
 * Score the catalogue and return a state for every skill in it.
 *
 * Resolves to { states, teams, source, reason, degraded }. `degraded: true`
 * means nothing was decided and the caller must leave the session alone.
 */
async function decide(index, signals, options) {
  const opts = Object.assign(
    { timeoutMs: DECISION_TIMEOUT_MS, retries: 0 },
    options && options.jevOpts,
  );
  // Nothing here goes to the network unless the user asked this hook for it.
  // See jevEnv().
  if (!opts.env) opts.env = jevEnv();
  const jev = (options && options.jev) || loadJev();

  const allOn = (reason) => ({
    states: Object.create(null),
    teams: {
      kept: uniq(index.map((r) => r.team).filter(Boolean)),
      dropped: [],
    },
    source: "none",
    reason: reason,
    degraded: true,
  });

  if (!jev || typeof jev.batch !== "function")
    return allOn("decision layer unavailable");
  if (!index.length) return allOn("empty skill index");
  if (signals.empty) return allOn("no project signals");

  const byTeam = Object.create(null);
  for (const row of index) {
    const team = row.team || "Engineering";
    (byTeam[team] = byTeam[team] || []).push(row);
  }
  const teamsPresent = Object.keys(byTeam);

  const stage1 = await scoreTeams(jev, signals.text, teamsPresent, opts);
  const teamScores = normalize(stage1.probabilities, teamsPresent);

  // No usable signal: the local scorer reports confidence 0 and a flat
  // distribution when nothing in the project overlaps anything in the options.
  // Gating on that is guessing, so do not gate at all.
  if (
    stage1.confidence <= 0 ||
    teamScores.max <= 0 ||
    teamScores.spread < MIN_SPREAD
  ) {
    return allOn("no signal in team scoring");
  }

  const ranked = teamsPresent
    .slice()
    .sort(
      (a, b) =>
        (Number(stage1.probabilities[b]) || 0) -
          (Number(stage1.probabilities[a]) || 0) ||
        (a < b ? -1 : a > b ? 1 : 0),
    );

  // How many teams survive: a narrow project keeps MIN_TEAMS, a whole-product
  // one keeps MIN_TEAMS + 2. Teams scoring in the upper part of the spread
  // survive regardless of where the cut fell.
  const keepCount = Math.min(
    teamsPresent.length,
    MIN_TEAMS + Math.max(0, Math.min(2, Math.round(stage1.breadth))),
  );
  const forced = ALWAYS_KEEP_TEAMS.concat(
    branchForcedTeams(signals.parts.branch),
  ).filter((t) => teamsPresent.indexOf(t) !== -1);
  const kept = uniq(
    ranked
      .filter(
        (team, i) => i < keepCount || (teamScores.z[team] || 0) >= TEAM_KEEP_Z,
      )
      .concat(forced),
  );
  const dropped = teamsPresent.filter((t) => kept.indexOf(t) === -1);

  const stage2 = await scoreSkills(jev, signals.text, kept, byTeam, opts);

  const keepDescription = new Set();
  for (const group of stage2.groups) {
    for (const name of pickOn(group)) keepDescription.add(name);
  }

  const forcedAgents = branchForcedAgents(signals.parts.branch, index);
  const states = Object.create(null);

  for (const row of index) {
    const team = row.team || "Engineering";
    if (isAlwaysOn(row.name) || forcedAgents.indexOf(row.agent) !== -1) {
      states[row.name] = STATE_ON;
      continue;
    }
    if (kept.indexOf(team) !== -1) {
      states[row.name] = keepDescription.has(row.name)
        ? STATE_ON
        : STATE_NAME_ONLY;
      continue;
    }
    // Dropped team: the agent's own door (`/forge`, `/warden`) stays visible by
    // name, the rest of the team leaves the context and stays reachable by
    // typing its slash command.
    states[row.name] = isEntrySkill(row) ? STATE_NAME_ONLY : STATE_USER_ONLY;
  }

  // Never silence a surviving team completely, whatever the ranking did.
  for (const team of kept) {
    const rows = byTeam[team] || [];
    if (rows.length && !rows.some((r) => states[r.name] === STATE_ON)) {
      states[rows[0].name] = STATE_ON;
    }
  }

  const source =
    stage1.source === "jev" && stage2.source === "jev"
      ? "jev"
      : stage2.source || stage1.source || "local";

  return {
    states,
    teams: { kept, dropped },
    source,
    reason: "scored",
    degraded: false,
  };
}

// ── Token accounting ──────────────────────────────────────────────────────────

/** What the catalogue costs in a session, before and after the states apply. */
function accounting(index, states) {
  let beforeChars = 0;
  let afterChars = 0;
  const counts = { on: 0, "name-only": 0, "user-invocable-only": 0 };

  for (const row of index) {
    const nameChars = row.name.length;
    const fullChars = nameChars + 2 + row.description.length;
    beforeChars += fullChars;

    const state = sanitizeState(states[row.name] || STATE_ON);
    counts[state]++;
    if (state === STATE_ON) afterChars += fullChars;
    else if (state === STATE_NAME_ONLY) afterChars += nameChars;
  }

  const before = {
    skills: index.length,
    chars: beforeChars,
    tokens: estimateTokens(beforeChars),
  };
  const after = {
    skills: counts.on + counts["name-only"],
    chars: afterChars,
    tokens: estimateTokens(afterChars),
  };
  const savedTokens = Math.max(0, before.tokens - after.tokens);
  return {
    before,
    after,
    counts,
    saved: {
      tokens: savedTokens,
      pct: before.tokens ? Math.round((savedTokens / before.tokens) * 100) : 0,
    },
  };
}

// ── Cache ─────────────────────────────────────────────────────────────────────
//
// Keyed on the project signals plus a fingerprint of the skill index, so a new
// skill, an edited description or a changed project all invalidate it. Stored
// beside the jev response cache (TONONE_JEV_CACHE_DIR relocates both).

/** A fingerprint of this hook's own source. Any change to the scoring — a new
 *  threshold, a reworded team description, a different cut — produces a new
 *  cache key, so a code change can never keep serving decisions made by the
 *  version before it. Falls back to the tunables when the source is unreadable. */
let ALGO_FINGERPRINT = null;
function algoFingerprint() {
  if (ALGO_FINGERPRINT) return ALGO_FINGERPRINT;
  let material = "";
  try {
    material = fs.readFileSync(__filename, "utf8");
  } catch {
    material = JSON.stringify([
      MIN_TEAMS,
      TEAM_KEEP_Z,
      SKILL_ON_Z,
      MAX_ON_FRACTION,
      MIN_SPREAD,
      MAX_OPTIONS_PER_QUESTION,
      ALWAYS_KEEP_TEAMS,
      ALWAYS_ON_PREFIXES,
      ALWAYS_ON_NAMES,
      TEAMS,
    ]);
  }
  ALGO_FINGERPRINT = crypto
    .createHash("sha256")
    .update(material)
    .digest("hex")
    .slice(0, 16);
  return ALGO_FINGERPRINT;
}

function indexFingerprint(index) {
  const material = index
    .map((r) => r.name + "\u0000" + r.description)
    .join("\u0001");
  return crypto
    .createHash("sha256")
    .update(material)
    .digest("hex")
    .slice(0, 16);
}

function cacheKey(cache, signals, index) {
  if (!cache || typeof cache.keyFor !== "function") return null;
  return cache.keyFor({
    ns: "tonone-skill-gate/1",
    algo: algoFingerprint(),
    index: indexFingerprint(index),
    signals: {
      project: signals.parts.project,
      branch: signals.parts.branch,
      manifests: signals.parts.manifests,
      directories: signals.parts.directories,
      extensions: signals.parts.extensions,
      dependencies: signals.parts.dependencies,
      commits: signals.parts.commits,
    },
  });
}

// ── Settings ──────────────────────────────────────────────────────────────────

function projectRoot(cwd) {
  const top = git(cwd, ["rev-parse", "--show-toplevel"]);
  return top && fs.existsSync(top) ? top : cwd;
}

function settingsPath(root) {
  return path.join(root, ".claude", "settings.local.json");
}

/** Which overrides this hook wrote last time, so a later run can retract them
 *  without ever touching an override the user wrote by hand. Kept out of the
 *  settings file on purpose: an unknown key there is user-visible noise.
 *
 *  It lives next to the file it describes — `.claude/tonone-skill-gate.json`,
 *  beside `.claude/settings.local.json` — so that the two are created, moved,
 *  copied and deleted together. An earlier version kept it in the cache
 *  directory, keyed on a hash of the absolute project path; a cache clean, a
 *  machine move or a re-clone to another path then orphaned every override,
 *  because an override with no provenance reads as the user's and is never
 *  touched again. That made --reset a no-op and froze the gate on a stale
 *  decision. `TONONE_GATE_STATE_DIR` still overrides the location for tests
 *  and tooling, and the old cache location is still read once, so an install
 *  that was gated by the earlier version keeps its undo. */
function provenancePath(root) {
  const override = process.env.TONONE_GATE_STATE_DIR;
  if (override) {
    const id = crypto
      .createHash("sha256")
      .update(root)
      .digest("hex")
      .slice(0, 16);
    return path.join(override, id + ".json");
  }
  return path.join(root, ".claude", "tonone-skill-gate.json");
}

/** Where releases before this one kept the record. Read-only, for migration. */
function legacyProvenancePath(root) {
  const base = path.join(
    process.env.XDG_CACHE_HOME && path.isAbsolute(process.env.XDG_CACHE_HOME)
      ? process.env.XDG_CACHE_HOME
      : path.join(os.homedir() || os.tmpdir(), ".cache"),
    "tonone",
    "skill-gate",
  );
  const id = crypto
    .createHash("sha256")
    .update(root)
    .digest("hex")
    .slice(0, 16);
  return path.join(base, id + ".json");
}

function readProvenance(root) {
  const current = provenancePath(root);
  let data = readJsonFile(current);
  if (!data || typeof data !== "object" || typeof data.managed !== "object") {
    // Fall back to the pre-migration location, once, and only when the current
    // one is absent or unusable. Never when the location was overridden.
    const legacy = process.env.TONONE_GATE_STATE_DIR
      ? null
      : legacyProvenancePath(root);
    data = legacy && legacy !== current ? readJsonFile(legacy) : null;
  }
  if (!data || typeof data !== "object" || typeof data.managed !== "object") {
    return { managed: {} };
  }
  return { managed: data.managed || {} };
}

function writeProvenance(root, managed) {
  const file = provenancePath(root);
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    writeFileAtomic(
      file,
      JSON.stringify({ v: 1, root, updatedAt: Date.now(), managed }, null, 2),
      0o600,
    );
    return true;
  } catch {
    return false;
  }
}

function writeFileAtomic(file, contents, mode) {
  const tmp =
    file + ".tmp." + process.pid + "." + crypto.randomBytes(4).toString("hex");
  try {
    fs.writeFileSync(tmp, contents, mode ? { mode } : undefined);
    fs.renameSync(tmp, file);
    return true;
  } catch {
    try {
      fs.unlinkSync(tmp);
    } catch {}
    return false;
  }
}

/**
 * Merge the decision into .claude/settings.local.json.
 *
 * Rules, in order of precedence:
 *   1. Every key in the file that is not `skillOverrides` is untouched.
 *   2. An override the user wrote by hand is never modified or removed.
 *   3. An override this hook wrote before is replaced or retracted freely.
 *   4. `off` is never written, by construction (sanitizeState).
 *
 * Returns { ok, changed, written, path, reason }.
 */
function applySettings(root, states) {
  const file = settingsPath(root);
  const prev = readProvenance(root);
  // A settings file that exists but cannot be read is the one case where doing
  // nothing is mandatory: rewriting it would drop permissions, env, mcpServers
  // and everything else in it. JSON with a comment in it, a half-written file
  // and a permission error all land here.
  const read = readJsonFileStrict(file);
  if (!read.ok) {
    return {
      ok: false,
      changed: false,
      written: 0,
      path: file,
      reason: "settings file is unreadable or not valid JSON; left untouched",
    };
  }
  const settings = read.exists ? read.value : {};
  if (!settings || typeof settings !== "object" || Array.isArray(settings)) {
    return {
      ok: false,
      changed: false,
      written: 0,
      path: file,
      reason: "settings file is not an object",
    };
  }

  const existing =
    settings.skillOverrides &&
    typeof settings.skillOverrides === "object" &&
    !Array.isArray(settings.skillOverrides)
      ? settings.skillOverrides
      : {};
  const next = Object.assign(Object.create(null), existing);
  const managed = Object.create(null);

  // An entry counts as the user's — and is then never touched again — when it
  // is in the file and either this hook never wrote it, or this hook wrote a
  // different value than the one there now. Editing an override by hand is how
  // a person overrules the gate, so that edit has to survive the next run.
  const userOwned = (name) =>
    Object.prototype.hasOwnProperty.call(existing, name) &&
    (!Object.prototype.hasOwnProperty.call(prev.managed, name) ||
      existing[name] !== prev.managed[name]);

  // Retract everything this hook still owns; whatever is still deserved is
  // re-added immediately below, so a shrinking decision leaves no stale entry.
  for (const name of Object.keys(prev.managed)) {
    if (!Object.prototype.hasOwnProperty.call(next, name)) continue;
    if (userOwned(name)) continue;
    delete next[name];
  }

  for (const name of Object.keys(states)) {
    if (userOwned(name)) continue;

    const state = sanitizeState(states[name]);
    if (state === STATE_ON) continue; // `on` is the default; writing it is noise
    next[name] = state;
    managed[name] = state;
  }

  // Belt and braces: nothing but the three states ever reaches the file.
  for (const name of Object.keys(next)) {
    if (VALID_STATES.indexOf(next[name]) === -1) delete next[name];
  }

  const before = JSON.stringify(existing);
  const after = JSON.stringify(next);
  if (Object.keys(next).length) settings.skillOverrides = next;
  else delete settings.skillOverrides;

  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
  } catch {
    return {
      ok: false,
      changed: false,
      written: 0,
      path: file,
      reason: "cannot create .claude/",
    };
  }

  const ok = writeFileAtomic(file, JSON.stringify(settings, null, 2) + "\n");
  if (!ok) {
    return {
      ok: false,
      changed: false,
      written: 0,
      path: file,
      reason: "settings file not writable",
    };
  }
  writeProvenance(root, managed);

  return {
    ok: true,
    changed: before !== after,
    written: Object.keys(managed).length,
    path: file,
    reason: "written",
  };
}

/**
 * Remove every override this hook wrote and forget it ever wrote them.
 *
 * With `{ all: true }` it removes the whole `skillOverrides` object instead,
 * including entries written by hand. That is the guaranteed way out when the
 * provenance record has been lost and the hook can no longer tell its own
 * entries from the user's; it is never the default, because it discards a
 * deliberate hand edit.
 *
 * Returns { ok, removed, path, reason }.
 */
function resetSettings(root, options) {
  const all = Boolean(options && options.all);
  const file = settingsPath(root);
  const prev = readProvenance(root);
  const read = readJsonFileStrict(file);
  let removed = 0;

  // Same rule as applySettings: a file that exists but cannot be read is never
  // rewritten, and the provenance record is kept so a later run can still undo.
  if (!read.ok) {
    return {
      ok: false,
      removed: 0,
      path: file,
      reason: "settings file is unreadable or not valid JSON; left untouched",
    };
  }

  const settings = read.value;
  if (
    settings &&
    typeof settings === "object" &&
    !Array.isArray(settings) &&
    settings.skillOverrides
  ) {
    const names = all
      ? Object.keys(settings.skillOverrides)
      : Object.keys(prev.managed);
    for (const name of names) {
      if (Object.prototype.hasOwnProperty.call(settings.skillOverrides, name)) {
        delete settings.skillOverrides[name];
        removed++;
      }
    }
    if (!Object.keys(settings.skillOverrides).length)
      delete settings.skillOverrides;
    writeFileAtomic(file, JSON.stringify(settings, null, 2) + "\n");
  }
  writeProvenance(root, {});
  return { ok: true, removed, path: file, reason: "reset" };
}

// ── Output ────────────────────────────────────────────────────────────────────

function fmt(n) {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function renderReport(result) {
  const a = result.accounting;
  const lines = [];
  lines.push("╭─ TONONE ── skill-gate " + "─".repeat(24) + "╮");
  lines.push("");
  lines.push(
    "  ## " +
      fmt(a.before.tokens) +
      " → " +
      fmt(a.after.tokens) +
      " tokens of skill catalogue (−" +
      a.saved.pct +
      "%)",
  );
  lines.push("");
  lines.push("  ### Decision");
  lines.push(
    "  - ● INFO — source: " +
      result.source +
      (result.cached ? " (cached)" : ""),
  );
  lines.push(
    "  - ● INFO — teams kept: " + (result.teams.kept.join(", ") || "none"),
  );
  lines.push(
    "  - ● INFO — teams dropped: " +
      (result.teams.dropped.join(", ") || "none"),
  );
  if (result.degraded) {
    lines.push("  - ▲ WARNING — no overrides applied: " + result.reason);
  }
  lines.push("");
  lines.push("  ### Skill states");
  lines.push("  ┌────────────────────────┬───────┬────────┐");
  lines.push("  │ State                  │ Count │ Tokens │");
  lines.push("  ├────────────────────────┼───────┼────────┤");
  lines.push(row3("on", a.counts.on, "full"));
  lines.push(row3("name-only", a.counts["name-only"], "name"));
  lines.push(row3("user-invocable-only", a.counts["user-invocable-only"], "0"));
  lines.push("  └────────────────────────┴───────┴────────┘");
  lines.push("");
  lines.push("  ### Next Steps");
  lines.push("  → node hooks/tonone-skill-gate.js --reset  to undo");
  lines.push("  → /apex-gate for the per-skill breakdown");
  lines.push("");
  lines.push(
    "╰─ estimate: " +
      CHARS_PER_TOKEN +
      " chars ≈ 1 token " +
      "─".repeat(14) +
      "╯",
  );
  return lines.join("\n");
}

function row3(label, count, tokens) {
  const pad = (s, w, right) => {
    s = String(s);
    if (s.length > w) s = s.slice(0, w - 1) + "…";
    return right ? " ".repeat(w - s.length) + s : s + " ".repeat(w - s.length);
  };
  return (
    "  │ " +
    pad(label, 22) +
    " │ " +
    pad(count, 5, true) +
    " │ " +
    pad(tokens, 6, true) +
    " │"
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

function parseArgs(argv) {
  const args = {
    dryRun: false,
    json: false,
    force: false,
    reset: false,
    all: false,
    cwd: null,
    help: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--dry-run") args.dryRun = true;
    else if (arg === "--json") args.json = true;
    else if (arg === "--force") args.force = true;
    else if (arg === "--reset") args.reset = true;
    else if (arg === "--all") args.all = true;
    else if (arg === "--help" || arg === "-h") args.help = true;
    else if (arg === "--cwd") args.cwd = argv[++i] || null;
    else if (arg.startsWith("--cwd=")) args.cwd = arg.slice(6);
  }
  return args;
}

const HELP = [
  "tonone-skill-gate — score the skill catalogue against this project",
  "",
  "  --dry-run   score and print the before/after token count, write nothing",
  "  --json      machine-readable output",
  "  --force     ignore the cached decision",
  "  --reset     remove every override this hook wrote, then exit",
  "  --reset --all",
  "              remove every skillOverrides entry, including hand-written",
  "              ones — the way out when the record of what the hook owns",
  "              has been lost",
  "  --cwd DIR   score DIR instead of the current directory",
  "",
  "  TONONE_GATE=off disables the hook.",
  "  TONONE_GATE_JEV=1 opts this hook in to the hosted decision model. Without",
  "  it the gate scores locally and performs no network I/O, whatever API keys",
  "  happen to be exported in the environment.",
].join("\n");

async function run(argv, hookInput) {
  const args = parseArgs(argv);

  if (args.help) {
    process.stdout.write(HELP + "\n");
    return 0;
  }

  const cwd = args.cwd || (hookInput && hookInput.cwd) || process.cwd();

  if (args.reset) {
    const result = resetSettings(projectRoot(cwd), { all: args.all });
    process.stdout.write(
      args.json
        ? JSON.stringify(result) + "\n"
        : result.ok
          ? "skill gate reset: " +
            result.removed +
            " override(s) removed\n" +
            (result.removed === 0 && !args.all
              ? "  nothing was owned by the gate. If overrides remain, " +
                "--reset --all removes every skillOverrides entry.\n"
              : "")
          : "skill gate reset: " + result.reason + "\n",
    );
    return 0;
  }

  if (String(process.env.TONONE_GATE || "").toLowerCase() === "off") {
    if (args.dryRun || args.json) {
      process.stdout.write(
        args.json
          ? JSON.stringify({ ok: false, reason: "TONONE_GATE=off" }) + "\n"
          : "skill gate: off\n",
      );
    }
    return 0;
  }

  const index = readSkillIndex();
  if (!index.length) {
    // Nothing to gate. A tonone checkout without docs/skill-index.json is a
    // broken checkout, not a reason to interfere with the session.
    if (args.dryRun || args.json) {
      const reason = "no skill index at " + skillIndexPath();
      process.stdout.write(
        (args.json
          ? JSON.stringify({ ok: false, reason: reason })
          : "skill gate: " + reason) + "\n",
      );
    }
    return 0;
  }

  const signals = gatherSignals(cwd);
  const cache = loadCache();
  const key = args.force ? null : cacheKey(cache, signals, index);

  let decision = null;
  let cached = false;
  if (key && cache) {
    const hit = cache.get(key, CACHE_TTL_MS);
    if (hit && hit.states && typeof hit.states === "object") {
      decision = hit;
      cached = true;
    }
  }

  if (!decision) {
    decision = await decide(index, signals);
    if (key && cache && !decision.degraded) cache.set(key, decision);
  }

  const result = {
    ok: true,
    cached,
    source: decision.source,
    reason: decision.reason,
    degraded: Boolean(decision.degraded),
    teams: decision.teams,
    accounting: accounting(index, decision.states),
  };
  // The per-skill states are the whole decision; --json is the only place they
  // are printed, because the human report has a 40-line budget.
  if (args.json) result.states = decision.states;

  if (args.dryRun) {
    process.stdout.write(
      (args.json ? JSON.stringify(result, null, 2) : renderReport(result)) +
        "\n",
    );
    return 0;
  }

  if (decision.degraded) {
    if (args.json) process.stdout.write(JSON.stringify(result) + "\n");
    return 0;
  }

  const applied = applySettings(projectRoot(cwd), decision.states);
  result.applied = applied;

  if (args.json) {
    process.stdout.write(JSON.stringify(result) + "\n");
    return 0;
  }

  // The receipt is itself context, so it is one line and only when something
  // actually changed. It names the decision source, because "the hosted model
  // answered this" is exactly the thing a user is entitled to notice.
  if (applied.ok && applied.changed) {
    const a = result.accounting;
    const remote = decision.source === "jev" || decision.source === "fallback";
    process.stdout.write(
      "tonone skill gate: " +
        a.before.skills +
        " skills → " +
        a.after.skills +
        " in context, ~" +
        fmt(a.saved.tokens) +
        " tokens saved (−" +
        a.saved.pct +
        "%)" +
        (remote ? ", scored by the Jev API (TONONE_GATE_JEV=1)" : "") +
        ". Undo: node hooks/tonone-skill-gate.js --reset\n",
    );
  } else if (!applied.ok) {
    // Silence here would be the worst outcome: the settings file was left
    // alone for a reason and the user cannot see why.
    process.stdout.write(
      "tonone skill gate: " + applied.reason + "; no overrides written\n",
    );
  }
  return 0;
}

function main() {
  // Nothing below may keep the session waiting, and nothing below may throw.
  const deadline = setTimeout(() => process.exit(0), DEADLINE_MS);
  if (typeof deadline.unref === "function") deadline.unref();
  process.on("uncaughtException", () => process.exit(0));
  process.on("unhandledRejection", () => process.exit(0));

  const argv = process.argv.slice(2);

  const go = (hookInput) => {
    Promise.resolve()
      .then(() => run(argv, hookInput))
      .then(() => process.exit(0))
      .catch(() => process.exit(0));
  };

  // Hook invocations arrive as one JSON object on stdin; CLI invocations do not.
  if (argv.length || process.stdin.isTTY) {
    go(null);
    return;
  }

  let input = "";
  let stdinTimer = null;
  let done = false;

  // One exit from the read, used by end, error and the timeout alike. The
  // timeout used to call go(null) directly, which threw away a payload that had
  // already arrived — gating whatever directory the process happened to start
  // in rather than the project named in the payload — and left `done` false, so
  // a later end event started a second concurrent run. Parsing what has been
  // buffered so far is both safer and strictly more informed.
  const finish = () => {
    if (done) return;
    done = true;
    if (stdinTimer) clearTimeout(stdinTimer);
    let parsed = null;
    try {
      parsed = JSON.parse(input);
    } catch {}
    go(parsed);
  };

  stdinTimer = setTimeout(finish, STDIN_TIMEOUT_MS);
  if (typeof stdinTimer.unref === "function") stdinTimer.unref();
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (c) => (input += c));
  process.stdin.on("end", finish);
  process.stdin.on("error", finish);
}

if (require.main === module) {
  main();
} else {
  module.exports = {
    STATE_ON,
    STATE_NAME_ONLY,
    STATE_USER_ONLY,
    VALID_STATES,
    TEAMS,
    accounting,
    applySettings,
    branchForcedAgents,
    branchForcedTeams,
    decide,
    estimateTokens,
    gatherSignals,
    isAlwaysOn,
    isEntrySkill,
    jevEnv,
    legacyProvenancePath,
    provenancePath,
    algoFingerprint,
    readSkillIndex,
    resetSettings,
    skillIndexPath,
    run,
    sanitizeState,
    settingsPath,
  };
}
