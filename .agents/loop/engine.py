#!/usr/bin/env python3
"""Antigravity Autonomous Engineering Loop Engine (`.agents/loop/engine.py`).

Provides a deterministic, persistent 11-state state machine with quality gates,
circuit breaker, retry budgeting, automated diagnostic capture, and verification logging.

States:
  DISCOVER -> SPECIFY -> PLAN -> APPROVAL -> IMPLEMENT -> TEST -> E2E -> SECURITY -> REVIEW -> VERIFY -> ACCEPT
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import os
import pathlib
import subprocess
import sys
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class LoopState(str, Enum):
    """The 11 mandatory states of the Engineering Loop plus terminal states."""
    DISCOVER = "DISCOVER"
    SPECIFY = "SPECIFY"
    PLAN = "PLAN"
    APPROVAL = "APPROVAL"
    IMPLEMENT = "IMPLEMENT"
    TEST = "TEST"
    E2E = "E2E"
    SECURITY = "SECURITY"
    REVIEW = "REVIEW"
    VERIFY = "VERIFY"
    ACCEPT = "ACCEPT"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class GateVerdict(str, Enum):
    """Verdicts for quality gates."""
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclasses.dataclass(frozen=True)
class GateResult:
    """Immutable result of a quality gate evaluation."""
    gate_id: str
    target_state: str
    verdict: GateVerdict
    exit_code: int
    duration_seconds: float
    evidence: str
    diagnostics: Optional[Dict[str, Any]] = None
    timestamp_utc: str = dataclasses.field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class EngineeringLoopEngine:
    """Persistent state machine orchestrator for the Antigravity Autonomous Engineering Loop."""

    STATE_SEQUENCE: List[LoopState] = [
        LoopState.DISCOVER,
        LoopState.SPECIFY,
        LoopState.PLAN,
        LoopState.APPROVAL,
        LoopState.IMPLEMENT,
        LoopState.TEST,
        LoopState.E2E,
        LoopState.SECURITY,
        LoopState.REVIEW,
        LoopState.VERIFY,
        LoopState.ACCEPT,
        LoopState.COMPLETED,
    ]

    GATE_ORDER: List[str] = [
        "GATE-01-DISCOVERY",
        "GATE-02-SPECIFICATION",
        "GATE-03-PLAN",
        "GATE-04-APPROVAL",
        "GATE-05-IMPLEMENTATION",
        "GATE-06-TEST",
        "GATE-07-E2E",
        "GATE-08-SECURITY",
        "GATE-09-REVIEW",
        "GATE-10-VERIFY",
        "GATE-11-ACCEPT",
    ]

    def __init__(
        self,
        base_dir: Optional[pathlib.Path] = None,
        config_file: Optional[pathlib.Path] = None,
        state_file: Optional[pathlib.Path] = None,
    ) -> None:
        if base_dir is None:
            self.base_dir = pathlib.Path(__file__).resolve().parent.parent.parent
        else:
            self.base_dir = base_dir

        self.config_file = config_file or (self.base_dir / ".agents" / "loop" / "config.json")
        self.state_file = state_file or (self.base_dir / ".agents" / "loop" / "state.json")

        self.config = self._load_config()
        self.state = self._load_state()

    # -------------------------------------------------------------------------
    # Persistence & Loading
    # -------------------------------------------------------------------------

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        with open(self.config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_state(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return self._init_default_state()
        with open(self.state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _init_default_state(self) -> Dict[str, Any]:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        state: Dict[str, Any] = {
            "task_id": "DEFAULT-TASK",
            "spec_id": "SPEC-0018",
            "title": "Default Engineering Loop Task",
            "current_state": LoopState.DISCOVER.value,
            "history": [
                {
                    "from_state": None,
                    "to_state": LoopState.DISCOVER.value,
                    "timestamp_utc": now,
                    "reason": "Default initialization",
                }
            ],
            "gate_verdicts": {},
            "retries": {},
            "is_blocked": false if hasattr(sys, "_is_false_hack") else False,
            "block_reason": None,
            "last_updated_utc": now,
        }
        self._save_state(state)
        return state

    def _save_state(self, state: Optional[Dict[str, Any]] = None) -> None:
        if state is not None:
            self.state = state
        self.state["last_updated_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write
        tmp_file = self.state_file.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
        tmp_file.replace(self.state_file)

    # -------------------------------------------------------------------------
    # Inspection & Status
    # -------------------------------------------------------------------------

    @property
    def current_state(self) -> LoopState:
        return LoopState(self.state.get("current_state", LoopState.DISCOVER.value))

    @property
    def is_blocked(self) -> bool:
        return bool(self.state.get("is_blocked", False))

    @property
    def max_retries(self) -> int:
        return int(self.config.get("max_retries_per_gate", 3))

    def get_gate_info(self, gate_id: str) -> Dict[str, Any]:
        gates = self.config.get("gates", {})
        if gate_id not in gates:
            raise ValueError(f"Unknown gate identifier: {gate_id}")
        return gates[gate_id]

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured diagnostic status of the entire loop."""
        return {
            "task_id": self.state.get("task_id"),
            "spec_id": self.state.get("spec_id"),
            "title": self.state.get("title"),
            "current_state": self.current_state.value,
            "is_blocked": self.is_blocked,
            "block_reason": self.state.get("block_reason"),
            "gate_verdicts": self.state.get("gate_verdicts", {}),
            "retries": self.state.get("retries", {}),
            "history_count": len(self.state.get("history", [])),
            "last_updated_utc": self.state.get("last_updated_utc"),
        }

    # -------------------------------------------------------------------------
    # State Transitions & Gate Enforcement
    # -------------------------------------------------------------------------

    def transition_to(self, target_state: LoopState, reason: str = "") -> None:
        """Transitions state machine to target_state and logs to history."""
        old_state = self.current_state
        self.state["current_state"] = target_state.value
        if "history" not in self.state:
            self.state["history"] = []
        self.state["history"].append({
            "from_state": old_state.value,
            "to_state": target_state.value,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "reason": reason,
        })
        if target_state == LoopState.BLOCKED:
            self.state["is_blocked"] = True
        elif self.is_blocked and target_state != LoopState.BLOCKED:
            self.state["is_blocked"] = False
            self.state["block_reason"] = None
        self._save_state()

    def trip_circuit_breaker(self, reason: str) -> None:
        """Trips circuit breaker due to exceeded retries or unrecoverable defect."""
        self.state["block_reason"] = reason
        self.transition_to(LoopState.BLOCKED, reason=f"Circuit breaker tripped: {reason}")

    def reset(self, task_id: str, spec_id: str, title: str) -> None:
        """Resets the state machine for a fresh engineering run."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.state = {
            "task_id": task_id,
            "spec_id": spec_id,
            "title": title,
            "current_state": LoopState.DISCOVER.value,
            "history": [
                {
                    "from_state": None,
                    "to_state": LoopState.DISCOVER.value,
                    "timestamp_utc": now,
                    "reason": f"Loop reset for task {task_id}",
                }
            ],
            "gate_verdicts": {},
            "retries": {},
            "is_blocked": False,
            "block_reason": None,
            "last_updated_utc": now,
        }
        self._save_state()

    def record_gate_verdict(
        self,
        gate_id: str,
        passed: bool,
        evidence: str,
        details: Optional[Dict[str, Any]] = None,
        duration_seconds: float = 0.0,
        exit_code: int = 0,
    ) -> GateResult:
        """Records the outcome of a gate, manages retries and transitions state if passed."""
        gate_info = self.get_gate_info(gate_id)
        target_state_name = gate_info["target_state"]
        next_state_name = gate_info["next_state"]

        # Enforce human stakeholder approval invariant
        if gate_info.get("requires_human_approval") and passed:
            if not details or not details.get("approved_by"):
                raise PermissionError(
                    f"Gate {gate_id} requires explicit human stakeholder approval. "
                    "Use engine.approve_plan(approved_by=...) or CLI 'approve-plan'."
                )

        # Enforce circuit breaker lockout
        if self.is_blocked and passed:
            raise RuntimeError(
                f"Engineering Loop is BLOCKED (Reason: {self.state.get('block_reason')}). "
                "Must perform root-cause remediation and execute 'unblock' before recording passing verdicts."
            )

        verdict = GateVerdict.PASSED if passed else GateVerdict.FAILED
        result = GateResult(
            gate_id=gate_id,
            target_state=target_state_name,
            verdict=verdict,
            exit_code=exit_code if not passed and exit_code == 0 else exit_code,
            duration_seconds=duration_seconds,
            evidence=evidence,
            diagnostics=details,
        )

        # Store in state
        if "gate_verdicts" not in self.state:
            self.state["gate_verdicts"] = {}
        self.state["gate_verdicts"][gate_id] = dataclasses.asdict(result)

        if passed:
            # Reset retry counter for this gate
            if "retries" in self.state and gate_id in self.state["retries"]:
                self.state["retries"][gate_id] = 0
            
            # Transition to next state if not completed
            if next_state_name == "COMPLETED":
                self.transition_to(LoopState.COMPLETED, reason=f"All gates cleared ({gate_id} passed)")
            else:
                next_state = LoopState(next_state_name)
                self.transition_to(next_state, reason=f"{gate_id} passed")
        else:
            # Handle failure & retry budgeting
            if "retries" not in self.state:
                self.state["retries"] = {}
            current_retries = self.state["retries"].get(gate_id, 0) + 1
            self.state["retries"][gate_id] = current_retries

            if current_retries > self.max_retries:
                # Trip circuit breaker
                block_msg = (
                    f"Gate {gate_id} failed {current_retries} times (max allowed: {self.max_retries}). "
                    f"Evidence: {evidence}"
                )
                self.trip_circuit_breaker(block_msg)
            else:
                self._save_state()

        return result

    def approve_plan(self, approved_by: str, notes: str = "") -> GateResult:
        """Unlocks GATE-04-APPROVAL with recorded human stakeholder authorization."""
        if self.current_state != LoopState.APPROVAL and not self.is_blocked:
            raise RuntimeError(f"Cannot approve plan while in state {self.current_state.value}. State must be APPROVAL.")
        
        evidence = f"Approval explicitly granted by {approved_by}. Notes: {notes or 'No notes provided.'}"
        return self.record_gate_verdict(
            gate_id="GATE-04-APPROVAL",
            passed=True,
            evidence=evidence,
            details={"approved_by": approved_by, "notes": notes},
        )

    def run_gate(self, gate_id: str, timeout_seconds: int = 180) -> GateResult:
        """Executes the automated command attached to a gate and records verdict."""
        gate_info = self.get_gate_info(gate_id)
        command = gate_info.get("command")

        if self.is_blocked:
            raise RuntimeError(
                f"Engineering Loop is BLOCKED (Reason: {self.state.get('block_reason')}). "
                "Must perform root-cause remediation and execute 'scripts/run_loop.py unblock' before re-running gates."
            )

        if not command:
            raise ValueError(f"Gate {gate_id} does not have an automated command configured.")

        start_time = datetime.datetime.now()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            duration = (datetime.datetime.now() - start_time).total_seconds()
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            passed = (proc.returncode == 0)

            # Build evidence string
            if passed:
                evidence_lines = stdout.splitlines()[-5:] if stdout else ["Command completed cleanly."]
                evidence = "\n".join(evidence_lines)
            else:
                err_lines = (stderr or stdout).splitlines()[-10:]
                evidence = f"Exit code {proc.returncode}:\n" + "\n".join(err_lines)

            details = {
                "command": command,
                "stdout_excerpt": stdout[-1000:],
                "stderr_excerpt": stderr[-1000:],
            }

            return self.record_gate_verdict(
                gate_id=gate_id,
                passed=passed,
                evidence=evidence,
                details=details,
                duration_seconds=duration,
                exit_code=proc.returncode,
            )

        except subprocess.TimeoutExpired as exc:
            duration = (datetime.datetime.now() - start_time).total_seconds()
            evidence = f"Gate timed out after {timeout_seconds} seconds."
            return self.record_gate_verdict(
                gate_id=gate_id,
                passed=False,
                evidence=evidence,
                details={"timeout_seconds": timeout_seconds, "error": str(exc)},
                duration_seconds=duration,
                exit_code=124,
            )

    def generate_introspection_report(self, gate_id: str) -> Dict[str, Any]:
        """Generates structured incident introspection report for debugging and root cause isolation."""
        verdict_data = self.state.get("gate_verdicts", {}).get(gate_id, {})
        retries = self.state.get("retries", {}).get(gate_id, 0)
        return {
            "incident_id": f"INC-{self.state.get('task_id', 'TASK')}-{gate_id}-{retries}",
            "task_id": self.state.get("task_id"),
            "gate_id": gate_id,
            "current_state": self.current_state.value,
            "is_circuit_breaker_tripped": self.is_blocked,
            "retry_count": retries,
            "retry_budget_remaining": max(0, self.max_retries - retries),
            "evidence": verdict_data.get("evidence"),
            "diagnostics": verdict_data.get("diagnostics"),
            "recommended_recovery_action": (
                "Review failing test/rule output, apply minimal surgical fix, "
                "re-run test suite before re-attempting gate."
            ),
        }
