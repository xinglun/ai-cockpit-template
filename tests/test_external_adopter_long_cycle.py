import json
import subprocess
import sys
from pathlib import Path

import external_adopter_long_cycle

ROOT = Path(__file__).resolve().parents[1]


def test_external_adopter_lifecycle_records_independent_git_evidence():
    direct_evidence = external_adopter_long_cycle.run()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "external_adopter_long_cycle.py")],
        check=True,
        capture_output=True,
        text=True,
    )
    evidence = json.loads(result.stdout)
    assert direct_evidence["defaultBranch"] == evidence["defaultBranch"]
    assert evidence["defaultBranch"] == "main"
    assert evidence["remote"] == "local bare origin"
    assert evidence["baselineCommit"] != evidence["upgradeCommit"]
    assert evidence["mergeCommit"] != evidence["rollbackCommit"]
    assert evidence["upgradeWorktreeRemoved"] is True
    assert evidence["localBranchesCleaned"] is True
    assert evidence["remoteBranchesCleaned"] is True
    assert evidence["enterpriseAssurance"] == "not_claimed"
