// tests/hooks/test-worktree-close.js
const { test } = require("node:test");
const assert = require("node:assert");
const { execSync, spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../hooks/tonone-worktree-close.js");

function makeTempRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "wt-close-"));
  execSync("git init", { cwd: dir });
  execSync("git config user.email test@test.com", { cwd: dir });
  execSync("git config user.name Test", { cwd: dir });
  fs.writeFileSync(path.join(dir, "README.md"), "test");
  execSync("git add README.md", { cwd: dir });
  execSync("git commit -m init", { cwd: dir });
  return dir;
}

function makeWorktree(mainRepo, name = "test-branch") {
  const wtPath = path.join(mainRepo, ".claude", "worktrees", name);
  fs.mkdirSync(path.join(mainRepo, ".claude", "worktrees"), { recursive: true });
  execSync(`git worktree add "${wtPath}" -b ${name}`, { cwd: mainRepo });
  return wtPath;
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

test("not in a worktree (main repo) — exits 0, no output", () => {
  const dir = makeTempRepo();
  try {
    const result = runHook(dir);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.strictEqual(result.stdout.trim(), "");
  } finally {
    cleanup(dir);
  }
});

test("clean worktree (no changes) — silent exit, worktree preserved", () => {
  // Stop fires after every turn, not just at session exit. Auto-deleting a clean
  // worktree here would kill it mid-session. Pruning happens at SessionStart instead.
  const dir = makeTempRepo();
  try {
    const wtPath = makeWorktree(dir);
    const result = runHook(wtPath);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.strictEqual(result.stdout.trim(), "", "no output for clean worktree");
    assert.ok(fs.existsSync(wtPath), "clean worktree should be preserved");
    try { execSync(`git worktree remove --force "${wtPath}"`, { cwd: dir }); } catch {}
  } finally {
    cleanup(dir);
  }
});

test("dirty worktree (committed changes) — prints /ship suggestion, keeps worktree", () => {
  const dir = makeTempRepo();
  try {
    const wtPath = makeWorktree(dir);
    fs.writeFileSync(path.join(wtPath, "feature.txt"), "new content");
    execSync("git add feature.txt", { cwd: wtPath });
    execSync('git commit -m "add feature"', { cwd: wtPath });
    const result = runHook(wtPath);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /\/ship/);
    assert.ok(fs.existsSync(wtPath), "worktree should still exist");
    try { execSync(`git worktree remove --force "${wtPath}"`, { cwd: dir }); } catch {}
  } finally {
    cleanup(dir);
  }
});

test("dirty worktree (uncommitted changes) — prints /ship suggestion, keeps worktree", () => {
  const dir = makeTempRepo();
  try {
    const wtPath = makeWorktree(dir);
    fs.writeFileSync(path.join(wtPath, "dirty.txt"), "not staged");
    const result = runHook(wtPath);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /\/ship/);
    assert.ok(fs.existsSync(wtPath), "worktree should still exist");
    try { execSync(`git worktree remove --force "${wtPath}"`, { cwd: dir }); } catch {}
  } finally {
    cleanup(dir);
  }
});
