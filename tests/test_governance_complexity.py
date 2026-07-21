import json
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import check_governance_complexity


def test_generated_current_status_is_not_persistent_markdown_complexity(monkeypatch, tmp_path):
    generated = tmp_path / ".ai" / "cockpit" / "current_status.md"
    persisted = tmp_path / "README.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("generated\n" * 20, encoding="utf-8")
    persisted.write_text("persisted\n", encoding="utf-8")
    monkeypatch.setattr(
        check_governance_complexity, "tracked_files", lambda _root: [generated, persisted]
    )
    assert (
        check_governance_complexity.line_count(
            check_governance_complexity.complexity_files(tmp_path, [generated, persisted]), ".md"
        )
        == 1
    )


def test_complexity_report_records_increment(monkeypatch):
    monkeypatch.setenv("AI_COMPLEXITY_BASELINE_PYTHON_LINES", "1")
    report, issues = check_governance_complexity.build_report(
        check_governance_complexity.ROOT,
        check_governance_complexity.ROOT / ".ai" / "guards" / "governance_complexity_policy.yaml",
    )
    assert issues == []
    assert report["complexityDelta"]["pythonLines"] > 0


def test_report_records_three_provenance_bound_baselines(monkeypatch):
    monkeypatch.setenv("AI_COMPLEXITY_ACTIVE_BASE_COMMIT", "HEAD")
    monkeypatch.setenv("AI_COMPLEXITY_WORK_ITEM_BASE_COMMIT", "HEAD")
    monkeypatch.delenv("AI_COMPLEXITY_ADOPTION_BASE_COMMIT", raising=False)

    report, issues = check_governance_complexity.build_report(
        check_governance_complexity.ROOT,
        check_governance_complexity.ROOT / ".ai" / "guards" / "governance_complexity_policy.yaml",
    )

    assert issues == []
    assert report["baselineEvidence"]["adoption"]["status"] == "unavailable"
    assert report["baselineEvidence"]["active"]["status"] == "resolved"
    assert report["baselineEvidence"]["workItem"]["status"] == "resolved"
    assert report["classification"]["historicalDebt"]["status"] == "unavailable"
    assert report["policyActivation"]["status"] == "confirmed"


def test_policy_activation_is_explicit_and_fail_closed(tmp_path):
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text("version: 1\nmax:\n  pythonLines: 1\n", encoding="utf-8")
    assert check_governance_complexity.policy_activation(policy_file)["status"] == "unavailable"


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
    assert report["metrics"]["pythonFiles"] >= 1
    assert report["metrics"]["guardFiles"] == 0


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
    assert not any("trackedFiles" in issue for issue in issues)


def test_tracked_files_are_observational_when_policy_omits_the_former_threshold(
    tmp_path, monkeypatch
):
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(
        "version: 1\nmax:\n  pythonLines: 10\n  markdownLines: 10\n",
        encoding="utf-8",
    )
    files = [tmp_path / f"file-{index}.py" for index in range(741)]
    for path in files:
        path.write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(check_governance_complexity, "tracked_files", lambda root: files)

    report, issues = check_governance_complexity.build_report(tmp_path, policy_file)

    assert report["metrics"]["trackedFiles"] == 741
    assert not any("trackedFiles" in issue for issue in issues)


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
        "version: 1\nmax:\n  pythonLines: nope\n  markdownLines: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="max.pythonLines"):
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


def test_archive_metrics_validates_index_coverage_identity_and_hashes(tmp_path):
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    contract = archive / "work.contract.json"
    summary = archive / "work.summary.json"
    contract.write_text(json.dumps({"workItemId": "work"}), encoding="utf-8")
    summary.write_text(json.dumps({"workItemId": "work"}), encoding="utf-8")
    rel_contract = contract.relative_to(tmp_path).as_posix()
    rel_summary = summary.relative_to(tmp_path).as_posix()

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    manifest = archive / "work.archive-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "format": "ai-cockpit-archive-manifest",
                "contractSha256": digest(contract),
                "summarySha256": digest(summary),
            }
        ),
        encoding="utf-8",
    )

    (archive.parent / "index.json").write_text(
        json.dumps(
            {
                "indexVersion": 1,
                "entries": [
                    {
                        "workItemId": "work",
                        "archiveSequence": 100,
                        "contractPath": rel_contract,
                        "summaryPath": rel_summary,
                        "contractSha256": digest(contract),
                        "summarySha256": digest(summary),
                        "manifestPath": manifest.relative_to(tmp_path).as_posix(),
                        "manifestSha256": digest(manifest),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    _, issues = check_governance_complexity.archive_metrics(tmp_path)

    assert issues == []

    contract.write_text(json.dumps({"workItemId": "tampered"}), encoding="utf-8")
    _, issues = check_governance_complexity.archive_metrics(tmp_path)
    assert any("contractSha256 mismatch" in issue for issue in issues)
    assert any("workItemId mismatch" in issue for issue in issues)


def test_archive_metrics_rejects_authoritative_pair_missing_from_index(tmp_path):
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    contract = archive / "unindexed.contract.json"
    summary = archive / "unindexed.summary.json"
    contract.write_text(json.dumps({"workItemId": "unindexed"}), encoding="utf-8")
    summary.write_text(json.dumps({"workItemId": "unindexed"}), encoding="utf-8")
    (archive.parent / "index.json").write_text('{"entries": []}', encoding="utf-8")

    _, issues = check_governance_complexity.archive_metrics(tmp_path)

    assert any("does not cover authoritative archive pair" in issue for issue in issues)


def test_archive_metrics_rejects_duplicate_strict_paths(tmp_path):
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    first_contract = archive / "first.contract.json"
    first_summary = archive / "first.summary.json"
    second_contract = archive / "second.contract.json"
    second_summary = archive / "second.summary.json"
    for path, item in (
        (first_contract, "first"),
        (first_summary, "first"),
        (second_contract, "second"),
        (second_summary, "second"),
    ):
        path.write_text(json.dumps({"workItemId": item}), encoding="utf-8")

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    entries = []
    for sequence, contract, summary, item in (
        (100, first_contract, first_summary, "first"),
        (100, second_contract, second_summary, "first"),
    ):
        entries.append(
            {
                "workItemId": item,
                "archiveSequence": sequence,
                "contractPath": first_contract.relative_to(tmp_path).as_posix(),
                "summaryPath": summary.relative_to(tmp_path).as_posix(),
                "contractSha256": digest(contract),
                "summarySha256": digest(summary),
            }
        )
    (archive.parent / "index.json").write_text(json.dumps({"entries": entries}), encoding="utf-8")

    _, issues = check_governance_complexity.archive_metrics(tmp_path)

    assert any("duplicates Contract path" in issue for issue in issues)
    assert any("duplicates workItemId" in issue for issue in issues)
    assert any("duplicates archiveSequence" in issue for issue in issues)


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


def test_repository_shape_metrics_are_reported(tmp_path):
    script = tmp_path / "scripts"
    script.mkdir()
    source = script / "sample.py"
    source.write_text(
        "def sample(value):\n    if value:\n        return True\n    return False\n",
        encoding="utf-8",
    )
    schema = tmp_path / ".ai" / "trust" / "schema"
    schema.mkdir(parents=True)
    (schema / "sample.schema.json").write_text("{}", encoding="utf-8")
    guard = tmp_path / ".ai" / "guards"
    guard.mkdir(parents=True)
    (guard / "sample.yaml").write_text("version: 1\n", encoding="utf-8")

    metrics = check_governance_complexity.repository_shape_metrics(
        tmp_path,
        [source, schema / "sample.schema.json", guard / "sample.yaml"],
        {"archiveContracts": 4},
    )

    assert metrics["functionComplexity"] == 2
    assert metrics["schemaCount"] == 1
    assert metrics["guardCount"] == 1
    assert metrics["dependencyCycles"] == 0
    assert metrics["archiveGrowth"] == 4
    assert "generatedEvidenceRatio" in metrics


def test_budget_increase_without_repayment_is_blocked(tmp_path, monkeypatch):
    source = tmp_path / "x.py"
    source.write_text("pass\n", encoding="utf-8")
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(
        "version: 1\nmax:\n  pythonLines: 2\nbaseline:\n  pythonLines: 1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_governance_complexity, "tracked_files", lambda root: [source])
    monkeypatch.setattr(
        check_governance_complexity,
        "archive_metrics",
        lambda root: ({"archiveContracts": 0, "archiveSummaries": 0, "archiveIndexEntries": 0}, []),
    )

    _, issues = check_governance_complexity.build_report(tmp_path, policy_file)

    assert any("lacks owner/due-date repayment record" in issue for issue in issues)


def test_budget_increase_with_repayment_owner_and_due_date_passes(tmp_path, monkeypatch):
    source = tmp_path / "x.py"
    source.write_text("pass\n", encoding="utf-8")
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(
        "version: 1\nmax:\n  pythonLines: 2\nbaseline:\n  pythonLines: 1\n"
        "repaymentRecords:\n"
        "  - wi|pythonLines|1|2|owner|2026-08-01|remove duplicate concepts\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_governance_complexity, "tracked_files", lambda root: [source])
    monkeypatch.setattr(
        check_governance_complexity,
        "archive_metrics",
        lambda root: ({"archiveContracts": 0, "archiveSummaries": 0, "archiveIndexEntries": 0}, []),
    )

    report, issues = check_governance_complexity.build_report(tmp_path, policy_file)

    assert issues == []
    assert report["complexityDelta"]["budgetIncreases"] == {"pythonLines": 1.0}
