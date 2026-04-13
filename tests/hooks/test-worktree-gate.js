// tests/hooks/test-worktree-gate.js
const { test } = require("node:test");
const assert = require("node:assert");
const { execSync, spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../hooks/tonone-worktree-gate.js");

function makeTempRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "wt-gate-"));
  execSync("git init", { cwd: dir });
  execSync("git config user.email test@test.com", { cwd: dir });
  execSync("git config user.name Test", { cwd: dir });
  fs.writeFileSync(path.join(dir, "README.md"), "test");
  execSync("git add README.md", { cwd: dir });
  execSync("git commit -m init", { cwd: dir });
  return dir;
}

function cleanup(dir) {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
}

function runHook(cwd, toolName = "Edit", extraInput = {}) {
  const input = JSON.stringify({ tool_name: toolName, tool_input: { file_path: "foo.txt", ...extraInput } });
  return spawnSync("node", [HOOK], {
    input,
    encoding: "utf8",
    cwd,
    timeout: 10000,
  });
}

test("non-edit tool (Bash) — exits 0, no output", () => {
  const dir = makeTempRepo();
  try {
    const result = runHook(dir, "Bash");
    assert.strictEqual(result.status, 0, result.stderr);
    assert.strictEqual(result.stdout.trim(), "");
  } finally {
    cleanup(dir);
  }
});

test("already in a worktree — exits 0, no output", () => {
  const main = makeTempRepo();
  try {
    const wtPath = path.join(main, ".claude", "worktrees", "existing");
    fs.mkdirSync(path.join(main, ".claude", "worktrees"), { recursive: true });
    execSync(`git worktree add "${wtPath}" -b existing`, { cwd: main });
    const result = runHook(wtPath, "Edit");
    assert.strictEqual(result.status, 0, result.stderr);
    assert.strictEqual(result.stdout.trim(), "");
    try { execSync(`git worktree remove --force "${wtPath}"`, { cwd: main }); } catch {}
  } finally {
    cleanup(main);
  }
});

test("skip-worktree marker present and fresh — exits 0", () => {
  const dir = makeTempRepo();
  try {
    fs.mkdirSync(path.join(dir, ".claude"), { recursive: true });
    fs.writeFileSync(path.join(dir, ".claude", "skip-worktree"), "");
    const result = runHook(dir, "Edit");
    assert.strictEqual(result.status, 0, result.stderr);
    assert.strictEqual(result.stdout.trim(), "");
  } finally {
    cleanup(dir);
  }
});

test("writing skip-worktree itself — exits 0 regardless", () => {
  const dir = makeTempRepo();
  try {
    const result = runHook(dir, "Write", { file_path: ".claude/skip-worktree" });
    assert.strictEqual(result.status, 0, result.stderr);
  } finally {
    cleanup(dir);
  }
});

test("on main — exits 1, message contains WORKTREE_REQUIRED and EnterWorktree", () => {
  const dir = makeTempRepo();
  try {
    const result = runHook(dir, "Edit");
    assert.strictEqual(result.status, 1, "should block on main");
    assert.match(result.stdout, /WORKTREE_REQUIRED/);
    assert.match(result.stdout, /EnterWorktree/);
    assert.match(result.stdout, /git worktree add/);
  } finally {
    cleanup(dir);
  }
});

test("on main — message includes skip-worktree opt-out hint", () => {
  const dir = makeTempRepo();
  try {
    const result = runHook(dir, "Write");
    assert.match(result.stdout, /skip-worktree/);
  } finally {
    cleanup(dir);
  }
});
