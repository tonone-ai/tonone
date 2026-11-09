// Run: node --test tests/hooks/test-form-design-lint.js
// (Node test files here are not auto-discovered by pytest; see tests/hooks/*.js.)
const { test } = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const ROOT = path.join(__dirname, "../..");
const CLI = path.join(ROOT, "team/form/scripts/design-lint/design-lint.js");
const HOOK = path.join(ROOT, "team/form/hooks/form-design-lint.js");
const FIX = path.join(ROOT, "tests/fixtures/design-lint");
const { rules } = require(CLI);

function cli(args, opts = {}) {
  return spawnSync("node", [CLI, ...args], {
    encoding: "utf8",
    timeout: 10000,
    ...opts,
  });
}
function lintJson(args) {
  const r = cli([...args, "--json"]);
  return {
    status: r.status,
    json: r.stdout ? JSON.parse(r.stdout) : null,
    stderr: r.stderr,
  };
}
function runHook(raw, env = {}) {
  return spawnSync("node", [HOOK], {
    input: typeof raw === "string" ? raw : JSON.stringify(raw),
    encoding: "utf8",
    timeout: 5000,
    env: { ...process.env, TONONE_DESIGN_LINT: "", ...env },
  });
}
function project(files, config) {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "dlint-")));
  fs.mkdirSync(path.join(dir, ".git"));
  if (config) {
    fs.mkdirSync(path.join(dir, ".tonone"));
    fs.writeFileSync(
      path.join(dir, ".tonone/design.json"),
      JSON.stringify(config),
    );
  }
  for (const [name, body] of Object.entries(files)) {
    fs.mkdirSync(path.dirname(path.join(dir, name)), { recursive: true });
    fs.writeFileSync(path.join(dir, name), body);
  }
  return dir;
}
const GRAD = `export const H = () => <h1 className="bg-gradient-to-r from-a to-b bg-clip-text text-transparent">x</h1>;\n`;
const hookInput = (dir, file, sid = "s1") => ({
  session_id: sid + Math.random(),
  cwd: dir,
  tool_name: "Write",
  tool_input: { file_path: path.join(dir, file) },
});

// ── rules ──────────────────────────────────────────────────────────────────
test("rule table: ~20 rules, unique ids, valid tiers", () => {
  assert.ok(rules.length >= 19);
  assert.strictEqual(new Set(rules.map((r) => r.id)).size, rules.length);
  for (const r of rules) {
    assert.ok(["immediate", "advisory"].includes(r.tier), r.id);
    assert.ok(r.message && r.fix && typeof r.detect === "function", r.id);
  }
});

test("positive fixtures: every rule fires on its fixture", () => {
  const dir = path.join(FIX, "positive");
  const { json } = lintJson([dir, "--root", dir]);
  const byFile = {};
  for (const f of json.findings) (byFile[f.file] ||= new Set()).add(f.rule);
  const ruleIds = new Set(rules.map((r) => r.id));
  for (const file of fs.readdirSync(dir)) {
    const id = file.replace(/(-css)?\.[a-z]+$/, "");
    assert.ok(ruleIds.has(id), `fixture ${file} names unknown rule`);
    assert.ok(
      byFile[file] && byFile[file].has(id),
      `${file}: expected ${id}, got ${[...(byFile[file] || [])]}`,
    );
  }
});

test("drift fixtures: DESIGN.md tokens drive drift rules", () => {
  const dir = path.join(FIX, "drift");
  const { json } = lintJson([dir, "--root", dir]);
  const got = new Set(json.findings.map((f) => f.rule));
  assert.ok(got.has("design-system-drift"));
  assert.ok(got.has("design-system-drift-scale"));
  assert.strictEqual(
    json.findings.find((f) => f.rule === "design-system-drift").tier,
    "immediate",
  );
  assert.ok(
    !json.findings.some((f) => f.message.includes("#f7f6f3")),
    "in-palette color must not drift",
  );
});

test("drift is inert without DESIGN.md", () => {
  const dir = project({ "a.css": ".x { color: #ff00aa; font-size: 13px; }\n" });
  const { json } = lintJson([dir, "--root", dir]);
  assert.ok(
    !json.findings.some((f) => f.rule.startsWith("design-system-drift")),
  );
});

test("FALSE-POSITIVE SILENCE: clean corpus has zero findings", () => {
  const dir = path.join(FIX, "clean");
  const { status, json } = lintJson([dir, "--root", dir]);
  assert.deepStrictEqual(json.findings, []);
  assert.strictEqual(status, 0);
});

test("tiers: --tier immediate drops advisory", () => {
  const dir = path.join(FIX, "positive");
  const { json } = lintJson([dir, "--root", dir, "--tier", "immediate"]);
  assert.ok(json.findings.length > 0);
  assert.ok(json.findings.every((f) => f.tier === "immediate"));
});

test("json shape is stable", () => {
  const dir = path.join(FIX, "positive");
  const { json } = lintJson([
    path.join(dir, "gradient-text.tsx"),
    "--root",
    dir,
  ]);
  const f = json.findings[0];
  for (const k of ["file", "line", "rule", "tier", "severity", "message"])
    assert.ok(k in f, k);
  assert.strictEqual(f.file, "gradient-text.tsx");
});

test("human output follows the 40-line rule", () => {
  const dir = path.join(FIX, "positive");
  const r = cli([dir, "--root", dir]);
  assert.ok(r.stdout.split("\n").length <= 40);
  assert.match(r.stdout, /FORM ── form-lint/);
});

// ── exit codes ─────────────────────────────────────────────────────────────
test("exit codes: 0 clean, 1 immediate, 0 advisory-only, 2 usage", () => {
  const pos = path.join(FIX, "positive");
  assert.strictEqual(
    cli([path.join(pos, "gradient-text.tsx"), "--root", pos]).status,
    1,
  );
  assert.strictEqual(
    cli([path.join(pos, "emoji-as-icon.tsx"), "--root", pos]).status,
    0,
  );
  assert.strictEqual(
    cli([path.join(FIX, "clean"), "--root", path.join(FIX, "clean")]).status,
    0,
  );
  assert.strictEqual(cli(["--bogus"]).status, 2);
  assert.strictEqual(cli([pos, "--tier", "nope"]).status, 2);
  assert.strictEqual(cli(["/no/such/path/xyz"]).status, 2);
});

test("walk skips node_modules/.git/dist and non-design extensions", () => {
  const dir = project({
    "node_modules/x/a.tsx": GRAD,
    "dist/a.tsx": GRAD,
    "build/a.css": ".t{font-size:8px}",
    "notes.md": "font-size: 8px",
    "src/ok.tsx": "export const A = () => <p>hi</p>;\n",
  });
  const { json } = lintJson([dir, "--root", dir]);
  assert.deepStrictEqual(json.findings, []);
  assert.strictEqual(json.scanned, 1);
});

// ── suppressions ───────────────────────────────────────────────────────────
test("inline disable-next-line suppresses only the named rule on the next line", () => {
  const dir = project({
    "a.tsx": `// design-lint-disable-next-line gradient-text\n${GRAD}`,
    "b.tsx": `// design-lint-disable-next-line side-tab\n${GRAD}`,
    "c.tsx": `${GRAD}\n// design-lint-disable-next-line gradient-text\n${GRAD}`,
  });
  const { json } = lintJson([dir, "--root", dir]);
  const files = json.findings.map((f) => `${f.file}:${f.rule}`);
  assert.ok(!files.includes("a.tsx:gradient-text"));
  assert.ok(files.includes("b.tsx:gradient-text"));
  assert.strictEqual(
    files.filter((f) => f === "c.tsx:gradient-text").length,
    1,
  );
});

test("ignoreRules + ignoreFiles honored; missing reason warns but still applies", () => {
  const dir = project(
    {
      "a.tsx": GRAD,
      "legacy/b.tsx": GRAD,
      "legacy/deep/c.css": ".t{font-size:8px}",
      "d.css": ".t{font-size:8px}",
    },
    {
      ignoreRules: [{ rule: "tiny-text", reason: "" }],
      ignoreFiles: [{ glob: "legacy/**", reason: "old marketing site" }],
    },
  );
  const { json } = lintJson([dir, "--root", dir]);
  assert.deepStrictEqual(
    json.findings.map((f) => `${f.file}:${f.rule}`),
    ["a.tsx:gradient-text"],
  );
  assert.ok(json.warnings.some((w) => /tiny-text/.test(w) && /reason/.test(w)));
});

test("glob: ** and * semantics", () => {
  const { globToRegExp } = require(CLI);
  assert.ok(globToRegExp("src/**/*.css").test("src/a/b/c.css"));
  assert.ok(globToRegExp("src/**/*.css").test("src/c.css"));
  assert.ok(!globToRegExp("src/*.css").test("src/a/c.css"));
  assert.ok(globToRegExp("*.tsx").test("a.tsx"));
  assert.ok(!globToRegExp("*.tsx").test("x/a.tsx"));
});

// ── hook ───────────────────────────────────────────────────────────────────
test("hook: inert by default (no config, no env)", () => {
  const dir = project({ "a.tsx": GRAD });
  const r = runHook(hookInput(dir, "a.tsx"));
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout, "");
});

test("hook: enabled via .tonone/design.json hook:true surfaces additionalContext, never blocks", () => {
  const dir = project({ "a.tsx": GRAD }, { hook: true });
  const r = runHook(hookInput(dir, "a.tsx"));
  assert.strictEqual(r.status, 0);
  const out = JSON.parse(r.stdout);
  assert.strictEqual(out.hookSpecificOutput.hookEventName, "PostToolUse");
  assert.match(out.hookSpecificOutput.additionalContext, /gradient-text/);
  assert.ok(!("decision" in out));
  assert.ok(!JSON.stringify(out).includes('"block"'));
});

test("hook: enabled via env; off wins over config and env on", () => {
  const dir = project({ "a.tsx": GRAD });
  assert.match(
    runHook(hookInput(dir, "a.tsx"), { TONONE_DESIGN_LINT: "on" }).stdout,
    /gradient-text/,
  );
  const dir2 = project({ "a.tsx": GRAD }, { hook: true });
  assert.strictEqual(
    runHook(hookInput(dir2, "a.tsx"), { TONONE_DESIGN_LINT: "off" }).stdout,
    "",
  );
});

test("hook: only immediate tier, only matching extensions and write tools", () => {
  const dir = project(
    {
      "e.tsx": "export const I = () => <li>🚀 Fast</li>;\n",
      "n.md": "font-size: 8px",
      "a.tsx": GRAD,
    },
    { hook: true },
  );
  assert.strictEqual(
    runHook(hookInput(dir, "e.tsx")).stdout,
    "",
    "advisory must not surface",
  );
  assert.strictEqual(runHook(hookInput(dir, "n.md")).stdout, "");
  const bash = { ...hookInput(dir, "a.tsx"), tool_name: "Bash" };
  assert.strictEqual(runHook(bash).stdout, "");
});

test("hook: dedup within a session, re-reports for a new session", () => {
  const dir = project({ "a.tsx": GRAD }, { hook: true });
  const input = hookInput(dir, "a.tsx", "dedup");
  assert.match(runHook(input).stdout, /gradient-text/);
  assert.strictEqual(
    runHook(input).stdout,
    "",
    "second identical report suppressed",
  );
  assert.match(
    runHook({ ...input, session_id: "other-" + Math.random() }).stdout,
    /gradient-text/,
  );
});

test("hook: caps at 5 findings with a 'run /form-lint' tail", () => {
  const body =
    Array.from(
      { length: 9 },
      (_, i) => `.c${i} { font-size: ${i + 1}px; }`,
    ).join("\n") + "\n";
  const dir = project({ "a.css": body }, { hook: true });
  const ctx = JSON.parse(runHook(hookInput(dir, "a.css")).stdout)
    .hookSpecificOutput.additionalContext;
  assert.strictEqual((ctx.match(/\[tiny-text\]/g) || []).length, 5);
  assert.match(ctx, /4 more, run \/form-lint/);
});

test("hook: respects ignoreFiles and skips oversized files", () => {
  const dir = project(
    {
      "a.tsx": GRAD,
      "big.css": ".t{font-size:8px}\n" + "/* x */\n".repeat(50000),
    },
    { hook: true, ignoreFiles: [{ glob: "a.tsx", reason: "legacy" }] },
  );
  assert.strictEqual(runHook(hookInput(dir, "a.tsx")).stdout, "");
  assert.strictEqual(runHook(hookInput(dir, "big.css")).stdout, "");
});

test("hook: fails open on garbage / empty / wrong-shape stdin and missing files", () => {
  for (const raw of [
    "",
    "not json {{{",
    "null",
    "[]",
    '{"tool_name":"Write"}',
    '{"tool_name":"Write","tool_input":{"file_path":"/no/such/file.tsx"}}',
  ]) {
    const r = runHook(raw, { TONONE_DESIGN_LINT: "on" });
    assert.strictEqual(r.status, 0, raw);
    assert.strictEqual(r.stdout, "", raw);
  }
});

test("hook: finishes well under the time budget", () => {
  const dir = project({ "a.tsx": GRAD }, { hook: true });
  const t = Date.now();
  runHook(hookInput(dir, "a.tsx"));
  assert.ok(Date.now() - t < 1500);
});

// ── opt-in metrics ─────────────────────────────────────────────────────────
test("metrics: on writes form-lint hook_shown; output unchanged; off writes nothing", () => {
  const dirA = project({ "a.tsx": GRAD }, { hook: true });
  const dirB = project({ "a.tsx": GRAD }, { hook: true });
  const sid = "fixed-sid-" + Math.random();
  const mk = (d) => ({
    ...hookInput(d, "a.tsx"),
    session_id: sid + path.basename(d),
  });
  const off = runHook(mk(dirA), { TONONE_METRICS: "" });
  assert.ok(off.stdout.includes("design-lint"));
  assert.ok(!fs.existsSync(path.join(dirA, ".tonone/metrics.jsonl")));
  const on = runHook(mk(dirB), { TONONE_METRICS: "on" });
  assert.strictEqual(
    on.stdout.replace(/a\.tsx/g, ""),
    off.stdout.replace(/a\.tsx/g, ""),
  );
  const lines = fs
    .readFileSync(path.join(dirB, ".tonone/metrics.jsonl"), "utf8")
    .trim()
    .split("\n")
    .map((l) => JSON.parse(l));
  assert.strictEqual(lines.length, 1);
  assert.strictEqual(lines[0].tool, "form-lint");
  assert.strictEqual(lines[0].event, "hook_shown");
  assert.ok(lines[0].shown >= 1 && Array.isArray(lines[0].rules));
});
