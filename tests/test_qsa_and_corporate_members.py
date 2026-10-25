"""Unit and integration tests for SPEC-0013 (Receita Federal QSA and Individual Campaign Donor Crossmatch)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import (
    evaluate_qsa_individual_donor_rule,
    evaluate_qsa_shared_partner_rule,
)
from deolhonobrasil.pipeline.models import (
    CuratedCorporateMemberRecord,
    CuratedElectoralDonation,
    CuratedPublicExpense,
    EpistemicClassification,
    OfficialSource,
    ProvenanceMetadata,
)


class TestCorporateMembersAndQSACrossmatch(unittest.TestCase):
    """Verifies SPEC-0013 QSA model, partner masking, shared partner rule, and individual campaign donor crossmatch."""

    def setUp(self) -> None:
        self.rfb_provenance = ProvenanceMetadata(
            source=OfficialSource.RECEITA_FEDERAL_CNPJ,
            source_url="https://dadosabertos.rfb.gov.br/CNPJ/socios.zip",
            source_record_id="RFB-QSA-BATCH-001",
            collected_at_utc="2026-10-24T18:00:00Z",
            raw_batch_sha256="a" * 64,
        )
        self.expense_provenance = ProvenanceMetadata(
            source=OfficialSource.CAMARA_CEAP,
            source_url="https://dadosabertos.camara.leg.br/api/v2/deputados/despesas",
            source_record_id="CEAP-BATCH-001",
            collected_at_utc="2026-10-24T18:05:00Z",
            raw_batch_sha256="b" * 64,
        )
        self.tse_provenance = ProvenanceMetadata(
            source=OfficialSource.TSE_ELEICOES,
            source_url="https://divulgacandcontas.tse.jus.br/divulga/rest/v1/prestador/consulta",
            source_record_id="TSE-BATCH-001",
            collected_at_utc="2026-10-24T18:10:00Z",
            raw_batch_sha256="c" * 64,
        )

    def test_corporate_member_model_validation_and_masking(self) -> None:
        """`FR-028`, `DATA-015`, `SEC-016`, `AC-050`: Validates CuratedCorporateMemberRecord creation, LGPD masking, and immutability."""
        member = CuratedCorporateMemberRecord(
            corporate_root_cnpj="12345678",
            full_cnpj_normalized="12.345.678/0001-95",
            member_name_raw="Carlos Eduardo da Silva",
            member_doc_masked="***.982.247-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2020-03-15",
            provenance=self.rfb_provenance,
        )

        self.assertEqual(member.corporate_root_cnpj, "12345678")
        self.assertEqual(member.member_name_raw, "Carlos Eduardo da Silva")
        self.assertEqual(member.member_doc_masked, "***.982.247-**")
        self.assertEqual(member.qualification_description, "Sócio-Administrador")
        self.assertEqual(member.provenance.source, OfficialSource.RECEITA_FEDERAL_CNPJ)
        self.assertTrue(len(member.natural_key) == 64)

        # Immutability check
        with self.assertRaises(AttributeError):
            member.member_name_raw = "Outro Nome"  # type: ignore[misc]

    def test_qsa_shared_partner_rule_detects_common_partners_in_same_organ(self) -> None:
        """`FR-029`, `NFR-016`, `AC-051`: Detects shared administrators across competing suppliers for the same organ."""
        member_a = CuratedCorporateMemberRecord(
            corporate_root_cnpj="11222333",
            full_cnpj_normalized="11.222.333/0001-81",
            member_name_raw="Carlos Eduardo da Silva",
            member_doc_masked="***.982.247-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2020-01-10",
            provenance=self.rfb_provenance,
        )
        member_b = CuratedCorporateMemberRecord(
            corporate_root_cnpj="33000167",
            full_cnpj_normalized="33.000.167/0001-01",
            member_name_raw="Carlos Eduardo da Silva",
            member_doc_masked="***.982.247-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2021-05-20",
            provenance=self.rfb_provenance,
        )

        expense_1 = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=8,
            issue_date=date(2026, 8, 10),
            sphere="FEDERAL",
            organ_code="UASG-250005",
            organ_name="Ministério da Saúde",
            public_agent_id="DEP-9999",
            public_agent_name="Deputado Responsável",
            party_sigla="PART_A",
            state_uf="DF",
            expense_category="LOCACAO_DE_VEICULOS",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Fornecedor Alpha Serviços Ltda",
            document_number="NF-101",
            gross_amount_raw=Decimal("45000.00"),
            net_amount_raw=Decimal("45000.00"),
            document_evidence_url=None,
            provenance=self.expense_provenance,
        )
        expense_2 = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=8,
            issue_date=date(2026, 8, 15),
            sphere="FEDERAL",
            organ_code="UASG-250005",
            organ_name="Ministério da Saúde",
            public_agent_id="DEP-9999",
            public_agent_name="Deputado Responsável",
            party_sigla="PART_A",
            state_uf="DF",
            expense_category="LOCACAO_DE_VEICULOS",
            supplier_raw_doc="33.000.167/0001-01",
            supplier_name="Fornecedor Beta Transportes Ltda",
            document_number="NF-202",
            gross_amount_raw=Decimal("55000.00"),
            net_amount_raw=Decimal("55000.00"),
            document_evidence_url=None,
            provenance=self.expense_provenance,
        )

        signal = evaluate_qsa_shared_partner_rule(
            organ_code="UASG-250005",
            organ_name="Ministério da Saúde",
            expenses=[expense_1, expense_2],
            qsa_records=[member_a, member_b],
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal.rule_code, "R-CROSS-QSA-SHARED-PARTNER")
        self.assertEqual(signal.epistemic_layer, EpistemicClassification.CROSS_SOURCE_DIVERGENCE)
        self.assertEqual(signal.audited_amount, Decimal("100000.00"))
        self.assertIn("Carlos Eduardo da Silva", signal.official_fact_summary)
        self.assertIn(self.rfb_provenance.raw_batch_sha256, signal.provenance_hashes)
        self.assertIn(self.expense_provenance.raw_batch_sha256, signal.provenance_hashes)

    def test_qsa_individual_donor_rule_detects_partner_donation_to_mandatario(self) -> None:
        """`FR-029`, `NFR-016`, `AC-052`: Detects when an individual partner of a public supplier donated to the contracting politician."""
        member = CuratedCorporateMemberRecord(
            corporate_root_cnpj="33000167",
            full_cnpj_normalized="33.000.167/0001-01",
            member_name_raw="Mariana Albuquerque",
            member_doc_masked="***.982.247-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2019-04-01",
            provenance=self.rfb_provenance,
        )

        expense = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=9,
            issue_date=date(2026, 9, 1),
            sphere="FEDERAL",
            organ_code="CAMARA_DEPUTADOS",
            organ_name="Câmara dos Deputados",
            public_agent_id="DEP-8888",
            public_agent_name="Deputado João da Silva",
            party_sigla="PART_A",
            state_uf="DF",
            expense_category="DIVULGACAO_DA_ATIVIDADE_PARLAMENTAR",
            supplier_raw_doc="33.000.167/0001-01",
            supplier_name="Soluções Estratégicas Brasília S.A.",
            document_number="NF-303",
            gross_amount_raw=Decimal("120000.00"),
            net_amount_raw=Decimal("120000.00"),
            document_evidence_url=None,
            provenance=self.expense_provenance,
        )

        donation = CuratedElectoralDonation.create_validated(
            election_year=2026,
            candidate_id="DEP-8888",
            candidate_name="Deputado João da Silva",
            candidate_office="DEPUTADO_FEDERAL",
            donor_raw_doc="529.982.247-25",
            donor_name="Mariana Albuquerque",
            donation_amount_raw=Decimal("30000.00"),
            donation_date=date(2026, 8, 20),
            receipt_number="REC-TSE-9988",
            provenance=self.tse_provenance,
        )

        signal = evaluate_qsa_individual_donor_rule(
            public_agent_id="DEP-8888",
            expenses=[expense],
            qsa_records=[member],
            donations=[donation],
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal.rule_code, "R-CROSS-QSA-DONOR-SUPPLIER")
        self.assertEqual(signal.epistemic_layer, EpistemicClassification.CROSS_SOURCE_DIVERGENCE)
        self.assertEqual(signal.audited_amount, Decimal("120000.00"))
        self.assertIn("Mariana Albuquerque", signal.official_fact_summary)
        self.assertIn("30000.00", signal.official_fact_summary)
        # Triple provenance
        self.assertIn(self.rfb_provenance.raw_batch_sha256, signal.provenance_hashes)
        self.assertIn(self.expense_provenance.raw_batch_sha256, signal.provenance_hashes)
        self.assertIn(self.tse_provenance.raw_batch_sha256, signal.provenance_hashes)

    def test_qsa_rules_ignore_unrelated_companies_or_non_donors(self) -> None:
        """`FR-029`, `AC-053`: Neither rule emits signals when suppliers do not share partners or partners made no donations."""
        member_x = CuratedCorporateMemberRecord(
            corporate_root_cnpj="11222333",
            full_cnpj_normalized="11.222.333/0001-81",
            member_name_raw="Fernando Souza",
            member_doc_masked="***.982.247-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2022-01-01",
            provenance=self.rfb_provenance,
        )
        member_y = CuratedCorporateMemberRecord(
            corporate_root_cnpj="33000167",
            full_cnpj_normalized="33.000.167/0001-01",
            member_name_raw="Juliana Mendes",
            member_doc_masked="***.456.789-**",
            qualification_code="49",
            qualification_description="Sócio-Administrador",
            entry_date="2022-02-01",
            provenance=self.rfb_provenance,
        )

        expense_x = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=9,
            issue_date=date(2026, 9, 2),
            sphere="FEDERAL",
            organ_code="CAMARA_DEPUTADOS",
            organ_name="Câmara dos Deputados",
            public_agent_id="DEP-7777",
            public_agent_name="Outro Parlamentar",
            party_sigla="PART_A",
            state_uf="DF",
            expense_category="COMBUSTIVEL",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Fornecedor Delta",
            document_number="NF-404",
            gross_amount_raw=Decimal("15000.00"),
            net_amount_raw=Decimal("15000.00"),
            document_evidence_url=None,
            provenance=self.expense_provenance,
        )
        expense_y = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=9,
            issue_date=date(2026, 9, 3),
            sphere="FEDERAL",
            organ_code="CAMARA_DEPUTADOS",
            organ_name="Câmara dos Deputados",
            public_agent_id="DEP-7777",
            public_agent_name="Outro Parlamentar",
            party_sigla="PART_A",
            state_uf="DF",
            expense_category="COMBUSTIVEL",
            supplier_raw_doc="33.000.167/0001-01",
            supplier_name="Fornecedor Epsilon",
            document_number="NF-505",
            gross_amount_raw=Decimal("18000.00"),
            net_amount_raw=Decimal("18000.00"),
            document_evidence_url=None,
            provenance=self.expense_provenance,
        )

        # 1. No shared partner
        signal_shared = evaluate_qsa_shared_partner_rule(
            organ_code="CAMARA_DEPUTADOS",
            organ_name="Câmara dos Deputados",
            expenses=[expense_x, expense_y],
            qsa_records=[member_x, member_y],
        )
        self.assertIsNone(signal_shared)

        # 2. No donation by partner
        unrelated_donation = CuratedElectoralDonation.create_validated(
            election_year=2026,
            candidate_id="DEP-7777",
            candidate_name="Outro Parlamentar",
            candidate_office="DEPUTADO_FEDERAL",
            donor_raw_doc="123.456.789-09",
            donor_name="Doador Não Relacionado",
            donation_amount_raw=Decimal("5000.00"),
            donation_date=date(2026, 8, 15),
            receipt_number="REC-TSE-7777",
            provenance=self.tse_provenance,
        )
        signal_donor = evaluate_qsa_individual_donor_rule(
            public_agent_id="DEP-7777",
            expenses=[expense_x],
            qsa_records=[member_x],
            donations=[unrelated_donation],
        )
        self.assertIsNone(signal_donor)


if __name__ == "__main__":
    unittest.main()
