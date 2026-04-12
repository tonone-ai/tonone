#!/usr/bin/env node
// elephant-recall — SessionStart hook
// Reads local + global memory, renders a smart recall block.

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const PLUGIN_ROOT =
  process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..");
const LOCAL_MEM = path.join(PLUGIN_ROOT, ".elephant", "memory.md");
const GLOBAL_MEM = path.join(os.homedir(), ".claude", "elephant", "memory.md");
const REPO = path.basename(PLUGIN_ROOT);

// Parse a memory file into entry objects
// Line format: `[!!]? YYYY-MM-DD HH:MM : [repo :] text`
function parseFile(filePath, isGlobal) {
  try {
    const lines = fs.readFileSync(filePath, "utf8").split("\n").filter(Boolean);
    return lines.map((line) => {
      const important = line.startsWith("[!!]");
      const body = important ? line.slice(4).trim() : line.trim();
      // Extract timestamp
      const tsMatch = body.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})/);
      const tsStr = tsMatch ? tsMatch[1] : null;
      const date = tsStr ? new Date(tsStr) : null;
      const rest = tsStr ? body.slice(tsStr.length).replace(/^\s*:\s*/, "") : body;

      let repo = null;
      let text = rest;
      if (isGlobal) {
        // `repo : text`
        const repoMatch = rest.match(/^([^:]+?)\s*:\s*(.+)$/);
        if (repoMatch) {
          repo = repoMatch[1].trim();
          text = repoMatch[2].trim();
        }
      }

      return { important, tsStr, date, repo, text, raw: line };
    });
  } catch {
    return [];
  }
}

function main() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const cutoff7 = new Date(now - 7 * 24 * 60 * 60 * 1000);

  // Local entries (this repo)
  const local = parseFile(LOCAL_MEM, false);

  // Global entries (other repos only)
  const global = parseFile(GLOBAL_MEM, true).filter(
    (e) => e.repo && e.repo !== REPO
  );

  if (local.length === 0 && global.length === 0) {
    console.log(
      "🐘 ELEPHANT RECALL\n└ nothing yet. use /elephant save to start remembering."
    );
    return;
  }

  const lines = [];

  // Local: today in full, last 7 days in full (cap 10), older only [!!]
  const today = local.filter((e) => e.tsStr?.startsWith(todayStr));
  const week = local.filter(
    (e) => !e.tsStr?.startsWith(todayStr) && e.date && e.date >= cutoff7
  );
  const older = local.filter(
    (e) => e.date && e.date < cutoff7 && e.important
  );

  for (const e of today) lines.push(`${e.important ? "[!!] " : ""}${e.tsStr} : ${e.text}`);
  const weekBudget = Math.max(0, 10 - today.length);
  for (const e of week.slice(0, weekBudget)) lines.push(`${e.important ? "[!!] " : ""}${e.tsStr} : ${e.text}`);
  for (const e of older) lines.push(`[!!] ${e.tsStr} : ${e.text}`);

  // Other repos: last 3 entries
  const otherEntries = global.slice(0, 3);
  // Only show other-repos section if there's room (need separator + at least 1 entry)
  const roomForOthers = 15 - lines.length;
  if (otherEntries.length > 0 && roomForOthers >= 2) {
    lines.push("── other repos ──");
    for (const e of otherEntries.slice(0, roomForOthers - 1)) {
      const dateShort = e.tsStr ? e.tsStr.slice(5, 10) : "??-??";
      lines.push(`${e.repo} : ${e.text} (${dateShort})`);
    }
  }

  // Cap at 15 lines
  const capped = lines.slice(0, 15);

  // Footer stats
  const total = local.length;
  const important = local.filter((e) => e.important).length;
  const oldest = local.length
    ? local[local.length - 1].tsStr?.slice(0, 10) || "?"
    : "?";

  // Render
  const body = capped.map((l) => `├ ${l}`);

  console.log("🐘 ELEPHANT RECALL");
  for (const l of body) console.log(l);
  console.log(
    `└ ${total} entries total │ ${important} important │ oldest: ${oldest}`
  );
}

main();
