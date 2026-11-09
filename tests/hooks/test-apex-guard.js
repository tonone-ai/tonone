const { test } = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../team/apex/hooks/apex-guard.js");

function runHook(rawInput, env) {
  return spawnSync("node", [HOOK], {
    input: typeof rawInput === "string" ? rawInput : JSON.stringify(rawInput),
    encoding: "utf8",
    timeout: 5000,
    env: { ...process.env, TONONE_GUARD: "", TONONE_APEX_GUARD: "", ...env },
  });
}

function makeProject(state) {
  const dir = fs.realpathSync(
    fs.mkdtempSync(path.join(os.tmpdir(), "apex-guard-")),
  );
  fs.mkdirSync(path.join(dir, ".claude"), { recursive: true });
  if (state) {
    fs.writeFileSync(
      path.join(dir, ".claude", "tonone-guard.json"),
      JSON.stringify({
        version: 1,
        careful: false,
        freeze: null,
        session_id: "s1",
        armed_at: new Date().toISOString(),
        ...state,
      }),
    );
  }
  return dir;
}

function stateOf(dir) {
  return JSON.parse(
    fs.readFileSync(path.join(dir, ".claude", "tonone-guard.json"), "utf8"),
  );
}

function cleanup(dir) {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch {}
}

function bash(dir, command, extra) {
  const r = runHook(
    {
      tool_name: "Bash",
      tool_input: { command },
      cwd: dir,
      session_id: "s1",
      ...extra,
    },
    { CLAUDE_PROJECT_DIR: dir },
  );
  return r;
}

function decision(r) {
  if (!r.stdout.trim()) return null;
  return JSON.parse(r.stdout).hookSpecificOutput.permissionDecision;
}

function edit(dir, file, tool, extra) {
  return runHook(
    {
      tool_name: tool || "Write",
      tool_input: { file_path: file },
      cwd: dir,
      session_id: "s1",
      ...extra,
    },
    { CLAUDE_PROJECT_DIR: dir },
  );
}

// ── Inert / fail open ────────────────────────────────────────────────────────

test("no state file: silent", () => {
  const dir = makeProject(null);
  const r = bash(dir, "git reset --hard");
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout, "");
  cleanup(dir);
});

test("no state file, walk-up from cwd finds none: silent", () => {
  const dir = makeProject(null);
  const r = runHook(
    {
      tool_name: "Bash",
      tool_input: { command: "git reset --hard" },
      cwd: dir,
    },
    { CLAUDE_PROJECT_DIR: "" },
  );
  assert.strictEqual(r.stdout, "");
  cleanup(dir);
});

test("TONONE_GUARD=off and TONONE_APEX_GUARD=off: silent", () => {
  const dir = makeProject({ careful: true });
  for (const k of ["TONONE_GUARD", "TONONE_APEX_GUARD"]) {
    const r = runHook(
      {
        tool_name: "Bash",
        tool_input: { command: "git reset --hard" },
        cwd: dir,
        session_id: "s1",
      },
      { CLAUDE_PROJECT_DIR: dir, [k]: "off" },
    );
    assert.strictEqual(r.status, 0);
    assert.strictEqual(r.stdout, "");
  }
  cleanup(dir);
});

test("malformed input: exit 0, silent", () => {
  const dir = makeProject({ careful: true });
  for (const raw of ["", "not json", "{", "null", "[]", '{"tool_name":5}']) {
    const r = runHook(raw, { CLAUDE_PROJECT_DIR: dir });
    assert.strictEqual(r.status, 0);
    assert.strictEqual(r.stdout, "");
  }
  cleanup(dir);
});

test("malformed state file: exit 0, silent", () => {
  const dir = makeProject(null);
  fs.writeFileSync(path.join(dir, ".claude", "tonone-guard.json"), "{nope");
  const r = bash(dir, "git reset --hard");
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout, "");
  cleanup(dir);
});

test("--check flag works", () => {
  const dir = makeProject({ careful: true });
  const r = spawnSync(
    "node",
    [
      HOOK,
      "--check",
      JSON.stringify({
        tool_name: "Bash",
        tool_input: { command: "git reset --hard" },
        cwd: dir,
        session_id: "s1",
      }),
    ],
    {
      encoding: "utf8",
      env: { ...process.env, CLAUDE_PROJECT_DIR: dir, TONONE_GUARD: "" },
    },
  );
  assert.strictEqual(decision(r), "ask");
  cleanup(dir);
});

// ── Careful: ask ─────────────────────────────────────────────────────────────

const ASK = [
  "rm -rf src",
  "rm -fr ./data",
  "rm -r build/../important",
  "sudo rm -rf /var/lib/foo",
  "git push --force origin main",
  "git push -f",
  "git push origin main --force",
  "git reset --hard HEAD~3",
  "git clean -fd",
  "git checkout -- .",
  "git checkout .",
  "git restore .",
  "git branch -D feature",
  'psql -c "DROP TABLE users"',
  'psql -c "drop database prod"',
  'mysql -e "TRUNCATE users"',
  'psql -c "truncate table users"',
  'psql -c "DELETE FROM users"',
  'psql -c "DELETE FROM users;"',
  "kubectl delete pod foo",
  "kubectl -n prod delete deployment api",
  "terraform destroy",
  "docker system prune -af",
  "docker volume rm pgdata",
  "chmod -R 777 /srv",
  "dd if=x.img of=/dev/loop0",
  "mkfs.ext4 /dev/loop0",
  "echo hi && rm -rf src",
];

for (const cmd of ASK) {
  test(`careful ask: ${cmd}`, () => {
    const dir = makeProject({ careful: true });
    const r = bash(dir, cmd);
    assert.strictEqual(r.status, 0);
    assert.strictEqual(decision(r), "ask", r.stdout);
    const out = JSON.parse(r.stdout).hookSpecificOutput;
    assert.strictEqual(out.hookEventName, "PreToolUse");
    assert.match(out.permissionDecisionReason, /^apex-guard: /);
    cleanup(dir);
  });
}

// ── Careful: not flagged ─────────────────────────────────────────────────────

const QUIET = [
  "git push --force-with-lease origin main",
  "git push origin main",
  "git status",
  "git clean -n",
  "git restore --staged .",
  "git checkout ./file.txt",
  "git checkout -b feature",
  "git branch -d merged",
  "rm file.txt",
  "rm -f file.txt",
  'psql -c "DELETE FROM users WHERE id = 1"',
  'psql -c "SELECT * FROM users"',
  "kubectl get pods",
  "terraform plan",
  "chmod 755 script.sh",
  "chmod -R 755 dir",
  "dd if=/dev/zero of=/dev/null count=1",
  "truncate -s 0 app.log",
  "ls -la",
];

for (const cmd of QUIET) {
  test(`careful quiet: ${cmd}`, () => {
    const dir = makeProject({ careful: true });
    const r = bash(dir, cmd);
    assert.strictEqual(r.status, 0);
    assert.strictEqual(r.stdout, "", `unexpected output for: ${cmd}`);
    cleanup(dir);
  });
}

test("known false positive: destructive text inside a quoted commit message still asks", () => {
  const dir = makeProject({ careful: true });
  assert.strictEqual(
    decision(bash(dir, 'git commit -m "docs: mention git reset --hard"')),
    "ask",
  );
  cleanup(dir);
});

test("artifact rm exempt when every target is an artifact dir", () => {
  const dir = makeProject({ careful: true });
  for (const cmd of [
    "rm -rf node_modules",
    "rm -rf node_modules dist build",
    "rm -rf ./dist/",
    "rm -rf packages/web/.next",
    "rm -rf target __pycache__ .cache coverage",
  ]) {
    assert.strictEqual(bash(dir, cmd).stdout, "", cmd);
  }
  cleanup(dir);
});

test("artifact rm not exempt when mixed with other targets or odd paths", () => {
  const dir = makeProject({ careful: true });
  for (const cmd of [
    "rm -rf node_modules src",
    "rm -rf /node_modules",
    "rm -rf dist/*",
    "rm -rf $X/dist",
  ]) {
    assert.strictEqual(decision(bash(dir, cmd)), "ask", cmd);
  }
  cleanup(dir);
});

// ── Careful: deny ────────────────────────────────────────────────────────────

const DENY = [
  "rm -rf /",
  "rm -rf /*",
  "rm -rf ~",
  "rm -rf ~/",
  "rm -rf $HOME",
  'rm -rf "$HOME"',
  "rm -rf ${HOME}/",
  "sudo rm -rf --no-preserve-root /",
  "rm -r /",
  ":(){ :|:& };:",
  "mkfs.ext4 /dev/sda1",
  "dd if=/dev/zero of=/dev/sda bs=1M",
  "dd if=x.iso of=/dev/disk2",
  "echo ok; rm -rf /",
];

for (const cmd of DENY) {
  test(`careful deny: ${cmd}`, () => {
    const dir = makeProject({ careful: true });
    const r = bash(dir, cmd);
    assert.strictEqual(r.status, 0);
    assert.strictEqual(decision(r), "deny", r.stdout);
    cleanup(dir);
  });
}

// ── Freeze ───────────────────────────────────────────────────────────────────

test("freeze: edit inside frozen dir allowed, outside denied", () => {
  const dir = makeProject(null);
  const frozen = path.join(dir, "src");
  fs.mkdirSync(frozen);
  fs.writeFileSync(
    path.join(dir, ".claude", "tonone-guard.json"),
    JSON.stringify({
      version: 1,
      careful: false,
      freeze: frozen,
      session_id: "s1",
      armed_at: new Date().toISOString(),
    }),
  );
  assert.strictEqual(edit(dir, path.join(frozen, "a.js")).stdout, "");
  assert.strictEqual(
    edit(dir, path.join(frozen, "deep/new/dir/a.js"), "Write").stdout,
    "",
  );
  assert.strictEqual(
    edit(dir, path.join(frozen, "a.js"), "MultiEdit").stdout,
    "",
  );
  const out = edit(dir, path.join(dir, "README.md"));
  assert.strictEqual(decision(out), "deny");
  assert.match(out.stdout, /outside frozen dir/);
  assert.strictEqual(
    decision(edit(dir, path.join(dir, "x.js"), "Edit")),
    "deny",
  );
  cleanup(dir);
});

test("freeze: prefix-sibling dir denied", () => {
  const dir = makeProject(null);
  const frozen = path.join(dir, "src");
  fs.mkdirSync(frozen);
  fs.mkdirSync(path.join(dir, "src-other"));
  fs.writeFileSync(
    path.join(dir, ".claude", "tonone-guard.json"),
    JSON.stringify({
      version: 1,
      careful: false,
      freeze: frozen,
      session_id: "s1",
      armed_at: new Date().toISOString(),
    }),
  );
  assert.strictEqual(
    decision(edit(dir, path.join(dir, "src-other", "a.js"))),
    "deny",
  );
  assert.strictEqual(decision(edit(dir, path.join(dir, "srcx"))), "deny");
  cleanup(dir);
});

test("freeze: relative paths resolve against cwd, .. escapes denied", () => {
  const dir = makeProject(null);
  const frozen = path.join(dir, "src");
  fs.mkdirSync(frozen);
  fs.writeFileSync(
    path.join(dir, ".claude", "tonone-guard.json"),
    JSON.stringify({
      version: 1,
      careful: false,
      freeze: frozen,
      session_id: "s1",
      armed_at: new Date().toISOString(),
    }),
  );
  assert.strictEqual(
    edit(dir, "lib/a.js", "Write", { cwd: frozen }).stdout,
    "",
  );
  assert.strictEqual(decision(edit(dir, "README.md")), "deny");
  assert.strictEqual(
    decision(edit(dir, "../README.md", "Write", { cwd: frozen })),
    "deny",
  );
  assert.strictEqual(decision(edit(dir, "src/../README.md")), "deny");
  cleanup(dir);
});

test("freeze: symlink escaping the frozen dir is denied", () => {
  const dir = makeProject(null);
  const frozen = path.join(dir, "src");
  fs.mkdirSync(frozen);
  fs.mkdirSync(path.join(dir, "outside"));
  fs.symlinkSync(path.join(dir, "outside"), path.join(frozen, "link"));
  fs.writeFileSync(
    path.join(dir, ".claude", "tonone-guard.json"),
    JSON.stringify({
      version: 1,
      careful: false,
      freeze: frozen,
      session_id: "s1",
      armed_at: new Date().toISOString(),
    }),
  );
  assert.strictEqual(
    decision(edit(dir, path.join(frozen, "link", "a.js"))),
    "deny",
  );
  cleanup(dir);
});

test("freeze: NotebookEdit uses notebook_path", () => {
  const dir = makeProject(null);
  const frozen = path.join(dir, "src");
  fs.mkdirSync(frozen);
  fs.writeFileSync(
    path.join(dir, ".claude", "tonone-guard.json"),
    JSON.stringify({
      version: 1,
      careful: false,
      freeze: frozen,
      session_id: "s1",
      armed_at: new Date().toISOString(),
    }),
  );
  const mk = (p) =>
    runHook(
      {
        tool_name: "NotebookEdit",
        tool_input: { notebook_path: p },
        cwd: dir,
        session_id: "s1",
      },
      { CLAUDE_PROJECT_DIR: dir },
    );
  assert.strictEqual(mk(path.join(frozen, "n.ipynb")).stdout, "");
  assert.strictEqual(decision(mk(path.join(dir, "n.ipynb"))), "deny");
  cleanup(dir);
});

test("freeze-only: Bash not affected, even destructive", () => {
  const dir = makeProject({ careful: false, freeze: "/tmp/somewhere" });
  assert.strictEqual(bash(dir, "rm -rf src").stdout, "");
  assert.strictEqual(bash(dir, "echo x > /etc/foo").stdout, "");
  cleanup(dir);
});

test("careful-only: file edits not affected", () => {
  const dir = makeProject({ careful: true, freeze: null });
  assert.strictEqual(edit(dir, path.join(dir, "anything.js")).stdout, "");
  cleanup(dir);
});

// ── Session binding and expiry ───────────────────────────────────────────────

test("session_id null: first call binds to hook session_id", () => {
  const dir = makeProject({ careful: true, session_id: null });
  const r = bash(dir, "git reset --hard", { session_id: "abc" });
  assert.strictEqual(decision(r), "ask");
  assert.strictEqual(stateOf(dir).session_id, "abc");
  // same session still guarded; leftover tmp files not left behind
  assert.strictEqual(
    decision(bash(dir, "git reset --hard", { session_id: "abc" })),
    "ask",
  );
  assert.deepStrictEqual(
    fs.readdirSync(path.join(dir, ".claude")).filter((f) => f.endsWith(".tmp")),
    [],
  );
  cleanup(dir);
});

test("file bound to a different session is ignored and removed", () => {
  const dir = makeProject({ careful: true, session_id: "old" });
  const r = bash(dir, "git reset --hard", { session_id: "new" });
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout, "");
  assert.strictEqual(
    fs.existsSync(path.join(dir, ".claude", "tonone-guard.json")),
    false,
  );
  cleanup(dir);
});

test("state older than 24h is ignored", () => {
  const old = new Date(Date.now() - 25 * 3600 * 1000).toISOString();
  const dir = makeProject({ careful: true, armed_at: old });
  assert.strictEqual(bash(dir, "git reset --hard").stdout, "");
  cleanup(dir);
});

test("state with armed_at just inside 24h is live", () => {
  const recent = new Date(Date.now() - 23 * 3600 * 1000).toISOString();
  const dir = makeProject({ careful: true, armed_at: recent });
  assert.strictEqual(decision(bash(dir, "git reset --hard")), "ask");
  cleanup(dir);
});

test("walk-up from nested cwd finds state file when CLAUDE_PROJECT_DIR unset", () => {
  const dir = makeProject({ careful: true });
  const nested = path.join(dir, "a", "b", "c");
  fs.mkdirSync(nested, { recursive: true });
  const r = runHook(
    {
      tool_name: "Bash",
      tool_input: { command: "git reset --hard" },
      cwd: nested,
      session_id: "s1",
    },
    { CLAUDE_PROJECT_DIR: "" },
  );
  assert.strictEqual(decision(r), "ask");
  cleanup(dir);
});

// ── opt-in metrics (TONONE_METRICS=on) ───────────────────────────────────────
function guardRun(dir, command, metrics) {
  return runHook(
    {
      tool_name: "Bash",
      tool_input: { command },
      cwd: dir,
      session_id: "s1",
    },
    { CLAUDE_PROJECT_DIR: dir, TONONE_METRICS: metrics },
  );
}

test("metrics: on writes ask/deny events with rule ids, output unchanged", () => {
  const dir = makeProject({ careful: true });
  const off = guardRun(dir, "git reset --hard", "");
  const on = guardRun(dir, "git reset --hard", "on");
  assert.strictEqual(on.stdout, off.stdout);
  guardRun(dir, "dd if=/dev/zero of=/dev/sda", "on");
  const lines = fs
    .readFileSync(path.join(dir, ".tonone", "metrics.jsonl"), "utf8")
    .trim()
    .split("\n")
    .map((l) => JSON.parse(l));
  assert.strictEqual(lines.length, 2);
  assert.strictEqual(lines[0].tool, "apex-guard");
  assert.strictEqual(lines[0].event, "ask");
  assert.deepStrictEqual(lines[0].rules, ["git-reset-hard"]);
  assert.strictEqual(lines[1].event, "deny");
  assert.ok(!JSON.stringify(lines).includes("/dev/sda"));
  cleanup(dir);
});

test("metrics: nothing written when off or not exactly 'on'", () => {
  const dir = makeProject({ careful: true });
  for (const v of ["", "off", "1", "ON"]) guardRun(dir, "git reset --hard", v);
  assert.ok(!fs.existsSync(path.join(dir, ".tonone")));
  cleanup(dir);
});
