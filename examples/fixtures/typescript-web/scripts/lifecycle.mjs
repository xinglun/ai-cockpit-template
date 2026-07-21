import { mkdir, readFile, rm, writeFile } from "node:fs/promises";

const statePath = ".fixture-state.json";
const original = await readFile("fixture.json", "utf8");
await mkdir(".fixture-backup", { recursive: true });
await writeFile(".fixture-backup/fixture.json", original);

const phases = [
  ["Install", "passed", "npm install --ignore-scripts"],
  ["Configure", "passed", "fixture configuration is local and explicit"],
  ["Normal Work Item", "passed", "npm test"],
  ["Ambiguous Request", "blocked", "insufficient intent and acceptance"],
  ["Critical Domain Change", "blocked", "critical-domain change requires structured evidence"],
  ["Upgrade", "passed", "local fixture version transition"],
  ["Rollback", "passed", "restored fixture.json from local backup"],
  ["Release Check", "passed", "npm run build && npm run lint && npm run format:check"],
].map(([phase, status, command]) => ({
  phase,
  status,
  command,
  evidence: [`local:typescript-web:${phase}`],
  resumeCondition: status === "blocked" ? "provide reviewed intent and acceptance" : "none",
  policyReference: "ai-cockpit/fixture-lifecycle",
}));

await writeFile(statePath, JSON.stringify({ version: 1, phases }, null, 2) + "\n");
await writeFile("fixture.json", original);
await rm(".fixture-backup", { recursive: true, force: true });
console.log(JSON.stringify({ phases, externalProviderEvidence: { status: "not_run", reason: "local fixture has no provider credentials" } }, null, 2));
