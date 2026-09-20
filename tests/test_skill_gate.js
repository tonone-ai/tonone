"use strict";

/**
 * Tests for the skill-manifest gate (hooks/tonone-skill-gate.js).
 *
 *   node --test tests/test_skill_gate.js
 *
 * Node's built-in test runner, matching tests/test_jev.js. No dependencies, no
 * credentials, no network: the decision layer runs on its local scorer, and the
 * tests that need a specific ranking inject a fake one.
 *
 * Every test runs against a temporary project directory and a temporary cache,
 * so the suite never reads or writes the developer's own settings.
 */

const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const ROOT = path.join(__dirname, "..");
const HOOK = path.join(ROOT, "hooks", "tonone-skill-gate.js");
const REAL_INDEX = path.join(ROOT, "docs", "skill-index.json");

const gate = require(HOOK);

// ── Helpers ─────────────────────────────────────────────────────────────────

function tmpdir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), "tonone-gate-" + prefix + "-"));
}

/** A project with enough shape that gatherSignals() does not call it empty. */
function makeProject(kind) {
  const dir = tmpdir(kind || "proj");
  if (kind === "frontend") {
    fs.mkdirSync(path.join(dir, "src", "components"), { recursive: true });
    fs.writeFileSync(
      path.join(dir, "package.json"),
      JSON.stringify({
        name: "storefront-ui",
        description:
          "React storefront: components, design tokens, typography and accessible checkout.",
        dependencies: {
          react: "^18.0.0",
          tailwindcss: "^3.4.0",
          "framer-motion": "^11.0.0",
        },
        devDependencies: {
          vite: "^5.0.0",
          typescript: "^5.0.0",
          storybook: "^7.6.0",
        },
      }),
    );
    fs.writeFileSync(
      path.join(dir, "src", "components", "Button.tsx"),
      "export const Button = () => null;\n",
    );
    fs.writeFileSync(path.join(dir, "src", "styles.css"), ":root{--bg:#fff}\n");
  } else {
    fs.mkdirSync(path.join(dir, "modules"), { recursive: true });
    fs.writeFileSync(
      path.join(dir, "package.json"),
      JSON.stringify({
        name: "svc",
        description: "HTTP API service",
        dependencies: { express: "^4.0.0" },
      }),
    );
    fs.writeFileSync(path.join(dir, "index.js"), "require('express')();\n");
  }
  return dir;
}

/** Run the hook as the hook runner would, with an isolated cache and state. */
function runGate(args, options) {
  const opts = options || {};
  const env = Object.assign({}, process.env, {
    TONONE_JEV_CACHE_DIR: opts.cacheDir || tmpdir("cache"),
    TONONE_GATE_STATE_DIR: opts.stateDir || tmpdir("state"),
    TONONE_JEV_OFFLINE: "1",
  });
  if (opts.index !== undefined) env.TONONE_GATE_INDEX = opts.index;
  if (opts.ttlMs !== undefined) env.TONONE_GATE_TTL_MS = String(opts.ttlMs);
  if (opts.gate !== undefined) env.TONONE_GATE = opts.gate;
  for (const key of opts.unset || []) delete env[key];

  // The child always runs in a throwaway directory. Without --cwd and without
  // parseable hook input the gate falls back to its own working directory, and
  // that must never be the checkout this suite is running from.
  const result = spawnSync(process.execPath, [HOOK].concat(args), {
    encoding: "utf8",
    env: env,
    cwd: opts.cwd || tmpdir("cwd"),
    input: opts.input === undefined ? "" : opts.input,
    timeout: 30000,
  });
  return {
    status: result.status,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
    json() {
      try {
        return JSON.parse(this.stdout);
      } catch {
        return null;
      }
    },
  };
}

function settingsFile(dir) {
  return path.join(dir, ".claude", "settings.local.json");
}

function readSettings(dir) {
  try {
    return JSON.parse(fs.readFileSync(settingsFile(dir), "utf8"));
  } catch {
    return null;
  }
}

/** A small stand-in catalogue: two teams, enough rows to rank. */
function fakeIndex() {
  const rows = [];
  const teams = {
    Engineering: ["spine", "flux", "proof"],
    Design: ["hue", "grid", "axe"],
  };
  for (const team of Object.keys(teams)) {
    for (const agent of teams[team]) {
      for (const action of ["recon", "audit", "design"]) {
        rows.push({
          name: agent + "-" + action,
          agent: agent,
          team: team,
          description:
            team + " work: " + agent + " " + action + " of the project.",
        });
      }
    }
  }
  rows.push({
    name: "apex-plan",
    agent: "apex",
    team: "Engineering",
    description: "Plan and scope.",
  });
  rows.push({
    name: "atlas-report",
    agent: "atlas",
    team: "Engineering",
    description: "Render a report.",
  });
  return rows;
}

/**
 * A decision layer that always ranks by a fixed preference. Same call shape as
 * lib/jev/client.js batch(), same result shape.
 */
function fakeJev(preferred) {
  return {
    async batch(state, questions) {
      const answers = Object.create(null);
      for (const key of Object.keys(questions)) {
        const spec = questions[key];
        if (spec.type === "score") {
          answers[key] = {
            type: "score",
            answer: 0,
            confidence: 0.6,
            probabilities: {},
            legend: {},
            source: "local",
          };
          continue;
        }
        const keys = Object.keys(spec.options || {});
        const probabilities = Object.create(null);
        keys.forEach((k, i) => {
          probabilities[k] =
            k === preferred || String(k).indexOf(preferred) === 0
              ? 1
              : 0.1 / (i + 1);
        });
        answers[key] = {
          type: "choice",
          answer: keys[0] || null,
          confidence: 0.7,
          probabilities: probabilities,
          source: "local",
        };
      }
      return {
        answers,
        source: "local",
        provider: null,
        cached: false,
        usage: null,
        model: null,
        error: null,
      };
    },
  };
}

// ── The never-writes-off invariant ──────────────────────────────────────────

test("sanitizeState can never produce off", () => {
  const hostile = [
    "off",
    "OFF",
    " off ",
    "disabled",
    "",
    null,
    undefined,
    0,
    {},
    ["off"],
    "on\noff",
  ];
  for (const value of hostile) {
    const state = gate.sanitizeState(value);
    assert.notStrictEqual(state, "off");
    assert.ok(
      gate.VALID_STATES.indexOf(state) !== -1,
      "unexpected state: " + state,
    );
  }
  assert.strictEqual(
    gate.VALID_STATES.indexOf("off"),
    -1,
    "off must not be a valid state",
  );
});

test("applySettings writes no off, even when handed one", () => {
  const dir = tmpdir("off");
  process.env.TONONE_GATE_STATE_DIR = path.join(dir, "state");
  const applied = gate.applySettings(dir, {
    "a-one": "off",
    "a-two": "user-invocable-only",
    "a-three": "name-only",
    "a-four": "on",
  });
  assert.strictEqual(applied.ok, true);
  const settings = readSettings(dir);
  const values = Object.values(settings.skillOverrides);
  assert.ok(values.indexOf("off") === -1, "off reached the settings file");
  for (const value of values)
    assert.ok(gate.VALID_STATES.indexOf(value) !== -1);
  assert.strictEqual(settings.skillOverrides["a-two"], "user-invocable-only");
  // `on` is the default, so it is not written at all.
  assert.ok(!("a-four" in settings.skillOverrides));
  delete process.env.TONONE_GATE_STATE_DIR;
});

test("a full decision never assigns off to any skill", async () => {
  const index = fakeIndex();
  const signals = {
    text: "A design system: color tokens, typography, spacing.",
    parts: { branch: "main" },
    empty: false,
  };
  const decision = await gate.decide(index, signals, { jev: fakeJev("hue") });
  assert.strictEqual(decision.degraded, false);
  const values = Object.values(decision.states);
  assert.ok(values.length > 0);
  for (const value of values) {
    assert.notStrictEqual(value, "off");
    assert.ok(gate.VALID_STATES.indexOf(value) !== -1);
  }
});

// ── Missing skill index ─────────────────────────────────────────────────────

test("readSkillIndex returns [] for a missing or malformed index", () => {
  const dir = tmpdir("index");
  assert.deepStrictEqual(gate.readSkillIndex(path.join(dir, "nope.json")), []);
  const bad = path.join(dir, "bad.json");
  fs.writeFileSync(bad, "{ not json");
  assert.deepStrictEqual(gate.readSkillIndex(bad), []);
  const wrongShape = path.join(dir, "obj.json");
  fs.writeFileSync(wrongShape, JSON.stringify({ skills: [] }));
  assert.deepStrictEqual(gate.readSkillIndex(wrongShape), []);
  const partial = path.join(dir, "partial.json");
  fs.writeFileSync(
    partial,
    JSON.stringify([{ name: "ok-one" }, { agent: "x" }, null, 7]),
  );
  assert.deepStrictEqual(gate.readSkillIndex(partial), [
    { name: "ok-one", agent: "", team: "", description: "" },
  ]);
});

test("a missing skill index leaves the session untouched", () => {
  const dir = makeProject("backend");
  const missing = path.join(dir, "no-such-index.json");
  const result = runGate(["--cwd", dir], { index: missing });
  assert.strictEqual(result.status, 0);
  assert.strictEqual(
    readSettings(dir),
    null,
    "settings were written with no index",
  );

  const dry = runGate(["--cwd", dir, "--dry-run"], { index: missing });
  assert.strictEqual(dry.status, 0);
  assert.match(dry.stdout, /no skill index/);
});

// ── Unwritable settings ─────────────────────────────────────────────────────

test("an unwritable settings location is reported, not thrown", () => {
  const dir = tmpdir("unwritable");
  // .claude is a regular file, so the directory can never be created.
  fs.writeFileSync(path.join(dir, ".claude"), "not a directory\n");
  process.env.TONONE_GATE_STATE_DIR = path.join(dir, "state");
  const applied = gate.applySettings(dir, { "a-one": "name-only" });
  assert.strictEqual(applied.ok, false);
  assert.strictEqual(applied.written, 0);
  assert.ok(typeof applied.reason === "string" && applied.reason.length > 0);
  delete process.env.TONONE_GATE_STATE_DIR;
});

test("a settings file that is not an object is left alone", () => {
  const dir = tmpdir("array");
  fs.mkdirSync(path.join(dir, ".claude"));
  fs.writeFileSync(settingsFile(dir), JSON.stringify(["surprise"]));
  process.env.TONONE_GATE_STATE_DIR = path.join(dir, "state");
  const applied = gate.applySettings(dir, { "a-one": "name-only" });
  assert.strictEqual(applied.ok, false);
  assert.deepStrictEqual(readSettings(dir), ["surprise"]);
  delete process.env.TONONE_GATE_STATE_DIR;
});

test("the hook exits 0 when the settings file cannot be written", () => {
  const dir = makeProject("frontend");
  fs.writeFileSync(path.join(dir, ".claude"), "not a directory\n");
  const result = runGate(["--cwd", dir, "--json"]);
  assert.strictEqual(result.status, 0);
  const payload = result.json();
  assert.ok(payload, "expected JSON on stdout");
  if (payload.applied) assert.strictEqual(payload.applied.ok, false);
});

// ── Empty project ───────────────────────────────────────────────────────────

test("an empty directory yields no signals and no decision", async () => {
  const dir = tmpdir("empty");
  const signals = gate.gatherSignals(dir);
  assert.strictEqual(signals.empty, true);
  const decision = await gate.decide(fakeIndex(), signals, {
    jev: fakeJev("hue"),
  });
  assert.strictEqual(decision.degraded, true);
  assert.deepStrictEqual(Object.keys(decision.states), []);
});

test("the hook writes nothing for an empty project", () => {
  const dir = tmpdir("empty-cli");
  const result = runGate(["--cwd", dir, "--json"]);
  assert.strictEqual(result.status, 0);
  const payload = result.json();
  assert.ok(payload);
  assert.strictEqual(payload.degraded, true);
  assert.strictEqual(readSettings(dir), null);
});

test("a decision layer that is absent degrades to doing nothing", async () => {
  const signals = {
    text: "a project",
    parts: { branch: "main" },
    empty: false,
  };
  const decision = await gate.decide(fakeIndex(), signals, { jev: {} });
  assert.strictEqual(decision.degraded, true);
  assert.deepStrictEqual(decision.teams.dropped, []);
});

// ── Cache ───────────────────────────────────────────────────────────────────

test("the decision is cached and expires", () => {
  const dir = makeProject("frontend");
  const cacheDir = tmpdir("cache-shared");
  const stateDir = tmpdir("state-shared");

  const first = runGate(["--cwd", dir, "--dry-run", "--json"], {
    cacheDir,
    stateDir,
  });
  assert.strictEqual(first.json().cached, false);

  const second = runGate(["--cwd", dir, "--dry-run", "--json"], {
    cacheDir,
    stateDir,
  });
  assert.strictEqual(
    second.json().cached,
    true,
    "second run should hit the cache",
  );
  assert.deepStrictEqual(second.json().accounting, first.json().accounting);

  // A TTL of 1 ms expires the entry that was just written.
  const expired = runGate(["--cwd", dir, "--dry-run", "--json"], {
    cacheDir,
    stateDir,
    ttlMs: 1,
  });
  assert.strictEqual(
    expired.json().cached,
    false,
    "an expired entry must not be served",
  );

  // --force ignores a live entry.
  const forced = runGate(["--cwd", dir, "--dry-run", "--json", "--force"], {
    cacheDir,
    stateDir,
  });
  assert.strictEqual(forced.json().cached, false);
});

test("a change to the scoring invalidates cached decisions", () => {
  const dir = makeProject("frontend");
  const cacheDir = tmpdir("cache-algo");
  const stateDir = tmpdir("state-algo");
  assert.match(gate.algoFingerprint(), /^[0-9a-f]{16}$/);

  const first = runGate(["--cwd", dir, "--dry-run", "--json"], {
    cacheDir,
    stateDir,
  });
  assert.strictEqual(first.json().cached, false);
  assert.strictEqual(
    runGate(["--cwd", dir, "--dry-run", "--json"], {
      cacheDir,
      stateDir,
    }).json().cached,
    true,
  );

  // A copy of the hook with one changed line is a different algorithm, so it
  // must not be served the previous version's decision.
  const variant = path.join(tmpdir("variant"), "tonone-skill-gate.js");
  fs.mkdirSync(path.join(path.dirname(variant), "..", "lib"), {
    recursive: true,
  });
  const source = fs.readFileSync(
    path.join(ROOT, "hooks", "tonone-skill-gate.js"),
    "utf8",
  );
  assert.ok(source.indexOf("const MIN_TEAMS = 3;") !== -1);
  fs.writeFileSync(
    variant,
    source.replace("const MIN_TEAMS = 3;", "const MIN_TEAMS = 4;"),
  );

  const env = Object.assign({}, process.env, {
    TONONE_JEV_CACHE_DIR: cacheDir,
    TONONE_GATE_STATE_DIR: stateDir,
    TONONE_JEV_OFFLINE: "1",
    CLAUDE_PLUGIN_ROOT: ROOT, // the variant lives elsewhere; read the real index and lib
  });
  const result = spawnSync(
    process.execPath,
    [variant, "--cwd", dir, "--dry-run", "--json"],
    {
      encoding: "utf8",
      env: env,
      cwd: tmpdir("cwd"),
      input: "",
      timeout: 30000,
    },
  );
  assert.strictEqual(result.status, 0);
  const payload = JSON.parse(result.stdout);
  assert.strictEqual(
    payload.cached,
    false,
    "a changed algorithm reused an old decision",
  );
});

test("a different project does not reuse another project's decision", () => {
  const cacheDir = tmpdir("cache-two");
  const stateDir = tmpdir("state-two");
  const frontend = makeProject("frontend");
  const backend = makeProject("backend");
  runGate(["--cwd", frontend, "--dry-run", "--json"], { cacheDir, stateDir });
  const other = runGate(["--cwd", backend, "--dry-run", "--json"], {
    cacheDir,
    stateDir,
  });
  assert.strictEqual(other.json().cached, false);
});

// ── Merging ─────────────────────────────────────────────────────────────────

test("applySettings merges and never clobbers", () => {
  const dir = tmpdir("merge");
  const stateDir = path.join(dir, "state");
  process.env.TONONE_GATE_STATE_DIR = stateDir;
  fs.mkdirSync(path.join(dir, ".claude"));
  fs.writeFileSync(
    settingsFile(dir),
    JSON.stringify({
      permissions: { allow: ["Bash(npm test)"] },
      env: { FOO: "bar" },
      skillOverrides: { "hand-written": "name-only" },
    }),
  );

  const first = gate.applySettings(dir, {
    "a-one": "user-invocable-only",
    "a-two": "name-only",
  });
  assert.strictEqual(first.ok, true);
  let settings = readSettings(dir);
  assert.deepStrictEqual(settings.permissions, { allow: ["Bash(npm test)"] });
  assert.deepStrictEqual(settings.env, { FOO: "bar" });
  assert.strictEqual(settings.skillOverrides["hand-written"], "name-only");
  assert.strictEqual(settings.skillOverrides["a-one"], "user-invocable-only");

  // A later, smaller decision retracts what the hook wrote before and only that.
  const second = gate.applySettings(dir, { "a-one": "name-only" });
  assert.strictEqual(second.ok, true);
  settings = readSettings(dir);
  assert.strictEqual(settings.skillOverrides["hand-written"], "name-only");
  assert.strictEqual(settings.skillOverrides["a-one"], "name-only");
  assert.ok(!("a-two" in settings.skillOverrides), "stale override survived");

  // Editing an override by hand is how a person overrules the gate, so the
  // edited value survives the next run and the hook stops managing that skill.
  settings.skillOverrides["a-one"] = "on";
  fs.writeFileSync(settingsFile(dir), JSON.stringify(settings));
  gate.applySettings(dir, { "a-one": "user-invocable-only" });
  assert.strictEqual(readSettings(dir).skillOverrides["a-one"], "on");
  gate.applySettings(dir, { "a-one": "name-only" });
  assert.strictEqual(readSettings(dir).skillOverrides["a-one"], "on");

  // --reset removes exactly what the hook owns and nothing else: neither the
  // hand-written entry nor the entry the user took over above.
  gate.applySettings(dir, {
    "a-one": "name-only",
    "a-five": "user-invocable-only",
  });
  const reset = gate.resetSettings(dir);
  assert.strictEqual(reset.removed, 1);
  assert.deepStrictEqual(readSettings(dir).skillOverrides, {
    "hand-written": "name-only",
    "a-one": "on",
  });
  delete process.env.TONONE_GATE_STATE_DIR;
});

// ── Decision shape ──────────────────────────────────────────────────────────

test("dropped teams lose descriptions, kept teams keep some", async () => {
  const index = fakeIndex();
  const signals = {
    text: "Color tokens, typography, spacing, contrast.",
    parts: { branch: "main" },
    empty: false,
  };
  const decision = await gate.decide(index, signals, { jev: fakeJev("hue") });

  // Engineering is pinned, so with two teams nothing is dropped here; the
  // per-skill cut still has to happen.
  const engineering = index.filter((r) => r.team === "Engineering");
  assert.ok(
    engineering.some((r) => decision.states[r.name] === "on"),
    "a kept team must keep at least one description",
  );
  assert.ok(
    index.some((r) => decision.states[r.name] === "name-only"),
    "the per-skill cut produced nothing",
  );
});

test("apex, helm and atlas-report are always on", async () => {
  assert.strictEqual(gate.isAlwaysOn("apex-plan"), true);
  assert.strictEqual(gate.isAlwaysOn("helm-brief"), true);
  assert.strictEqual(gate.isAlwaysOn("atlas-report"), true);
  assert.strictEqual(gate.isAlwaysOn("warden-scan"), false);

  const index = gate.readSkillIndex(REAL_INDEX);
  if (!index.length) return; // a checkout without the index has nothing to assert
  const signals = gate.gatherSignals(makeProject("frontend"));
  const decision = await gate.decide(index, signals, {});
  if (decision.degraded) return;
  for (const row of index) {
    if (gate.isAlwaysOn(row.name)) {
      assert.strictEqual(
        decision.states[row.name],
        "on",
        row.name + " must stay on",
      );
    }
  }
});

test("the branch name forces its own domain to survive", () => {
  assert.deepStrictEqual(
    gate.branchForcedTeams("feat/ui-token-refresh").sort(),
    ["Design", "Engineering"],
  );
  assert.deepStrictEqual(gate.branchForcedTeams("chore/gdpr-dpa"), ["Legal"]);
  assert.deepStrictEqual(gate.branchForcedTeams("main"), []);
  const index = fakeIndex();
  assert.deepStrictEqual(gate.branchForcedAgents("fix/hue-contrast", index), [
    "hue",
  ]);
  assert.deepStrictEqual(gate.branchForcedAgents("main", index), []);
});

test("a branch-named agent keeps its skills on even in a dropped team", async () => {
  const index = fakeIndex();
  const signals = {
    text: "An HTTP service: routes, handlers, database migrations.",
    parts: { branch: "fix/hue-contrast" },
    empty: false,
  };
  const decision = await gate.decide(index, signals, { jev: fakeJev("spine") });
  for (const row of index.filter((r) => r.agent === "hue")) {
    assert.strictEqual(
      decision.states[row.name],
      "on",
      row.name + " was named by the branch",
    );
  }
});

// ── Accounting ──────────────────────────────────────────────────────────────

test("accounting adds up and never claims a negative saving", () => {
  const index = gate.readSkillIndex(REAL_INDEX);
  assert.ok(
    index.length > 0,
    "the repository's own skill index should be readable",
  );

  const none = gate.accounting(index, {});
  assert.strictEqual(none.before.tokens, none.after.tokens);
  assert.strictEqual(none.saved.tokens, 0);
  assert.strictEqual(none.counts.on, index.length);

  const states = Object.create(null);
  index.forEach((row, i) => {
    states[row.name] =
      i % 3 === 0 ? "on" : i % 3 === 1 ? "name-only" : "user-invocable-only";
  });
  const some = gate.accounting(index, states);
  assert.strictEqual(
    some.counts.on +
      some.counts["name-only"] +
      some.counts["user-invocable-only"],
    index.length,
  );
  assert.ok(some.after.tokens < some.before.tokens);
  assert.ok(some.saved.pct > 0 && some.saved.pct <= 100);
  assert.strictEqual(gate.estimateTokens(0), 0);
});

// ── Process contract ────────────────────────────────────────────────────────

test("TONONE_GATE=off disables the hook", () => {
  const dir = makeProject("frontend");
  const result = runGate(["--cwd", dir], { gate: "off" });
  assert.strictEqual(result.status, 0);
  assert.strictEqual(readSettings(dir), null);

  const dry = runGate(["--cwd", dir, "--dry-run"], { gate: "off" });
  assert.match(dry.stdout, /off/);
});

test("--dry-run prints a before/after token count and writes nothing", () => {
  const dir = makeProject("frontend");
  const result = runGate(["--cwd", dir, "--dry-run"]);
  assert.strictEqual(result.status, 0);
  assert.match(result.stdout, /tokens of skill catalogue/);
  assert.ok(
    result.stdout.split("\n").length <= 40,
    "the report must fit the 40-line budget",
  );
  assert.strictEqual(
    readSettings(dir),
    null,
    "--dry-run wrote to the settings file",
  );
});

test("the hook accepts hook input on stdin and always exits 0", () => {
  const dir = makeProject("frontend");
  const good = runGate([], {
    input: JSON.stringify({
      hook_event_name: "SessionStart",
      cwd: dir,
      session_id: "test",
    }),
  });
  assert.strictEqual(good.status, 0);
  assert.strictEqual(good.stderr, "");
  const settings = readSettings(dir);
  assert.ok(
    settings && settings.skillOverrides,
    "the hook should have written overrides",
  );
  assert.ok(Object.values(settings.skillOverrides).indexOf("off") === -1);

  // No --cwd and no parseable input: the gate falls back to its own working
  // directory, which here is a throwaway one. It must still exit 0 and, because
  // that directory is empty, must decide nothing.
  const garbage = runGate([], { input: "not json at all" });
  assert.strictEqual(garbage.status, 0);

  const empty = runGate([], { input: "" });
  assert.strictEqual(empty.status, 0);

  const fallbackDir = tmpdir("fallback");
  const fallback = runGate(["--json"], { cwd: fallbackDir, input: "" });
  assert.strictEqual(fallback.status, 0);
  assert.strictEqual(readSettings(fallbackDir), null);
});

test("--help and --reset are safe on a project that was never gated", () => {
  const dir = tmpdir("never");
  const help = runGate(["--help"]);
  assert.strictEqual(help.status, 0);
  assert.match(help.stdout, /--dry-run/);

  const reset = runGate(["--cwd", dir, "--reset"]);
  assert.strictEqual(reset.status, 0);
  assert.match(reset.stdout, /0 override/);
});

// ── Regressions ─────────────────────────────────────────────────────────────

test("a settings file that cannot be parsed is never rewritten", () => {
  const dir = tmpdir("jsonc");
  fs.mkdirSync(path.join(dir, ".claude"));
  const original =
    "// local overrides\n" +
    JSON.stringify({
      permissions: { allow: ["Bash(npm test)"] },
      env: { FOO: "bar" },
    }) +
    "\n";
  fs.writeFileSync(settingsFile(dir), original);
  process.env.TONONE_GATE_STATE_DIR = path.join(dir, "state");

  const applied = gate.applySettings(dir, { "a-one": "name-only" });
  assert.strictEqual(applied.ok, false);
  assert.strictEqual(applied.written, 0);
  assert.match(applied.reason, /valid JSON/);
  assert.strictEqual(
    fs.readFileSync(settingsFile(dir), "utf8"),
    original,
    "an unparseable settings file was rewritten",
  );

  // Reset is held to the same rule, and keeps the provenance record so a later
  // run can still undo what it wrote.
  const reset = gate.resetSettings(dir);
  assert.strictEqual(reset.ok, false);
  assert.strictEqual(fs.readFileSync(settingsFile(dir), "utf8"), original);
  delete process.env.TONONE_GATE_STATE_DIR;
});

test("the hook says so when it leaves the settings file alone", () => {
  const dir = makeProject("frontend");
  fs.mkdirSync(path.join(dir, ".claude"));
  fs.writeFileSync(settingsFile(dir), "{ not json");
  const result = runGate(["--cwd", dir]);
  assert.strictEqual(result.status, 0);
  assert.match(result.stdout, /no overrides written/);
  assert.strictEqual(fs.readFileSync(settingsFile(dir), "utf8"), "{ not json");
});

test("provenance lives beside the settings file it describes", () => {
  const dir = tmpdir("provenance");
  const saved = process.env.TONONE_GATE_STATE_DIR;
  delete process.env.TONONE_GATE_STATE_DIR;
  try {
    assert.strictEqual(
      gate.provenancePath(dir),
      path.join(dir, ".claude", "tonone-skill-gate.json"),
    );
    const applied = gate.applySettings(dir, {
      "a-one": "name-only",
      "a-two": "user-invocable-only",
    });
    assert.strictEqual(applied.ok, true);
    assert.ok(
      fs.existsSync(gate.provenancePath(dir)),
      "no provenance record was written",
    );

    // A cache clean cannot reach it, so --reset still knows what it owns.
    assert.notStrictEqual(
      gate.provenancePath(dir),
      gate.legacyProvenancePath(dir),
    );
    const reset = gate.resetSettings(dir);
    assert.strictEqual(reset.removed, 2);
    assert.strictEqual(readSettings(dir).skillOverrides, undefined);
  } finally {
    if (saved === undefined) delete process.env.TONONE_GATE_STATE_DIR;
    else process.env.TONONE_GATE_STATE_DIR = saved;
  }
});

test("--reset --all is the way out when provenance is lost", () => {
  const dir = tmpdir("orphaned");
  const saved = process.env.TONONE_GATE_STATE_DIR;
  delete process.env.TONONE_GATE_STATE_DIR;
  try {
    gate.applySettings(dir, {
      "a-one": "name-only",
      "a-two": "user-invocable-only",
    });
    fs.unlinkSync(gate.provenancePath(dir));

    // Every entry now reads as the user's, so a plain reset must not touch them.
    const plain = gate.resetSettings(dir);
    assert.strictEqual(plain.removed, 0);
    assert.strictEqual(Object.keys(readSettings(dir).skillOverrides).length, 2);

    const all = gate.resetSettings(dir, { all: true });
    assert.strictEqual(all.removed, 2);
    assert.strictEqual(readSettings(dir).skillOverrides, undefined);
  } finally {
    if (saved === undefined) delete process.env.TONONE_GATE_STATE_DIR;
    else process.env.TONONE_GATE_STATE_DIR = saved;
  }
});

test("an ambient API key is not an opt-in to the network", () => {
  const client = require(path.join(ROOT, "lib", "jev", "client.js"));
  const saved = {
    OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY,
    JEV_API_KEY: process.env.JEV_API_KEY,
    TYPESAFE_API_KEY: process.env.TYPESAFE_API_KEY,
    TONONE_GATE_JEV: process.env.TONONE_GATE_JEV,
    TONONE_JEV_OFFLINE: process.env.TONONE_JEV_OFFLINE,
  };
  try {
    delete process.env.TONONE_JEV_OFFLINE;
    delete process.env.TONONE_GATE_JEV;
    process.env.OPENROUTER_API_KEY = "sk-fake-ambient-key";
    process.env.JEV_API_KEY = "jev-fake-ambient-key";
    process.env.TYPESAFE_API_KEY = "ts-fake-ambient-key";

    // The client on its own would call out; the gate's view of the environment
    // must not let it.
    assert.ok(
      client.resolveProvider(process.env),
      "fixture is wrong: no provider from an ambient key",
    );
    assert.strictEqual(client.resolveProvider(gate.jevEnv()), null);

    process.env.TONONE_GATE_JEV = "1";
    const provider = client.resolveProvider(gate.jevEnv());
    assert.ok(
      provider && provider.key,
      "TONONE_GATE_JEV=1 must opt the hook in",
    );
  } finally {
    for (const key of Object.keys(saved)) {
      if (saved[key] === undefined) delete process.env[key];
      else process.env[key] = saved[key];
    }
  }
});

test("a hook payload is honoured even when the pipe stays open", () => {
  const dir = makeProject("frontend");
  const elsewhere = tmpdir("elsewhere");
  const payload = JSON.stringify({
    hook_event_name: "SessionStart",
    cwd: dir,
    session_id: "t",
  });
  const env = Object.assign({}, process.env, {
    TONONE_JEV_CACHE_DIR: tmpdir("cache"),
    TONONE_GATE_STATE_DIR: tmpdir("state"),
    TONONE_JEV_OFFLINE: "1",
    TONONE_GATE_STDIN_MS: "300",
  });

  // The payload arrives at once; the writer then holds the pipe open well past
  // the stdin timeout, which is exactly what a hook runner does.
  const result = spawnSync(
    "/bin/sh",
    [
      "-c",
      "( printf %s " +
        JSON.stringify(payload) +
        "; sleep 2 ) | " +
        JSON.stringify(process.execPath) +
        " " +
        JSON.stringify(HOOK),
    ],
    { encoding: "utf8", env: env, cwd: elsewhere, timeout: 30000 },
  );

  assert.strictEqual(result.status, 0);
  const settings = readSettings(dir);
  assert.ok(
    settings && settings.skillOverrides,
    "the payload's cwd was not gated",
  );
  assert.strictEqual(
    readSettings(elsewhere),
    null,
    "the process's own cwd was gated instead",
  );

  // The timeout must not start a second run on top of the first.
  const receipts = result.stdout
    .split("\n")
    .filter((l) => l.indexOf("tonone skill gate:") === 0);
  assert.strictEqual(
    receipts.length,
    1,
    "the gate ran twice: " + JSON.stringify(result.stdout),
  );
});
