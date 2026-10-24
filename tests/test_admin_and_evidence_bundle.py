"""TDD Unit & Integration Tests for `SPEC-0006` — Editorial Admin API & Verifiable Evidence Bundle."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from deolhonobrasil.api.service import CivicAuditAPIService, CivicAuditHTTPApp
from deolhonobrasil.audit.laya_engine import LayaSystem1Adapter
from deolhonobrasil.audit.rag_narrator import GroundedDossierNarrator
from deolhonobrasil.audit.rules import AuditSignal
from deolhonobrasil.governance.dossiers import (
    AuditDossier,
    DossierStatus,
    VerifiableEvidenceBundle,
)
from deolhonobrasil.pipeline.models import EpistemicClassification
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


class TestEditorialAdminAndEvidenceBundle(unittest.TestCase):
    """Tests `FR-014`, `FR-015`, `NFR-009`, `DATA-008`, `SEC-009`, and `AC-022..025`."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.storage = CivicLakehouseStorage(self.data_dir)
        self.admin_token = "admin-secret-token-spec0006"
        self.service = CivicAuditAPIService(
            storage=self.storage,
            admin_token=self.admin_token,
        )
        self.app = CivicAuditHTTPApp(self.service)

        signal = AuditSignal(
            signal_id="SIG-SPEC6-001",
            rule_code="R-CEAP-OUTLIER-Z3",
            title="Sinal estatístico de dispersão em cota parlamentar para verificação documental",
            official_fact_summary="Nota fiscal registrada no valor líquido de R$ 15.000,00.",
            statistical_inference_summary="Z-Score paramétrico de 4.20 acima da média de pares.",
            scope_limitation_summary="Sinal quantitativo preliminar que exige conferência documental.",
            epistemic_layer=EpistemicClassification.STATISTICAL_ANOMALY,
            metric_name="z_score",
            metric_value=Decimal("4.20"),
            threshold_value=Decimal("3.00"),
            audited_amount=Decimal("15000.00"),
            provenance_hashes=("a" * 64,),
            requires_human_review=True,
        )
        laya = LayaSystem1Adapter().evaluate(signal)
        sections = GroundedDossierNarrator().generate(signal, laya)
        self.triage_dossier = AuditDossier(
            dossier_id="DOS-SPEC6-001",
            signal=signal,
            laya_decision=laya,
            grounded_sections=sections,
            status=DossierStatus.EM_TRIAGEM_INTERNA,
            reviewer_id=None,
            right_of_reply=None,
            correction_note=None,
            updated_at_utc="2026-10-23T21:00:00Z",
        )
        self.storage.upsert_dossier(self.triage_dossier, actor_id="system_pipeline")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_admin_approve_dossier_requires_token_and_publishes_to_public(self) -> None:
        """`FR-014`, `SEC-009`, `AC-022`: Admin approval requires valid `X-Admin-Token` and transitions dossier to `PUBLICADO_COM_REVISAO`."""
        # 1. Without token -> 403 Forbidden
        unauthorized = self.app.handle_request(
            method="POST",
            path="/api/v1/admin/dossiers/approve",
            json_body={
                "dossier_id": "DOS-SPEC6-001",
                "reviewer_id": "auditor_chefe_01",
            },
        )
        self.assertEqual(unauthorized.status_code, 403)

        # 2. Public reader still sees 0 dossiers
        pub_before = self.app.handle_request(method="GET", path="/api/v1/dossiers")
        self.assertEqual(pub_before.body["total"], 0)

        # 3. With valid X-Admin-Token -> 200 OK & status PUBLICADO_COM_REVISAO
        approved = self.app.handle_request(
            method="POST",
            path="/api/v1/admin/dossiers/approve",
            headers={"X-Admin-Token": self.admin_token},
            json_body={
                "dossier_id": "DOS-SPEC6-001",
                "reviewer_id": "auditor_chefe_01",
            },
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.body["status"], DossierStatus.PUBLICADO_COM_REVISAO.value)
        self.assertEqual(approved.body["reviewer_id"], "auditor_chefe_01")

        # 4. Public reader now sees the approved dossier
        pub_after = self.app.handle_request(method="GET", path="/api/v1/dossiers")
        self.assertEqual(pub_after.body["total"], 1)

    def test_admin_rectify_material_error_updates_status_and_blocks_accusatory_note(self) -> None:
        """`FR-014`, `SEC-009`, `AC-023`: Material error rectification enforces non-accusatory language and records correction."""
        # 1. Accusatory correction_note is rejected with 422
        bad_rectify = self.app.handle_request(
            method="POST",
            path="/api/v1/admin/dossiers/rectify",
            headers={"X-Admin-Token": self.admin_token},
            json_body={
                "dossier_id": "DOS-SPEC6-001",
                "reviewer_id": "auditor_chefe_01",
                "correction_note": "Houve fraude comprovada no lançamento.",
            },
        )
        self.assertEqual(bad_rectify.status_code, 422)

        # 2. Valid technical correction_note transitions status to ERRO_MATERIAL_RETIFICADO
        ok_rectify = self.app.handle_request(
            method="POST",
            path="/api/v1/admin/dossiers/rectify",
            headers={"X-Admin-Token": self.admin_token},
            json_body={
                "dossier_id": "DOS-SPEC6-001",
                "reviewer_id": "auditor_chefe_01",
                "correction_note": "Retificação cadastral: nota fiscal cancelada e substituída na fonte oficial.",
            },
        )
        self.assertEqual(ok_rectify.status_code, 200)
        self.assertEqual(ok_rectify.body["status"], DossierStatus.ERRO_MATERIAL_RETIFICADO.value)
        self.assertIn("Retificação cadastral", str(ok_rectify.body["correction_note"]))

    def test_admin_audit_trail_endpoint_returns_immutable_history(self) -> None:
        """`FR-014`, `AC-023`: `GET /api/v1/admin/audit-trail` returns the append-only editorial history."""
        self.app.handle_request(
            method="POST",
            path="/api/v1/admin/dossiers/approve",
            headers={"X-Admin-Token": self.admin_token},
            json_body={
                "dossier_id": "DOS-SPEC6-001",
                "reviewer_id": "auditor_chefe_01",
            },
        )
        trail_resp = self.app.handle_request(
            method="GET",
            path="/api/v1/admin/audit-trail",
            query_params={"dossier_id": "DOS-SPEC6-001"},
            headers={"X-Admin-Token": self.admin_token},
        )
        self.assertEqual(trail_resp.status_code, 200)
        events = trail_resp.body["events"]
        assert isinstance(events, list)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["new_status"], "EM_TRIAGEM_INTERNA")
        self.assertEqual(events[1]["new_status"], "PUBLICADO_COM_REVISAO")
        self.assertEqual(events[1]["actor_id"], "auditor_chefe_01")

    def test_evidence_bundle_blocks_unreviewed_dossier_for_public_reader(self) -> None:
        """`FR-015`, `SEC-009`, `AC-024`: `public_reader` cannot export an evidence bundle for a dossier in `EM_TRIAGEM_INTERNA`."""
        blocked = self.app.handle_request(
            method="GET",
            path="/api/v1/dossiers/evidence-bundle",
            query_params={"dossier_id": "DOS-SPEC6-001"},
        )
        self.assertEqual(blocked.status_code, 404)

    def test_verifiable_evidence_bundle_canonical_sha256_integrity(self) -> None:
        """`FR-015`, `NFR-009`, `DATA-008`, `AC-025`: Published dossier exports a self-verifying `VerifiableEvidenceBundle`."""
        self.app.handle_request(
            method="POST",
            path="/api/v1/admin/dossiers/approve",
            headers={"X-Admin-Token": self.admin_token},
            json_body={
                "dossier_id": "DOS-SPEC6-001",
                "reviewer_id": "auditor_chefe_01",
            },
        )
        bundle_resp = self.app.handle_request(
            method="GET",
            path="/api/v1/dossiers/evidence-bundle",
            query_params={"dossier_id": "DOS-SPEC6-001"},
        )
        self.assertEqual(bundle_resp.status_code, 200)
        payload = bundle_resp.body
        self.assertEqual(payload["dossier_id"], "DOS-SPEC6-001")
        self.assertEqual(payload["status"], "PUBLICADO_COM_REVISAO")
        self.assertEqual(len(str(payload["bundle_sha256"])), 64)

        bundle_obj = VerifiableEvidenceBundle.from_dict(payload)
        self.assertTrue(bundle_obj.verify_integrity())


if __name__ == "__main__":
    unittest.main()
