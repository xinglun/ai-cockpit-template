import { readFile } from "node:fs/promises";

const source = await readFile("src/index.ts", "utf8");
if (!source.includes("export function evaluateRequest") || source.includes("any")) {
  console.error("fixture lint failed");
  process.exit(1);
}
console.log("fixture lint passed");
