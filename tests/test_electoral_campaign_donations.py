"""TDD Unit & Integration Tests for `SPEC-0012` — Electoral Campaign Donors Crossmatch."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import (
    evaluate_electoral_donor_supplier_crossmatch_rule,
)
from deolhonobrasil.pipeline.models import (
    CuratedElectoralDonation,
    CuratedPublicExpense,
    EpistemicClassification,
    OfficialSource,
    ProvenanceMetadata,
)


def _make_tse_provenance(record_id: str, sha: str = "t" * 64) -> ProvenanceMetadata:
    return ProvenanceMetadata(
        source=OfficialSource.TSE_ELEICOES,
        source_url="https://divulgacandcontas.tse.jus.br/divulga/rest/v1/prestador/consulta",
        source_record_id=record_id,
        collected_at_utc="2026-10-24T10:00:00Z",
        raw_batch_sha256=sha,
    )


def _make_expense(
    expense_id: str,
    amount_str: str,
    issue_date: date,
    public_agent_id: str = "DEP-101",
    public_agent_name: str = "Deputado Auditor",
    supplier_raw_doc: str = "33.000.167/0001-01",
    supplier_name: str = "EMPRESA DE APOIO LTDA",
    sha: str = "e" * 64,
) -> CuratedPublicExpense:
    prov = ProvenanceMetadata(
        source=OfficialSource.CAMARA_CEAP,
        source_url="https://dadosabertos.camara.leg.br/api/v2/proposicoes",
        source_record_id=expense_id,
        collected_at_utc="2026-10-24T10:00:00Z",
        raw_batch_sha256=sha,
    )
    return CuratedPublicExpense.create_validated(
        competence_year=issue_date.year,
        competence_month=issue_date.month,
        issue_date=issue_date,
        sphere="FEDERAL",
        organ_code="CAMARA_DEPUTADOS",
        organ_name="CAMARA DOS DEPUTADOS",
        public_agent_id=public_agent_id,
        public_agent_name=public_agent_name,
        party_sigla="PART_A",
        state_uf="DF",
        expense_category="CONSULTORIAS, PESQUISAS E TRABALHOS TECNICOS",
        supplier_raw_doc=supplier_raw_doc,
        supplier_name=supplier_name,
        document_number="NF-8822",
        gross_amount_raw=amount_str,
        net_amount_raw=amount_str,
        document_evidence_url=None,
        provenance=prov,
    )


class TestElectoralCampaignDonationsCrossmatch(unittest.TestCase):
    """Test suite validating CuratedElectoralDonation and R-CROSS-ELECTORAL-DONOR-SUPPLIER rule."""

    def test_electoral_donation_model_validation_and_masking(self) -> None:
        """AC-046: CuratedElectoralDonation validates fields, masks CPF, and calculates natural key."""
        prov = _make_tse_provenance("REC-01")
        # CNPJ donation
        don_cnpj = CuratedElectoralDonation.create_validated(
            election_year=2022,
            candidate_id="DEP-101",
            candidate_name="Deputado Auditor",
            candidate_office="DEPUTADO FEDERAL",
            donor_raw_doc="33.000.167/0001-01",
            donor_name="EMPRESA DOADORA LTDA",
            donation_amount_raw="25000.00",
            donation_date=date(2022, 9, 15),
            receipt_number="REC-998811",
            provenance=prov,
        )
        self.assertEqual(don_cnpj.donor_doc_normalized, "33000167000101")
        self.assertEqual(don_cnpj.donor_doc_type, "CNPJ")
        self.assertEqual(don_cnpj.donation_amount, Decimal("25000.00"))
        self.assertTrue(don_cnpj.natural_key)

        # CPF donation (must be masked under LGPD)
        don_cpf = CuratedElectoralDonation.create_validated(
            election_year=2022,
            candidate_id="DEP-101",
            candidate_name="Deputado Auditor",
            candidate_office="DEPUTADO FEDERAL",
            donor_raw_doc="529.982.247-25",
            donor_name="Cidadão Apoiador",
            donation_amount_raw="1500.00",
            donation_date=date(2022, 9, 20),
            receipt_number="REC-998812",
            provenance=prov,
        )
        self.assertEqual(don_cpf.donor_doc_normalized, "***.982.247-**")
        self.assertEqual(don_cpf.donor_doc_type, "CPF_MASKED")

    def test_electoral_crossmatch_rule_detects_donor_as_supplier(self) -> None:
        """AC-047: evaluate_electoral_donor_supplier_crossmatch_rule detects donor who is public supplier."""
        tse_sha = "t" * 64
        exp_sha = "e" * 64
        prov_tse = _make_tse_provenance("REC-100", sha=tse_sha)

        donation = CuratedElectoralDonation.create_validated(
            election_year=2022,
            candidate_id="DEP-101",
            candidate_name="Deputado Auditor",
            candidate_office="DEPUTADO FEDERAL",
            donor_raw_doc="33.000.167/0001-01",
            donor_name="POSTO CAPITAL LTDA",
            donation_amount_raw="20000.00",
            donation_date=date(2022, 9, 10),
            receipt_number="REC-100",
            provenance=prov_tse,
        )

        expense1 = _make_expense(
            "EXP-01", "12000.00", date(2023, 5, 10), public_agent_id="DEP-101", sha=exp_sha
        )
        expense2 = _make_expense(
            "EXP-02", "15000.00", date(2023, 6, 12), public_agent_id="DEP-101", sha=exp_sha
        )

        signals = evaluate_electoral_donor_supplier_crossmatch_rule(
            expenses=[expense1, expense2],
            donations=[donation],
        )

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-CROSS-ELECTORAL-DONOR-SUPPLIER")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.CROSS_SOURCE_DIVERGENCE)
        self.assertEqual(sig.metric_value, Decimal("20000.00"))
        self.assertEqual(sig.audited_amount, Decimal("27000.00"))
        self.assertTrue(sig.requires_human_review)
        # Verify dual provenance hashes
        self.assertIn(tse_sha, sig.provenance_hashes)
        self.assertIn(exp_sha, sig.provenance_hashes)
        self.assertIn("Doações de campanha eleitoral declaradas perante o TSE", sig.scope_limitation_summary)

    def test_electoral_crossmatch_rule_ignores_masked_cpf_homonym(self) -> None:
        """AC-048: evaluate_electoral_donor_supplier_crossmatch_rule ignores masked CPFs to prevent homonym false positives."""
        prov_tse = _make_tse_provenance("REC-200")
        donation_cpf = CuratedElectoralDonation.create_validated(
            election_year=2022,
            candidate_id="DEP-101",
            candidate_name="Deputado Auditor",
            candidate_office="DEPUTADO FEDERAL",
            donor_raw_doc="529.982.247-25",
            donor_name="Fulano de Tal",
            donation_amount_raw="5000.00",
            donation_date=date(2022, 9, 10),
            receipt_number="REC-200",
            provenance=prov_tse,
        )

        # Expense with same masked CPF
        expense_cpf = _make_expense(
            "EXP-CPF",
            "3500.00",
            date(2023, 4, 15),
            public_agent_id="DEP-101",
            supplier_raw_doc="529.982.247-25",
            supplier_name="Fulano de Tal Consultoria",
        )

        signals = evaluate_electoral_donor_supplier_crossmatch_rule(
            expenses=[expense_cpf],
            donations=[donation_cpf],
        )
        self.assertEqual(signals, [])

    def test_electoral_crossmatch_rule_ignores_unrelated_supplier(self) -> None:
        """AC-049: evaluate_electoral_donor_supplier_crossmatch_rule returns empty for unrelated suppliers."""
        prov_tse = _make_tse_provenance("REC-300")
        donation = CuratedElectoralDonation.create_validated(
            election_year=2022,
            candidate_id="DEP-101",
            candidate_name="Deputado Auditor",
            candidate_office="DEPUTADO FEDERAL",
            donor_raw_doc="33.000.167/0001-01",
            donor_name="POSTO CAPITAL LTDA",
            donation_amount_raw="10000.00",
            donation_date=date(2022, 9, 10),
            receipt_number="REC-300",
            provenance=prov_tse,
        )

        # Expense from completely different supplier CNPJ (Petrobras: 33.000.167/0002-92 or Caixa: 00.360.305/0001-04)
        expense = _make_expense(
            "EXP-OTHER",
            "8000.00",
            date(2023, 5, 20),
            public_agent_id="DEP-101",
            supplier_raw_doc="00.360.305/0001-04",
            supplier_name="CAIXA ECONOMICA FEDERAL",
        )

        signals = evaluate_electoral_donor_supplier_crossmatch_rule(
            expenses=[expense],
            donations=[donation],
        )
        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
