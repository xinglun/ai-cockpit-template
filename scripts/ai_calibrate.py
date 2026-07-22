#!/usr/bin/env python3
"""Generate and validate project boundary calibration Profiles."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_project_profile import BOUNDARY_KEYS, FACT_KEYS, load_profile


CALIBRATION_STAGES = (
    "repository_role",
    "language_and_stack",
    "source_boundaries",
    "test_boundaries",
    "generated_artifacts",
    "critical_paths",
    "quality_commands",
    "review_requirements",
    "risk_and_unknowns",
    "adoption_readiness",
)
ANSWER_TYPES = ("yes_no", "alternative_input", "unknown", "not_applicable")
CONFIRMATION_PHASES = ("reviewer", "owner")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _evidence(kind: str, detail: str, *, status: str = "passed") -> dict[str, str]:
    return {"kind": kind, "status": status, "detail": detail, "recordedAt": _now()}


class CalibrationError(ValueError):
    """Raised when a calibration session transition is invalid."""


class CalibrationSession:
    """Durable, side-effect-free calibration session state machine.

    The object is JSON serializable. Repository persistence is deliberately
    handled by :func:`save_session`, so callers can review a snapshot before
    writing it to an adopter's calibration directory.
    """

    def __init__(self, data: dict[str, Any]):
        self.data = data

    @classmethod
    def start(cls, session_id: str) -> "CalibrationSession":
        if not session_id:
            raise CalibrationError("session_id must not be empty")
        stages: list[dict[str, Any]] = [
            {
                "id": stage,
                "position": index,
                "status": "current" if index == 0 else "pending",
                "checklist": {
                    "answerTypes": list(ANSWER_TYPES),
                    "answer": None,
                    "reason": None,
                },
                "evidence": [],
            }
            for index, stage in enumerate(CALIBRATION_STAGES)
        ]
        return cls(
            {
                "schemaVersion": 1,
                "sessionId": session_id,
                "language": "ja",
                "state": "in_progress",
                "currentStage": CALIBRATION_STAGES[0],
                "stages": stages,
                "events": [_evidence("session_started", "Calibration session created.")],
                "checks": {},
                "confirmations": {},
                "candidate": {"status": "not_prepared", "configuration": None},
                "active": {"status": "unchanged", "configuration": None},
                "staleStages": [],
            }
        )

    def _stage(self, stage_id: str) -> dict[str, Any]:
        for stage in self.data["stages"]:
            if stage["id"] == stage_id:
                return stage
        raise CalibrationError(f"unknown calibration stage: {stage_id}")

    def _require_live(self) -> None:
        if self.data["state"] == "paused":
            raise CalibrationError("resume the paused session before continuing")
        if self.data["state"] in {"activated", "aborted"}:
            raise CalibrationError(f"session is already {self.data['state']}")

    def answer(
        self,
        stage_id: str,
        answer: str,
        *,
        answer_type: str = "alternative_input",
        reason: str = "",
    ) -> None:
        self._require_live()
        stage = self._stage(stage_id)
        if answer_type not in ANSWER_TYPES:
            raise CalibrationError(f"unsupported answer type: {answer_type}")
        if not isinstance(answer, str) or not answer.strip():
            raise CalibrationError("answer must be a non-empty string")
        if answer_type == "yes_no" and answer not in {"Y", "N"}:
            raise CalibrationError("yes_no answers must be Y or N")
        if answer_type == "not_applicable" and not reason.strip():
            raise CalibrationError("Not Applicable requires a reason")
        previous = stage["checklist"].get("answer")
        stage["checklist"] = {
            "answerTypes": list(ANSWER_TYPES),
            "answer": answer,
            "reason": reason or None,
        }
        stage["checklist"]["answerType"] = answer_type
        stage["status"] = "complete"
        stage["evidence"].append(_evidence("answer", f"{stage_id}: {answer_type}={answer}"))
        self.data["events"].append(_evidence("answer_recorded", stage_id))
        position = stage["position"]
        if previous is not None and previous != answer:
            for downstream in self.data["stages"][position + 1 :]:
                if downstream["status"] == "complete":
                    downstream["status"] = "stale"
                if downstream["id"] not in self.data["staleStages"]:
                    self.data["staleStages"].append(downstream["id"])
            self.data["events"].append(_evidence("dependency_stale", stage_id, status="warning"))
        if position + 1 < len(self.data["stages"]):
            self.data["currentStage"] = self.data["stages"][position + 1]["id"]
            if self.data["stages"][position + 1]["status"] == "pending":
                self.data["stages"][position + 1]["status"] = "current"
        else:
            self.data["currentStage"] = None

    def back(self) -> None:
        self._require_live()
        current = self.data.get("currentStage")
        if current is None:
            index = len(self.data["stages"]) - 1
        else:
            index = next(
                stage["position"] for stage in self.data["stages"] if stage["id"] == current
            )
        if index == 0:
            raise CalibrationError("already at the first stage")
        self.data["stages"][index]["status"] = "pending"
        previous = self.data["stages"][index - 1]
        previous["status"] = "current"
        self.data["currentStage"] = previous["id"]
        self.data["events"].append(_evidence("back", previous["id"]))

    def review(self) -> dict[str, Any]:
        incomplete = [stage["id"] for stage in self.data["stages"] if stage["status"] != "complete"]
        review = {
            "status": "blocked" if incomplete else "ready",
            "incompleteStages": incomplete,
            "evidence": _evidence("review", "Calibration review generated."),
        }
        self.data["review"] = review
        self.data["events"].append(review["evidence"])
        return review

    def pause(self) -> None:
        if self.data["state"] != "in_progress":
            raise CalibrationError("only an in-progress session can be paused")
        self.data["state"] = "paused"
        self.data["events"].append(_evidence("paused", "Session paused for later resume."))

    def resume(self) -> None:
        if self.data["state"] != "paused":
            raise CalibrationError("session is not paused")
        self.data["state"] = "in_progress"
        self.data["events"].append(_evidence("resumed", "Session resumed."))

    def _check(self, name: str, passed: bool, detail: str) -> dict[str, Any]:
        result = {
            "status": "passed" if passed else "blocked",
            "evidence": _evidence(name, detail, status="passed" if passed else "blocked"),
        }
        self.data["checks"][name] = result
        return result

    def stage_self_check(self) -> dict[str, Any]:
        current_stage = self.data.get("currentStage")
        stage = (
            self._stage(current_stage)
            if isinstance(current_stage, str)
            else self.data["stages"][-1]
        )
        return self._check(
            "stage_self_check",
            stage["status"] == "complete",
            f"Stage {stage['id']} checklist state.",
        )

    def full_self_check(self) -> dict[str, Any]:
        complete = all(stage["status"] == "complete" for stage in self.data["stages"])
        return self._check("full_self_check", complete, "All ten stages are complete.")

    def governance_simulation(self) -> dict[str, Any]:
        passed = (
            all(stage["status"] == "complete" for stage in self.data["stages"])
            and not self.data["staleStages"]
        )
        return self._check(
            "governance_simulation",
            passed,
            "Candidate governance checks use recorded calibration answers.",
        )

    def confirm(self, phase: str) -> None:
        if phase not in CONFIRMATION_PHASES:
            raise CalibrationError(f"confirmation phase must be one of {CONFIRMATION_PHASES}")
        if self.data.get("checks", {}).get("full_self_check", {}).get("status") != "passed":
            raise CalibrationError("full self-check must pass before human confirmation")
        self.data["confirmations"][phase] = {
            "status": "confirmed",
            "evidence": _evidence("human_confirmation", phase),
        }

    def activate(self, *, active_path: Path, fail: bool = False) -> None:
        if set(self.data.get("confirmations", {})) != set(CONFIRMATION_PHASES):
            raise CalibrationError("both human confirmation phases are required")
        if self.data.get("checks", {}).get("governance_simulation", {}).get("status") != "passed":
            raise CalibrationError("governance simulation must pass before activation")
        candidate = {
            "sessionId": self.data["sessionId"],
            "language": self.data["language"],
            "answers": {stage["id"]: stage["checklist"] for stage in self.data["stages"]},
        }
        if fail:
            self.data["candidate"] = {
                "status": "blocked",
                "configuration": candidate,
                "evidence": _evidence(
                    "candidate_activation", "Activation failed closed.", status="blocked"
                ),
            }
            raise CalibrationError("candidate activation failed closed")
        active_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="calibration-active-", dir=str(active_path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(candidate, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temporary, active_path)
        except Exception:
            Path(temporary).unlink(missing_ok=True)
            self.data["candidate"] = {
                "status": "blocked",
                "configuration": candidate,
                "evidence": _evidence(
                    "candidate_activation", "Activation failed closed.", status="blocked"
                ),
            }
            raise
        self.data["candidate"] = {
            "status": "activated",
            "configuration": candidate,
            "evidence": _evidence("candidate_activation", "Candidate atomically activated."),
        }
        self.data["active"] = {"status": "active", "configuration": candidate}
        self.data["state"] = "activated"


def save_session(session: CalibrationSession, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_session(path: Path) -> CalibrationSession:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CalibrationError(f"failed to read session: {exc}") from exc
    if value.get("schemaVersion") != 1 or value.get("language") != "ja":
        raise CalibrationError("unsupported calibration session schema or language")
    if [stage.get("id") for stage in value.get("stages", [])] != list(CALIBRATION_STAGES):
        raise CalibrationError("calibration session must contain exactly ten ordered stages")
    return CalibrationSession(value)


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def values(items: Any, key: str) -> list[str]:
    if not isinstance(items, list):
        return []
    return sorted({str(item[key]) for item in items if isinstance(item, dict) and item.get(key)})


def render_key_list(lines: list[str], indent: str, key: str, items: list[str]) -> None:
    if not items:
        lines.append(f"{indent}{key}: []")
        return
    lines.append(f"{indent}{key}:")
    lines.extend(f"{indent}  - {quote(item)}" for item in items)


def proposed_profile(report: dict[str, Any]) -> str:
    facts = report.get("detectedFacts", {})
    suggestions = report.get("suggestedBoundaries", {})
    lines = [
        "# Generated proposal. Review facts and suggestions; do not treat this file as approved.",
        "version: 1",
        "repositoryRole: template",
        "",
        "detectedFacts:",
    ]
    for key in FACT_KEYS:
        render_key_list(
            lines, "  ", key, values(facts.get(key, []) if isinstance(facts, dict) else [], "value")
        )
    lines.extend(["", "suggestedBoundaries:"])
    for key in BOUNDARY_KEYS:
        render_key_list(
            lines,
            "  ",
            key,
            values(suggestions.get(key, []) if isinstance(suggestions, dict) else [], "path"),
        )
    project_signals = report.get("projectSignals", {})
    lines.extend(["", "projectSignals:"])
    for key in ("qualityCommands", "criticalDomains"):
        items = project_signals.get(key, []) if isinstance(project_signals, dict) else []
        values_list = [
            str(item.get("value")) for item in items if isinstance(item, dict) and item.get("value")
        ]
        render_key_list(lines, "  ", key, sorted(set(values_list)))
    lines.extend(["", "approvedBoundaries:"])
    for key in BOUNDARY_KEYS:
        render_key_list(lines, "  ", key, [])
    lines.extend(["", "reviewRequirements: []", ""])
    render_key_list(
        lines,
        "",
        "unknowns",
        [str(item) for item in report.get("unknowns", []) if isinstance(item, str)],
    )
    evidence = []
    if isinstance(facts, dict):
        for category in FACT_KEYS:
            for item in facts.get(category, []):
                if isinstance(item, dict):
                    evidence.append(
                        f"{category}:{item.get('value', '')}|confidence:{item.get('confidence', '')}|evidence:{item.get('evidence', '')}"
                    )
    lines.append("")
    render_key_list(lines, "", "evidence", evidence)
    lines.extend(["", "approval:", "  reviewed: false", '  reviewedBy: ""', '  reason: ""'])
    return "\n".join(lines) + "\n"


def generate(root: Path, report_path: Path, output: Path) -> int:
    if output.exists():
        print(f"ERROR: refusing to overwrite calibration proposal: {output}", file=sys.stderr)
        return 2
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to read Doctor report: {exc}", file=sys.stderr)
        return 2
    if report.get("reportVersion") != 1:
        print("ERROR: unsupported Doctor report version", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(proposed_profile(report), encoding="utf-8")
    print(f"calibration proposal: {output.relative_to(root)}")
    print(
        "Review and copy approved values into .ai/project_profile.yaml; this command does not modify Guards."
    )
    return 0


def validate(path: Path, *, confirmed: bool) -> int:
    _, issues = load_profile(path, require_approval=confirmed)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    print(f"project Profile validation passed: {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--root", default=".")
    generate_parser.add_argument("--report", default="target/ai_project_doctor_report.json")
    generate_parser.add_argument("--output", default=".ai/project_profile.proposed.yaml")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--profile", default=".ai/project_profile.proposed.yaml")
    validate_parser.add_argument("--confirmed", action="store_true")
    session_parser = subparsers.add_parser(
        "session", help="run the resumable ten-stage calibration session"
    )
    session_parser.add_argument(
        "action",
        choices=(
            "start",
            "answer",
            "back",
            "review",
            "pause",
            "resume",
            "stage-self-check",
            "full-self-check",
            "simulate",
            "confirm",
            "activate",
        ),
    )
    session_parser.add_argument("--session", default=".ai/calibration/session.json")
    session_parser.add_argument("--session-id", default="calibration-1")
    session_parser.add_argument("--stage")
    session_parser.add_argument("--answer")
    session_parser.add_argument("--answer-type", default="alternative_input", choices=ANSWER_TYPES)
    session_parser.add_argument("--reason", default="")
    session_parser.add_argument("--phase", choices=CONFIRMATION_PHASES)
    session_parser.add_argument("--active", default=".ai/calibration/active.json")
    session_parser.add_argument("--fail", action="store_true")
    args = parser.parse_args()
    if args.command == "generate":
        root = Path(args.root).resolve()
        return generate(root, root / args.report, root / args.output)
    if args.command == "validate":
        return validate(Path(args.profile), confirmed=args.confirmed)
    try:
        session_path = Path(args.session)
        if args.action == "start":
            session = CalibrationSession.start(args.session_id)
        else:
            session = load_session(session_path)
            if args.action == "answer":
                if not args.stage or args.answer is None:
                    raise CalibrationError("answer requires --stage and --answer")
                session.answer(
                    args.stage, args.answer, answer_type=args.answer_type, reason=args.reason
                )
            elif args.action == "back":
                session.back()
            elif args.action == "review":
                session.review()
            elif args.action == "pause":
                session.pause()
            elif args.action == "resume":
                session.resume()
            elif args.action == "stage-self-check":
                session.stage_self_check()
            elif args.action == "full-self-check":
                session.full_self_check()
            elif args.action == "simulate":
                session.governance_simulation()
            elif args.action == "confirm":
                if not args.phase:
                    raise CalibrationError("confirm requires --phase")
                session.confirm(args.phase)
            elif args.action == "activate":
                session.activate(active_path=Path(args.active), fail=args.fail)
        save_session(session, session_path)
        print(json.dumps(session.data, ensure_ascii=False, indent=2))
        return 0
    except CalibrationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
