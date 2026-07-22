import { spawnSync } from "node:child_process";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";

const statePath = ".fixture-state.json";
const original = await readFile("fixture.json", "utf8");
await mkdir(".fixture-backup", { recursive: true });
await writeFile(".fixture-backup/fixture.json", original);

function npmPhase(phase, args) {
  const command = `npm ${args.join(" ")}`;
  const result = spawnSync("npm", args, { encoding: "utf8" });
  if (result.error?.code === "ENOENT") {
    return {
      phase,
      status: "not_run",
      executionKind: "not_run",
      command,
      reason: "npm executable is unavailable",
      evidence: [`local:typescript-web:${phase}`],
      resumeCondition: "install a supported Node/npm toolchain",
      policyReference: "ai-cockpit/fixture-lifecycle",
    };
  }
  const status = result.status === 0 ? "passed" : "failed";
  return {
    phase,
    status,
    executionKind: "local_real_execution",
    command,
    reason: status === "passed" ? "command completed successfully" : "command exited non-zero",
    evidence: [`local:typescript-web:${phase}`],
    resumeCondition: status === "passed" ? "none" : "repair the fixture command and rerun",
    outputTail: `${result.stdout ?? ""}${result.stderr ?? ""}`.slice(-1000),
    policyReference: "ai-cockpit/fixture-lifecycle",
  };
}

async function localPhase(phase, action, command) {
  try {
    await action();
    return {
      phase,
      status: "passed",
      executionKind: "local_real_execution",
      command,
      reason: "local filesystem transition completed and was verified",
      evidence: [`local:typescript-web:${phase}`],
      resumeCondition: "none",
      policyReference: "ai-cockpit/fixture-lifecycle",
    };
  } catch (error) {
    return {
      phase,
      status: "failed",
      executionKind: "local_real_execution",
      command,
      reason: error instanceof Error ? error.message : "local transition failed",
      evidence: [`local:typescript-web:${phase}`],
      resumeCondition: "repair the fixture transition and rerun",
      policyReference: "ai-cockpit/fixture-lifecycle",
    };
  }
}

const phases = [];
try {
  phases.push(npmPhase("Install", ["install", "--ignore-scripts", "--no-audit", "--no-fund"]));
  phases.push(
    await localPhase(
      "Configure",
      async () => {
        const config = JSON.parse(await readFile("fixture.json", "utf8"));
        if (config.stack !== "typescript-web" || config.evidenceBoundary === undefined) {
          throw new Error("fixture configuration is incomplete");
        }
      },
      "read fixture.json and validate local configuration",
    ),
  );
  phases.push(npmPhase("Normal Work Item", ["test"]));
  phases.push({
    phase: "Ambiguous Request",
    status: "blocked",
    executionKind: "blocked",
    command: "insufficient intent and acceptance",
    reason: "the fixture intentionally refuses an ambiguous request",
    evidence: ["local:typescript-web:Ambiguous Request"],
    resumeCondition: "provide reviewed intent and acceptance",
    policyReference: "ai-cockpit/fixture-lifecycle",
  });
  phases.push({
    phase: "Critical Domain Change",
    status: "blocked",
    executionKind: "blocked",
    command: "critical-domain change requires structured evidence",
    reason: "the fixture intentionally refuses an unbounded critical-domain change",
    evidence: ["local:typescript-web:Critical Domain Change"],
    resumeCondition: "provide reviewed intent and acceptance",
    policyReference: "ai-cockpit/fixture-lifecycle",
  });
  phases.push(
    await localPhase(
      "Upgrade",
      async () => {
        const upgraded = { ...JSON.parse(original), fixtureVersion: 2 };
        await writeFile("fixture.json", JSON.stringify(upgraded, null, 2) + "\n");
        if (JSON.parse(await readFile("fixture.json", "utf8")).fixtureVersion !== 2) {
          throw new Error("upgrade transition was not persisted");
        }
      },
      "write and verify fixture.json version 2",
    ),
  );
  phases.push(
    await localPhase(
      "Rollback",
      async () => {
        await writeFile("fixture.json", original);
        if ((await readFile("fixture.json", "utf8")) !== original) {
          throw new Error("rollback did not restore the original fixture");
        }
      },
      "restore and verify fixture.json from local backup",
    ),
  );
  const release = [npmPhase("Release Check: build", ["run", "build"]), npmPhase("Release Check: lint", ["run", "lint"]), npmPhase("Release Check: format", ["run", "format:check"])]
    .map((item) => item);
  phases.push({
    phase: "Release Check",
    status: release.some((item) => item.status === "failed")
      ? "failed"
      : release.some((item) => item.status === "not_run")
        ? "not_run"
        : "passed",
    executionKind: release.every((item) => item.executionKind === "local_real_execution") ? "local_real_execution" : "not_run",
    command: release.map((item) => item.command).join(" && "),
    reason: release.map((item) => `${item.phase}: ${item.reason}`).join("; "),
    evidence: release.flatMap((item) => item.evidence),
    resumeCondition: release.every((item) => item.status === "passed") ? "none" : "install the toolchain or repair release checks",
    policyReference: "ai-cockpit/fixture-lifecycle",
  });
} finally {
  await writeFile("fixture.json", original);
  await writeFile(statePath, JSON.stringify({ version: 2, phases }, null, 2) + "\n");
  await rm(".fixture-backup", { recursive: true, force: true });
}

if (phases.some((item) => item.status === "failed")) {
  process.exitCode = 1;
}
console.log(JSON.stringify({ phases, externalProviderEvidence: { status: "not_run", reason: "local fixture has no provider credentials" } }, null, 2));
