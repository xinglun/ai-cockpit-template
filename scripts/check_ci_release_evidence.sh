#!/usr/bin/env bash
set -euo pipefail

evidence_path=${1:?usage: check_ci_release_evidence.sh EVIDENCE_JSON [EXPECTED_HEAD_SHA]}
expected_head=${2:-}

fail() {
  echo "CI/Release Evidence invalid: $*" >&2
  exit 1
}

[[ -s "$evidence_path" ]] || fail "evidence file is missing or empty"
command -v jq >/dev/null 2>&1 || fail "jq is required"

jq -e 'type == "object"' "$evidence_path" >/dev/null || fail "root must be an object"
jq -e '
  .format == "ai-cockpit-ci-release-evidence" and
  .schemaVersion == 1 and
  (.state | IN("failed", "candidate", "verified", "published")) and
  (.evidenceSource | IN("github_api", "github_actions")) and
  (.workflowRunId | tostring | length > 0) and
  (.headSha | type == "string" and test("^[0-9a-f]{40}$")) and
  (.requiredJobNames | type == "array" and length > 0 and all(.[]; type == "string" and length > 0)) and
  (.workflowRuns | type == "array" and length > 0) and
  (.conclusion | IN("success", "failure", "cancelled", "skipped")) and
  (.failureReasons | type == "array" and all(.[]; type == "string" and length > 0)) and
  (.artifactDigests | type == "object") and
  (.artifactDigests["sbom.json"] == null or ((.artifactDigests["sbom.json"] | type) == "string" and (.artifactDigests["sbom.json"] | test("^[0-9a-f]{64}$")))) and
  (.artifactDigests["provenance.json"] == null or ((.artifactDigests["provenance.json"] | type) == "string" and (.artifactDigests["provenance.json"] | test("^[0-9a-f]{64}$"))))
' "$evidence_path" >/dev/null || fail "required evidence fields are missing or malformed"

if [[ -n "$expected_head" ]]; then
  [[ "$expected_head" =~ ^[0-9a-f]{40}$ ]] || fail "expected head SHA is malformed"
  [[ "$(jq -r '.headSha' "$evidence_path")" == "$expected_head" ]] || fail "head SHA does not match expected source"
fi

jq -e '
  all(.workflowRuns[];
    . as $run |
    ($run.workflowRunId | tostring | length > 0) and
    ($run.workflowName | type == "string" and length > 0) and
    ($run.headSha == $headSha and ($run.headSha | test("^[0-9a-f]{40}$"))) and
    ($run.requiredJobNames | type == "array" and length > 0) and
    ($run.jobs | type == "array") and
    ($run.conclusion | IN("success", "failure", "cancelled", "skipped")) and
    ($run.failureReasons | type == "array") and
    (all($run.jobs[]; (.name | type == "string" and length > 0) and (.conclusion | IN("success", "failure", "cancelled", "skipped")))) and
    (all($run.requiredJobNames[]; . as $required | any($run.jobs[]; .name == $required)))
  )
' --arg headSha "$(jq -r '.headSha' "$evidence_path")" "$evidence_path" >/dev/null || fail "workflow run evidence is not bound to the top-level head"

jq -e '
  . as $e |
  ($e.headToMergeRelationship | type == "string" and length > 0) and
  (if ($e.state | IN("verified", "published")) then
    ($e.mergeCommitSha | type == "string" and test("^[0-9a-f]{40}$")) and
    ($e.conclusion == "success") and
    ($e.failureReasons | length == 0) and
    (all($e.requiredJobNames[]; . as $required | any($e.workflowRuns[].jobs[]; .name == $required and .conclusion == "success"))) and
    ($e.artifactDigests["sbom.json"] | type == "string" and test("^[0-9a-f]{64}$")) and
    ($e.artifactDigests["provenance.json"] | type == "string" and test("^[0-9a-f]{64}$")) and
    ($e.sbom | type == "object" and .digest == $sbom and .sourceCommit == $headSha) and
    ($e.provenance | type == "object" and .digest == $provenance and .sourceCommit == $headSha)
  else true end)
' --arg headSha "$(jq -r '.headSha' "$evidence_path")" \
  --arg sbom "$(jq -r '.artifactDigests["sbom.json"] // ""' "$evidence_path")" \
  --arg provenance "$(jq -r '.artifactDigests["provenance.json"] // ""' "$evidence_path")" \
  "$evidence_path" >/dev/null || fail "verified/published evidence is not complete or source-bound"

jq -e '
  (if .state == "failed" then (.failureReasons | length > 0) else true end) and
  (.evidenceSource != "pr_body") and
  ((.source // "") != "pr_body")
' "$evidence_path" >/dev/null || fail "failed evidence needs reasons and PR Body is not an evidence source"

echo "CI/Release Evidence valid: $evidence_path"
