#!/usr/bin/env node
// tonone-agent-tracker — PostToolUse hook for Agent tool
// Tracks active subagents in a bridge file for the statusline to read

const fs = require("fs");
const path = require("path");
const os = require("os");

let input = "";
const timeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    const data = JSON.parse(input);
    const session = data.session_id;
    if (!session || /[/\\]|\.\./.test(session)) process.exit(0);

    const bridgePath = path.join(os.tmpdir(), `tonone-agents-${session}.json`);

    // Read existing state
    let state = { agents: [] };
    try {
      state = JSON.parse(fs.readFileSync(bridgePath, "utf8"));
    } catch {}

    const toolInput = data.tool_input || {};
    const toolOutput = data.tool_output || {};

    // Agent tool was invoked — a subagent started or completed
    const agentDesc =
      toolInput.description || toolInput.prompt?.slice(0, 40) || "agent";

    // Start = agentId present AND no output yet (agent was launched)
    const isStart = Boolean(toolOutput.agentId) && !toolOutput.output;

    if (isStart) {
      // New agent started
      state = {
        ...state,
        agents: [
          ...state.agents,
          {
            id: toolOutput.agentId,
            desc: agentDesc,
            started: Date.now(),
            finished: null,
          },
        ],
      };
    } else {
      // Completion — match by desc (agentId may not be present on completion)
      const now = Date.now();
      state = {
        ...state,
        agents: state.agents.map((a) =>
          a.desc === agentDesc && !a.finished ? { ...a, finished: now } : a,
        ),
      };
    }

    // Prune agents older than 10 minutes
    const cutoff = Date.now() - 600_000;
    state.agents = state.agents.filter((a) => a.started > cutoff);

    // Atomic write — temp file + rename to prevent race conditions
    const tmpPath = bridgePath + ".tmp." + process.pid;
    fs.writeFileSync(tmpPath, JSON.stringify(state));
    fs.renameSync(tmpPath, bridgePath);
  } catch {
    // Silent fail
  }
});
