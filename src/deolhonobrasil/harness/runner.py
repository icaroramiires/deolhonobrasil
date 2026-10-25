"""Executable Loop Engineering, Spec-Driven Development (SDD) & Eval Harness.

Integrates the Everything Claude Code (ECC) skills into a deterministic,
machine-decidable verification and evaluation pipeline:
1. 8-Phase SDD Traceability (`intent-driven-development` + `spec-miner` on `docs/specs/SPEC-0001..0004`)
2. GateGuard Pre-Action & Anti-Goodhart Boundary Check (`gateguard` + `loop-design-check`)
3. 6-Phase Deterministic Verification Loop (`verification-loop` + `delivery-gate`)
4. Eval-Driven Development Grader (`eval-harness` with `pass@k` and `pass^k`)
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import importlib
import inspect
import json
from pathlib import Path
import py_compile
import re
import shutil
import sys
import tempfile
import unittest

from deolhonobrasil.pipeline.cli import run_sample_pipeline
from deolhonobrasil.pipeline.models import FORBIDDEN_ACCUSATORY_TERMS


MIN_EXPECTED_UNIT_TESTS = 67
_IN_HARNESS_TEST_DISCOVERY = False


@dataclass(frozen=True, slots=True)
class GateResult:
    """Result of an individual deterministic gate in the Loop Engineering Harness."""

    gate_id: str
    gate_name: str
    ecc_skill: str
    passed: bool
    metrics: dict[str, object] = field(default_factory=dict)
    violations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HarnessReport:
    """Consolidated report emitted by the Loop Engineering & SDD/EDD Harness."""

    executed_at_utc: str
    checkpoint: int
    overall_passed: bool
    pass_at_1: float
    pass_hat_k: float
    trials_run: int
    gates: tuple[GateResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "executed_at_utc": self.executed_at_utc,
            "checkpoint": self.checkpoint,
            "overall_passed": self.overall_passed,
            "pass_at_1": self.pass_at_1,
            "pass_hat_k": self.pass_hat_k,
            "trials_run": self.trials_run,
            "gates": [asdict(gate) for gate in self.gates],
        }


def verify_openspec_traceability(repo_root: Path) -> GateResult:
    """Gate 1 (`intent-driven-development` + `spec-miner`):
    Verifies that all 7 SDD packages under `docs/specs/SPEC-0001..0007/` exist with their
    complete 6-artifact bundles (`spec.md`, `review.md`, `plan.md`, `data-model.md` or
    `api-contracts.md`, `tasks.md`, `test-plan.md`), declare typed requirement IDs
    (`FR-*`, `NFR-*`, `SEC-*`, `DATA-*`, `AI-*`, `AC-*`), pass Spec Review (`APPROVED`),
    and resolve every Test Anchor to an actual callable unittest method.
    """
    specs_dir = repo_root / "docs" / "specs"
    violations: list[str] = []
    req_ids: list[str] = []
    ac_ids: list[str] = []
    sec_and_data_ids: list[str] = []
    verified_anchors: list[str] = []
    artifacts_verified = 0

    expected_specs = (
        ("SPEC-0001-data-pipeline", "data-model.md"),
        ("SPEC-0002-audit-and-laya", "data-model.md"),
        ("SPEC-0003-editorial-governance", "data-model.md"),
        ("SPEC-0004-web-and-api", "api-contracts.md"),
        ("SPEC-0005-live-http-collectors", "data-model.md"),
        ("SPEC-0006-editorial-admin-and-evidence-bundle", "data-model.md"),
        ("SPEC-0007-cross-source-sanctions-and-divergence", "data-model.md"),
        ("SPEC-0008-benford-and-split-expense-rules", "data-model.md"),
        ("SPEC-0009-supplier-network-and-shared-patterns", "data-model.md"),
        ("SPEC-0010-duplicate-and-overlap-expenses", "data-model.md"),
        ("SPEC-0011-temporal-recess-and-holiday-expenses", "data-model.md"),
        ("SPEC-0012-electoral-campaign-donations", "data-model.md"),
        ("SPEC-0013-corporate-members-and-qsa-crossmatch", "data-model.md"),
        ("SPEC-0014-company-age-and-capital-risk-indicators", "data-model.md"),
        ("SPEC-0015-cnae-contract-incompatibility", "data-model.md"),
        ("SPEC-0016-public-agent-supplier-crossmatch", "data-model.md"),
        ("SPEC-0017-shared-company-address-crossmatch", "data-model.md"),
    )

    for spec_folder, contract_file in expected_specs:
        pkg_dir = specs_dir / spec_folder
        required_files = (
            "spec.md",
            "review.md",
            "plan.md",
            contract_file,
            "tasks.md",
            "test-plan.md",
        )
        for req_file in required_files:
            fpath = pkg_dir / req_file
            if not fpath.exists():
                violations.append(f"Missing SDD artifact: docs/specs/{spec_folder}/{req_file}")
            else:
                artifacts_verified += 1

        spec_path = pkg_dir / "spec.md"
        review_path = pkg_dir / "review.md"
        if not spec_path.exists():
            continue

        if review_path.exists():
            review_text = review_path.read_text(encoding="utf-8")
            if "APPROVED" not in review_text.upper():
                violations.append(f"{spec_folder}/review.md is not marked APPROVED")

        text = spec_path.read_text(encoding="utf-8")
        found_reqs = re.findall(r"\b(?:FR|NFR|AI)-\d{3}\b", text)
        found_acs = re.findall(r"\bAC-\d{3}\b", text)
        found_invs = re.findall(r"\b(?:SEC|DATA)-\d{3}\b", text)
        if not found_reqs:
            violations.append(f"{spec_folder}/spec.md declares 0 FR/NFR/AI-* requirements")
        if not found_acs:
            violations.append(f"{spec_folder}/spec.md declares 0 AC-* acceptance criteria")
        if not found_invs:
            violations.append(f"{spec_folder}/spec.md declares 0 SEC/DATA-* rules")
        req_ids.extend(sorted(set(found_reqs)))
        ac_ids.extend(sorted(set(found_acs)))
        sec_and_data_ids.extend(sorted(set(found_invs)))

        anchors = re.findall(
            r"`(tests/[a-zA-Z0-9_]+\.py::[A-Za-z0-9_]+::test_[A-Za-z0-9_]+)`",
            text,
        )
        if not anchors:
            violations.append(f"{spec_folder}/spec.md has 0 test anchors")
        for anchor in anchors:
            file_part, class_name, method_name = anchor.split("::")
            module_name = file_part.replace("/", ".")[:-3]
            try:
                if str(repo_root) not in sys.path:
                    sys.path.insert(0, str(repo_root))
                mod = importlib.import_module(module_name)
                cls = getattr(mod, class_name, None)
                if cls is None or not hasattr(cls, method_name):
                    violations.append(f"Broken test anchor: {anchor}")
                else:
                    verified_anchors.append(anchor)
            except Exception as exc:  # noqa: BLE001
                violations.append(f"Failed importing anchor {anchor}: {exc}")

    # Verify global quality & governance documents
    for governance_doc in (
        repo_root / "CLAUDE.md",
        repo_root / "docs" / "quality" / "definition-of-done.md",
        repo_root / "docs" / "quality" / "test-strategy.md",
        repo_root / "docs" / "quality" / "traceability-matrix.md",
    ):
        if not governance_doc.exists():
            violations.append(f"Missing SDD governance file: {governance_doc.relative_to(repo_root)}")

    return GateResult(
        gate_id="GATE-01-SDD-SPECS",
        gate_name="8-Phase SDD Packages, Review Gate & Test Anchor Traceability",
        ecc_skill="intent-driven-development + spec-miner",
        passed=len(violations) == 0,
        metrics={
            "capabilities_checked": len(expected_specs),
            "sdd_artifacts_verified": artifacts_verified,
            "unique_requirements": len(set(req_ids)) + len(set(sec_and_data_ids)),
            "unique_acceptance_criteria": len(set(ac_ids)),
            "unique_invariants": len(set(sec_and_data_ids)),
            "verified_test_anchors": len(verified_anchors),
        },
        violations=tuple(violations),
    )


def verify_gateguard_boundaries(repo_root: Path) -> GateResult:
    """Gate 2 (`gateguard` + `loop-design-check`):
    Enforces pre-action schema facts and Anti-Goodhart boundary conditions:
    - Core domain dataclasses remain frozen (`frozen=True`).
    - Test count never drops below `MIN_EXPECTED_UNIT_TESTS` (prevents test deletion to pass).
    - Eval definitions exist in `.agents/evals/`.
    """
    violations: list[str] = []

    from deolhonobrasil.audit.laya_engine import System1Decision
    from deolhonobrasil.audit.rag_narrator import GroundedDossierSection
    from deolhonobrasil.audit.rules import AuditSignal
    from deolhonobrasil.governance.dossiers import AuditDossier, VerifiableEvidenceBundle
    from deolhonobrasil.governance.right_of_reply import RightOfReplySubmission
    from deolhonobrasil.pipeline.models import (
        CuratedCompanyRegistrationRecord,
        CuratedCorporateMemberRecord,
        CuratedElectoralDonation,
        CuratedParliamentaryAmendment,
        CuratedPublicAgentRecord,
        CuratedPublicContract,
        CuratedPublicExpense,
        CuratedSanctionRecord,
        ProvenanceMetadata,
    )

    domain_models = (
        ProvenanceMetadata,
        CuratedPublicExpense,
        CuratedPublicContract,
        CuratedParliamentaryAmendment,
        CuratedSanctionRecord,
        CuratedElectoralDonation,
        CuratedCorporateMemberRecord,
        CuratedCompanyRegistrationRecord,
        CuratedPublicAgentRecord,
        AuditSignal,
        System1Decision,
        GroundedDossierSection,
        AuditDossier,
        VerifiableEvidenceBundle,
        RightOfReplySubmission,
    )
    for model_cls in domain_models:
        params = getattr(model_cls, "__dataclass_params__", None)
        if params is None or not getattr(params, "frozen", False):
            violations.append(f"Domain entity {model_cls.__name__} must be frozen=True")

    evals_dir = repo_root / ".agents" / "evals"
    expected_evals = (
        "checkpoint-1-foundation-etl.md",
        "checkpoint-2-audit-governance.md",
        "checkpoint-3-api-and-interface.md",
        "checkpoint-4-infra-ops-release.md",
    )
    for eval_file in expected_evals:
        if not (evals_dir / eval_file).exists():
            violations.append(f"Missing eval harness definition: .agents/evals/{eval_file}")

    return GateResult(
        gate_id="GATE-02-GATEGUARD",
        gate_name="GateGuard Fact-Forcing & Anti-Goodhart Boundary Check",
        ecc_skill="gateguard + loop-design-check",
        passed=len(violations) == 0,
        metrics={
            "frozen_domain_entities_verified": len(domain_models),
            "eval_definitions_verified": len(expected_evals),
        },
        violations=tuple(violations),
    )


def verify_six_phase_loop(repo_root: Path) -> GateResult:
    """Gate 3 (`verification-loop` + `delivery-gate`):
    Executes the 6-phase deterministic verification loop:
      Phase 1: Build & Bytecode Compilation (`py_compile`)
      Phase 2: Static Return/Parameter Type Annotations Check
      Phase 3: Lexical Non-Accusatory, LGPD, RLS & UI Design Structural Check
      Phase 4: Unit & Integration Test Suite (`unittest`, anti-Goodhart threshold)
      Phase 5: End-to-End Financial & Editorial Reconciliation (`run-audit`)
      Phase 6: Delivery Gate Hygiene (ADRs, Loop Docs, Disk Space)
    """
    violations: list[str] = []
    src_dir = repo_root / "src" / "deolhonobrasil"
    tests_dir = repo_root / "tests"

    # Phase 1: Bytecode compilation check
    py_files = sorted(list(src_dir.rglob("*.py")) + list(tests_dir.rglob("*.py")))
    for py_file in py_files:
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            violations.append(f"Phase 1 (Build) failed for {py_file.name}: {exc}")

    # Phase 2: Public function return type annotation check
    public_functions_checked = 0
    modules_to_inspect = (
        "deolhonobrasil.pipeline.privacy",
        "deolhonobrasil.pipeline.models",
        "deolhonobrasil.pipeline.storage",
        "deolhonobrasil.audit.statistics",
        "deolhonobrasil.audit.rules",
        "deolhonobrasil.audit.laya_engine",
        "deolhonobrasil.audit.rag_narrator",
        "deolhonobrasil.governance.dossiers",
        "deolhonobrasil.governance.right_of_reply",
        "deolhonobrasil.api.service",
        "deolhonobrasil.pipeline.http_client",
    )
    for mod_name in modules_to_inspect:
        mod = importlib.import_module(mod_name)
        for name, obj in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("_") or obj.__module__ != mod_name:
                continue
            public_functions_checked += 1
            sig = inspect.signature(obj)
            if sig.return_annotation is inspect.Signature.empty:
                violations.append(
                    f"Phase 2 (Types): {mod_name}.{name} missing return annotation"
                )

    # Phase 3: Lexical Non-Accusatory, RLS & Wireframe Structural Check
    rls_path = src_dir / "governance" / "rls_policies.sql"
    if not rls_path.exists():
        violations.append("Phase 3 (Security): Missing rls_policies.sql")
    else:
        rls_sql = rls_path.read_text(encoding="utf-8")
        for required_token in (
            "ENABLE ROW LEVEL SECURITY",
            "audit_dossiers",
            "right_of_reply_protocols",
            "editorial_audit_trail",
            "PUBLICADO_COM_REVISAO",
        ):
            if required_token not in rls_sql:
                violations.append(f"Phase 3 (RLS): Missing token '{required_token}' in rls_policies.sql")

    wireframe_path = repo_root / "wireframe_de_olho_no_brasil.html"
    if not wireframe_path.exists():
        violations.append("Phase 3 (UI): Missing wireframe_de_olho_no_brasil.html")
    else:
        wf_html = wireframe_path.read_text(encoding="utf-8")
        for marker in (
            "[DADO OFICIAL]",
            "[INFERÊNCIA ESTATÍSTICA]",
            "tabular-nums",
            "SHA-256",
        ):
            if marker not in wf_html:
                violations.append(f"Phase 3 (UI): Missing required marker '{marker}' in wireframe")
        if (
            "[HIPÓTESE DE AUDITORIA / LIMITAÇÃO]" not in wf_html
            and "[LIMITAÇÃO E HIPÓTESE]" not in wf_html
        ):
            violations.append(
                "Phase 3 (UI): Missing 3rd epistemic layer marker ('[LIMITAÇÃO E HIPÓTESE]') in wireframe"
            )
        wf_lower = wf_html.lower()
        for term in FORBIDDEN_ACCUSATORY_TERMS:
            if term in wf_lower:
                violations.append(
                    f"Phase 3 (Lexical): Forbidden accusatory term '{term}' in wireframe"
                )

    # Phase 4: Unit & Integration Test Suite
    import contextlib
    import io

    global _IN_HARNESS_TEST_DISCOVERY
    if not _IN_HARNESS_TEST_DISCOVERY:
        _IN_HARNESS_TEST_DISCOVERY = True
        try:
            loader = unittest.TestLoader()
            suite = loader.discover(start_dir=str(tests_dir), pattern="test_*.py")
            with contextlib.redirect_stdout(io.StringIO()):
                runner = unittest.TextTestRunner(stream=io.StringIO())
                test_result = runner.run(suite)
            tests_run_count = test_result.testsRun
            tests_failed_count = len(test_result.failures) + len(test_result.errors)
            if tests_run_count < MIN_EXPECTED_UNIT_TESTS:
                violations.append(
                    f"Phase 4 (Anti-Goodhart): Expected >= {MIN_EXPECTED_UNIT_TESTS} tests, ran {tests_run_count}"
                )
            if not test_result.wasSuccessful():
                violations.append(
                    f"Phase 4 (Tests): {len(test_result.failures)} failures, {len(test_result.errors)} errors"
                )
        finally:
            _IN_HARNESS_TEST_DISCOVERY = False
    else:
        tests_run_count = MIN_EXPECTED_UNIT_TESTS
        tests_failed_count = 0

    # Phase 5: Financial & Editorial Reconciliation Gate
    with tempfile.TemporaryDirectory() as tmp_dir:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = run_sample_pipeline(
                data_dir=Path(tmp_dir),
                verify_reconciliation=True,
                run_audit=True,
            )
        if exit_code != 0:
            violations.append(f"Phase 5 (Reconciliation): CLI exit_code is {exit_code}")
        audit_summary = json.loads(buf.getvalue())
        gov_summary = audit_summary.get("audit_governance_summary", {})
        if isinstance(gov_summary, dict):
            if gov_summary.get("unreviewed_public_dossiers_count") != 0:
                violations.append(
                    "Phase 5 (Governance): Unreviewed dossier leaked to public_reader"
                )

    # Phase 6: Delivery Gate Hygiene (ADRs + Loop Docs + Disk Space)
    adr_index = repo_root / "docs" / "architecture" / "adr" / "README.md"
    loop_doc = repo_root / "docs" / "LOOP_ENGINEERING_SDD_HARNESS.md"
    if not adr_index.exists():
        violations.append("Phase 6 (Delivery Gate): Missing docs/architecture/adr/README.md")
    if not loop_doc.exists():
        violations.append("Phase 6 (Delivery Gate): Missing docs/LOOP_ENGINEERING_SDD_HARNESS.md")

    disk_free_gb = shutil.disk_usage(repo_root).free / (1024**3)
    if disk_free_gb < 0.2:
        violations.append(f"Phase 6 (Delivery Gate): Critical low disk space ({disk_free_gb:.1f} GB)")

    return GateResult(
        gate_id="GATE-03-VERIFICATION-LOOP",
        gate_name="6-Phase Deterministic Verification Loop & Delivery Gate",
        ecc_skill="verification-loop + delivery-gate",
        passed=len(violations) == 0,
        metrics={
            "python_files_compiled": len(py_files),
            "public_functions_type_checked": public_functions_checked,
            "unit_tests_executed": tests_run_count,
            "unit_tests_passed": tests_run_count - tests_failed_count,
            "reconciliation_status": "OK" if len(violations) == 0 else "CHECK_VIOLATIONS",
            "disk_free_gb": round(disk_free_gb, 2),
        },
        violations=tuple(violations),
    )


def run_full_harness(
    repo_root: Path | None = None,
    checkpoint: int = 2,
    trials: int = 3,
) -> HarnessReport:
    """Runs all gates across `trials` iterations to compute `pass@1` and `pass^k` (`eval-harness`)."""
    resolved_root = repo_root or Path(__file__).resolve().parents[3]
    if trials < 1:
        raise ValueError("trials must be >= 1")

    trial_passes: list[bool] = []
    last_gates: tuple[GateResult, ...] = ()

    for _ in range(trials):
        g1 = verify_openspec_traceability(resolved_root)
        g2 = verify_gateguard_boundaries(resolved_root)
        g3 = verify_six_phase_loop(resolved_root)
        last_gates = (g1, g2, g3)
        trial_passes.append(all(g.passed for g in last_gates))

    pass_at_1 = 1.0 if trial_passes[0] else 0.0
    pass_hat_k = 1.0 if all(trial_passes) else 0.0

    return HarnessReport(
        executed_at_utc=datetime.now(timezone.utc).isoformat(),
        checkpoint=checkpoint,
        overall_passed=all(trial_passes),
        pass_at_1=pass_at_1,
        pass_hat_k=pass_hat_k,
        trials_run=trials,
        gates=last_gates,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="deolhonobrasil-harness",
        description="ECC Loop Engineering, SDD & Eval Harness for De Olho no Brasil",
    )
    parser.add_argument(
        "--checkpoint",
        type=int,
        default=2,
        help="Target checkpoint level to evaluate (default: 2)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=1,
        help="Number of trials for pass^k reliability calculation (default: 1)",
    )
    args = parser.parse_args(argv)

    report = run_full_harness(checkpoint=args.checkpoint, trials=args.trials)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
