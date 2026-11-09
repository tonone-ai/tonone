#!/usr/bin/env node
"use strict";
// design-lint — deterministic design linter. Pure Node >=18, zero deps.
//
//   node design-lint.js [paths...] [--json] [--tier immediate|all] [--root DIR]
//
// Exit: 0 clean (or advisory only) / 1 immediate-tier findings / 2 usage error.
// Suppress: `design-lint-disable-next-line <rule>[, rule]` on the line above, or
// .tonone/design.json {"ignoreRules":[{"rule","reason"}],"ignoreFiles":[{"glob","reason"}]}.
// A missing reason warns but is still honored. Read-only; never writes files.

const fs = require("fs");
const path = require("path");
const { EXTS, buildContext, parseColor } = require("./parse");
const { rules } = require("./rules");

const SKIP_DIRS = new Set([
  "node_modules",
  ".git",
  "dist",
  "build",
  ".next",
  ".turbo",
  ".vercel",
  "coverage",
  ".svelte-kit",
  ".nuxt",
]);
const MAX_BYTES = 1024 * 1024;
const SEV_ICON = {
  critical: "■ CRITICAL",
  warning: "▲ WARNING",
  info: "● INFO",
};

// ── glob (** and * and ?) ─────────────────────────────────────────────────────
function globToRegExp(glob) {
  let re = "";
  const g = glob.replace(/\\/g, "/").replace(/^\.\//, "");
  for (let i = 0; i < g.length; i++) {
    const c = g[i];
    if (c === "*") {
      if (g[i + 1] === "*") {
        i++;
        if (g[i + 1] === "/") {
          i++;
          re += "(?:.*/)?";
        } else re += ".*";
      } else re += "[^/]*";
    } else if (c === "?") re += "[^/]";
    else re += c.replace(/[.+^${}()|[\]\\]/g, "\\$&");
  }
  return new RegExp("^" + re + "$");
}

// ── root / config / DESIGN.md ─────────────────────────────────────────────────
function findRoot(start) {
  let dir = path.resolve(start);
  for (let i = 0; i < 20; i++) {
    for (const marker of [
      path.join(".tonone", "design.json"),
      "DESIGN.md",
      ".git",
    ]) {
      if (fs.existsSync(path.join(dir, marker))) return dir;
    }
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return path.resolve(start);
}

function loadConfig(root) {
  const cfg = { ignoreRules: [], ignoreFiles: [], hook: false, warnings: [] };
  let raw;
  try {
    raw = fs.readFileSync(path.join(root, ".tonone", "design.json"), "utf8");
  } catch {
    return cfg;
  }
  let j;
  try {
    j = JSON.parse(raw);
  } catch {
    cfg.warnings.push(".tonone/design.json: invalid JSON, ignored");
    return cfg;
  }
  if (!j || typeof j !== "object") return cfg;
  cfg.hook = j.hook === true;
  const norm = (arr, key, label) => {
    if (!Array.isArray(arr)) return [];
    const out = [];
    for (const e of arr) {
      const o = typeof e === "string" ? { [key]: e } : e;
      if (!o || typeof o[key] !== "string") continue;
      if (!o.reason || !String(o.reason).trim())
        cfg.warnings.push(
          `${label} "${o[key]}" has no reason — add one (honored anyway)`,
        );
      out.push({ [key]: o[key], reason: o.reason || "" });
    }
    return out;
  };
  cfg.ignoreRules = norm(j.ignoreRules, "rule", "ignoreRules");
  cfg.ignoreFiles = norm(j.ignoreFiles, "glob", "ignoreFiles").map((e) => ({
    ...e,
    re: globToRegExp(e.glob),
  }));
  return cfg;
}

function loadDesignMd(root) {
  let text;
  try {
    const f = path.join(root, "DESIGN.md");
    if (fs.statSync(f).size > 512 * 1024) return null;
    text = fs.readFileSync(f, "utf8");
  } catch {
    return null;
  }
  const hex = new Set();
  for (const m of text.matchAll(
    /#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b/g,
  )) {
    let h = m[1].toLowerCase();
    if (h.length <= 4) h = h.replace(/./g, (c) => c + c);
    hex.add(h.slice(0, 6));
  }
  const scale = new Set();
  for (const m of text.matchAll(/(\d*\.?\d+)\s*(px|rem)\b/g)) {
    scale.add(
      Math.round(parseFloat(m[1]) * (m[2] === "rem" ? 16 : 1) * 100) / 100,
    );
  }
  // rgb()/hsl() literals count as sanctioned colors too (docs/design-md.md).
  for (const m of text.matchAll(/\b(?:rgba?|hsla?)\([^)]{5,60}\)/gi)) {
    const c = parseColor(m[0]);
    if (c) {
      const h = (v) => Math.max(0, Math.min(255, v)).toString(16).padStart(2, "0");
      hex.add(h(c.r) + h(c.g) + h(c.b));
    }
  }
  // Format sniff: "unified" = frontmatter + platform sections; "legacy" =
  // pre-unification /form-brief headings. Both parse identically (headings are ignored).
  const format = /^---\r?\n[\s\S]*?\r?\n---/.test(text)
    ? "unified"
    : /^##\s+(Visual Theme|Color Palette)/im.test(text)
      ? "legacy"
      : "unified";
  return { text: text.toLowerCase(), hex, scale, format };
}

// ── core ──────────────────────────────────────────────────────────────────────
// lintSource({file (rel, '/'), src, ext, designMd, config, tier, deadline}) → findings[]
function lintSource(opts) {
  const {
    file,
    src,
    designMd = null,
    config = null,
    tier = "all",
    deadline = Infinity,
  } = opts;
  const ext = opts.ext || path.extname(file).toLowerCase();
  if (!EXTS.has(ext)) return [];
  const ctx = buildContext(file, src, ext);
  ctx.designMd = designMd;
  const srcLines = src.split("\n");
  const ignoredRules = new Set(
    ((config && config.ignoreRules) || []).map((r) => r.rule),
  );
  const findings = [];
  const seen = new Set();
  for (const rule of rules) {
    if (Date.now() > deadline) break;
    if (tier === "immediate" && rule.tier !== "immediate") continue;
    if (!rule.fileTypes.includes(ext) || ignoredRules.has(rule.id)) continue;
    let hits = [];
    try {
      hits = rule.detect(ctx) || [];
    } catch {
      continue; // a broken rule must never break the run
    }
    for (const h of hits) {
      const key = rule.id + ":" + h.line;
      if (seen.has(key)) continue;
      seen.add(key);
      if (isDisabledInline(srcLines, h.line, rule.id)) continue;
      findings.push({
        file,
        line: h.line,
        rule: rule.id,
        tier: rule.tier,
        severity: rule.severity,
        message: h.message || rule.message,
        fix: rule.fix,
      });
    }
  }
  return findings.sort(
    (a, b) => a.line - b.line || a.rule.localeCompare(b.rule),
  );
}

function isDisabledInline(lines, line, rule) {
  const m = /design-lint-disable-next-line\s+([^\n]*?)(?:\*\/|-->|\}\}|$)/.exec(
    lines[line - 2] || "",
  );
  if (!m) return false;
  const ids = m[1].split(/[\s,]+/).filter(Boolean);
  return ids.includes(rule) || ids.includes("all");
}

function isIgnoredFile(config, rel) {
  return !!(config && config.ignoreFiles.some((e) => e.re.test(rel)));
}

function walk(target, out, root) {
  let st;
  try {
    st = fs.statSync(target);
  } catch {
    return false;
  }
  if (st.isFile()) {
    if (EXTS.has(path.extname(target).toLowerCase())) out.push(target);
    return true;
  }
  let entries = [];
  try {
    entries = fs.readdirSync(target, { withFileTypes: true });
  } catch {
    return true;
  }
  entries.sort((a, b) => (a.name < b.name ? -1 : 1));
  for (const e of entries) {
    if (e.isDirectory()) {
      if (!SKIP_DIRS.has(e.name)) walk(path.join(target, e.name), out, root);
    } else if (e.isFile() && EXTS.has(path.extname(e.name).toLowerCase()))
      out.push(path.join(target, e.name));
  }
  return true;
}

function lintPaths(paths, { root, tier = "all" }) {
  const config = loadConfig(root);
  const designMd = loadDesignMd(root);
  const files = [];
  const missing = [];
  for (const p of paths)
    if (!walk(path.resolve(p), files, root)) missing.push(p);
  const findings = [];
  let scanned = 0;
  for (const abs of files) {
    const rel = path.relative(root, abs).split(path.sep).join("/");
    if (isIgnoredFile(config, rel)) continue;
    let src;
    try {
      if (fs.statSync(abs).size > MAX_BYTES) continue;
      src = fs.readFileSync(abs, "utf8");
    } catch {
      continue;
    }
    scanned++;
    findings.push(...lintSource({ file: rel, src, designMd, config, tier }));
  }
  return { findings, warnings: config.warnings, scanned, missing };
}

// ── output ────────────────────────────────────────────────────────────────────
function renderHuman(res, tier) {
  const f = res.findings;
  const imm = f.filter((x) => x.tier === "immediate").length;
  const adv = f.length - imm;
  const L = [];
  L.push("╭─ FORM ── form-lint ──────────────────────────╮", "");
  if (!f.length) L.push(`  ## Clean — ${res.scanned} file(s), no findings`);
  else
    L.push(`  ## ${imm} immediate, ${adv} advisory in ${res.scanned} file(s)`);
  if (f.length) L.push("", "  ### Findings");
  const MAX = 14;
  for (const x of f.slice(0, MAX)) {
    L.push(
      `  - ${SEV_ICON[x.severity]} ${x.file}:${x.line} [${x.rule}] ${x.message}`,
    );
  }
  if (f.length > MAX) L.push(`  - ${f.length - MAX} more — rerun with --json`);
  for (const w of res.warnings.slice(0, 3)) L.push(`  ! ${w}`);
  if (f.length) {
    L.push("", "  ### Next Steps");
    L.push("  → Fix immediate findings; advisory = taste, Form/human decides");
    L.push("  → /form-polish to fix, /form-critique for direction");
  }
  L.push(
    "",
    `╰─ tier: ${tier} · exit ${imm ? 1 : 0} ─────────────────────────╯`,
  );
  return L.join("\n");
}

const USAGE =
  "usage: design-lint.js [paths...] [--json] [--tier immediate|all] [--root DIR]";

function main(argv) {
  const paths = [];
  let json = false;
  let tier = "all";
  let root = null;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--json") json = true;
    else if (a === "--tier") tier = argv[++i];
    else if (a.startsWith("--tier=")) tier = a.slice(7);
    else if (a === "--root") root = argv[++i];
    else if (a.startsWith("--root=")) root = a.slice(7);
    else if (a === "-h" || a === "--help") {
      process.stdout.write(USAGE + "\n");
      return 0;
    } else if (a.startsWith("-")) {
      process.stderr.write(`unknown option ${a}\n${USAGE}\n`);
      return 2;
    } else paths.push(a);
  }
  if (tier !== "immediate" && tier !== "all") {
    process.stderr.write(`--tier must be immediate or all\n${USAGE}\n`);
    return 2;
  }
  if (root !== null && (!root || !fs.existsSync(root))) {
    process.stderr.write(`--root: directory not found\n${USAGE}\n`);
    return 2;
  }
  if (!paths.length) paths.push(".");
  root = root ? path.resolve(root) : findRoot(process.cwd());
  const res = lintPaths(paths, { root, tier });
  if (res.missing.length) {
    process.stderr.write(
      `path not found: ${res.missing.join(", ")}\n${USAGE}\n`,
    );
    return 2;
  }
  const imm = res.findings.some((f) => f.tier === "immediate");
  if (json) {
    process.stdout.write(
      JSON.stringify(
        {
          version: 1,
          findings: res.findings,
          warnings: res.warnings,
          scanned: res.scanned,
        },
        null,
        2,
      ) + "\n",
    );
  } else {
    process.stdout.write(renderHuman(res, tier) + "\n");
  }
  return imm ? 1 : 0;
}

module.exports = {
  lintSource,
  lintPaths,
  loadConfig,
  loadDesignMd,
  findRoot,
  globToRegExp,
  isIgnoredFile,
  rules,
};

if (require.main === module) process.exitCode = main(process.argv.slice(2));
