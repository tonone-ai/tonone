#!/usr/bin/env node
"use strict";

/**
 * lib/jev/cli.js — thin command-line front end so prose skills can reach the
 * decision layer from a Bash step.
 *
 *   node lib/jev/cli.js choice  --state-file ctx.txt --question "Which team?" \
 *                               --options billing,orders,account
 *   node lib/jev/cli.js noul    --state "..." --question "Is this a defect?" \
 *                               --criteria-true "..." --criteria-false "..."
 *   node lib/jev/cli.js score   --state-file ctx.txt --question "How urgent?" \
 *                               --levels "can wait,this week,blocking revenue"
 *   node lib/jev/cli.js batch   --state-file ctx.txt --questions-file q.json
 *   node lib/jev/cli.js provider
 *
 * Contract: a single JSON object on stdout, exit code 0, always. Failures are
 * reported in the JSON (`ok: false` plus `error`), never as a non-zero exit and
 * never as a stack trace, so a skill step can pipe this into jq without
 * guarding the call.
 */

const fs = require("fs");
const path = require("path");

const client = require("./client");

const USAGE =
  "usage: node lib/jev/cli.js <noul|choice|score|batch|provider> [flags]\n" +
  "  --state TEXT | --state-file PATH (- for stdin)\n" +
  "  --question TEXT\n" +
  "  --criteria-true TEXT   --criteria-false TEXT   (noul)\n" +
  "  --options a,b,c | --options-file PATH.json     (choice)\n" +
  "  --levels a,b,c | --levels-file PATH.json       (score)\n" +
  "  --questions-file PATH.json                     (batch)\n" +
  "  --session-id ID  --timeout MS  --no-cache  --pretty";

function parseArgs(argv) {
  const flags = {};
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg.indexOf("--") === 0) {
      const eq = arg.indexOf("=");
      let name;
      let value;
      if (eq !== -1) {
        name = arg.slice(2, eq);
        value = arg.slice(eq + 1);
      } else {
        name = arg.slice(2);
        const next = argv[i + 1];
        if (next === undefined || next.indexOf("--") === 0) {
          value = "true";
        } else {
          value = next;
          i++;
        }
      }
      flags[name] = value;
    } else {
      positional.push(arg);
    }
  }
  return { flags: flags, positional: positional };
}

function emit(payload, pretty) {
  try {
    process.stdout.write(JSON.stringify(payload, null, pretty ? 2 : 0) + "\n");
  } catch {
    process.stdout.write('{"ok":false,"error":"could not serialize result"}\n');
  }
}

function readStdin() {
  try {
    return fs.readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function readTextFile(file) {
  if (file === "-") return readStdin();
  try {
    return fs.readFileSync(path.resolve(file), "utf8");
  } catch {
    return null;
  }
}

function readJsonFile(file) {
  const text = readTextFile(file);
  if (text === null) return { error: "cannot read " + file };
  try {
    return { value: JSON.parse(text) };
  } catch {
    return { error: "invalid JSON in " + file };
  }
}

function splitList(value) {
  if (typeof value !== "string") return [];
  return value
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

function resolveState(flags) {
  if (flags["state-file"]) {
    const text = readTextFile(flags["state-file"]);
    if (text === null) return { error: "cannot read " + flags["state-file"] };
    return { value: text };
  }
  if (flags.state !== undefined) return { value: flags.state };
  return { value: "" };
}

async function main() {
  const parsed = parseArgs(process.argv.slice(2));
  const flags = parsed.flags;
  const pretty = flags.pretty !== undefined;
  const command = (parsed.positional[0] || "").toLowerCase();

  if (!command || flags.help !== undefined) {
    emit({ ok: false, error: "no command", usage: USAGE }, pretty);
    return;
  }

  if (command === "provider") {
    const provider = client.resolveProvider();
    emit(
      {
        ok: true,
        provider: provider ? provider.name : "local",
        model: provider ? provider.model : null,
        endpoint: provider ? provider.endpoint : null,
      },
      pretty,
    );
    return;
  }

  const state = resolveState(flags);
  if (state.error) {
    emit({ ok: false, error: state.error }, pretty);
    return;
  }

  const opts = {
    cache: flags["no-cache"] === undefined,
    sessionId: flags["session-id"] || null,
  };
  const timeout = parseInt(flags.timeout || "", 10);
  if (isFinite(timeout) && timeout > 0) opts.timeoutMs = timeout;

  const question = flags.question || "";

  if (command === "noul") {
    if (flags["criteria-true"] || flags["criteria-false"]) {
      opts.criteria = {
        true: flags["criteria-true"] || "",
        false: flags["criteria-false"] || "",
      };
    }
    const result = await client.noul(state.value, question, opts);
    emit(Object.assign({ ok: true }, result), pretty);
    return;
  }

  if (command === "choice") {
    let options = null;
    if (flags["options-file"]) {
      const loaded = readJsonFile(flags["options-file"]);
      if (loaded.error) {
        emit({ ok: false, error: loaded.error }, pretty);
        return;
      }
      options = loaded.value;
    } else {
      options = splitList(flags.options);
    }
    const result = await client.choice(state.value, question, options, opts);
    emit(Object.assign({ ok: true }, result), pretty);
    return;
  }

  if (command === "score") {
    let levels = null;
    if (flags["levels-file"]) {
      const loaded = readJsonFile(flags["levels-file"]);
      if (loaded.error) {
        emit({ ok: false, error: loaded.error }, pretty);
        return;
      }
      levels = loaded.value;
    } else {
      levels = splitList(flags.levels);
    }
    const result = await client.score(state.value, question, levels, opts);
    emit(Object.assign({ ok: true }, result), pretty);
    return;
  }

  if (command === "batch") {
    if (!flags["questions-file"]) {
      emit(
        { ok: false, error: "batch requires --questions-file", usage: USAGE },
        pretty,
      );
      return;
    }
    const loaded = readJsonFile(flags["questions-file"]);
    if (loaded.error) {
      emit({ ok: false, error: loaded.error }, pretty);
      return;
    }
    const result = await client.batch(state.value, loaded.value, opts);
    emit(Object.assign({ ok: true }, result), pretty);
    return;
  }

  emit(
    { ok: false, error: "unknown command: " + command, usage: USAGE },
    pretty,
  );
}

main()
  .then(() => {
    process.exitCode = 0;
  })
  .catch((err) => {
    // Unreachable by design; if it ever happens the contract still holds.
    emit(
      { ok: false, error: (err && err.message) || "unexpected failure" },
      false,
    );
    process.exitCode = 0;
  });
