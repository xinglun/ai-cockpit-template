import assert from "node:assert/strict";
import test from "node:test";
import { evaluateRequest } from "../dist/index.js";

test("allows a normal local request", () => {
  assert.equal(evaluateRequest("update the local demo").decision, "allow");
});

test("blocks an unsupported dangerous request with a resume condition", () => {
  const result = evaluateRequest("build a rocket");
  assert.equal(result.decision, "block");
  assert.notEqual(result.resumeCondition, "none");
});
