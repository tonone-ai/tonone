const { test } = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../hooks/tonone-pr-attribution.js");

function runHook(input, cwd) {
  return spawnSync("node", [HOOK], {
    input: JSON.stringify(input),
    encoding: "utf8",
    cwd,
    timeout: 5000,
  });
}

function makeTempDir(agents) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "pr-attr-"));
  fs.mkdirSync(path.join(dir, ".claude"), { recursive: true });
  if (agents && agents.length > 0) {
    fs.writeFileSync(path.join(dir, ".claude", "session-agents"), agents.join("\n") + "\n");
  }
  return dir;
}

function cleanup(dir) {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
}

// Load formatAttribution for pure function tests
const hook = require(HOOK);

test("formatAttribution — single agent, title-cased, includes tonone link", () => {
  const line = hook.formatAttribution(["spine"]);
  assert.ok(line.includes("Spine"), line);
  assert.ok(line.includes("https://second.tonone.ai"), line);
  assert.ok(line.includes("[tonone]"), line);
});

test("formatAttribution — multiple agents, alphabetical, title-cased", () => {
  const line = hook.formatAttribution(["warden", "spine", "proof"]);
  assert.ok(line.includes("Proof · Spine · Warden"), line);
});

test("formatAttribution — more than 5 agents, truncated with count", () => {
  const line = hook.formatAttribution(["apex", "atlas", "forge", "lens", "proof", "spine", "warden"]);
  assert.ok(line.includes("and 2 more"), line);
});

test("formatAttribution — empty agents list, minimal attribution with link", () => {
  const line = hook.formatAttribution([]);
  assert.ok(line.includes("[tonone]"), line);
  assert.ok(line.includes("https://second.tonone.ai"), line);
});

test("non gh-pr-create command — exits 0, session-agents not cleared", () => {
  const dir = makeTempDir(["spine"]);
  try {
    const result = runHook(
      { tool_name: "Bash", tool_input: { command: "git status" }, tool_output: {} },
      dir
    );
    assert.strictEqual(result.status, 0, result.stderr);
    // session-agents file should still exist (not cleared)
    assert.ok(fs.existsSync(path.join(dir, ".claude", "session-agents")));
  } finally {
    cleanup(dir);
  }
});

test("gh pr create — session-agents cleared after run (regardless of gh success)", () => {
  const dir = makeTempDir(["spine", "warden"]);
  try {
    runHook(
      {
        tool_name: "Bash",
        tool_input: { command: "gh pr create --title test --body test" },
        tool_output: { output: "https://github.com/owner/repo/pull/1" },
      },
      dir
    );
    // session-agents should be cleared regardless of gh success/failure
    const content = fs.existsSync(path.join(dir, ".claude", "session-agents"))
      ? fs.readFileSync(path.join(dir, ".claude", "session-agents"), "utf8")
      : "";
    assert.strictEqual(content.trim(), "", `expected empty session-agents, got: ${content}`);
  } finally {
    cleanup(dir);
  }
});

test("malformed JSON input — exits 0 silently", () => {
  const result = spawnSync("node", [HOOK], {
    input: "not-json",
    encoding: "utf8",
    timeout: 5000,
  });
  assert.strictEqual(result.status, 0);
});
