#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$root/scripts" python3 - <<'PY'
import json
from pathlib import Path

from ai_installer_detection import missing_runtime_scripts
from ai_installer_ownership import is_project_owned
from ai_installer_repository import git_target_args

catalog = json.loads((Path.cwd() / "scripts" / "ai_installer_catalog.json").read_text())
assert "ai_installer_repository.py" in catalog["scripts"]
assert missing_runtime_scripts({"runtime.py"}, set()) == ["runtime.py"]
assert is_project_owned(".ai/guards/example.yaml")
assert git_target_args(Path("/tmp/project"))[0].startswith("--git-dir=")
PY
echo "installer boundary regression passed"
