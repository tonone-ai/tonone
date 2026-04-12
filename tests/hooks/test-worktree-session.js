const { test } = require("node:test");
const assert = require("node:assert");
const { execSync, spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../hooks/tonone-worktree-session.js");

function makeTempRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "wt-sess-"));
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

function runHook(cwd) {
  return spawnSync("node", [HOOK], {
    input: "{}",
    encoding: "utf8",
    cwd,
    timeout: 15000,
  });
}

test("not a git repo — exits 0 with git init tip", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "wt-nogit-"));
  try {
    const result = runHook(dir);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /git init/);
  } finally {
    cleanup(dir);
  }
});

test("already in a worktree — exits 0, no WORKTREE_READY", () => {
  const main = makeTempRepo();
  try {
    const wtPath = path.join(main, ".claude", "worktrees", "existing");
    fs.mkdirSync(path.join(main, ".claude", "worktrees"), { recursive: true });
    execSync(`git worktree add "${wtPath}" -b existing`, { cwd: main });
    const result = runHook(wtPath);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.doesNotMatch(result.stdout, /WORKTREE_READY/);
  } finally {
    cleanup(main);
  }
});

test("on main — creates worktree, prints WORKTREE_READY with EnterWorktree call", () => {
  const dir = makeTempRepo();
  try {
    const result = runHook(dir);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /WORKTREE_READY/);
    assert.match(result.stdout, /EnterWorktree/);
    assert.match(result.stdout, /session-\d{8}-\d{6}/);
    // Verify the worktree directory was actually created on disk
    const wtDir = path.join(dir, ".claude", "worktrees");
    const entries = fs.readdirSync(wtDir).filter((e) => e.startsWith("session-"));
    assert.ok(entries.length > 0, "expected a session-* worktree directory");
  } finally {
    cleanup(dir);
  }
});

test("on main — branch rename hint is included in output", () => {
  const dir = makeTempRepo();
  try {
    const result = runHook(dir);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /git branch -m/);
  } finally {
    cleanup(dir);
  }
});
