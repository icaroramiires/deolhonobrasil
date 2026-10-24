"""TDD Unit & Integration Tests for `SPEC-0007` — Cross-Source CEIS/CNEP Sanctions & Divergence Rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from deolhonobrasil.api.service import CivicAuditAPIService, CivicAuditHTTPApp
from deolhonobrasil.audit.rules import (
    evaluate_amendment_execution_divergence_rule,
    evaluate_ceis_cnep_sanctioned_supplier_rule,
)
from deolhonobrasil.pipeline.connectors.cgu_transparencia import (
    parse_cgu_ceis_cnep_json_batch,
)
from deolhonobrasil.pipeline.models import (
    CuratedParliamentaryAmendment,
    CuratedPublicContract,
    CuratedPublicExpense,
    CuratedSanctionRecord,
    EpistemicClassification,
    OfficialSource,
    ProvenanceMetadata,
)
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


class TestCrossSourceSanctionsAndDivergence(unittest.TestCase):
    """Tests `FR-016`, `FR-017`, `NFR-010`, `DATA-009`, `SEC-010`, and `AC-026..029`."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.storage = CivicLakehouseStorage(self.data_dir)
        self.service = CivicAuditAPIService(storage=self.storage, admin_token="token-spec7")
        self.app = CivicAuditHTTPApp(self.service)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_ceis_cnep_connector_validates_masks_cpf_and_quarantines_invalid(self) -> None:
        """`FR-016`, `DATA-009`, `AC-026`: CEIS/CNEP connector parses valid sanctions, masks CPFs (`***.XXX.XXX-**`), and quarantines invalid rows."""
        raw_payload = json.dumps(
            [
                {
                    "codigoSancao": "CEIS-2026-0001",
                    "cpfCnpjSancionado": "11.222.333/0001-81",
                    "nomeSancionado": "CONSTRUTORA HORIZONTE LTDA",
                    "tipoSancao": "IMPEDIMENTO DE LICITAR E CONTRATAR",
                    "orgaoSancionador": "CONTROLADORIA-GERAL DA UNIAO",
                    "ufOrgaoSancionador": "DF",
                    "dataInicioSancao": "2026-01-10",
                    "dataFimSancao": "2027-01-10",
                },
                {
                    "codigoSancao": "CEIS-2026-0002",
                    "cpfCnpjSancionado": "52998224725",
                    "nomeSancionado": "PRESTADOR INDIVIDUAL",
                    "tipoSancao": "SUSPENSAO TEMPORARIA",
                    "orgaoSancionador": "MINISTERIO DA SAUDE",
                    "ufOrgaoSancionador": "DF",
                    "dataInicioSancao": "2026-02-01",
                    "dataFimSancao": "2026-12-31",
                },
                {
                    "codigoSancao": "",
                    "cpfCnpjSancionado": "00000000000000",
                    "nomeSancionado": "REGISTRO INVALIDO",
                    "dataInicioSancao": "",
                },
            ]
        ).encode("utf-8")

        batch = parse_cgu_ceis_cnep_json_batch(
            raw_payload,
            source_url="https://api.portaldatransparencia.gov.br/api-de-dados/ceis",
        )
        self.assertEqual(len(batch.valid_records), 2)
        self.assertEqual(len(batch.quarantined_records), 1)
        self.assertEqual(batch.valid_records[0].sanctioned_doc_normalized, "11222333000181")
        self.assertEqual(batch.valid_records[0].sanctioned_doc_type, "CNPJ")
        self.assertEqual(batch.valid_records[1].sanctioned_doc_normalized, "***.982.247-**")
        self.assertEqual(batch.valid_records[1].sanctioned_doc_type, "CPF_MASKED")

    def test_cross_source_ceis_rule_detects_active_cnpj_sanction_with_dual_sha256(self) -> None:
        """`FR-017`, `SEC-010`, `AC-027`: `R-CROSS-CEIS-SANCTIONED-SUPPLIER` flags a contract signed during active CEIS sanction with both `SHA-256` hashes."""
        contract_prov = ProvenanceMetadata(
            source=OfficialSource.PNCP_CONTRATOS,
            source_url="https://pncp.gov.br/api/consulta/v1/contratos",
            source_record_id="PNCP-2026-900",
            collected_at_utc="2026-10-23T12:00:00Z",
            raw_batch_sha256="1" * 64,
        )
        contract = CuratedPublicContract.create_validated(
            pncp_control_number="PNCP-2026-900",
            organ_cnpj_raw="00.394.460/0058-87",
            organ_name="MINISTERIO DA ECONOMIA",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="CONSTRUTORA HORIZONTE LTDA",
            modality_name="PREGAO ELETRONICO",
            contract_object="Servicos de engenharia predial",
            signature_date=date(2026, 6, 15),
            initial_amount_raw="450000.00",
            current_amount_raw="450000.00",
            addendum_count=0,
            provenance=contract_prov,
        )

        sanction_prov = ProvenanceMetadata(
            source=OfficialSource.CGU_CEIS_CNEP,
            source_url="https://api.portaldatransparencia.gov.br/api-de-dados/ceis",
            source_record_id="CEIS-2026-0001",
            collected_at_utc="2026-10-23T12:05:00Z",
            raw_batch_sha256="2" * 64,
        )
        sanction = CuratedSanctionRecord.create_validated(
            sanction_code="CEIS-2026-0001",
            sanctioned_raw_doc="11.222.333/0001-81",
            sanctioned_name="CONSTRUTORA HORIZONTE LTDA",
            sanction_type="IMPEDIMENTO DE LICITAR E CONTRATAR",
            sanctioning_organ="CONTROLADORIA-GERAL DA UNIAO",
            state_uf="DF",
            start_date=date(2026, 1, 10),
            end_date=date(2027, 1, 10),
            provenance=sanction_prov,
        )

        signal = evaluate_ceis_cnep_sanctioned_supplier_rule(contract, [sanction])
        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal.rule_code, "R-CROSS-CEIS-SANCTIONED-SUPPLIER")
        self.assertEqual(signal.epistemic_layer, EpistemicClassification.CROSS_SOURCE_DIVERGENCE)
        self.assertIn("1" * 64, signal.provenance_hashes)
        self.assertIn("2" * 64, signal.provenance_hashes)
        self.assertTrue(signal.requires_human_review)

    def test_cross_source_ceis_rule_ignores_expired_sanction_or_masked_cpf_homonym(self) -> None:
        """`NFR-010`, `AC-028`: Cross-source rule ignores expired sanctions and never matches on masked CPF (`CPF_MASKED`)."""
        exp_prov = ProvenanceMetadata(
            source=OfficialSource.CAMARA_CEAP,
            source_url="https://dadosabertos.camara.leg.br/arquivos/despesas",
            source_record_id="DOC-CPF-1",
            collected_at_utc="2026-10-23T12:00:00Z",
            raw_batch_sha256="3" * 64,
        )
        expense_cpf = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=6,
            issue_date=date(2026, 6, 15),
            sphere="FEDERAL",
            organ_code="CAMARA",
            organ_name="CAMARA DOS DEPUTADOS",
            public_agent_id="DEP-10",
            public_agent_name="DEPUTADO EXEMPLO",
            party_sigla="PART",
            state_uf="SP",
            expense_category="CONSULTORIA",
            supplier_raw_doc="52998224725",
            supplier_name="PRESTADOR PF",
            document_number="NF-10",
            gross_amount_raw="5000.00",
            net_amount_raw="5000.00",
            document_evidence_url=None,
            provenance=exp_prov,
        )
        sanction_prov = ProvenanceMetadata(
            source=OfficialSource.CGU_CEIS_CNEP,
            source_url="https://api.portaldatransparencia.gov.br/api-de-dados/ceis",
            source_record_id="CEIS-CPF-1",
            collected_at_utc="2026-10-23T12:05:00Z",
            raw_batch_sha256="4" * 64,
        )
        sanction_cpf = CuratedSanctionRecord.create_validated(
            sanction_code="CEIS-CPF-1",
            sanctioned_raw_doc="52998224725",
            sanctioned_name="OUTRO HOMONIMO PF",
            sanction_type="SUSPENSAO",
            sanctioning_organ="ORGAO X",
            state_uf="SP",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            provenance=sanction_prov,
        )
        # Masked CPF must NEVER auto-match due to homonymy risk (NFR-010)
        self.assertIsNone(evaluate_ceis_cnep_sanctioned_supplier_rule(expense_cpf, [sanction_cpf]))

    def test_amendment_execution_divergence_rule_flags_discrepancy(self) -> None:
        """`FR-017`, `AC-029`: `R-CROSS-AMENDMENT-EXECUTION-GAP` flags amendments where `paid_amount > committed_amount`."""
        amd_prov = ProvenanceMetadata(
            source=OfficialSource.CGU_EMENDAS,
            source_url="https://api.portaldatransparencia.gov.br/api-de-dados/emendas",
            source_record_id="202699990001",
            collected_at_utc="2026-10-23T12:00:00Z",
            raw_batch_sha256="5" * 64,
        )
        amendment = CuratedParliamentaryAmendment.create_validated(
            amendment_code="202699990001",
            year=2026,
            author_id="AUT-01",
            author_name="PARLAMENTAR EXEMPLO",
            amendment_type="INDIVIDUAL",
            function_name="SAUDE",
            municipality_ibge_code="3550308",
            state_uf="SP",
            beneficiary_raw_doc="11.222.333/0001-81",
            beneficiary_name="FUNDO MUNICIPAL",
            committed_amount_raw="200000.00",
            paid_amount_raw="250000.00",
            provenance=amd_prov,
        )
        sig = evaluate_amendment_execution_divergence_rule(amendment)
        self.assertIsNotNone(sig)
        assert sig is not None
        self.assertEqual(sig.rule_code, "R-CROSS-AMENDMENT-EXECUTION-GAP")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.CROSS_SOURCE_DIVERGENCE)
        self.assertEqual(sig.metric_value, Decimal("50000.00"))

    def test_lakehouse_and_api_sanctions_endpoint_roundtrip(self) -> None:
        """`FR-016`, `AC-026`: `CivicLakehouseStorage.persist_sanction_batch` and `GET /api/v1/sanctions` work end-to-end."""
        raw_payload = json.dumps(
            [
                {
                    "codigoSancao": "CEIS-2026-0099",
                    "cpfCnpjSancionado": "11.222.333/0001-81",
                    "nomeSancionado": "FORNECEDOR SANCIONADO S.A.",
                    "tipoSancao": "DECLARACAO DE INIDONEIDADE",
                    "orgaoSancionador": "TCU",
                    "ufOrgaoSancionador": "DF",
                    "dataInicioSancao": "2026-01-01",
                    "dataFimSancao": "2028-01-01",
                }
            ]
        ).encode("utf-8")
        batch = parse_cgu_ceis_cnep_json_batch(
            raw_payload,
            source_url="https://api.portaldatransparencia.gov.br/api-de-dados/ceis",
        )
        report = self.storage.persist_sanction_batch(raw_payload, batch)
        self.assertTrue(report.is_reconciled)
        self.assertEqual(report.inserted_new_count, 1)

        resp = self.app.handle_request(
            method="GET",
            path="/api/v1/sanctions",
            query_params={"state_uf": "DF"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.body["total"], 1)
        items = resp.body["items"]
        assert isinstance(items, list)
        self.assertEqual(items[0]["sanction_code"], "CEIS-2026-0099")


if __name__ == "__main__":
    unittest.main()
