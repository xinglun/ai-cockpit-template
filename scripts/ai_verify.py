"""Lightweight Task/PR/Release verification primitives."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from ai_check_registry import CheckerRegistry, CheckResult
from ai_verification_context import build_context

STAGES = ("task", "pr", "release")
MODES = ("legacy", "unified", "compare")


def evaluate_trend(
    metric: str, samples: list[float], *, threshold: float, minimum_samples: int = 3
) -> CheckResult:
    """Turn a bounded trend into a soft result without hiding missing history."""
    if len(samples) < minimum_samples:
        return CheckResult.warning(
            metric,
            reason_code="insufficient_samples",
            detail=f"{len(samples)} sample(s); {minimum_samples} required before escalation",
        )
    spread = max(samples) - min(samples)
    if spread > threshold:
        return CheckResult(
            metric,
            "needs_human_confirmation",
            "soft",
            "threshold_exceeded",
            f"trend spread {spread:g} exceeds threshold {threshold:g}",
        )
    return CheckResult.passed(
        metric, gate="soft", detail=f"trend spread {spread:g} within threshold {threshold:g}"
    )


def verify_stage(context, stage: str, registry: CheckerRegistry) -> list[CheckResult]:
    if stage not in STAGES:
        raise ValueError(f"unsupported verification stage: {stage}")
    requested: tuple[str, ...] = (
        ("scope", "tests") if stage == "task" else ("scope", "tests", "trust")
    )
    if stage == "release":
        requested = ("scope", "tests", "trust", "identity", "supply_chain")
    return registry.run(requested, available=set(registry.checker_ids))


def run_verification(context, registry: CheckerRegistry, *, mode: str = "unified"):
    """Preserve the legacy surface while exposing unified and compare modes."""
    if mode not in MODES:
        raise ValueError(f"unsupported verification mode: {mode}")
    legacy = {"mode": "legacy", "results": verify_stage(context, "task", registry)}
    unified = {
        "mode": "unified",
        "results": {stage: verify_stage(context, stage, registry) for stage in STAGES},
    }
    if mode == "legacy":
        return legacy
    if mode == "compare":
        return {"mode": "compare", "legacy": legacy, "unified": unified}
    return unified


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--stage", choices=STAGES, default="task")
    parser.add_argument("--mode", choices=MODES, default="unified")
    args = parser.parse_args()
    context = build_context(args.root, args.contract, args.summary)
    registry = CheckerRegistry()
    results = run_verification(context, registry, mode=args.mode)
    if args.mode == "unified":
        results = {
            args.stage: [asdict(result) for result in results["results"][args.stage]],
            "mode": args.mode,
        }
    elif args.mode == "legacy":
        results["results"] = [asdict(result) for result in results["results"]]
    else:
        results["legacy"]["results"] = [asdict(result) for result in results["legacy"]["results"]]
        results["unified"]["results"] = {
            stage: [asdict(result) for result in values]
            for stage, values in results["unified"]["results"].items()
        }
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
