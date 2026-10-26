"""TDD Unit Tests for SPEC-0018 — Burla à Sanção Administrativa e Impedimento de Licitar (QSA vs CEIS/CNEP).

Validates:
- `FR-038`: Systematic crossmatch between RFB QSA records and CGU CEIS/CNEP sanctions.
- `FR-039`: Deterministic rule `evaluate_sanctioned_partner_supplier_rule` (`R-CROSS-SANCTIONED-PARTNER`).
- `NFR-021`: Strict temporal validity window and anti-homonímia name+CPF matching.
- `DATA-020`: Triple cryptographic provenance chain (Sanction + QSA + Contract/Expense).
- `SEC-021`: Non-accusatory language, 3-layer epistemic separation, and Art. 14, § 1º, II / Art. 160 of Law 14.133/2021 limitation scope.
- `AC-070` to `AC-073`: Four acceptance criteria mapped to the 4 Test Anchors.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import (
    evaluate_sanctioned_partner_supplier_rule,
)
from deolhonobrasil.pipeline.models import (
    CuratedCorporateMemberRecord,
    CuratedPublicContract,
    CuratedPublicExpense,
    CuratedSanctionRecord,
    EpistemicClassification,
    OfficialSource,
    ProvenanceMetadata,
)


class TestSanctionedPartnerCrossmatchRules(unittest.TestCase):
    """Test suite for SPEC-0018 evaluating crossmatch between corporate partners and administrative sanctions."""

    def setUp(self) -> None:
        self.rfb_provenance = ProvenanceMetadata(
            source=OfficialSource.RECEITA_FEDERAL_CNPJ,
            source_url="https://dadosabertos.rfb.gov.br/CNPJ/socios.zip",
            source_record_id="RFB-QSA-BATCH-001",
            collected_at_utc="2026-10-26T08:00:00Z",
            raw_batch_sha256="1" * 64,
        )
        self.cgu_provenance = ProvenanceMetadata(
            source=OfficialSource.CGU_CEIS_CNEP,
            source_url="https://portaldatransparencia.gov.br/api-de-dados/ceis",
            source_record_id="CGU-CEIS-BATCH-001",
            collected_at_utc="2026-10-26T08:05:00Z",
            raw_batch_sha256="2" * 64,
        )
        self.pncp_provenance = ProvenanceMetadata(
            source=OfficialSource.PNCP_CONTRATOS,
            source_url="https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao",
            source_record_id="PNCP-BATCH-001",
            collected_at_utc="2026-10-26T08:10:00Z",
            raw_batch_sha256="3" * 64,
        )
        self.expense_provenance = ProvenanceMetadata(
            source=OfficialSource.CAMARA_CEAP,
            source_url="https://dadosabertos.camara.leg.br/api/v2/deputados/despesas",
            source_record_id="CEAP-BATCH-001",
            collected_at_utc="2026-10-26T08:15:00Z",
            raw_batch_sha256="4" * 64,
        )

    def test_sanctioned_partner_rule_detects_active_sanction_in_qsa(self) -> None:
        """Test Anchor 1 (`FR-038`, `FR-039`, `AC-070`): Detects active sanction on partner in QSA during contract validity."""
        # Member in QSA of company 12.345.678/0001-95
        member = CuratedCorporateMemberRecord(
            corporate_root_cnpj="12345678",
            full_cnpj_normalized="12.345.678/0001-95",
            member_name_raw="Carlos Eduardo da Silva",
            member_doc_masked="***.982.247-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2020-01-10",
            provenance=self.rfb_provenance,
        )

        # Active sanction in CEIS on the same person
        sanction = CuratedSanctionRecord.create_validated(
            sanction_code="CEIS-2025-0042",
            sanctioned_raw_doc="***.982.247-**",
            sanctioned_name="Carlos Eduardo da Silva",
            sanction_type="DECLARAÇÃO DE INIDONEIDADE",
            sanctioning_organ="TRIBUNAL DE CONTAS DA UNIAO",
            state_uf="DF",
            start_date=date(2025, 1, 1),
            end_date=date(2027, 1, 1),
            provenance=self.cgu_provenance,
        )

        # Contract executed on 2026-06-15 (within sanction period [2025-01-01, 2027-01-01])
        contract = CuratedPublicContract.create_validated(
            pncp_control_number="PNCP-2026-1234",
            organ_cnpj_raw="33.000.167/0001-01",
            organ_name="MINISTERIO DOS TRANSPORTES",
            supplier_raw_doc="12.345.678/0001-95",
            supplier_name="CONSTRUTORA ALVORADA LTDA",
            modality_name="PREGAO ELETRONICO",
            contract_object="OBRAS DE MANUTENCAO RODOVIARIA",
            signature_date=date(2026, 6, 15),
            initial_amount_raw="850000.00",
            current_amount_raw="850000.00",
            addendum_count=0,
            provenance=self.pncp_provenance,
        )

        signals = evaluate_sanctioned_partner_supplier_rule(
            corporate_members=[member],
            sanctions=[sanction],
            contracts=[contract],
        )

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-CROSS-SANCTIONED-PARTNER")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.CROSS_SOURCE_DIVERGENCE)
        self.assertEqual(sig.audited_amount, Decimal("850000.00"))
        self.assertTrue(sig.requires_human_review)

        # Verify Triple Provenance
        self.assertIn(self.rfb_provenance.raw_batch_sha256, sig.provenance_hashes)
        self.assertIn(self.cgu_provenance.raw_batch_sha256, sig.provenance_hashes)
        self.assertIn(self.pncp_provenance.raw_batch_sha256, sig.provenance_hashes)

        # Epistemic separation and non-accusatory language
        self.assertIn("MINISTERIO DOS TRANSPORTES", sig.official_fact_summary)
        self.assertIn("Carlos Eduardo da Silva", sig.official_fact_summary)
        self.assertIn("CEIS-2025-0042", sig.official_fact_summary)
        self.assertIn("art. 14, § 1º, inciso II e art. 160 da Lei nº 14.133/2021", sig.scope_limitation_summary)
        self.assertIn("Acórdãos nº 2.218/2012 e 1.637/2021-Plenário", sig.scope_limitation_summary)

    def test_sanctioned_partner_rule_ignores_expired_sanction(self) -> None:
        """Test Anchor 2 (`NFR-021`, `AC-071`): Ignores sanctions that expired before contract signature date."""
        member = CuratedCorporateMemberRecord(
            corporate_root_cnpj="12345678",
            full_cnpj_normalized="12.345.678/0001-95",
            member_name_raw="Carlos Eduardo da Silva",
            member_doc_masked="***.982.247-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2020-01-10",
            provenance=self.rfb_provenance,
        )

        # Sanction expired on 2025-12-31
        sanction = CuratedSanctionRecord.create_validated(
            sanction_code="CEIS-2024-9999",
            sanctioned_raw_doc="***.982.247-**",
            sanctioned_name="Carlos Eduardo da Silva",
            sanction_type="SUSPENSÃO TEMPORÁRIA",
            sanctioning_organ="PREFEITURA MUNICIPAL DE EXEMPLO",
            state_uf="SP",
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            provenance=self.cgu_provenance,
        )

        # Contract signed on 2026-06-15, after the sanction expired
        contract = CuratedPublicContract.create_validated(
            pncp_control_number="PNCP-2026-5678",
            organ_cnpj_raw="33.000.167/0001-01",
            organ_name="MINISTERIO DOS TRANSPORTES",
            supplier_raw_doc="12.345.678/0001-95",
            supplier_name="CONSTRUTORA ALVORADA LTDA",
            modality_name="PREGAO ELETRONICO",
            contract_object="OBRAS DE MANUTENCAO RODOVIARIA",
            signature_date=date(2026, 6, 15),
            initial_amount_raw="500000.00",
            current_amount_raw="500000.00",
            addendum_count=0,
            provenance=self.pncp_provenance,
        )

        signals = evaluate_sanctioned_partner_supplier_rule(
            corporate_members=[member],
            sanctions=[sanction],
            contracts=[contract],
        )

        self.assertEqual(signals, [])

    def test_sanctioned_partner_rule_ignores_masked_cpf_homonym_without_name_match(self) -> None:
        """Test Anchor 3 (`NFR-021`, `SEC-021`, `AC-072`): Discards homonyms where masked CPF matches but name is different."""
        member = CuratedCorporateMemberRecord(
            corporate_root_cnpj="12345678",
            full_cnpj_normalized="12.345.678/0001-95",
            member_name_raw="Carlos Eduardo da Silva",
            member_doc_masked="***.982.247-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2020-01-10",
            provenance=self.rfb_provenance,
        )

        # Same masked CPF ***.982.247-**, but totally different person name
        sanction = CuratedSanctionRecord.create_validated(
            sanction_code="CEIS-2025-0088",
            sanctioned_raw_doc="***.982.247-**",
            sanctioned_name="Sebastião Pereira de Oliveira",
            sanction_type="DECLARAÇÃO DE INIDONEIDADE",
            sanctioning_organ="CONTROLADORIA-GERAL DA UNIAO",
            state_uf="RJ",
            start_date=date(2025, 1, 1),
            end_date=date(2027, 1, 1),
            provenance=self.cgu_provenance,
        )

        contract = CuratedPublicContract.create_validated(
            pncp_control_number="PNCP-2026-9012",
            organ_cnpj_raw="33.000.167/0001-01",
            organ_name="MINISTERIO DOS TRANSPORTES",
            supplier_raw_doc="12.345.678/0001-95",
            supplier_name="CONSTRUTORA ALVORADA LTDA",
            modality_name="PREGAO ELETRONICO",
            contract_object="OBRAS DE MANUTENCAO RODOVIARIA",
            signature_date=date(2026, 6, 15),
            initial_amount_raw="350000.00",
            current_amount_raw="350000.00",
            addendum_count=0,
            provenance=self.pncp_provenance,
        )

        signals = evaluate_sanctioned_partner_supplier_rule(
            corporate_members=[member],
            sanctions=[sanction],
            contracts=[contract],
        )

        # Guard anti-homonímia must reject match
        self.assertEqual(signals, [])

    def test_sanctioned_partner_rule_ignores_unrelated_suppliers(self) -> None:
        """Test Anchor 4 (`AC-073`): Discards suppliers whose QSA members have clean records or unrelated sanctions."""
        # Member Roberto Mendes
        member = CuratedCorporateMemberRecord(
            corporate_root_cnpj="11222333",
            full_cnpj_normalized="11.222.333/0001-81",
            member_name_raw="Roberto Mendes de Souza",
            member_doc_masked="***.111.222-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2018-05-12",
            provenance=self.rfb_provenance,
        )

        # Sanction on an unrelated individual
        sanction = CuratedSanctionRecord.create_validated(
            sanction_code="CEIS-2025-0077",
            sanctioned_raw_doc="***.333.444-**",
            sanctioned_name="Marcos Vinicius Santos",
            sanction_type="IMPEDIMENTO DE LICITAR",
            sanctioning_organ="MINISTERIO DA SAUDE",
            state_uf="DF",
            start_date=date(2025, 1, 1),
            end_date=None,
            provenance=self.cgu_provenance,
        )

        # Public expense with supplier 11.222.333/0001-81
        expense = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=7,
            issue_date=date(2026, 7, 20),
            sphere="FEDERAL",
            organ_code="20000",
            organ_name="CAMARA DOS DEPUTADOS",
            public_agent_id="DEP-999",
            public_agent_name="Deputado Exemplar",
            party_sigla="PART",
            state_uf="SP",
            expense_category="CONSULTORIA TECNICA",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="SERVICOS TECNICOS INTEGRADOS LTDA",
            document_number="NF-7890",
            gross_amount_raw="25000.00",
            net_amount_raw="25000.00",
            document_evidence_url=None,
            provenance=self.expense_provenance,
        )

        signals = evaluate_sanctioned_partner_supplier_rule(
            corporate_members=[member],
            sanctions=[sanction],
            expenses=[expense],
        )

        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
