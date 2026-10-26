#!/usr/bin/env python3
"""CLI Runner for the Antigravity Autonomous Engineering Loop (`scripts/run_loop.py`).

Usage:
  python3 scripts/run_loop.py status
  python3 scripts/run_loop.py run-gate GATE-06-TEST
  python3 scripts/run_loop.py approve-plan --approver "Lead Architect" --notes "Approved"
  python3 scripts/run_loop.py record-gate --gate GATE-01-DISCOVERY --passed --evidence "Discovery done"
  python3 scripts/run_loop.py reset --task DONB-LOOP-01 --spec SPEC-0018 --title "Loop Harness"
  python3 scripts/run_loop.py unblock --reason "Fixed offending test"
  python3 scripts/run_loop.py report --gate GATE-06-TEST
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Ensure repository root is in python path
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".agents" / "loop"))

from engine import EngineeringLoopEngine, LoopState, GateVerdict


def format_status(engine: EngineeringLoopEngine) -> str:
    summary = engine.get_summary()
    lines = []
    lines.append("=" * 72)
    lines.append(f"  ANTIGRAVITY AUTONOMOUS ENGINEERING LOOP — STATUS")
    lines.append("=" * 72)
    lines.append(f"Task ID      : {summary['task_id']}")
    lines.append(f"Spec ID      : {summary['spec_id']}")
    lines.append(f"Title        : {summary['title']}")
    lines.append(f"State        : {summary['current_state']}")
    lines.append(f"Blocked      : {'YES (' + str(summary['block_reason']) + ')' if summary['is_blocked'] else 'NO'}")
    lines.append(f"Last Updated : {summary['last_updated_utc']}")
    lines.append("-" * 72)
    lines.append(f"{'GATE ID':<24} {'STATE':<12} {'VERDICT':<10} {'RETRIES':<8} {'EXIT'}")
    lines.append("-" * 72)

    verdicts = summary["gate_verdicts"]
    retries = summary["retries"]

    for gate_id in EngineeringLoopEngine.GATE_ORDER:
        info = engine.get_gate_info(gate_id)
        target_state = info["target_state"]
        res = verdicts.get(gate_id)
        if res:
            verd = res["verdict"]
            exit_c = str(res["exit_code"])
        else:
            verd = "PENDING"
            exit_c = "-"
        ret_count = str(retries.get(gate_id, 0))
        lines.append(f"{gate_id:<24} {target_state:<12} {verd:<10} {ret_count:<8} {exit_c}")

    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Antigravity Autonomous Engineering Loop CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # status
    subparsers.add_parser("status", help="Print current loop status and quality gates table")

    # run-gate
    p_run = subparsers.add_parser("run-gate", help="Execute automated quality gate command")
    p_run.add_argument("gate_id", help="Gate identifier (e.g. GATE-06-TEST)")
    p_run.add_argument("--timeout", type=int, default=180, help="Timeout in seconds")

    # approve-plan
    p_app = subparsers.add_parser("approve-plan", help="Record explicit stakeholder approval for GATE-04-APPROVAL")
    p_app.add_argument("--approver", required=True, help="Name or role of approving stakeholder")
    p_app.add_argument("--notes", default="", help="Approval context or notes")

    # record-gate
    p_rec = subparsers.add_parser("record-gate", help="Record manual verdict for a quality gate")
    p_rec.add_argument("--gate", required=True, help="Gate identifier")
    p_rec.add_argument("--passed", action="store_true", help="Mark gate as PASSED")
    p_rec.add_argument("--failed", action="store_true", help="Mark gate as FAILED")
    p_rec.add_argument("--evidence", required=True, help="Evidence string")

    # reset
    p_res = subparsers.add_parser("reset", help="Reset state machine for a new task")
    p_res.add_argument("--task", default="DONB-TASK-01", help="Task ID")
    p_res.add_argument("--spec", default="SPEC-0018", help="Spec ID")
    p_res.add_argument("--title", default="Engineering Loop Autonomous Harness", help="Task title")

    # unblock
    p_unb = subparsers.add_parser("unblock", help="Unblock tripped circuit breaker after remediation")
    p_unb.add_argument("--target-state", default="IMPLEMENT", help="State to transition into after unblock")
    p_unb.add_argument("--reason", required=True, help="Remediation reason")

    # report
    p_rep = subparsers.add_parser("report", help="Generate incident introspection report for a gate")
    p_rep.add_argument("--gate", required=True, help="Gate identifier")

    args = parser.parse_args()
    engine = EngineeringLoopEngine(base_dir=REPO_ROOT)

    if args.subcommand == "status":
        print(format_status(engine))
        return 0

    elif args.subcommand == "run-gate":
        print(f"Running automated gate: {args.gate_id}...")
        res = engine.run_gate(args.gate_id, timeout_seconds=args.timeout)
        print(f"Result : {res.verdict.value} (exit code {res.exit_code}, duration {res.duration_seconds:.2f}s)")
        print(f"Evidence:\n{res.evidence}")
        if res.verdict != GateVerdict.PASSED:
            return 1
        return 0

    elif args.subcommand == "approve-plan":
        res = engine.approve_plan(approved_by=args.approver, notes=args.notes)
        print(f"Plan approved successfully by {args.approver}. State transitioned to {engine.current_state.value}.")
        return 0

    elif args.subcommand == "record-gate":
        if args.gate == "GATE-04-APPROVAL":
            print("ERROR: GATE-04-APPROVAL cannot be recorded via 'record-gate'.")
            print("Explicit human authorization is required: use 'approve-plan --approver <name>'.")
            return 1

        passed = args.passed and not args.failed
        try:
            res = engine.record_gate_verdict(
                gate_id=args.gate,
                passed=passed,
                evidence=args.evidence,
            )
            print(f"Recorded verdict for {args.gate}: {res.verdict.value}. Current state: {engine.current_state.value}")
            return 0 if passed else 1
        except Exception as exc:
            print(f"ERROR: {exc}")
            return 1

    elif args.subcommand == "reset":
        engine.reset(task_id=args.task, spec_id=args.spec, title=args.title)
        print(f"Engineering Loop reset. State: {engine.current_state.value}")
        return 0

    elif args.subcommand == "unblock":
        target = LoopState(args.target_state)
        engine.transition_to(target, reason=f"Unblocked: {args.reason}")
        print(f"Circuit breaker reset. Transitioned to {target.value}.")
        return 0

    elif args.subcommand == "report":
        rep = engine.generate_introspection_report(args.gate)
        print(json.dumps(rep, indent=2, ensure_ascii=False))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
