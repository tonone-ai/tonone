const { test } = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../hooks/tonone-session-tracker.js");

function runHook(input, cwd) {
  return spawnSync("node", [HOOK], {
    input: JSON.stringify(input),
    encoding: "utf8",
    cwd,
    timeout: 5000,
  });
}

function makeTempDir() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "sess-tracker-"));
  fs.mkdirSync(path.join(dir, ".claude"), { recursive: true });
  return dir;
}

function cleanup(dir) {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch {}
}

test("tonone skill — appends agent name to .claude/session-agents", () => {
  const dir = makeTempDir();
  try {
    const result = runHook(
      { tool_name: "Skill", tool_input: { skill: "spine-api" } },
      dir,
    );
    assert.strictEqual(result.status, 0, result.stderr);
    const content = fs.readFileSync(
      path.join(dir, ".claude", "session-agents"),
      "utf8",
    );
    assert.ok(content.includes("spine"), `expected 'spine' in: ${content}`);
  } finally {
    cleanup(dir);
  }
});

test("non-tonone skill — ignored, file not written", () => {
  const dir = makeTempDir();
  try {
    const result = runHook(
      {
        tool_name: "Skill",
        tool_input: { skill: "superpowers:brainstorming" },
      },
      dir,
    );
    assert.strictEqual(result.status, 0, result.stderr);
    const filePath = path.join(dir, ".claude", "session-agents");
    assert.ok(
      !fs.existsSync(filePath),
      "file should not be created for non-tonone skill",
    );
  } finally {
    cleanup(dir);
  }
});

test("same agent invoked twice — deduplication, appears once", () => {
  const dir = makeTempDir();
  try {
    runHook({ tool_name: "Skill", tool_input: { skill: "warden-audit" } }, dir);
    runHook(
      { tool_name: "Skill", tool_input: { skill: "warden-harden" } },
      dir,
    );
    const content = fs.readFileSync(
      path.join(dir, ".claude", "session-agents"),
      "utf8",
    );
    const lines = content.trim().split("\n").filter(Boolean);
    const wardenLines = lines.filter((l) => l === "warden");
    assert.strictEqual(
      wardenLines.length,
      1,
      `expected 1 warden line, got: ${content}`,
    );
  } finally {
    cleanup(dir);
  }
});

test("multiple different agents — all appended", () => {
  const dir = makeTempDir();
  try {
    runHook({ tool_name: "Skill", tool_input: { skill: "spine-api" } }, dir);
    runHook({ tool_name: "Skill", tool_input: { skill: "atlas-map" } }, dir);
    runHook({ tool_name: "Skill", tool_input: { skill: "proof-audit" } }, dir);
    const content = fs.readFileSync(
      path.join(dir, ".claude", "session-agents"),
      "utf8",
    );
    assert.ok(content.includes("spine"), content);
    assert.ok(content.includes("atlas"), content);
    assert.ok(content.includes("proof"), content);
  } finally {
    cleanup(dir);
  }
});

test("non-Skill tool event — exits 0, no file written", () => {
  const dir = makeTempDir();
  try {
    const result = runHook(
      { tool_name: "Bash", tool_input: { command: "ls" } },
      dir,
    );
    assert.strictEqual(result.status, 0, result.stderr);
    assert.ok(!fs.existsSync(path.join(dir, ".claude", "session-agents")));
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
