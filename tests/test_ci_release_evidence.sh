#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
head='c2022fa1d0c2d94ed3edf6c1d16a89260d3fd68f'
valid="$tmp/valid.json"
jq -n --arg head "$head" '{format:"ai-cockpit-ci-release-evidence",schemaVersion:1,state:"verified",evidenceSource:"github_api",workflowRunId:"12345",headSha:$head,mergeCommitSha:("d"*40),headToMergeRelationship:"pull_request_merge_ref",requiredJobNames:["smoke"],workflowRuns:[{workflowRunId:"12345",workflowName:"smoke.yml",headSha:$head,requiredJobNames:["smoke"],jobs:[{name:"smoke",conclusion:"success"}],conclusion:"success",failureReasons:[]}],conclusion:"success",failureReasons:[],artifactDigests:{"sbom.json":("a"*64),"provenance.json":("b"*64)},sbom:{digest:("a"*64),sourceCommit:$head},provenance:{digest:("b"*64),sourceCommit:$head}}' > "$valid"
bash "$root/scripts/check_ci_release_evidence.sh" "$valid" "$head"

for mutation in missing-run stale-head failed-without-reason pr-body; do
  case "$mutation" in
    missing-run) jq '.workflowRunId = ""' "$valid" > "$tmp/$mutation.json" ;;
    stale-head) jq '.headSha = ("e"*40)' "$valid" > "$tmp/$mutation.json" ;;
    failed-without-reason) jq '.state = "failed" | .conclusion = "failure"' "$valid" > "$tmp/$mutation.json" ;;
    pr-body) jq '.evidenceSource = "pr_body"' "$valid" > "$tmp/$mutation.json" ;;
  esac
  if bash "$root/scripts/check_ci_release_evidence.sh" "$tmp/$mutation.json" "$head"; then
    echo "negative evidence case unexpectedly passed: $mutation" >&2
    exit 1
  fi
done
mkdir "$tmp/release"
jq -n '{releaseTag:"v0.5.33"}' > "$tmp/release/release.json"
jq -n '{releaseTag:"v0.5.34",releaseState:"candidate",published:false,basedOnReleaseTag:"v0.5.33"}' > "$tmp/release/next-release.json"
pub_digest="$(sha256sum "$tmp/release/release.json" | cut -d' ' -f1)"
candidate_digest="$(sha256sum "$tmp/release/next-release.json" | cut -d' ' -f1)"
jq -n --arg source "$head" --arg pub "$pub_digest" --arg candidate "$candidate_digest" --slurpfile evidence "$valid" '{schemaVersion:1,canonical:true,projections:{published:"release.json",candidate:"next-release.json"},state:"candidate_verified",releaseTag:"v0.5.34",sourceCommit:$source,previousRelease:"v0.5.33",evidenceStatus:"verified",evidenceBundleDigest:("a"*64),metadataDigests:{published:$pub,candidate:$candidate},ciEvidence:$evidence[0]}' > "$tmp/release/release-state.json"
PYTHONDONTWRITEBYTECODE=1 python3 "$root/scripts/check_release_state_consistency.py" --root "$tmp/release"
jq '.ciEvidence.evidenceSource = "pr_body"' "$tmp/release/release-state.json" > "$tmp/release/bad.json"
mv "$tmp/release/bad.json" "$tmp/release/release-state.json"
if PYTHONDONTWRITEBYTECODE=1 python3 "$root/scripts/check_release_state_consistency.py" --root "$tmp/release"; then
  echo 'PR Body-only canonical evidence unexpectedly passed' >&2
  exit 1
fi
echo 'CI/Release Evidence shell regression passed'
