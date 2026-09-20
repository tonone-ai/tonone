#!/usr/bin/env node
"use strict";

// warden-guard — PreToolUse hook (Edit, Write, Bash)
//
// Reads the pending tool input, scans the text that is about to land for a
// small set of high-signal security patterns, and prints a short advisory.
//
// It never blocks. A security hook that stops a legitimate edit gets
// uninstalled the same day, and an uninstalled hook protects nothing, so the
// contract is: warn, exit 0, always. Every error path also exits 0.
//
// The rule set lives in rules.json next to this file — rules are data, so a
// new pattern never requires touching this file.
//
// Suppression:
//   - `warden-guard: ignore` on the offending line or the line above it
//   - `warden-guard: off` anywhere in the scanned text
//   - TONONE_GUARD=off (also 0, false, no) in the environment
//
// Manual use:
//   node warden-guard.js --scan path/to/file.js
//   echo '<hook json>' | node warden-guard.js
//
// Tuning — the tradeoff, stated plainly:
//
// False positives are the real risk. Every rule here is deliberately biased
// towards missing a real issue rather than flagging a clean line, because the
// cost of a miss is one unflagged edit while the cost of noise is the hook
// being switched off. Concretely:
//
//   - Rules are anchored on a sink, never on a keyword alone. `innerHTML`
//     only counts when something is assigned to it; `SELECT` only counts
//     inside a string that is also being concatenated.
//   - A secret must clear a shape test and an entropy floor as well as a name
//     match, so `token = "replace-this-before-deploy"` stays quiet. Entropy
//     alone is not enough: per-character entropy cannot separate a key from a
//     hyphenated English phrase, and any floor low enough to catch a short
//     real key also passes `"hue-token": "user-invocable-only"` (3.72 bits).
//     So a value made only of alphabetic words joined by `-`, `_`, `.` or a
//     space is rejected before entropy is consulted.
//   - A long exclusion list (placeholders, env reads, secret managers,
//     sanitizers, parameterized queries, --force-with-lease) suppresses the
//     shapes that look risky and are not.
//   - Rules are scoped by file extension, so prose and config are not scanned
//     with code rules.
//   - One finding per rule and five findings per advisory. This is a nudge,
//     not a report; `/warden-scan` is where a full audit belongs.
//
// Measured on this repository by sweeping every file with a scanned extension
// (.git, node_modules and virtualenvs excluded; .claude and .vscode included):
// 3 findings across 1735 files, of which two are genuine interpolated shell
// commands in tests/hooks/ and one is a sample AWS key inside an editor cache.
// Tests assert silence on hooks/, lib/ and scripts/, and any new rule is
// expected to keep that corpus silent. Re-run the sweep after touching a rule
// rather than trusting this number.

const fs = require("fs");
const path = require("path");

// ── Limits ───────────────────────────────────────────────────────────────────

const RULES_PATH = path.join(__dirname, "rules.json");
const STDIN_TIMEOUT_MS = 3000;
const MAX_BYTES = 2 * 1024 * 1024; // ignore anything past 2 MB
const MAX_LINES = 20000; // ignore anything past 20k lines
const MAX_LINE_CHARS = 2000; // skip minified/bundled lines
const MAX_FINDINGS = 5; // advisory, not a report

const SUPPRESS_LINE = /warden-guard:\s*ignore|warden-guard-ignore/i;
const SUPPRESS_FILE = /warden-guard:\s*off/i;

const SEVERITY_LABEL = {
  CRITICAL: "■ CRITICAL",
  WARNING: "▲ WARNING ",
  INFO: "● INFO    ",
};
const SEVERITY_RANK = { CRITICAL: 0, WARNING: 1, INFO: 2 };

// Extensions treated as shell, so shell rules also apply to file content.
const SHELL_EXT = new Set(["sh", "bash", "zsh", "ksh", "bats"]);

// ── Rule loading ─────────────────────────────────────────────────────────────

const MACRO_PASSES = 4; // macros may reference macros; bounded to stop cycles

function expandMacros(pattern, macros) {
  let out = String(pattern);
  for (let pass = 0; pass < MACRO_PASSES; pass++) {
    const next = out.replace(/\{\{([A-Z0-9_]+)\}\}/g, (whole, key) =>
      Object.prototype.hasOwnProperty.call(macros, key) ? macros[key] : whole,
    );
    if (next === out) break;
    out = next;
  }
  return out;
}

// A pattern may opt in or out of case-insensitivity on its own with a leading
// `(?i)` or `(?-i)`, so one rule can hold a case-sensitive test next to a
// case-insensitive exclusion list.
function compileOne(pattern, macros, baseFlags) {
  let source = expandMacros(pattern, macros);
  let flags = baseFlags;
  const modifier = /^\(\?(-?)i\)/.exec(source);
  if (modifier) {
    source = source.slice(modifier[0].length);
    flags =
      modifier[1] === "-"
        ? flags.replace("i", "")
        : flags.includes("i")
          ? flags
          : flags + "i";
  }
  return new RegExp(source, flags);
}

function compileList(list, macros, flags) {
  if (!Array.isArray(list) || list.length === 0) return null;
  return list.map((p) => compileOne(p, macros, flags));
}

// Returns a compiled rule array. Any rule that fails to compile is dropped —
// a malformed rule must never take the hook down.
function loadRules(rulesPath) {
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(rulesPath || RULES_PATH, "utf8"));
  } catch {
    return [];
  }
  const macros = (raw && raw.macros) || {};
  const rules = Array.isArray(raw && raw.rules) ? raw.rules : [];
  const compiled = [];
  for (const rule of rules) {
    try {
      if (!rule || !rule.id) continue;
      const flags = rule.i ? "i" : "";
      const entry = {
        id: String(rule.id),
        title: String(rule.title || rule.id),
        severity: SEVERITY_LABEL[rule.severity] ? rule.severity : "WARNING",
        advice: String(rule.advice || ""),
        targets: Array.isArray(rule.targets) ? rule.targets : ["code"],
        ext: Array.isArray(rule.ext) ? new Set(rule.ext) : null,
        needle: Array.isArray(rule.needle)
          ? rule.needle.map((n) => String(n).toLowerCase())
          : null,
        all: compileList(rule.all, macros, flags),
        any: compileList(rule.any, macros, flags),
        none: compileList(rule.none, macros, flags),
        capture: null,
      };
      if (rule.capture && rule.capture.pattern) {
        entry.capture = {
          re: compileOne(rule.capture.pattern, macros, flags),
          group: rule.capture.group || 1,
          minEntropy: Number(rule.capture.minEntropy) || 0,
          reject: compileList(rule.capture.reject, macros, flags),
        };
      }
      if (!entry.all && !entry.any) continue; // a rule with no test matches all
      compiled.push(entry);
    } catch {
      // Drop the broken rule, keep the rest.
    }
  }
  return compiled;
}

// ── Heuristics ───────────────────────────────────────────────────────────────

// Shannon entropy in bits per character. A floor on repetitive filler such as
// "aaaaaaaaaaaaaaaa" or "abababababababab". It is not a word detector — an
// English phrase scores as high as a key — so word-shaped values are excluded
// by the rule's `capture.reject` list, not by this number.
function shannonEntropy(str) {
  if (!str) return 0;
  const freq = Object.create(null);
  for (const ch of str) freq[ch] = (freq[ch] || 0) + 1;
  let entropy = 0;
  for (const key of Object.keys(freq)) {
    const p = freq[key] / str.length;
    entropy -= p * Math.log2(p);
  }
  return entropy;
}

// The `ext` allowlist scopes a rule to a set of file types, so it only has
// meaning when the text came from a file. A Bash command has no extension, and
// a shell rule must still fire there.
function ruleApplies(rule, mode, ext) {
  if (!rule.targets.includes(mode)) return false;
  if (mode === "code" && rule.ext && !(ext && rule.ext.has(ext))) return false;
  return true;
}

function ruleMatchesLine(rule, line) {
  if (rule.all && !rule.all.every((re) => re.test(line))) return false;
  if (rule.any && !rule.any.some((re) => re.test(line))) return false;
  if (rule.none && rule.none.some((re) => re.test(line))) return false;
  if (rule.capture) {
    const m = rule.capture.re.exec(line);
    if (!m) return false;
    const value = m[rule.capture.group] || "";
    // Shape first, entropy second. Per-character entropy cannot tell a key
    // from a hyphenated English phrase — "user-invocable-only" scores 3.72
    // bits, above any floor low enough to still catch a short real key — so
    // the value must also not look like words before entropy gets a vote.
    if (rule.capture.reject && rule.capture.reject.some((re) => re.test(value)))
      return false;
    if (shannonEntropy(value) < rule.capture.minEntropy) return false;
  }
  return true;
}

function extensionOf(filePath) {
  if (!filePath || typeof filePath !== "string") return null;
  const base = path.basename(filePath);
  const dot = base.lastIndexOf(".");
  if (dot <= 0 || dot === base.length - 1) return null;
  return base.slice(dot + 1).toLowerCase();
}

// ── Scanner ──────────────────────────────────────────────────────────────────

/**
 * Scan a block of text.
 *
 * @param {string} text        content about to land
 * @param {object} opts        { mode: "code"|"shell", ext: string|null, rules }
 * @returns {Array<{id,title,severity,advice,line,excerpt}>}
 */
function scanText(text, opts) {
  const options = opts || {};
  if (typeof text !== "string" || text.length === 0) return [];
  if (text.length > MAX_BYTES) return [];
  if (SUPPRESS_FILE.test(text)) return [];

  const rules = options.rules || loadRules();
  if (rules.length === 0) return [];

  const ext = options.ext || null;
  const modes = [options.mode === "shell" ? "shell" : "code"];
  if (ext && SHELL_EXT.has(ext) && !modes.includes("shell"))
    modes.push("shell");

  const active = rules.filter((rule) =>
    modes.some((mode) => ruleApplies(rule, mode, ext)),
  );
  if (active.length === 0) return [];

  // Cheap whole-text prefilter: a rule with declared needles only runs when at
  // least one needle is present. This is what keeps large files fast.
  const haystack = text.toLowerCase();
  const candidates = active.filter(
    (rule) => !rule.needle || rule.needle.some((n) => haystack.includes(n)),
  );
  if (candidates.length === 0) return [];

  const lines = text.split("\n", MAX_LINES);
  const findings = [];
  const seen = new Set();

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line || line.length > MAX_LINE_CHARS) continue;
    if (SUPPRESS_LINE.test(line)) continue;
    if (i > 0 && SUPPRESS_LINE.test(lines[i - 1])) continue;

    for (const rule of candidates) {
      if (seen.has(rule.id)) continue; // one finding per rule, first hit wins
      if (!ruleMatchesLine(rule, line)) continue;
      seen.add(rule.id);
      findings.push({
        id: rule.id,
        title: rule.title,
        severity: rule.severity,
        advice: rule.advice,
        line: i + 1,
        excerpt: line.trim().slice(0, 80),
      });
    }
    if (seen.size === candidates.length) break;
  }

  findings.sort(
    (a, b) =>
      SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] || a.line - b.line,
  );
  return findings;
}

// ── Tool input → scan candidates ─────────────────────────────────────────────

/**
 * Turn a PreToolUse payload into the list of things worth scanning.
 * @returns {Array<{label,text,mode,ext,positional}>}
 */
function candidatesFrom(data) {
  const out = [];
  if (!data || typeof data !== "object") return out;
  const tool = data.tool_name;
  const input = data.tool_input || {};

  if (tool === "Bash") {
    const command = typeof input.command === "string" ? input.command : "";
    if (command)
      out.push({
        label: "command",
        text: command,
        mode: "shell",
        ext: null,
        positional: true,
      });
    return out;
  }

  if (tool === "Write") {
    const content = typeof input.content === "string" ? input.content : "";
    const file = typeof input.file_path === "string" ? input.file_path : "file";
    if (content) {
      out.push({
        label: file,
        text: content,
        mode: "code",
        ext: extensionOf(file),
        positional: true,
      });
    }
    return out;
  }

  if (tool === "Edit" || tool === "MultiEdit") {
    const file = typeof input.file_path === "string" ? input.file_path : "file";
    const ext = extensionOf(file);
    const chunks = [];
    if (typeof input.new_string === "string") chunks.push(input.new_string);
    if (Array.isArray(input.edits)) {
      for (const edit of input.edits) {
        if (edit && typeof edit.new_string === "string")
          chunks.push(edit.new_string);
      }
    }
    const text = chunks.join("\n");
    if (text) {
      out.push({ label: file, text, mode: "code", ext, positional: false });
    }
    return out;
  }

  return out;
}

// ── Advisory rendering ───────────────────────────────────────────────────────

function formatAdvisory(label, findings, positional) {
  if (!findings || findings.length === 0) return "";
  const shown = findings.slice(0, MAX_FINDINGS);
  const where = positional ? "line" : "new line";
  const lines = [
    `[warden-guard] ${findings.length} risky pattern${findings.length === 1 ? "" : "s"} in ${label}`,
  ];
  for (const f of shown) {
    lines.push(
      `  ${SEVERITY_LABEL[f.severity]}  ${f.title} (${where} ${f.line}) — ${f.advice}`,
    );
  }
  if (findings.length > shown.length) {
    lines.push(`  ...and ${findings.length - shown.length} more`);
  }
  lines.push(
    "  Advisory only, nothing blocked. Suppress with `warden-guard: ignore` on the line, or TONONE_GUARD=off.",
  );
  return lines.join("\n");
}

function guardDisabled(env) {
  const value = String((env || {}).TONONE_GUARD || "")
    .trim()
    .toLowerCase();
  return (
    value === "off" || value === "0" || value === "false" || value === "no"
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────

function runCli(argv) {
  const scanIndex = argv.indexOf("--scan");
  if (scanIndex === -1) return false;
  const target = argv[scanIndex + 1];
  if (!target) return true;
  let text = "";
  try {
    text = fs.readFileSync(target, "utf8");
  } catch {
    return true;
  }
  const ext = extensionOf(target);
  const mode = ext && SHELL_EXT.has(ext) ? "shell" : "code";
  const findings = scanText(text, { mode, ext });
  const advisory = formatAdvisory(target, findings, true);
  if (advisory) process.stdout.write(advisory + "\n");
  return true;
}

function main() {
  if (guardDisabled(process.env)) process.exit(0);
  if (runCli(process.argv.slice(2))) return;

  let input = "";
  const timer = setTimeout(() => process.exit(0), STDIN_TIMEOUT_MS);
  process.stdin.setEncoding("utf8");
  process.stdin.on("error", () => process.exit(0));
  process.stdin.on("data", (chunk) => {
    input += chunk;
    if (input.length > MAX_BYTES) {
      clearTimeout(timer);
      process.exit(0);
    }
  });
  process.stdin.on("end", () => {
    clearTimeout(timer);
    try {
      const data = JSON.parse(input);
      const rules = loadRules();
      const blocks = [];
      for (const candidate of candidatesFrom(data)) {
        const findings = scanText(candidate.text, {
          mode: candidate.mode,
          ext: candidate.ext,
          rules,
        });
        const advisory = formatAdvisory(
          candidate.label,
          findings,
          candidate.positional,
        );
        if (advisory) blocks.push(advisory);
      }
      if (blocks.length > 0) {
        const message = blocks.join("\n");
        process.stderr.write(message + "\n");
        process.stdout.write(
          JSON.stringify({
            systemMessage: message,
            hookSpecificOutput: {
              hookEventName: "PreToolUse",
              additionalContext: message,
            },
          }) + "\n",
        );
      }
    } catch {
      // Silent fail — never interrupt the session.
    }
    process.exit(0);
  });
}

module.exports = {
  loadRules,
  expandMacros,
  scanText,
  candidatesFrom,
  formatAdvisory,
  shannonEntropy,
  extensionOf,
  guardDisabled,
};

if (require.main === module) main();
