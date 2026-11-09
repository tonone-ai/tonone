#!/usr/bin/env node
"use strict";

// apex-guard — PreToolUse hook (Bash, Edit, MultiEdit, Write, NotebookEdit)
//
// Opt-in, session-scoped guardrail against destructive accidents. Inert until
// armed by `/apex-guard`, which writes `.claude/tonone-guard.json`.
//
// HONESTY: this is ADVISORY STRING MATCHING. It is trivially bypassable —
// aliases, wrapper scripts, `eval`, base64, `sh -c` payloads, other tools,
// other editors, a different cwd. It is not a security boundary. It exists to
// catch the "oops, wrong command" accident, not an adversary. Freeze mode
// constrains the file-edit tools only; Bash is NOT constrained by it.
//
// Modes (from the state file):
//   careful  Bash commands that look destructive -> `ask` (user confirms), and
//            a small catastrophic tier (rm -rf /, fork bomb, dd to a disk) -> `deny`.
//   freeze   Edit/MultiEdit/Write/NotebookEdit outside the frozen dir -> `deny`.
//
// Contract: print a PreToolUse decision JSON and exit 0, or print nothing and
// exit 0 (allow, leaving the user's normal permission prompts untouched). We
// never emit "allow". Every error path — bad JSON, unreadable state, timeout —
// fails open: no output, exit 0.
//
// State file `.claude/tonone-guard.json`:
//   {"version":1,"careful":true,"freeze":"/abs/dir"|null,
//    "session_id":null|"...","armed_at":"ISO-8601"}
// Located via CLAUDE_PROJECT_DIR, else by walking up from the input `cwd`
// (max 20 levels). Session scoping: `session_id: null` means armed-but-unbound;
// the first hook call that sees it binds it to that call's session_id (atomic
// rewrite, best-effort). A file bound to another session is stale and ignored
// (and best-effort deleted). Files older than 24h are ignored too.
//
// Disable: TONONE_GUARD=off or TONONE_APEX_GUARD=off (also 0, false, no).
//
// Manual use:
//   node apex-guard.js --check '{"tool_name":"Bash","tool_input":{"command":"git reset --hard"},"cwd":"."}'
//   echo '<hook json>' | node apex-guard.js
//   node apex-guard.js --status

const fs = require("fs");
const path = require("path");

const STATE_REL = path.join(".claude", "tonone-guard.json");
const STDIN_TIMEOUT_MS = 3000;
const MAX_WALK = 20;
const MAX_STATE_BYTES = 64 * 1024;
const MAX_AGE_MS = 24 * 60 * 60 * 1000;
const WRITE_TOOLS = new Set(["Edit", "MultiEdit", "Write", "NotebookEdit"]);

// ── Rules (data) ─────────────────────────────────────────────────────────────
// `re` runs on the whole command string. `unless` (optional) vetoes a match.
// rm is handled separately (see checkRm) because it needs per-target logic.

const SEG = "[^;&|\\n]"; // stay inside one shell segment

const RULES = [
  // deny tier
  {
    id: "forkbomb",
    decision: "deny",
    re: /:\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:/,
    reason: "fork bomb",
  },
  {
    id: "mkfs-disk",
    decision: "deny",
    re: new RegExp(`\\bmkfs\\S*${SEG}*\\s/dev/(?:sd|hd|vd|nvme|r?disk)`),
    reason: "mkfs on a physical disk device",
  },
  {
    id: "dd-disk",
    decision: "deny",
    re: new RegExp(`\\bdd\\b${SEG}*\\bof=/dev/(?:sd|hd|vd|nvme|r?disk)`),
    reason: "dd writing to a physical disk device",
  },
  // ask tier
  {
    id: "git-force-push",
    decision: "ask",
    re: new RegExp(
      `\\bgit\\s+(?:-\\S+\\s+)*push\\b${SEG}*?\\s(?:--force(?![-\\w])|-[a-zA-Z]*f[a-zA-Z]*)(?=\\s|$)`,
    ),
    reason: "git push --force rewrites remote history (use --force-with-lease)",
  },
  {
    id: "git-reset-hard",
    decision: "ask",
    re: /\bgit\s+(?:-\S+\s+)*reset\b[^;&|\n]*\s--hard\b/,
    reason: "git reset --hard discards uncommitted work",
  },
  {
    id: "git-clean",
    decision: "ask",
    re: new RegExp(
      `\\bgit\\s+(?:-\\S+\\s+)*clean\\b${SEG}*\\s(?:-[a-zA-Z]*f|--force)`,
    ),
    unless: /\s(?:-[a-zA-Z]*n|--dry-run)\b/,
    reason: "git clean -f deletes untracked files permanently",
  },
  {
    id: "git-mass-discard",
    decision: "ask",
    re: /\bgit\s+(?:-\S+\s+)*(?:checkout\s+(?:--\s+)?|restore\s+(?:[^;&|\n]*\s)?)\.(?=\s|$|[;&|])/,
    unless: /\s--staged\b(?![^;&|\n]*(?:--worktree|\s-W\b))/,
    reason: "mass discard of working-tree changes",
  },
  {
    id: "git-branch-D",
    decision: "ask",
    re: new RegExp(`\\bgit\\s+(?:-\\S+\\s+)*branch\\b${SEG}*\\s-[a-zA-Z]*D`),
    reason: "git branch -D force-deletes an unmerged branch",
  },
  {
    id: "sql-drop",
    decision: "ask",
    re: /\bdrop\s+(?:table|database|schema)\b/i,
    reason: "SQL DROP",
  },
  {
    id: "sql-truncate",
    decision: "ask",
    re: /\btruncate\s+table\b/i,
    reason: "SQL TRUNCATE",
  },
  {
    id: "sql-truncate-bare",
    decision: "ask",
    re: /\bTRUNCATE\s+["'`\w]/,
    reason: "SQL TRUNCATE",
  },
  {
    id: "sql-delete-all",
    decision: "ask",
    re: /\bdelete\s+from\s+[\w."`[\]]+(?=\s*(?:;|["')]|$))/i,
    reason: "SQL DELETE FROM without WHERE",
  },
  {
    id: "kubectl-delete",
    decision: "ask",
    re: new RegExp(`\\bkubectl\\b${SEG}*\\sdelete\\b`),
    reason: "kubectl delete removes cluster resources",
  },
  {
    id: "terraform-destroy",
    decision: "ask",
    re: /\b(?:terraform|tofu)\s+(?:-\S+\s+)*destroy\b/,
    reason: "terraform destroy tears down infrastructure",
  },
  {
    id: "docker-prune",
    decision: "ask",
    re: /\bdocker\s+(?:system\s+prune|volume\s+(?:rm|prune))\b/,
    reason: "docker prune / volume rm deletes data",
  },
  {
    id: "chmod-777-recursive",
    decision: "ask",
    re: new RegExp(
      `\\bchmod\\b(?=${SEG}*\\s(?:-[a-zA-Z]*R|--recursive)(?:\\s|$))(?=${SEG}*\\b0?777\\b)`,
    ),
    reason: "recursive chmod 777",
  },
  {
    id: "dd-dev",
    decision: "ask",
    re: new RegExp(
      `\\bdd\\b${SEG}*\\bof=/dev/(?!null\\b|zero\\b|stdout\\b|stderr\\b|fd/)`,
    ),
    reason: "dd writing to a device",
  },
  {
    id: "mkfs",
    decision: "ask",
    re: /(?:^|[\s;&|])(?:\/\S*\/)?mkfs(?:\.\w+)?(?=\s|$)/,
    reason: "mkfs formats a filesystem",
  },
];

// rm: deny catastrophic targets, ask on recursive rm unless all targets are
// well-known build artifacts.
const ARTIFACT_DIRS = new Set([
  "node_modules",
  "dist",
  "build",
  ".next",
  "target",
  "__pycache__",
  ".cache",
  "coverage",
]);
const CATASTROPHIC_TARGETS = new Set([
  "/",
  "/*",
  "~",
  "~/",
  "~/*",
  "$HOME",
  "$HOME/",
  "$HOME/*",
  "${HOME}",
  "${HOME}/",
  "${HOME}/*",
]);
const WRAPPERS = new Set([
  "sudo",
  "command",
  "env",
  "time",
  "nohup",
  "builtin",
]);

function unquote(tok) {
  return tok.replace(/^["']+|["']+$/g, "");
}

function checkRm(command) {
  const findings = [];
  const segments = command.split(/&&|\|\||[;\n|&]/);
  for (const seg of segments) {
    const toks = seg.trim().split(/\s+/).filter(Boolean).map(unquote);
    let i = 0;
    while (
      i < toks.length &&
      (WRAPPERS.has(toks[i]) || /^[A-Za-z_][A-Za-z0-9_]*=/.test(toks[i]))
    )
      i++;
    if (i >= toks.length) continue;
    const bin = path.basename(toks[i].replace(/^\\/, ""));
    if (bin !== "rm") continue;
    let recursive = false;
    const targets = [];
    let endOfOpts = false;
    for (const t of toks.slice(i + 1)) {
      if (!endOfOpts && t === "--") endOfOpts = true;
      else if (!endOfOpts && /^-/.test(t)) {
        if (t === "--recursive" || /^-[a-zA-Z]*[rR]/.test(t)) recursive = true;
      } else targets.push(t);
    }
    if (!recursive) continue;
    if (targets.some((t) => CATASTROPHIC_TARGETS.has(t))) {
      findings.push({
        decision: "deny",
        id: "rm-catastrophic",
        reason: "recursive rm of / or home directory",
      });
      continue;
    }
    const allArtifacts =
      targets.length > 0 &&
      targets.every((t) => {
        if (/[*$`?[]/.test(t)) return false;
        const base = t.replace(/\/+$/, "").split("/").pop();
        return ARTIFACT_DIRS.has(base) && t.replace(/\/+$/, "") !== "/" + base;
      });
    if (!allArtifacts)
      findings.push({
        decision: "ask",
        id: "rm-recursive",
        reason: `recursive rm of ${targets.join(" ") || "(no target parsed)"}`,
      });
  }
  return findings;
}

function checkCommand(command) {
  const findings = [];
  for (const rule of RULES) {
    if (rule.re.test(command) && !(rule.unless && rule.unless.test(command)))
      findings.push({ decision: rule.decision, reason: rule.reason, id: rule.id });
  }
  findings.push(...checkRm(command));
  return findings;
}

// ── Paths / freeze ───────────────────────────────────────────────────────────

// realpath of the deepest existing ancestor + the remaining tail.
function realpathBestEffort(p) {
  let cur = p;
  const tail = [];
  for (let i = 0; i < 64; i++) {
    try {
      const real = fs.realpathSync(cur);
      return tail.length ? path.join(real, ...tail.reverse()) : real;
    } catch {
      const parent = path.dirname(cur);
      if (parent === cur) break;
      tail.push(path.basename(cur));
      cur = parent;
    }
  }
  return p;
}

function insideDir(target, dir) {
  if (target === dir) return true;
  const prefix = dir.endsWith(path.sep) ? dir : dir + path.sep;
  return target.startsWith(prefix);
}

function checkFreeze(input, state) {
  const ti = input.tool_input || {};
  const raw = ti.file_path || ti.notebook_path || ti.path;
  if (typeof raw !== "string" || !raw) return null;
  const cwd =
    typeof input.cwd === "string" && input.cwd ? input.cwd : process.cwd();
  const target = realpathBestEffort(path.resolve(cwd, raw));
  const frozen = realpathBestEffort(path.resolve(state.freeze));
  if (insideDir(target, frozen)) return null;
  return {
    decision: "deny",
    reason: `edit blocked, ${target} is outside frozen dir ${frozen} (/apex-guard off to lift)`,
    rules: ["freeze"],
  };
}

// ── State ────────────────────────────────────────────────────────────────────

function findStateFile(input, env) {
  if (env.CLAUDE_PROJECT_DIR) {
    const f = path.join(env.CLAUDE_PROJECT_DIR, STATE_REL);
    return fs.existsSync(f) ? f : null;
  }
  let dir =
    typeof input.cwd === "string" && input.cwd ? input.cwd : process.cwd();
  dir = path.resolve(dir);
  for (let i = 0; i < MAX_WALK; i++) {
    const f = path.join(dir, STATE_REL);
    if (fs.existsSync(f)) return f;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function readState(file) {
  const st = fs.statSync(file);
  if (!st.isFile() || st.size > MAX_STATE_BYTES) return null;
  const state = JSON.parse(fs.readFileSync(file, "utf8"));
  return state && typeof state === "object" ? state : null;
}

function bestEffortUnlink(file) {
  try {
    fs.unlinkSync(file);
  } catch {}
}

function bindSession(file, state, sessionId) {
  try {
    const tmp = `${file}.${process.pid}.tmp`;
    fs.writeFileSync(
      tmp,
      JSON.stringify({ ...state, session_id: sessionId }, null, 2) + "\n",
    );
    fs.renameSync(tmp, file);
  } catch {}
}

// Returns the live state, or null if absent/stale/expired/invalid.
function loadLiveState(input, env, now) {
  const file = findStateFile(input, env);
  if (!file) return null;
  const state = readState(file);
  if (!state) return null;
  const armed = Date.parse(state.armed_at);
  if (!Number.isFinite(armed) || now - armed > MAX_AGE_MS) {
    if (Number.isFinite(armed)) bestEffortUnlink(file);
    return null;
  }
  const sid = typeof input.session_id === "string" ? input.session_id : null;
  if (state.session_id == null) {
    if (sid) bindSession(file, state, sid);
  } else if (state.session_id !== sid) {
    bestEffortUnlink(file);
    return null;
  }
  return state;
}

// ── Decision ─────────────────────────────────────────────────────────────────

function guardDisabled(env) {
  return ["TONONE_GUARD", "TONONE_APEX_GUARD"].some((k) =>
    /^(off|0|false|no)$/i.test(String(env[k] || "")),
  );
}

// Returns {decision, reason} or null (allow silently).
function evaluate(input, env, now) {
  if (!input || typeof input !== "object") return null;
  if (guardDisabled(env)) return null;
  const state = loadLiveState(input, env, now || Date.now());
  if (!state) return null;

  const tool = input.tool_name;
  const ti = input.tool_input || {};

  if (tool === "Bash" && state.careful === true) {
    const cmd = ti.command;
    if (typeof cmd !== "string" || !cmd) return null;
    const findings = checkCommand(cmd);
    if (!findings.length) return null;
    const deny = findings.filter((f) => f.decision === "deny");
    const pick = deny.length ? deny : findings;
    return {
      decision: deny.length ? "deny" : "ask",
      reason: [...new Set(pick.map((f) => f.reason))].slice(0, 3).join("; "),
      rules: [...new Set(pick.map((f) => f.id))].slice(0, 3),
    };
  }

  if (
    WRITE_TOOLS.has(tool) &&
    typeof state.freeze === "string" &&
    state.freeze
  ) {
    return checkFreeze(input, state);
  }
  return null;
}

function render(result) {
  return JSON.stringify({
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: result.decision,
      permissionDecisionReason: `apex-guard: ${result.reason}`,
    },
  });
}

// ── Main ─────────────────────────────────────────────────────────────────────

// Opt-in counter (TONONE_METRICS=on): ids only, never command text. Swallows errors.
function metric(input, result) {
  try {
    if (process.env.TONONE_METRICS !== "on") return;
    const root =
      process.env.CLAUDE_PROJECT_DIR ||
      (input && typeof input.cwd === "string" && input.cwd) ||
      process.cwd();
    const dir = path.join(root, ".tonone");
    fs.mkdirSync(dir, { recursive: true });
    const line = {
      ts: new Date().toISOString(),
      tool: "apex-guard",
      event: result.decision,
      rules: result.rules || [],
    };
    fs.appendFileSync(path.join(dir, "metrics.jsonl"), JSON.stringify(line) + "\n");
  } catch {}
}

function emit(input) {
  try {
    const result = evaluate(input, process.env);
    if (result) {
      process.stdout.write(render(result) + "\n");
      metric(input, result);
    }
  } catch {}
}

function printStatus() {
  try {
    const input = { cwd: process.cwd() };
    const file = findStateFile(input, process.env);
    if (!file) return process.stdout.write("apex-guard: not armed\n");
    process.stdout.write(`${file}\n${fs.readFileSync(file, "utf8")}`);
  } catch {}
}

function main() {
  try {
    const argv = process.argv.slice(2);
    if (argv[0] === "--status") return printStatus();
    if (argv[0] === "--check") {
      let input = null;
      try {
        input = JSON.parse(argv[1] || "");
      } catch {}
      return emit(input);
    }
    if (process.stdin.isTTY) return;

    let buf = "";
    let done = false;
    const finish = (run) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      if (run) {
        let input = null;
        try {
          input = JSON.parse(buf);
        } catch {}
        emit(input);
      }
    };
    const timer = setTimeout(() => {
      finish(false);
      process.exit(0);
    }, STDIN_TIMEOUT_MS);
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => {
      buf += c;
      if (buf.length > 4 * 1024 * 1024) finish(false);
    });
    process.stdin.on("end", () => finish(true));
    process.stdin.on("error", () => finish(false));
  } catch {}
}

module.exports = {
  evaluate,
  checkCommand,
  checkRm,
  checkFreeze,
  guardDisabled,
  render,
};

if (require.main === module) main();
