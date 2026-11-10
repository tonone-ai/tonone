// Copies the generated catalog indexes into the package so `npx tonone-mcp` is self-contained.
import { cpSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
mkdirSync(join(root, "data"), { recursive: true });
for (const f of ["agent-index.json", "skill-index.json"]) {
  cpSync(join(root, "..", "docs", f), join(root, "data", f));
}
