#!/usr/bin/env node
// tonone-session-tracker — PostToolUse Skill hook
// Tracks which tonone agents were invoked in this session.
// Appends agent name to .claude/session-agents for PR attribution.

"use strict";

const fs = require("fs");
const path = require("path");

const TONONE_AGENTS = new Set([
  "apex", "forge", "relay", "spine", "flux", "warden", "vigil",
  "prism", "cortex", "touch", "volt", "atlas", "lens", "proof",
  "pave", "helm", "echo", "lumen", "draft", "form", "crest",
  "pitch", "surge",
]);

const SESSION_FILE = path.join(".claude", "session-agents");

function appendAgent(agentName) {
  // Read existing agents
  let existing = new Set();
  try {
    const content = fs.readFileSync(SESSION_FILE, "utf8");
    content.trim().split("\n").filter(Boolean).forEach(l => existing.add(l));
  } catch {}

  if (existing.has(agentName)) return; // Already tracked

  existing.add(agentName);

  // Atomic write
  fs.mkdirSync(path.dirname(SESSION_FILE), { recursive: true });
  const tmp = SESSION_FILE + ".tmp." + process.pid;
  fs.writeFileSync(tmp, [...existing].join("\n") + "\n");
  fs.renameSync(tmp, SESSION_FILE);
}

let input = "";
const timeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    const data = JSON.parse(input);

    if (data.tool_name !== "Skill") process.exit(0);

    const skillName = (data.tool_input && data.tool_input.skill) || "";
    if (!skillName) process.exit(0);

    // Extract agent name: "spine-api" → "spine", "superpowers:brainstorming" → skip
    const base = skillName.includes(":") ? "" : skillName.split("-")[0];
    if (!base || !TONONE_AGENTS.has(base)) process.exit(0);

    appendAgent(base);
  } catch {
    // Silent fail — never block workflow
  }
});
