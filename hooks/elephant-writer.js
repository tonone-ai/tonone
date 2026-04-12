#!/usr/bin/env node
// elephant-writer — PostToolUse hook
// Auto-captures agent completions, git commits, and skill runs to memory files.

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const PLUGIN_ROOT =
  process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..");
const LOCAL_DIR = path.join(PLUGIN_ROOT, ".elephant");
const LOCAL_MEM = path.join(LOCAL_DIR, "memory.md");
const GLOBAL_DIR = path.join(os.homedir(), ".claude", "elephant");
const GLOBAL_MEM = path.join(GLOBAL_DIR, "memory.md");

// Detect repo name from PLUGIN_ROOT
function repoName() {
  return path.basename(PLUGIN_ROOT);
}

// Caveman compression — drop filler, shorten, truncate to ~100 chars
function compress(text) {
  if (!text) return "";
  const drop = /\b(a|an|the|just|really|basically|actually|simply|successfully|I've|I'll|we've|we'll|it's been)\b/gi;
  const shorten = [
    [/\bimplemented\b/gi, "built"],
    [/\bcompleted\b/gi, "done"],
    [/\bcreated\b/gi, "create"],
    [/\bgenerated\b/gi, "gen"],
    [/\bfunctions?\b/gi, "fn"],
  ];
  let out = text.replace(drop, "").replace(/\s{2,}/g, " ").trim();
  for (const [re, rep] of shorten) out = out.replace(re, rep);
  return out.slice(0, 100).trim();
}

// Format timestamp as YYYY-MM-DD HH:MM
function ts() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Prepend a line to a file (create file + dirs if needed)
function prepend(filePath, line) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  let existing = "";
  try {
    existing = fs.readFileSync(filePath, "utf8");
  } catch {}
  const tmp = filePath + ".tmp." + process.pid;
  fs.writeFileSync(tmp, line + "\n" + existing);
  fs.renameSync(tmp, filePath);
}

// Main
let raw = "";
const timeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (c) => (raw += c));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    const data = JSON.parse(raw);
    const tool = data.tool_name || "";
    const inp = data.tool_input || {};
    const out = data.tool_output || {};

    let desc = null;

    if (tool === "Agent") {
      // Only capture completions (not starts)
      const isStart = Boolean(out.agentId) && !out.output;
      if (isStart) process.exit(0);
      desc = inp.description || inp.prompt?.slice(0, 60) || "agent run";
      desc = compress(desc);
    } else if (tool === "Bash") {
      const cmd = inp.command || "";
      if (!cmd.includes("git commit")) process.exit(0);
      // Extract -m message if present
      const mMatch = cmd.match(/-m\s+["']([^"']{1,80})/);
      desc = mMatch ? `commit: ${mMatch[1]}` : `commit: ${compress(cmd.slice(0, 80))}`;
    } else if (tool === "Skill") {
      const skillName = inp.skill || "unknown";
      const args = inp.args ? ` ${inp.args.slice(0, 40)}` : "";
      desc = `ran /${skillName}${args}`;
    } else {
      process.exit(0);
    }

    if (!desc) process.exit(0);

    const stamp = ts();
    const localLine = `${stamp} : ${desc}`;
    const repo = repoName();
    const globalLine = `${stamp} : ${repo} : ${desc}`;

    prepend(LOCAL_MEM, localLine);
    prepend(GLOBAL_MEM, globalLine);
  } catch {
    // Silent fail
  }
});
