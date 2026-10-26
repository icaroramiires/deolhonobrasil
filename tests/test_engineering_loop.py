"""Unit tests for the Antigravity Autonomous Engineering Loop Engine (`.agents/loop/engine.py`)."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / ".agents" / "loop") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / ".agents" / "loop"))

from engine import EngineeringLoopEngine, GateVerdict, LoopState


class TestEngineeringLoopEngine(unittest.TestCase):
    """Verifies state machine transitions, quality gates, retry limits, and circuit breaker."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)
        self.config_file = self.tmp_dir / "config.json"
        self.state_file = self.tmp_dir / "state.json"

        # Copy real config to temp
        real_config = (REPO_ROOT / ".agents" / "loop" / "config.json").read_text(encoding="utf-8")
        self.config_file.write_text(real_config, encoding="utf-8")

        self.engine = EngineeringLoopEngine(
            base_dir=REPO_ROOT,
            config_file=self.config_file,
            state_file=self.state_file,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_initial_state_defaults_to_discover(self) -> None:
        self.assertEqual(self.engine.current_state, LoopState.DISCOVER)
        self.assertFalse(self.engine.is_blocked)
        summary = self.engine.get_summary()
        self.assertEqual(summary["current_state"], "DISCOVER")
        self.assertFalse(summary["is_blocked"])

    def test_gate_verdict_passing_advances_state(self) -> None:
        # Gate 1: DISCOVER -> SPECIFY
        res = self.engine.record_gate_verdict(
            gate_id="GATE-01-DISCOVERY",
            passed=True,
            evidence="Context and architecture discovered cleanly.",
        )
        self.assertEqual(res.verdict, GateVerdict.PASSED)
        self.assertEqual(self.engine.current_state, LoopState.SPECIFY)

        # Gate 2: SPECIFY -> PLAN
        res2 = self.engine.record_gate_verdict(
            gate_id="GATE-02-SPECIFICATION",
            passed=True,
            evidence="SDD 6-file bundle approved.",
        )
        self.assertEqual(res2.verdict, GateVerdict.PASSED)
        self.assertEqual(self.engine.current_state, LoopState.PLAN)

    def test_plan_approval_gate_requires_human_approval(self) -> None:
        # Advance to APPROVAL
        self.engine.transition_to(LoopState.APPROVAL, reason="Test advance to APPROVAL")
        self.assertEqual(self.engine.current_state, LoopState.APPROVAL)

        # Approve plan
        res = self.engine.approve_plan(
            approved_by="Principal Architect",
            notes="Formal architecture and plan approved.",
        )
        self.assertEqual(res.verdict, GateVerdict.PASSED)
        self.assertEqual(self.engine.current_state, LoopState.IMPLEMENT)

    def test_circuit_breaker_trips_when_retries_exceeded(self) -> None:
        self.engine.transition_to(LoopState.TEST, reason="Advancing to test")
        
        # Max retries in config is 3
        # Attempt 1
        self.engine.record_gate_verdict("GATE-06-TEST", passed=False, evidence="Assertion error 1")
        self.assertFalse(self.engine.is_blocked)
        self.assertEqual(self.engine.state["retries"]["GATE-06-TEST"], 1)

        # Attempt 2
        self.engine.record_gate_verdict("GATE-06-TEST", passed=False, evidence="Assertion error 2")
        self.assertFalse(self.engine.is_blocked)
        self.assertEqual(self.engine.state["retries"]["GATE-06-TEST"], 2)

        # Attempt 3
        self.engine.record_gate_verdict("GATE-06-TEST", passed=False, evidence="Assertion error 3")
        self.assertFalse(self.engine.is_blocked)
        self.assertEqual(self.engine.state["retries"]["GATE-06-TEST"], 3)

        # Attempt 4: Exceeds max_retries (3) -> trips circuit breaker
        self.engine.record_gate_verdict("GATE-06-TEST", passed=False, evidence="Assertion error 4")
        self.assertTrue(self.engine.is_blocked)
        self.assertEqual(self.engine.current_state, LoopState.BLOCKED)
        self.assertIn("failed 4 times", self.engine.state["block_reason"])

    def test_introspection_report_generation(self) -> None:
        self.engine.record_gate_verdict(
            "GATE-08-SECURITY",
            passed=False,
            evidence="Secret detected in mock test",
            details={"file": "foo.py", "line": 42},
        )
        report = self.engine.generate_introspection_report("GATE-08-SECURITY")
        self.assertEqual(report["gate_id"], "GATE-08-SECURITY")
        self.assertEqual(report["retry_count"], 1)
        self.assertEqual(report["retry_budget_remaining"], 2)
        self.assertIn("Secret detected", report["evidence"])

    def test_reset_and_unblock(self) -> None:
        self.engine.trip_circuit_breaker("Simulated fault")
        self.assertTrue(self.engine.is_blocked)

        # Unblock
        self.engine.transition_to(LoopState.IMPLEMENT, reason="Unblocked by engineer")
        self.assertFalse(self.engine.is_blocked)
        self.assertEqual(self.engine.current_state, LoopState.IMPLEMENT)

        # Reset
        self.engine.reset(task_id="DONB-TEST-99", spec_id="SPEC-0019", title="Test Task")
        self.assertEqual(self.engine.current_state, LoopState.DISCOVER)
        self.assertEqual(self.engine.state["task_id"], "DONB-TEST-99")


if __name__ == "__main__":
    unittest.main()
