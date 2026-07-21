export type Decision = "allow" | "block";

export interface RequestEvaluation {
  readonly decision: Decision;
  readonly reason: string;
  readonly resumeCondition: string;
}

/** Evaluate the small fixture request surface with explicit fail-closed outcomes. */
export function evaluateRequest(request: string): RequestEvaluation {
  const normalized = request.toLowerCase();
  if (normalized.includes("rocket") || normalized.includes("delete all tests")) {
    return {
      decision: "block",
      reason: "request requires structured evidence and a safe execution boundary",
      resumeCondition: "provide reviewed intent, acceptance, and sandbox evidence",
    };
  }
  return {
    decision: "allow",
    reason: "request is within the local fixture boundary",
    resumeCondition: "none",
  };
}
