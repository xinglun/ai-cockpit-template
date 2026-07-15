import json
from pathlib import Path

import check_governance_complexity


def policy(path: Path, **limits: int) -> None:
    values = {
        "trackedFiles": 100,
        "pythonLines": 100,
        "markdownLines": 100,
        "archiveContracts": 10,
        "archiveSummaries": 10,
    }
    values.update(limits)
    path.write_text(
        "version: 1\nmax:\n" + "".join(f"  {key}: {value}\n" for key, value in values.items()),
        encoding="utf-8",
    )


def test_report_passes_and_writes_metrics(tmp_path, monkeypatch):
    (tmp_path / ".ai" / "work-items" / "archive" / "2026").mkdir(parents=True)
    archive = tmp_path / ".ai" / "work-items" / "archive"
    (archive / "2026" / "task.contract.json").write_text("{}", encoding="utf-8")
    (archive / "2026" / "task.summary.json").write_text("{}", encoding="utf-8")
    (archive / "index.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "workItemId": "task",
                        "contractPath": ".ai/work-items/archive/2026/task.contract.json",
                        "summaryPath": ".ai/work-items/archive/2026/task.summary.json",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(
        "version: 1\nmax:\n  trackedFiles: 10\n  pythonLines: 10\n  markdownLines: 10\n  archiveContracts: 2\n  archiveSummaries: 2\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        check_governance_complexity, "tracked_files", lambda root: [root / "x.py", root / "x.md"]
    )
    (tmp_path / "x.py").write_text("x\n", encoding="utf-8")
    (tmp_path / "x.md").write_text("x\n", encoding="utf-8")

    report, issues = check_governance_complexity.build_report(tmp_path, policy_file)

    assert issues == []
    assert report["metrics"]["archiveContracts"] == 1
    assert report["metrics"]["archiveIndexEntries"] == 1


def test_report_fails_on_threshold_and_missing_archive_pair(tmp_path, monkeypatch):
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    (archive / "orphan.contract.json").write_text("{}", encoding="utf-8")
    (archive.parent / "index.json").write_text(
        '{"entries": [{"contractPath": ".ai/work-items/archive/2026/missing.contract.json", "summaryPath": ".ai/work-items/archive/2026/missing.summary.json"}]}',
        encoding="utf-8",
    )
    policy_file = tmp_path / "policy.yaml"
    policy(policy_file, trackedFiles=1)
    monkeypatch.setattr(
        check_governance_complexity, "tracked_files", lambda root: [root / "x.py", root / "y.py"]
    )

    report, issues = check_governance_complexity.build_report(tmp_path, policy_file)

    assert report["issues"] == issues
    assert any("missing paired Summary" in issue for issue in issues)
    assert any("archive index references missing" in issue for issue in issues)
    assert any("trackedFiles=2" in issue for issue in issues)
