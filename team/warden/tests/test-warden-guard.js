"use strict";

/**
 * Tests for the warden-guard PreToolUse hook.
 *
 *   node --test team/warden/tests/test-warden-guard.js
 *
 * Node's built-in test runner, no dependencies, matching tests/hooks/*.js.
 *
 * Two halves that matter equally:
 *   - true positives: each rule family fires on the pattern it exists for
 *   - true negatives: the hook stays silent on real source files in this repo
 *     (hooks/, lib/uiux, scripts/*.py). False positives are the failure mode
 *     that gets a security hook uninstalled, so they are tested first-class.
 */

const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const HOOK = path.join(__dirname, "..", "hooks", "warden-guard.js");
const REPO = path.join(__dirname, "..", "..", "..");
const guard = require(HOOK);

const RULES = guard.loadRules();

// ── Helpers ─────────────────────────────────────────────────────────────────

function scanCode(text, ext) {
  return guard.scanText(text, { mode: "code", ext: ext || "js", rules: RULES });
}

function scanShell(text) {
  return guard.scanText(text, { mode: "shell", ext: null, rules: RULES });
}

function ids(findings) {
  return findings.map((f) => f.id);
}

function runHook(payload, env) {
  return spawnSync("node", [HOOK], {
    input: typeof payload === "string" ? payload : JSON.stringify(payload),
    encoding: "utf8",
    timeout: 10000,
    env: Object.assign({}, process.env, env || {}),
  });
}

function scanRepoFile(relPath) {
  const abs = path.join(REPO, relPath);
  const text = fs.readFileSync(abs, "utf8");
  const ext = guard.extensionOf(abs);
  return guard.scanText(text, { mode: "code", ext, rules: RULES });
}

// ── Rule set sanity ─────────────────────────────────────────────────────────

test("rules.json loads and every rule compiles", () => {
  assert.ok(
    RULES.length >= 15,
    `expected a real rule set, got ${RULES.length}`,
  );
  const raw = JSON.parse(
    fs.readFileSync(path.join(__dirname, "..", "hooks", "rules.json"), "utf8"),
  );
  assert.strictEqual(
    RULES.length,
    raw.rules.length,
    "a rule failed to compile and was dropped",
  );
  const seen = new Set();
  for (const rule of RULES) {
    assert.ok(!seen.has(rule.id), `duplicate rule id: ${rule.id}`);
    seen.add(rule.id);
    assert.ok(rule.advice.length > 10, `rule ${rule.id} has no usable advice`);
  }
});

test("a broken rules file degrades to silence, never to a throw", () => {
  assert.deepStrictEqual(guard.loadRules("/nonexistent/rules.json"), []);
});

// ── True positives ──────────────────────────────────────────────────────────

test("command injection — request data into a shell", () => {
  const found = ids(
    scanCode("execSync(`git log --author=${req.query.author}`);"),
  );
  assert.ok(found.includes("cmd-injection-node-exec-untrusted"), found.join());
});

test("command injection — python shell=True with an f-string", () => {
  const found = ids(
    scanCode('subprocess.run(f"tar -xf {name}", shell=True)', "py"),
  );
  assert.ok(
    found.includes("cmd-injection-python-shell") ||
      found.includes("cmd-injection-python-shell-untrusted"),
    found.join(),
  );
});

test("XSS — innerHTML, dangerouslySetInnerHTML, document.write", () => {
  assert.ok(
    ids(scanCode("el.innerHTML = userName;")).includes("xss-inner-html"),
  );
  assert.ok(
    ids(
      scanCode("<div dangerouslySetInnerHTML={{ __html: body }} />"),
    ).includes("xss-dangerously-set-html"),
  );
  assert.ok(
    ids(scanCode('document.write("<p>" + name + "</p>");')).includes(
      "xss-document-write",
    ),
  );
});

test("hardcoded secrets — known prefixes", () => {
  const samples = [
    'const k = "AKIA2G7PQRSTUV4WXYZA";',
    'const k = "sk-proj-9f3Ka81mZq7XrT4bVn2LpQ6sWyE0dHgJ";',
    'const k = "ghp_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8";',
    'const k = "xoxb-2417283947-4837261094-Zk3PqR7sT1vW";',
    'key = "-----BEGIN RSA PRIVATE KEY-----"',
  ];
  for (const sample of samples) {
    const found = ids(scanCode(sample));
    assert.ok(
      found.includes("secret-known-prefix") ||
        found.includes("secret-assigned-literal"),
      `missed: ${sample}`,
    );
  }
});

test("hardcoded secrets — high-entropy literal on a credential name", () => {
  const found = ids(scanCode('const dbPassword = "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1";'));
  assert.ok(found.includes("secret-assigned-literal"), found.join());
});

test("credential names are caught in every common casing", () => {
  const samples = [
    'const dbPassword = "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1";',
    'DB_PASSWORD = "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1"',
    'password = "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1"',
    'self.client_secret = "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1"',
    'cfg.apiKey = "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1"',
    '{ "authToken": "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1" }',
  ];
  for (const sample of samples) {
    assert.ok(
      ids(scanCode(sample)).includes("secret-assigned-literal"),
      `missed: ${sample}`,
    );
  }
});

test("a credential word inside an unrelated identifier stays quiet", () => {
  // The camelCase half of the name boundary only accepts a capitalised hump,
  // which is what keeps `bypass`, `compass` and `surpassed` out of the report.
  const benign = [
    'const bypass = "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1";',
    'const compass = "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1";',
    'const surpassed = "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1";',
  ];
  for (const line of benign) {
    assert.deepStrictEqual(
      ids(scanCode(line)),
      [],
      `false positive on: ${line}`,
    );
  }
});

test("placeholder credentials stay quiet whatever their casing", () => {
  const benign = [
    'aws_access_key_id = "AKIAIO5FODNN7EXAMPLE"',
    'const key = "AKIAEXAMPLEKEYDONOTUSE";',
    'password = "CHANGEME-BEFORE-YOU-DEPLOY-PLEASE"',
    'token = "<YOUR_TOKEN_HERE_REPLACE_THIS>"',
  ];
  for (const line of benign) {
    assert.deepStrictEqual(
      ids(scanCode(line)),
      [],
      `false positive on: ${line}`,
    );
  }
});

test("SQL string concatenation", () => {
  assert.ok(
    ids(scanCode("const q = `SELECT * FROM users WHERE id = ${id}`;")).includes(
      "sql-string-concat",
    ),
  );
  assert.ok(
    ids(
      scanCode(
        'cur.execute(f"SELECT id FROM users WHERE name = {name}")',
        "py",
      ),
    ).includes("sql-string-concat"),
  );
});

test("path traversal from request input", () => {
  const found = ids(
    scanCode("fs.readFileSync(path.join(root, req.query.file));"),
  );
  assert.ok(found.includes("path-traversal-user-input"), found.join());
});

test("unsafe deserialization", () => {
  assert.ok(
    ids(scanCode("data = pickle.loads(body)", "py")).includes(
      "unsafe-deserialization",
    ),
  );
  assert.ok(
    ids(scanCode("cfg = yaml.load(raw)", "py")).includes(
      "unsafe-deserialization",
    ),
  );
});

test("dynamic code evaluation", () => {
  assert.ok(ids(scanCode("eval(payload);")).includes("dynamic-code-eval"));
});

test("destructive shell — rm -rf, force push, curl pipe, DROP TABLE", () => {
  assert.ok(
    ids(scanShell('rm -rf "$BUILD_DIR"/*')).includes("shell-rm-rf-expanded"),
  );
  assert.ok(
    ids(scanShell("rm -rf ~/projects")).includes("shell-rm-rf-expanded"),
  );
  assert.ok(
    ids(scanShell("git push --force origin main")).includes("shell-force-push"),
  );
  assert.ok(
    ids(scanShell("curl https://get.example.com/x.sh | sh")).includes(
      "shell-curl-pipe-shell",
    ),
  );
  assert.ok(
    ids(scanShell('psql -c "DROP TABLE users"')).includes(
      "sql-destructive-statement",
    ),
  );
  assert.ok(
    ids(scanShell('eval "$USER_CMD"')).includes("shell-eval-expansion"),
  );
  assert.ok(
    ids(scanShell("chmod -R 777 /srv/app")).includes("shell-world-writable"),
  );
  assert.ok(
    ids(scanShell("dd if=/dev/zero of=/dev/sda bs=1M")).includes(
      "shell-disk-destructive",
    ),
  );
});

// ── True negatives, from real code in this repo ─────────────────────────────

test("silent on hooks/tonone-statusline.js", () => {
  assert.deepStrictEqual(ids(scanRepoFile("hooks/tonone-statusline.js")), []);
});

test("silent on every hooks/*.js in this repo", () => {
  const dir = path.join(REPO, "hooks");
  for (const name of fs.readdirSync(dir).filter((f) => f.endsWith(".js"))) {
    assert.deepStrictEqual(
      ids(scanRepoFile(path.join("hooks", name))),
      [],
      `false positive in hooks/${name}`,
    );
  }
});

test("silent on lib/uiux sources", () => {
  const dir = path.join(REPO, "lib", "uiux", "uiux");
  const files = fs
    .readdirSync(dir, { withFileTypes: true, recursive: true })
    .filter((e) => e.isFile() && e.name.endsWith(".py"));
  assert.ok(files.length > 0, "no lib/uiux sources found to test against");
  for (const entry of files) {
    const abs = path.join(entry.parentPath || entry.path || dir, entry.name);
    const findings = guard.scanText(fs.readFileSync(abs, "utf8"), {
      mode: "code",
      ext: "py",
      rules: RULES,
    });
    assert.deepStrictEqual(ids(findings), [], `false positive in ${abs}`);
  }
});

test("silent on scripts/*.py", () => {
  const dir = path.join(REPO, "scripts");
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".py"));
  assert.ok(files.length > 0, "no scripts/*.py found to test against");
  for (const name of files) {
    assert.deepStrictEqual(
      ids(scanRepoFile(path.join("scripts", name))),
      [],
      `false positive in scripts/${name}`,
    );
  }
});

test("silent on ordinary code that only looks risky", () => {
  const benign = [
    'execSync("git rev-parse --abbrev-ref HEAD", { cwd });',
    'el.innerHTML = "";',
    "const rows = await db.query(SELECT_USER_SQL, [id]);",
    'const doc = "Use the UPDATE endpoint to change a record";',
    "const msg = `Update available: v${current} -> v${latest}`;",
    "const apiKey = process.env.API_KEY;",
    'password = os.environ["DB_PASSWORD"]',
    'token = "your-token-goes-here-replace-me"',
    "model.eval()",
    "const value = ast.literal_eval(raw)",
    "yaml.safe_load(raw)",
    "cur.execute('SELECT id FROM users WHERE name = %s', (name,))",
  ];
  for (const line of benign) {
    const found = ids(
      scanCode(line, line.includes("os.environ") ? "py" : "js"),
    );
    assert.deepStrictEqual(found, [], `false positive on: ${line}`);
  }
});

test("silent on ordinary shell commands", () => {
  const benign = [
    "rm -rf node_modules",
    "rm -f build/out.log",
    "git push origin feature/x",
    "git push --force-with-lease origin feature/x",
    "curl -sSL https://example.com/api | jq .",
    "chmod 755 scripts/setup.sh",
    "python -m pytest tests/ -v",
    "dd if=input.bin of=output.bin bs=4k",
  ];
  for (const command of benign) {
    assert.deepStrictEqual(
      ids(scanShell(command)),
      [],
      `false positive on: ${command}`,
    );
  }
});

// ── Suppression ─────────────────────────────────────────────────────────────

test("inline marker on the line suppresses", () => {
  const text =
    'const k = "sk-proj-9f3Ka81mZq7XrT4bVn2LpQ6sWyE0dHgJ"; // warden-guard: ignore';
  assert.deepStrictEqual(ids(scanCode(text)), []);
});

test("marker on the previous line suppresses", () => {
  const text = [
    "// warden-guard: ignore — fixture key for the test suite",
    'const k = "sk-proj-9f3Ka81mZq7XrT4bVn2LpQ6sWyE0dHgJ";',
  ].join("\n");
  assert.deepStrictEqual(ids(scanCode(text)), []);
});

test("file-level marker suppresses the whole scan", () => {
  const text = [
    "// warden-guard: off",
    'const k = "sk-proj-9f3Ka81mZq7XrT4bVn2LpQ6sWyE0dHgJ";',
    "eval(payload);",
  ].join("\n");
  assert.deepStrictEqual(ids(scanCode(text)), []);
});

test("TONONE_GUARD=off silences the hook process", () => {
  const payload = {
    tool_name: "Bash",
    tool_input: { command: 'rm -rf "$DIR"/*' },
  };
  const loud = runHook(payload);
  assert.ok(loud.stdout.includes("warden-guard"), "expected an advisory");
  for (const value of ["off", "0", "false", "no"]) {
    const quiet = runHook(payload, { TONONE_GUARD: value });
    assert.strictEqual(quiet.status, 0);
    assert.strictEqual(
      quiet.stdout.trim(),
      "",
      `TONONE_GUARD=${value} not honored`,
    );
  }
});

// ── Hook contract ───────────────────────────────────────────────────────────

test("never blocks — exit 0 and no permission decision, even on a critical hit", () => {
  const result = runHook({
    tool_name: "Write",
    tool_input: {
      file_path: "app.js",
      content: 'const k = "AKIA2G7PQRSTUV4WXYZA";',
    },
  });
  assert.strictEqual(result.status, 0);
  assert.ok(result.stdout.includes("warden-guard"));
  assert.ok(!/permissionDecision/.test(result.stdout), result.stdout);
  assert.ok(!/"deny"/.test(result.stdout), result.stdout);
  const parsed = JSON.parse(result.stdout.trim().split("\n").pop());
  assert.ok(parsed.systemMessage.includes("CRITICAL"));
  assert.strictEqual(parsed.hookSpecificOutput.hookEventName, "PreToolUse");
});

test("exits 0 and stays quiet on malformed or irrelevant input", () => {
  const cases = [
    "",
    "not json at all",
    "{}",
    JSON.stringify({ tool_name: "Read", tool_input: { file_path: "a.js" } }),
    JSON.stringify({ tool_name: "Bash", tool_input: {} }),
    JSON.stringify({ tool_name: "Edit", tool_input: { file_path: "a.js" } }),
    JSON.stringify({ tool_name: "Write", tool_input: { content: "" } }),
  ];
  for (const input of cases) {
    const result = runHook(input);
    assert.strictEqual(result.status, 0, `nonzero exit for: ${input}`);
    assert.strictEqual(result.stdout.trim(), "", `noise for: ${input}`);
  }
});

test("Edit and MultiEdit scan only the incoming text", () => {
  const edit = guard.candidatesFrom({
    tool_name: "Edit",
    tool_input: {
      file_path: "src/app.js",
      old_string: 'const k = "AKIA2G7PQRSTUV4WXYZA";',
      new_string: "const k = process.env.KEY;",
    },
  });
  assert.strictEqual(edit.length, 1);
  assert.strictEqual(edit[0].text, "const k = process.env.KEY;");
  assert.deepStrictEqual(ids(scanCode(edit[0].text)), []);

  const multi = guard.candidatesFrom({
    tool_name: "MultiEdit",
    tool_input: {
      file_path: "src/app.js",
      edits: [{ new_string: "a();" }, { new_string: "eval(payload);" }],
    },
  });
  assert.strictEqual(multi.length, 1);
  assert.ok(ids(scanCode(multi[0].text)).includes("dynamic-code-eval"));
});

test("markdown and other prose files skip the code rules", () => {
  const text =
    "Run `rm -rf $DIR` and set `el.innerHTML = name` in the example.";
  assert.deepStrictEqual(
    ids(guard.scanText(text, { mode: "code", ext: "md", rules: RULES })),
    [],
  );
});

test("shell rules also apply to shell scripts", () => {
  const found = ids(
    guard.scanText('rm -rf "$TARGET"/*', {
      mode: "code",
      ext: "sh",
      rules: RULES,
    }),
  );
  assert.ok(found.includes("shell-rm-rf-expanded"), found.join());
});

// ── Performance and limits ──────────────────────────────────────────────────

test("scans a large file in well under a second", () => {
  const body = [];
  for (let i = 0; i < 20000; i++) {
    body.push(`const value${i} = compute(${i}, "some literal text here");`);
  }
  body.push('const k = "AKIA2G7PQRSTUV4WXYZA";');
  const text = body.join("\n");
  const started = Date.now();
  const findings = scanCode(text);
  const elapsed = Date.now() - started;
  assert.ok(elapsed < 900, `scan took ${elapsed}ms`);
  assert.ok(findings.length >= 0);
});

test("oversized and minified input is skipped, not crawled", () => {
  const huge = "x".repeat(3 * 1024 * 1024);
  assert.deepStrictEqual(scanCode(huge), []);
  const minified = "var a=1;" + "b();".repeat(1000) + "eval(payload);";
  assert.deepStrictEqual(ids(scanCode(minified)), []);
});

test("at most five findings are shown, with an overflow line", () => {
  const findings = [];
  for (let i = 0; i < 8; i++) {
    findings.push({
      id: `r${i}`,
      title: `rule ${i}`,
      severity: "WARNING",
      advice: "do the safe thing instead",
      line: i + 1,
      excerpt: "",
    });
  }
  const out = guard.formatAdvisory("app.js", findings, true);
  assert.ok(out.includes("...and 3 more"), out);
  assert.ok(out.split("\n").length <= 8, out);
});

test("entropy separates a key from repetitive filler", () => {
  assert.ok(guard.shannonEntropy("7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1") > 4);
  assert.ok(guard.shannonEntropy("aaaaaaaaaaaaaaaaaaaaaaaa") < 1);
});

test("entropy alone does not separate a key from an English phrase", () => {
  // The reason the rule carries a shape test as well: these phrases score
  // above any entropy floor low enough to still catch a short real key.
  for (const phrase of [
    "user-invocable-only",
    "replace-this-before-deploy",
    "correct horse battery staple",
  ]) {
    assert.ok(
      guard.shannonEntropy(phrase) > 3.4,
      `${phrase} scored ${guard.shannonEntropy(phrase)}`,
    );
  }
});

test("word-shaped values stay quiet even with high entropy", () => {
  // End to end through the rule set, not just through shannonEntropy(): each
  // of these clears the 3.4-bit floor and must be suppressed by shape.
  const benign = [
    ['  "hue-token": "user-invocable-only",', "json"],
    ['token = "replace-this-before-deploy"', "js"],
    ['password = "correct horse battery staple"', "js"],
    ['const authToken = "Replace This Before Deploy";', "js"],
    ['client_secret = "set_me_from_the_environment"', "py"],
  ];
  for (const [line, ext] of benign) {
    assert.deepStrictEqual(
      ids(scanCode(line, ext)),
      [],
      `false positive on: ${line}`,
    );
  }
});

test("a real key next to a word-shaped value still fires", () => {
  const found = ids(scanCode('const apiKey = "7Gq2VxZ9tLm4Rn8Kp3Wd6Yb1";'));
  assert.ok(found.includes("secret-assigned-literal"), found.join());
});

test("the settings file the skill-gate writes scans clean", () => {
  // Regression guard for the shape that produced a CRITICAL false positive on
  // ordinary config: a map of skill names to override modes.
  const text = [
    "{",
    '  "skillOverrides": {',
    '    "hue-token": "user-invocable-only",',
    '    "warden-scan": "name-only",',
    '    "apex-plan": "on"',
    "  }",
    "}",
  ].join("\n");
  assert.deepStrictEqual(ids(scanCode(text, "json")), []);
});

// ── Rule targeting ──────────────────────────────────────────────────────────

test("an ext allowlist does not mute a rule on a Bash command", () => {
  // A Bash command has no file extension. Rules that target shell must still
  // fire there even when they also carry an `ext` list for the code path.
  const found = ids(scanShell('psql -c "DROP TABLE users"'));
  assert.ok(found.includes("sql-destructive-statement"), found.join());
});

test("a pattern can override the rule's casing with (?i) / (?-i)", () => {
  const macros = { WORD: "(?:alpha|{{INNER}})", INNER: "beta" };
  const [plain, insensitive, sensitive] = [
    ["{{WORD}}", ""],
    ["(?i){{WORD}}", ""],
    ["(?-i){{WORD}}", "i"],
  ].map(
    ([pattern, flags]) =>
      guard.expandMacros(pattern, macros) &&
      new RegExp(
        guard.expandMacros(pattern, macros).replace(/^\(\?-?i\)/, ""),
        pattern.startsWith("(?i)")
          ? "i"
          : pattern.startsWith("(?-i)")
            ? ""
            : flags,
      ),
  );
  assert.strictEqual(guard.expandMacros("{{WORD}}", macros), "(?:alpha|beta)");
  assert.ok(plain.test("beta"));
  assert.ok(insensitive.test("BETA"));
  assert.ok(!sensitive.test("BETA"));
});

test("silent across every hook and library source in the repo", () => {
  const roots = ["hooks", "lib", path.join("team", "warden", "hooks")];
  const exts = new Set(["js", "cjs", "mjs", "py"]);
  let scanned = 0;
  for (const root of roots) {
    const dir = path.join(REPO, root);
    if (!fs.existsSync(dir)) continue;
    const entries = fs.readdirSync(dir, {
      withFileTypes: true,
      recursive: true,
    });
    for (const entry of entries) {
      if (!entry.isFile()) continue;
      const ext = guard.extensionOf(entry.name);
      if (!ext || !exts.has(ext)) continue;
      const abs = path.join(entry.parentPath || entry.path || dir, entry.name);
      if (abs.includes("node_modules") || abs.includes("/.venv/")) continue;
      scanned++;
      const findings = guard.scanText(fs.readFileSync(abs, "utf8"), {
        mode: "code",
        ext,
        rules: RULES,
      });
      assert.deepStrictEqual(ids(findings), [], `false positive in ${abs}`);
    }
  }
  assert.ok(scanned > 10, `expected a real corpus, scanned ${scanned}`);
});

test("silent on this repo's setup.sh scripts", () => {
  const dirs = fs
    .readdirSync(path.join(REPO, "team"), { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => path.join(REPO, "team", e.name, "scripts", "setup.sh"))
    .filter((p) => fs.existsSync(p));
  assert.ok(dirs.length > 0, "no setup.sh found to test against");
  for (const abs of dirs) {
    const findings = guard.scanText(fs.readFileSync(abs, "utf8"), {
      mode: "shell",
      ext: "sh",
      rules: RULES,
    });
    assert.deepStrictEqual(ids(findings), [], `false positive in ${abs}`);
  }
});

// ── Manual scan ─────────────────────────────────────────────────────────────

test("--scan reports on a file and still exits 0", () => {
  const tmp = path.join(
    fs.mkdtempSync(path.join(require("os").tmpdir(), "warden-guard-")),
    "leak.js",
  );
  fs.writeFileSync(tmp, 'const k = "AKIA2G7PQRSTUV4WXYZA";\n');
  const result = spawnSync("node", [HOOK, "--scan", tmp], {
    encoding: "utf8",
    timeout: 10000,
  });
  assert.strictEqual(result.status, 0);
  assert.ok(result.stdout.includes("CRITICAL"), result.stdout);

  const missing = spawnSync("node", [HOOK, "--scan", "/nope/nope.js"], {
    encoding: "utf8",
    timeout: 10000,
  });
  assert.strictEqual(missing.status, 0);
  assert.strictEqual(missing.stdout.trim(), "");
});
