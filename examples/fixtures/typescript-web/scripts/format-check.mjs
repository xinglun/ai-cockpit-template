import { readFile } from "node:fs/promises";

const source = await readFile("src/index.ts", "utf8");
if (!source.endsWith("\n") || source.includes("\t")) {
  console.error("fixture format check failed");
  process.exit(1);
}
console.log("fixture format check passed");
