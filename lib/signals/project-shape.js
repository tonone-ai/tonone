"use strict";

/**
 * lib/signals/project-shape.js — shared project-shape detection for tonone.
 *
 * One place that answers "what kind of repository is this, and which handful
 * of the 100 agents would actually earn their keep here?". Two consumers are
 * expected to share it:
 *
 *   hooks/tonone-onboard.js     — recommends a roster once, at install time
 *   hooks/tonone-skill-gate.js  — scores skills per session
 *
 * The skill gate already gathers a rich view of a project — dependencies,
 * top-level directories, file types, branch name, README blurb, recent commit
 * subjects — and exports it as `gatherSignals`. This module imports that rather
 * than keeping a second copy, so the roster the banner proposes and the skills
 * the gate leaves on are reasoning about the same evidence and the same state
 * string. What it adds on top is the one thing the gate's shape cannot express:
 * individual file names. `next.config.js`, `main.tf` and `dbt_project.yml` are
 * the strongest shape markers there are, and the gate records only extensions.
 * If the gate is not on disk, the local snapshot stands alone and every roster
 * still resolves.
 *
 * The contract both of them lean on:
 *
 *   gather(cwd)          -> a bounded, synchronous snapshot of the repo
 *   digest(signals)      -> that snapshot as prose, usable as a Jev `state`
 *   scoreRosters(signals)-> deterministic weighted scores, no I/O, no network
 *   recommend(cwd, opts) -> async; deterministic scores, Jev only on a tie
 *
 * Three rules, and they are the whole design:
 *
 * 1. Nothing here throws. Every filesystem read, every parse and every
 *    decision call is wrapped. A repository that cannot be read produces an
 *    empty snapshot and the default roster, never an exception.
 * 2. Nothing here requires credentials or network, and nothing here reaches
 *    the network without being asked to. The deterministic scorer is the
 *    primary path and always runs. lib/jev is consulted only to break a
 *    near-tie, and only its offline local scorer runs unless TONONE_JEV=1 (or
 *    TONONE_JEV_ROSTER=1) opts in explicitly — an OPENROUTER_API_KEY set for
 *    some other tool is not consent. When the call is opted in, what leaves
 *    the machine is digest(): directory, file, dependency and extension
 *    names, capped at MAX_DIGEST_CHARS, and never the branch name, README
 *    text or commit subjects the skill gate also collects.
 * 3. Everything is bounded. Directory walks are depth-limited and
 *    entry-capped, file reads are byte-capped, and the Jev call gets a short
 *    deadline and no retries. This runs inside a SessionStart hook; it may
 *    not be the reason a session feels slow.
 */

const fs = require("fs");
const path = require("path");

const PLUGIN_ROOT =
  process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..", "..");

// Bump when the shape of `gather()`'s output changes, so a consumer that
// caches signals can tell a stale snapshot from a current one.
const SIGNAL_VERSION = 1;

/**
 * The skill gate, if it is installed. Requiring it is side-effect free — it
 * runs `main()` only when it is the entry point — and the result is cached by
 * Node, so this costs one resolution per process.
 */
function loadGate() {
  try {
    return require(path.join(PLUGIN_ROOT, "hooks", "tonone-skill-gate.js"));
  } catch {
    return null;
  }
}

// ── Walk limits ─────────────────────────────────────────────────────────────

const MAX_ROOT_ENTRIES = 400;
const MAX_SUBDIR_ENTRIES = 200;
const MAX_FILE_BYTES = 16 * 1024;

// Second-level directories worth a look. Everything else stays unread: the
// point is a shape, not an inventory.
const PROBE_DIRS = [
  "src",
  "app",
  "apps",
  "lib",
  "packages",
  "services",
  "infra",
  "infrastructure",
  "terraform",
  "deploy",
  "deployment",
  "k8s",
  "kubernetes",
  "charts",
  "notebooks",
  "data",
  "models",
  "prompts",
  "evals",
  "migrations",
  "ios",
  "android",
  ".github",
];

const IGNORED_DIRS = new Set([
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
  ".terraform",
  "coverage",
]);

// ── Roster catalog ──────────────────────────────────────────────────────────

/**
 * Each roster is a small, opinionated team plus any bundle in the same domain.
 *
 * `bundles` is a *wider net*, not an exact match: `design-team` installs ten
 * design specialists, of which this roster names one. The exact roster is
 * always installed agent by agent, which is why `installCommands` puts that
 * command first and the bundles after it.
 *
 * `desc` is written for lib/jev: contrastive prose, not a label. The local
 * scorer is a TF-IDF vector space over exactly these strings, so `what` /
 * `not_for` wording is what makes the tie-break work without a key.
 *
 * `markers` are the deterministic half. Each entry is a predicate over the
 * snapshot with a weight; weights are summed, and the sum is the score.
 */
const ROSTERS = [
  {
    id: "frontend-web",
    label: "Frontend web app",
    agents: ["prism", "form", "draft", "axe"],
    bundles: ["design-team"],
    why: "UI work, a design system, and an accessibility pass",
    desc: {
      what: "A browser application: Next.js, React, Vue, Svelte or Astro pages, components, CSS, design tokens, accessibility.",
      not_for:
        "Cloud infrastructure, database pipelines, model training, mobile app stores.",
      examples: "next.config.js, app/page.tsx, tailwind.config.ts, components/",
    },
    markers: [
      { w: 5, dep: ["next"] },
      { w: 4, file: ["next.config.js", "next.config.mjs", "next.config.ts"] },
      { w: 3, dep: ["react", "vue", "svelte", "astro", "@remix-run/react"] },
      { w: 2, dep: ["tailwindcss", "styled-components", "@emotion/react"] },
      { w: 2, file: ["tailwind.config.js", "tailwind.config.ts"] },
      { w: 2, dir: ["components", "pages", "app"] },
      { w: 2, ext: [".tsx", ".jsx", ".svelte", ".vue"] },
    ],
  },
  {
    id: "infra-iac",
    label: "Infrastructure / IaC",
    agents: ["terra", "forge", "finop", "kube"],
    bundles: ["infra-specialist-team"],
    why: "Modules, drift, cost and cluster config",
    desc: {
      what: "Cloud infrastructure as code: Terraform modules and state, Kubernetes manifests, Helm charts, cloud networking and spend.",
      not_for: "User interfaces, statistical models, contracts, mobile builds.",
      examples: "main.tf, .terraform.lock.hcl, charts/, k8s/deployment.yaml",
    },
    markers: [
      { w: 5, ext: [".tf", ".tfvars"] },
      { w: 4, file: [".terraform.lock.hcl", "main.tf", "terragrunt.hcl"] },
      { w: 3, dir: ["terraform", "infra", "infrastructure"] },
      { w: 3, file: ["Chart.yaml", "kustomization.yaml", "skaffold.yaml"] },
      { w: 3, dir: ["k8s", "kubernetes", "charts"] },
      { w: 2, file: ["pulumi.yaml", "cloudformation.yaml", "serverless.yml"] },
    ],
  },
  {
    id: "data-python",
    label: "Python data / analytics",
    agents: ["flux", "lens", "clean", "feat"],
    bundles: ["data-science-team"],
    why: "Schemas, pipelines, data quality and metrics",
    desc: {
      what: "Data work in Python: dataframes, ETL pipelines, warehouse models, notebooks, dashboards, feature engineering, data quality.",
      not_for:
        "Browser UI, Terraform, contract drafting, firmware, app store releases.",
      examples:
        "requirements.txt with pandas, dbt_project.yml, notebooks/*.ipynb",
    },
    markers: [
      { w: 4, dep: ["pandas", "polars", "numpy", "pyspark", "duckdb"] },
      { w: 4, dep: ["dbt-core", "apache-airflow", "dagster", "prefect"] },
      { w: 3, file: ["dbt_project.yml", "airflow.cfg"] },
      { w: 3, ext: [".ipynb"] },
      { w: 3, dir: ["notebooks", "dags", "warehouse"] },
      { w: 2, ext: [".sql"] },
      { w: 1, file: ["pyproject.toml", "requirements.txt", "setup.py"] },
    ],
  },
  {
    id: "backend-api",
    label: "Backend / API service",
    agents: ["spine", "flux", "schema", "proof"],
    bundles: ["engineering-team", "devx-team"],
    why: "API design, data model, schema quality and tests",
    desc: {
      what: "A server-side service: HTTP or gRPC endpoints, an OpenAPI or GraphQL schema, database migrations, background workers.",
      not_for:
        "Design systems, Terraform modules, model training, marketing copy.",
      examples: "openapi.yaml, go.mod, migrations/, src/routes/",
    },
    markers: [
      {
        w: 4,
        file: [
          "openapi.yaml",
          "openapi.json",
          "swagger.yaml",
          "schema.graphql",
        ],
      },
      {
        w: 3,
        dep: ["express", "fastify", "nestjs", "fastapi", "django", "flask"],
      },
      { w: 3, file: ["go.mod", "Cargo.toml", "pom.xml", "build.gradle"] },
      { w: 3, dir: ["migrations", "handlers", "controllers"] },
      { w: 2, ext: [".proto"] },
      { w: 2, file: ["docker-compose.yml", "docker-compose.yaml"] },
    ],
  },
  {
    id: "ai-product",
    label: "LLM / AI product",
    agents: ["cortex", "evals", "trace", "guard"],
    bundles: ["ai-ops-team"],
    why: "Prompts, evals, tracing and output guardrails",
    desc: {
      what: "A product built on language models: prompt templates, retrieval, evaluation harnesses, inference cost, safety filters.",
      not_for: "Terraform, design tokens, invoices, embedded firmware.",
      examples: "prompts/, evals/, dependency on anthropic or langchain",
    },
    markers: [
      {
        w: 5,
        dep: ["anthropic", "openai", "langchain", "llama-index", "litellm"],
      },
      { w: 4, dep: ["transformers", "torch", "vllm", "sentence-transformers"] },
      { w: 3, dir: ["prompts", "evals", "eval"] },
      {
        w: 3,
        dep: [
          "chromadb",
          "pinecone-client",
          "qdrant-client",
          "weaviate-client",
        ],
      },
      { w: 2, file: ["prompts.yaml", "evals.yaml"] },
    ],
  },
  {
    id: "mobile-app",
    label: "Mobile app",
    agents: ["touch", "form", "draft", "proof"],
    // No bundle spans mobile: Touch is engineering, Form and Draft are
    // product. An inaccurate bundle is worse than none, so this roster
    // installs agent by agent.
    bundles: [],
    why: "Native UI, visual design and release testing",
    desc: {
      what: "A phone application: iOS or Android sources, Swift or Kotlin, React Native or Flutter, app store release builds.",
      not_for:
        "Cloud infrastructure, warehouse SQL, legal review, server APIs.",
      examples: "ios/Podfile, android/build.gradle, pubspec.yaml",
    },
    markers: [
      { w: 5, file: ["pubspec.yaml", "Podfile"] },
      { w: 4, dep: ["react-native", "expo"] },
      { w: 4, dir: ["ios", "android"] },
      { w: 3, ext: [".swift", ".kt", ".xcodeproj"] },
      { w: 2, file: ["fastlane", "Fastfile"] },
    ],
  },
  {
    id: "security",
    label: "Security-sensitive repo",
    agents: ["warden", "sast", "chain", "patch"],
    bundles: ["secops-team"],
    why: "Threat model, code scanning, SBOM and CVE triage",
    desc: {
      what: "A repository with an explicit security posture: scanning workflows, dependency policy, SBOMs, vulnerability disclosure.",
      not_for: "Design systems, dashboards, roadmaps, forecasting models.",
      examples: "SECURITY.md, .snyk, codeql workflow, sbom.json",
    },
    markers: [
      // Tooling is evidence of a security practice. A policy file is not:
      // SECURITY.md is boilerplate in a large share of public repositories,
      // and on its own it must stay under MIN_SCORE.
      { w: 4, file: [".snyk", "sbom.json", "trivy.yaml"] },
      { w: 3, file: [".semgrep.yml", "codeql-config.yml"] },
      { w: 2, file: ["SECURITY.md"] },
      { w: 2, dir: ["security"] },
    ],
  },
];

// The roster proposed when nothing matches. Small on purpose: Apex routes to
// the other 96 on demand, so an unrecognised repo pays for four agents, not a
// hundred.
const DEFAULT_ROSTER = {
  id: "starter",
  label: "General engineering",
  agents: ["apex", "atlas", "spine", "prism"],
  bundles: ["engineering-team"],
  why: "Routing, docs, backend and frontend — Apex reaches the rest on demand",
  desc: {
    what: "A repository with no single dominant shape.",
    not_for: "",
    examples: "",
  },
  markers: [],
};

// Apex is the front door for every takeover, status and review workflow, so
// it belongs in every roster — same rule apex-profile states.
const ALWAYS = "apex";

// A roster only wins outright when it clears the noise floor and beats the
// runner-up by more than the tie margin. Otherwise Jev arbitrates.
const MIN_SCORE = 4;
const TIE_MARGIN = 3;

// ── Snapshot ────────────────────────────────────────────────────────────────

function safeReaddir(dir, limit) {
  try {
    return fs.readdirSync(dir, { withFileTypes: true }).slice(0, limit);
  } catch {
    return [];
  }
}

function safeRead(file) {
  try {
    const fd = fs.openSync(file, "r");
    try {
      const buf = Buffer.alloc(MAX_FILE_BYTES);
      const read = fs.readSync(fd, buf, 0, MAX_FILE_BYTES, 0);
      return buf.slice(0, read).toString("utf8");
    } finally {
      fs.closeSync(fd);
    }
  } catch {
    return "";
  }
}

function parseNodeDeps(text) {
  try {
    const pkg = JSON.parse(text);
    return Object.keys(
      Object.assign(
        {},
        pkg.dependencies,
        pkg.devDependencies,
        pkg.peerDependencies,
      ),
    );
  } catch {
    return [];
  }
}

// Python dependency names out of pyproject.toml / requirements.txt without a
// TOML parser: take the leading identifier of each line or quoted entry and
// drop the version specifier. Crude, bounded, and good enough for markers.
function parsePyDeps(text) {
  const names = [];
  const lines = String(text).split(/\r?\n/).slice(0, 400);
  for (const raw of lines) {
    const line = raw.trim().replace(/^["']|["'],?$/g, "");
    if (!line || line.startsWith("#") || line.startsWith("[")) continue;
    const m = /^([A-Za-z][A-Za-z0-9._-]*)\s*(?:[<>=!~[;].*)?$/.exec(line);
    if (m) names.push(m[1].toLowerCase());
  }
  return names;
}

/**
 * A bounded snapshot of `cwd`. Synchronous, never throws, does no network I/O.
 *
 * Two sources, merged:
 *   - the skill gate's `gatherSignals`, for dependencies, top-level
 *     directories, file types and the project blurb — the expensive half, and
 *     already written once;
 *   - a shallow local readdir, for the file *names* the gate's shape drops.
 *
 * opts.gate injects or disables the gate (`false` to skip it, an object to
 * substitute one). Tests use it; callers should not need to.
 *
 * Returns { version, cwd, dirs, files, exts, deps, gateText, empty, ok } where
 * `dirs` and `files` are lowercase name sets, `exts` counts file extensions,
 * and `gateText` is the gate's own state string when it was available. That
 * string stays local: it carries branch names, README text and commit
 * subjects, so digest() does not forward it to any decision layer.
 */
function gather(cwd, opts) {
  const options = opts && typeof opts === "object" ? opts : {};
  const root = cwd || process.cwd();
  const dirs = new Set();
  const files = new Set();
  const exts = Object.create(null);
  let deps = [];

  const note = (entry) => {
    const name = entry.name;
    if (entry.isDirectory()) {
      if (IGNORED_DIRS.has(name)) return false;
      dirs.add(name.toLowerCase());
      return true;
    }
    files.add(name.toLowerCase());
    const ext = path.extname(name).toLowerCase();
    if (ext) exts[ext] = (exts[ext] || 0) + 1;
    return false;
  };

  const rootEntries = safeReaddir(root, MAX_ROOT_ENTRIES);
  for (const entry of rootEntries) note(entry);

  for (const probe of PROBE_DIRS) {
    if (!dirs.has(probe)) continue;
    for (const entry of safeReaddir(
      path.join(root, probe),
      MAX_SUBDIR_ENTRIES,
    )) {
      note(entry);
    }
  }

  if (files.has("package.json")) {
    deps = deps.concat(
      parseNodeDeps(safeRead(path.join(root, "package.json"))),
    );
  }
  for (const pyFile of ["pyproject.toml", "requirements.txt"]) {
    if (files.has(pyFile)) {
      deps = deps.concat(parsePyDeps(safeRead(path.join(root, pyFile))));
    }
  }

  // Fold in the skill gate's view. It sees deeper (depth 3) and wider (five
  // manifest grammars, git history, README) than the walk above, and its
  // `text` is the exact state string the gate hands the decision layer.
  let gateText = "";
  let empty = null;
  const gate =
    options.gate === false
      ? null
      : options.gate && typeof options.gate === "object"
        ? options.gate
        : loadGate();
  if (gate && typeof gate.gatherSignals === "function") {
    try {
      const gs = gate.gatherSignals(root);
      const parts = (gs && gs.parts) || {};
      for (const dep of parts.dependencies || []) deps.push(dep);
      for (const dir of parts.directories || [])
        dirs.add(String(dir).toLowerCase());
      for (const ext of parts.extensions || []) {
        const key = "." + String(ext).toLowerCase();
        exts[key] = exts[key] || 1;
      }
      empty = typeof gs.empty === "boolean" ? gs.empty : null;
      // The gate's state string always names the directory, so an empty
      // directory still produces prose. When the gate itself says the project
      // tells us nothing, that prose is noise — drop it.
      gateText =
        empty === true ? "" : typeof gs.text === "string" ? gs.text : "";
    } catch {
      // The gate is an enrichment. A gate that throws costs us nothing.
    }
  }

  return {
    version: SIGNAL_VERSION,
    cwd: root,
    dirs: dirs,
    files: files,
    exts: exts,
    deps: new Set(deps.map((d) => String(d).toLowerCase())),
    gateText: gateText,
    empty: empty === null ? rootEntries.length === 0 : empty,
    ok: rootEntries.length > 0,
  };
}

// Hard ceiling on the state string. It is also a privacy ceiling, not only a
// cost one: whatever this returns is what leaves the machine when the hosted
// decision layer is explicitly enabled.
const MAX_DIGEST_CHARS = 600;

/**
 * The snapshot as prose, for use as a lib/jev `state`. Bounded to a few
 * hundred characters: Jev is billed per input token and a file listing is not
 * where the signal lives.
 *
 * Structural facts only — directory names, file names, dependency names and
 * file extensions. `signals.gateText` is deliberately NOT forwarded: the
 * gate's state string also carries the branch name, a README excerpt and
 * recent commit subjects, which are the repository's content rather than its
 * shape and have no business in a roster decision.
 */
function digest(signals) {
  if (!signals) return "an empty repository";
  const top = (obj, n) =>
    Object.keys(obj)
      .sort((a, b) => obj[b] - obj[a])
      .slice(0, n);
  const parts = [];
  const dirs = Array.from(signals.dirs || []).slice(0, 18);
  const files = Array.from(signals.files || []).slice(0, 24);
  const deps = Array.from(signals.deps || []).slice(0, 24);
  if (dirs.length) parts.push("Directories: " + dirs.join(", ") + ".");
  if (files.length) parts.push("Files: " + files.join(", ") + ".");
  if (deps.length) parts.push("Dependencies: " + deps.join(", ") + ".");
  const exts = top(signals.exts || {}, 8);
  if (exts.length) parts.push("Common file types: " + exts.join(", ") + ".");
  const prose = parts.join(" ");
  return prose ? prose.slice(0, MAX_DIGEST_CHARS) : "an empty repository";
}

// ── Deterministic scoring ───────────────────────────────────────────────────

function markerHit(marker, signals) {
  if (marker.dep) {
    for (const d of marker.dep) if (signals.deps.has(d.toLowerCase())) return d;
  }
  if (marker.file) {
    for (const f of marker.file)
      if (signals.files.has(f.toLowerCase())) return f;
  }
  if (marker.dir) {
    for (const d of marker.dir)
      if (signals.dirs.has(d.toLowerCase())) return d + "/";
  }
  if (marker.ext) {
    for (const e of marker.ext)
      if (signals.exts[e.toLowerCase()]) return "*" + e;
  }
  return null;
}

/**
 * Score every roster against a snapshot. Pure: no I/O, no network, no clock.
 * Returns the full catalog sorted by descending score, each entry carrying the
 * evidence that produced it so a caller can show its reasoning.
 */
function scoreRosters(signals) {
  const snapshot =
    signals && signals.dirs
      ? signals
      : { dirs: new Set(), files: new Set(), exts: {}, deps: new Set() };

  return ROSTERS.map((roster) => {
    let score = 0;
    const evidence = [];
    for (const marker of roster.markers) {
      const hit = markerHit(marker, snapshot);
      if (hit) {
        score += marker.w;
        evidence.push(hit);
      }
    }
    return { roster: roster, score: score, evidence: evidence };
  }).sort(
    (a, b) =>
      b.score - a.score ||
      ROSTERS.indexOf(a.roster) - ROSTERS.indexOf(b.roster),
  );
}

/** The agent list a roster installs, with Apex always included, no duplicates. */
function agentsFor(roster) {
  const list = [ALWAYS].concat(roster.agents || []);
  return list.filter((a, i) => list.indexOf(a) === i);
}

/**
 * `claude plugin install` one-liners for a roster.
 *
 * Index 0 installs exactly the recommended agents and nothing else — it is the
 * command a caller should show. Anything after it is a wider bundle in the
 * same domain, a superset offered for callers who want the whole discipline.
 * Callers must not present a bundle as if it were the roster.
 */
function installCommands(roster) {
  const exact =
    "claude plugin install " +
    agentsFor(roster)
      .map((a) => a + "@tonone-ai")
      .join(" ");
  return [exact].concat(
    (roster.bundles || []).map(
      (b) => "claude plugin install " + b + "@tonone-ai",
    ),
  );
}

// ── Recommendation ──────────────────────────────────────────────────────────

// Opt-in for the hosted decision layer. lib/jev picks up any generic
// OPENROUTER_API_KEY / JEV_API_KEY / TYPESAFE_API_KEY that happens to be in
// the environment, but a key the user set for some other tool is not consent
// for tonone's first-run onboarding to post a description of their repository
// to a third-party API. Nothing here reaches the network unless one of these
// tonone-specific variables is set to a truthy value.
const JEV_OPT_IN_VARS = ["TONONE_JEV", "TONONE_JEV_ROSTER"];

function truthyEnv(value) {
  if (!value) return false;
  const v = String(value).trim().toLowerCase();
  return v !== "" && v !== "0" && v !== "false" && v !== "no";
}

/** True only when tonone has been explicitly allowed to make the call. */
function jevOptIn(env) {
  try {
    const e = env || process.env;
    return JEV_OPT_IN_VARS.some((name) => truthyEnv(e[name]));
  } catch {
    return false;
  }
}

/**
 * Recommend one roster for `cwd`.
 *
 * The deterministic scorer decides whenever it can. lib/jev is consulted only
 * when the top two are within TIE_MARGIN of each other, and even then its
 * answer is accepted only if it names one of the candidates the scorer already
 * shortlisted — a decision model may arbitrate, it may not invent.
 *
 * opts: { jev, timeoutMs, env, signals }. `jev` injects the decision layer
 * (tests); omit it and lib/jev/client is loaded lazily, and if that require
 * fails the deterministic answer stands.
 *
 * Resolves to:
 *   { roster, alternate, score, evidence, source, confidence, signals }
 * where source is "signals" | "jev" | "local" | "fallback" | "default".
 */
async function recommend(cwd, opts) {
  const options = opts && typeof opts === "object" ? opts : {};
  const signals = options.signals || gather(cwd, { gate: options.gate });
  const ranked = scoreRosters(signals);
  const top = ranked[0];
  const second = ranked[1];

  const base = {
    signals: signals,
    ranked: ranked,
    alternate: second && second.score > 0 ? second.roster : null,
  };

  if (!top || top.score < MIN_SCORE) {
    return Object.assign({}, base, {
      roster: DEFAULT_ROSTER,
      score: top ? top.score : 0,
      evidence: [],
      source: "default",
      confidence: 0,
      alternate: null,
    });
  }

  const decided = Object.assign({}, base, {
    roster: top.roster,
    score: top.score,
    evidence: top.evidence,
    source: "signals",
    confidence: 1,
  });

  const contested =
    second && top.score - second.score < TIE_MARGIN && second.score > 0;
  if (!contested) return decided;

  // Near-tie: let the decision layer read the shape rather than the score.
  const candidates = ranked
    .filter((r) => top.score - r.score < TIE_MARGIN)
    .slice(0, 3);
  let jev = options.jev;
  if (!jev) {
    try {
      jev = require("../jev/client");
    } catch {
      return decided;
    }
  }

  // Without a tonone-specific opt-in the decision layer is forced offline: it
  // still arbitrates, using lib/jev's local lexical scorer, and performs zero
  // network I/O. Forwarding only the offline flag — rather than the caller's
  // environment — also keeps any unrelated API key out of lib/jev's reach.
  const jevEnv = jevOptIn(options.env)
    ? options.env || process.env
    : { TONONE_JEV_OFFLINE: "1" };

  let result;
  try {
    const optionMap = Object.create(null);
    for (const c of candidates) optionMap[c.roster.id] = c.roster.desc;
    result = await jev.choice(
      digest(signals),
      "Which kind of project is this repository, judged by what its files and dependencies are for?",
      optionMap,
      {
        timeoutMs: options.timeoutMs || 2500,
        retries: 0,
        env: jevEnv,
        sessionId: options.sessionId,
      },
    );
  } catch {
    // lib/jev promises never to reject; this is belt and braces.
    return decided;
  }

  const picked = candidates.find(
    (c) => result && c.roster.id === result.answer,
  );
  if (!picked || !result.answer) return decided;

  // A local answer is lexical overlap, not judgement. Accept it only when it
  // is genuinely decided; otherwise keep the deterministic winner.
  const trusted = result.source === "jev" || result.confidence >= 0.5;
  if (!trusted) return decided;

  return Object.assign({}, base, {
    roster: picked.roster,
    score: picked.score,
    evidence: picked.evidence,
    source: result.source,
    confidence: result.confidence,
    alternate: top.roster.id === picked.roster.id ? base.alternate : top.roster,
  });
}

/**
 * The recommendation as a handful of short lines for a CLI banner.
 * Deliberately capped: an onboarding message that scrolls is one nobody reads.
 */
function render(rec) {
  if (!rec || !rec.roster) return [];
  const roster = rec.roster;
  const lines = [
    "Detected: " + roster.label + " — suggested roster:",
    "  " + agentsFor(roster).join(", "),
  ];
  if (rec.evidence && rec.evidence.length) {
    lines.push("  from " + rec.evidence.slice(0, 3).join(", "));
  }
  // Deliberately no install command. The exact one runs past 90 characters,
  // and the banner's rows are 56 — a clipped command is a command that fails
  // when pasted. /tonone-onboard prints it in full, where there is room.
  return lines;
}

module.exports = {
  SIGNAL_VERSION: SIGNAL_VERSION,
  ROSTERS: ROSTERS,
  DEFAULT_ROSTER: DEFAULT_ROSTER,
  MIN_SCORE: MIN_SCORE,
  TIE_MARGIN: TIE_MARGIN,
  PROBE_DIRS: PROBE_DIRS,
  MAX_DIGEST_CHARS: MAX_DIGEST_CHARS,
  JEV_OPT_IN_VARS: JEV_OPT_IN_VARS,
  jevOptIn: jevOptIn,
  gather: gather,
  digest: digest,
  scoreRosters: scoreRosters,
  agentsFor: agentsFor,
  installCommands: installCommands,
  recommend: recommend,
  render: render,
};

// ── CLI ─────────────────────────────────────────────────────────────────────
//
// For prose skills that need the recommendation from a Bash step. One JSON
// object on stdout, exit code 0 always — a failure is reported as
// {"ok": false, ...} with the default roster, never as a non-zero exit.
//
//   node lib/signals/project-shape.js [--json] [--cwd DIR] [--pretty]

if (require.main === module) {
  const argv = process.argv.slice(2);
  const flag = (name) => {
    const i = argv.indexOf(name);
    return i >= 0 && i + 1 < argv.length ? argv[i + 1] : null;
  };
  const target = flag("--cwd") || process.cwd();
  const pretty = argv.indexOf("--pretty") >= 0;

  const emit = (obj) => {
    process.stdout.write(JSON.stringify(obj, null, pretty ? 2 : 0) + "\n");
    process.exitCode = 0;
  };

  Promise.resolve()
    .then(() => recommend(target, { timeoutMs: 3000 }))
    .then((rec) => {
      emit({
        ok: true,
        cwd: target,
        roster: rec.roster.id,
        label: rec.roster.label,
        why: rec.roster.why,
        agents: agentsFor(rec.roster),
        bundles: rec.roster.bundles,
        commands: installCommands(rec.roster),
        evidence: rec.evidence,
        source: rec.source,
        confidence: rec.confidence,
        alternate: rec.alternate ? rec.alternate.id : null,
        lines: render(rec),
      });
    })
    .catch((err) => {
      emit({
        ok: false,
        error: String((err && err.message) || err),
        roster: DEFAULT_ROSTER.id,
        label: DEFAULT_ROSTER.label,
        agents: agentsFor(DEFAULT_ROSTER),
        bundles: DEFAULT_ROSTER.bundles,
        commands: installCommands(DEFAULT_ROSTER),
        evidence: [],
        source: "default",
        confidence: 0,
        alternate: null,
        lines: render({ roster: DEFAULT_ROSTER, evidence: [] }),
      });
    });
}
