#!/bin/sh
set -eu

# Offline demonstration: no credentials, network, filesystem mutation, or production call.
blocked=0
for scenario in unclear-rocket-intent chinese-dangerous-expression scope-disguise stale-decision-evidence; do
  printf '{"scenario":"%s","status":"not_ready","decision":"stop","reason":"evidence or capability boundary is unresolved","evidenceSources":["rawUserRequest","declaredIntent","repository_capabilities","preflight_report"],"resumeCondition":"provide fresh matching evidence and rerun Preflight","governancePath":"Preflight/Capability/Intent Guard","unsafeOperation":false}\n' "$scenario"
  blocked=$((blocked + 1))
done
printf '{"scenario":"normal-low-risk-request","status":"ready","decision":"continue","reason":"declared intent and capabilities align","evidenceSources":["rawUserRequest","declaredIntent","repository_capabilities","preflight_report"],"resumeCondition":"implementation may proceed within declared scope","governancePath":"Preflight/Capability/Intent Guard","unsafeOperation":false}\n'
printf '{"summary":{"blockedScenarios":%s,"continuedScenarios":1,"unsafeOperations":0,"evidence":"machine-readable stop and continuation records"}}\n' "$blocked"
