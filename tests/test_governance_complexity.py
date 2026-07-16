import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import check_governance_complexity


def policy(path: Path, **limits: int) -> None:
    values = {
        "trackedFiles": 100,
        "pythonLines": 100,
        "markdownLines": 100,
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
        "version: 1\nmax:\n  trackedFiles: 10\n  pythonLines: 10\n  markdownLines: 10\n",
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


def test_archive_totals_are_observational_above_former_threshold(tmp_path, monkeypatch):
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    entries = []
    for index in range(261):
        stem = f"task-{index}"
        contract_path = archive / f"{stem}.contract.json"
        summary_path = archive / f"{stem}.summary.json"
        contract_path.write_text("{}", encoding="utf-8")
        summary_path.write_text("{}", encoding="utf-8")
        entries.append(
            {
                "contractPath": f".ai/work-items/archive/2026/{stem}.contract.json",
                "summaryPath": f".ai/work-items/archive/2026/{stem}.summary.json",
            }
        )
    (archive.parent / "index.json").write_text(json.dumps({"entries": entries}), encoding="utf-8")
    policy_file = tmp_path / "policy.yaml"
    policy(policy_file, trackedFiles=10, pythonLines=10, markdownLines=10)
    monkeypatch.setattr(check_governance_complexity, "tracked_files", lambda root: [root / "x.py"])
    (tmp_path / "x.py").write_text("x\n", encoding="utf-8")

    report, issues = check_governance_complexity.build_report(tmp_path, policy_file)

    assert report["metrics"]["archiveContracts"] == 261
    assert report["metrics"]["archiveSummaries"] == 261
    assert not any("archiveContracts" in issue or "archiveSummaries" in issue for issue in issues)


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


def test_archive_metrics_reports_missing_and_malformed_index_entries(tmp_path):
    archive = tmp_path / ".ai" / "work-items" / "archive"
    archive.mkdir(parents=True)

    metrics, issues = check_governance_complexity.archive_metrics(tmp_path)

    assert metrics == {"archiveContracts": 0, "archiveSummaries": 0, "archiveIndexEntries": 0}
    assert issues == ["archive index is missing"]

    (archive / "index.json").write_text(
        json.dumps(
            {
                "entries": [
                    "legacy entry",
                    {"contractPath": "only-contract"},
                    {"contractPath": "missing.contract", "summaryPath": "missing.summary"},
                ]
            }
        ),
        encoding="utf-8",
    )
    metrics, issues = check_governance_complexity.archive_metrics(tmp_path)

    assert metrics["archiveIndexEntries"] == 3
    assert "archive index entry lacks Contract/Summary paths" in issues
    assert "archive index references missing missing.contract" in issues


def test_archive_metrics_reports_unloadable_index(tmp_path):
    archive = tmp_path / ".ai" / "work-items" / "archive"
    archive.mkdir(parents=True)
    (archive / "index.json").write_text("not json", encoding="utf-8")

    _, issues = check_governance_complexity.archive_metrics(tmp_path)

    assert any(issue.startswith("archive index cannot be loaded:") for issue in issues)


def test_load_policy_rejects_missing_or_non_positive_limits(tmp_path):
    missing_max = tmp_path / "missing-max.yaml"
    missing_max.write_text("version: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="max mapping"):
        check_governance_complexity.load_policy(missing_max)

    invalid_limit = tmp_path / "invalid-limit.yaml"
    invalid_limit.write_text(
        "version: 1\nmax:\n  trackedFiles: nope\n  pythonLines: 1\n  markdownLines: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="max.trackedFiles"):
        check_governance_complexity.load_policy(invalid_limit)


def test_line_count_ignores_other_suffixes_and_unreadable_files(tmp_path):
    python_file = tmp_path / "ok.py"
    python_file.write_text("one\ntwo\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("ignored\n", encoding="utf-8")
    binary_file = tmp_path / "broken.py"
    binary_file.write_bytes(b"\xff\xfe")

    assert (
        check_governance_complexity.line_count(
            [python_file, tmp_path / "missing.py", tmp_path / "notes.md", binary_file], ".py"
        )
        == 2
    )


def test_tracked_files_raises_when_git_listing_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(
        check_governance_complexity.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=""),
    )

    with pytest.raises(RuntimeError, match="git ls-files failed"):
        check_governance_complexity.tracked_files(tmp_path)


def test_archive_metrics_reports_unpaired_records(tmp_path):
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    (archive / "contract-only.contract.json").write_text("{}", encoding="utf-8")
    (archive / "summary-only.summary.json").write_text("{}", encoding="utf-8")
    (archive.parent / "index.json").write_text('{"entries": []}', encoding="utf-8")

    _, issues = check_governance_complexity.archive_metrics(tmp_path)

    assert "missing paired Summary for contract-only" in issues
    assert "missing paired Contract for summary-only" in issues


def test_main_writes_success_report(tmp_path, monkeypatch):
    output = tmp_path / "target" / "report.json"
    monkeypatch.setattr(
        check_governance_complexity,
        "build_report",
        lambda root, policy: (
            {"metrics": {"trackedFiles": 1}, "issues": []},
            [],
        ),
    )
    monkeypatch.setattr(sys, "argv", ["check", "--root", str(tmp_path), "--output", str(output)])

    assert check_governance_complexity.main() == 0
    assert json.loads(output.read_text(encoding="utf-8"))["metrics"]["trackedFiles"] == 1


def test_main_returns_error_for_report_issues(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        check_governance_complexity,
        "build_report",
        lambda root, policy: ({"metrics": {}, "issues": ["bad"]}, ["bad"]),
    )
    monkeypatch.setattr(sys, "argv", ["check", "--root", str(tmp_path)])

    assert check_governance_complexity.main() == 1
    assert "[ERROR] bad" in capsys.readouterr().err
