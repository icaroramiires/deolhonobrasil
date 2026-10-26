"""Unit and integration tests for the ECC Loop Engineering & SDD/Eval Harness."""

from __future__ import annotations

from pathlib import Path
import unittest

from deolhonobrasil.harness.runner import (
    run_full_harness,
    verify_gateguard_boundaries,
    verify_openspec_traceability,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestLoopEngineeringHarness(unittest.TestCase):
    """Verifies the Spec-Driven Development (SDD) and Eval Harness gates."""

    def test_openspec_traceability_gate_passes_and_resolves_anchors(self) -> None:
        result = verify_openspec_traceability(REPO_ROOT)
        self.assertTrue(result.passed, f"SDD Spec violations: {result.violations}")
        self.assertEqual(result.metrics["capabilities_checked"], 19)
        self.assertEqual(result.metrics["sdd_artifacts_verified"], 114)
        self.assertGreaterEqual(int(result.metrics["unique_requirements"]), 55)
        self.assertGreaterEqual(int(result.metrics["verified_test_anchors"]), 84)

    def test_gateguard_boundaries_confirm_frozen_entities_and_eval_files(self) -> None:
        result = verify_gateguard_boundaries(REPO_ROOT)
        self.assertTrue(result.passed, f"GateGuard violations: {result.violations}")
        self.assertEqual(result.metrics["frozen_domain_entities_verified"], 15)
        self.assertEqual(result.metrics["eval_definitions_verified"], 4)

    def test_wireframe_passes_achromatic_ledger_structural_invariants(self) -> None:
        wireframe_path = REPO_ROOT / "wireframe_de_olho_no_brasil.html"
        self.assertTrue(wireframe_path.exists())
        html = wireframe_path.read_text(encoding="utf-8")
        self.assertIn("[DADO OFICIAL]", html)
        self.assertIn("[INFERÊNCIA ESTATÍSTICA]", html)
        self.assertTrue(
            "[LIMITAÇÃO E HIPÓTESE]" in html or "[HIPÓTESE DE AUDITORIA / LIMITAÇÃO]" in html
        )
        self.assertIn("tabular-nums", html)
        self.assertIn("SHA-256", html)

    def test_full_harness_report_serializes_cleanly(self) -> None:
        report = run_full_harness(repo_root=REPO_ROOT, checkpoint=2, trials=1)
        self.assertTrue(report.overall_passed, f"Gates: {report.gates}")
        self.assertEqual(report.pass_at_1, 1.0)
        payload = report.to_dict()
        self.assertEqual(payload["checkpoint"], 2)


if __name__ == "__main__":
    unittest.main()
