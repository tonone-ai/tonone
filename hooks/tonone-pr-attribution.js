#!/usr/bin/env node
// tonone-pr-attribution — PostToolUse Bash hook
// Detects `gh pr create`, appends agent credits to the PR description.

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync, spawnSync } = require("child_process");

const SESSION_FILE = path.join(".claude", "session-agents");
const TONONE_URL = "https://second.tonone.ai";
const MAX_AGENTS = 5;

function titleCase(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function formatAttribution(agents) {
  if (!agents || agents.length === 0) {
    return `*— [tonone](${TONONE_URL})*`;
  }
  const sorted = [...agents].sort();
  let names;
  if (sorted.length <= MAX_AGENTS) {
    names = sorted.map(titleCase).join(" · ");
  } else {
    const shown = sorted.slice(0, MAX_AGENTS).map(titleCase).join(" · ");
    const remaining = sorted.length - MAX_AGENTS;
    names = `${shown} and ${remaining} more`;
  }
  return `*${names} — [tonone](${TONONE_URL})*`;
}

function readAgents() {
  try {
    const content = fs.readFileSync(SESSION_FILE, "utf8");
    return [...new Set(content.trim().split("\n").filter(Boolean))];
  } catch {
    return [];
  }
}

function clearAgents() {
  try {
    fs.writeFileSync(SESSION_FILE, "");
  } catch {}
}

function getPrUrl(toolOutput) {
  const raw =
    (toolOutput &&
      (typeof toolOutput === "string" ? toolOutput : toolOutput.output)) ||
    "";
  const urlMatch = String(raw).match(
    /https:\/\/github\.com\/[\w.\-]+\/[\w.\-]+\/pull\/\d+/,
  );
  if (urlMatch) return urlMatch[0];
  try {
    const url = execSync("gh pr view --json url -q .url", {
      encoding: "utf8",
      timeout: 5000,
    }).trim();
    if (url.startsWith("http")) return url;
  } catch {}
  return null;
}

function appendAttribution(prUrl, attributionLine) {
  const tmpFile = path.join(os.tmpdir(), `tonone-pr-body-${process.pid}.md`);
  try {
    const viewResult = spawnSync(
      "gh",
      ["pr", "view", prUrl, "--json", "body", "-q", ".body"],
      { encoding: "utf8", timeout: 5000 },
    );
    const currentBody = (viewResult.stdout || "").trim();
    // Skip if relay-ship already wrote the rich Tonone footer
    if (
      currentBody.includes("tonone.ai") &&
      currentBody.includes("Co-Authored-By: Tonone")
    )
      return;
    const newBody = `${currentBody}\n\n---\n${attributionLine}`;
    fs.writeFileSync(tmpFile, newBody);
    spawnSync("gh", ["pr", "edit", prUrl, "--body-file", tmpFile], {
      timeout: 10000,
    });
  } finally {
    try {
      fs.unlinkSync(tmpFile);
    } catch {}
  }
}

if (require.main !== module) {
  module.exports = { formatAttribution };
  return;
}

let input = "";
const timeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    const data = JSON.parse(input);

    if (data.tool_name !== "Bash") process.exit(0);

    const command = (data.tool_input && data.tool_input.command) || "";
    if (!/\bgh\s+pr\s+create\b/.test(command)) process.exit(0);

    const agents = readAgents();
    const attributionLine = formatAttribution(agents);

    const prUrl = getPrUrl(data.tool_output);
    if (!prUrl) process.exit(0);

    appendAttribution(prUrl, attributionLine);
    clearAgents();
  } catch {
    // Silent fail
  }
});
