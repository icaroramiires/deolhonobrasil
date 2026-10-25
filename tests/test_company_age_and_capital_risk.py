"""TDD Unit Tests for `SPEC-0014` — Company Age & Capital Social Disproportionality Rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import (
    evaluate_low_capital_outlier_rule,
    evaluate_recent_company_creation_rule,
)
from deolhonobrasil.pipeline.models import (
    CuratedCompanyRegistrationRecord,
    CuratedPublicContract,
    CuratedPublicExpense,
    EpistemicClassification,
    OfficialSource,
    ProvenanceMetadata,
)


def _make_rfb_provenance(record_id: str = "RFB-REC-01", sha: str = "a" * 64) -> ProvenanceMetadata:
    return ProvenanceMetadata(
        source=OfficialSource.RECEITA_FEDERAL_CNPJ,
        source_url="https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica-cnpj",
        source_record_id=record_id,
        collected_at_utc="2026-10-25T10:00:00Z",
        raw_batch_sha256=sha,
    )


def _make_pncp_provenance(record_id: str = "PNCP-REC-01", sha: str = "b" * 64) -> ProvenanceMetadata:
    return ProvenanceMetadata(
        source=OfficialSource.PNCP_CONTRATOS,
        source_url="https://pncp.gov.br/api/consulta/v1/contratos",
        source_record_id=record_id,
        collected_at_utc="2026-10-25T10:00:00Z",
        raw_batch_sha256=sha,
    )


def _make_ceap_provenance(record_id: str = "CEAP-REC-01", sha: str = "c" * 64) -> ProvenanceMetadata:
    return ProvenanceMetadata(
        source=OfficialSource.CAMARA_CEAP,
        source_url="https://dadosabertos.camara.leg.br/api/v2/proposicoes",
        source_record_id=record_id,
        collected_at_utc="2026-10-25T10:00:00Z",
        raw_batch_sha256=sha,
    )


class TestCompanyAgeAndCapitalRiskRules(unittest.TestCase):
    """Test suite validating CuratedCompanyRegistrationRecord and SPEC-0014 audit rules."""

    def test_company_registration_model_validation(self) -> None:
        """`FR-030`, `DATA-016`, `SEC-017`, `AC-054`: Validates CuratedCompanyRegistrationRecord creation, immutability, and natural key."""
        prov = _make_rfb_provenance("RFB-01")
        company = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="11.222.333/0001-81",
            legal_name="Alpha Engenharia e Serviços Ltda",
            opening_date=date(2026, 4, 15),
            share_capital_raw="10000.00",
            provenance=prov,
            trade_name="Alpha Tech",
            cnae_main_code="6201-5/01",
            registration_status="ATIVA",
        )

        self.assertEqual(company.cnpj_normalized, "11222333000181")
        self.assertEqual(company.corporate_root_cnpj, "11222333")
        self.assertEqual(company.legal_name, "Alpha Engenharia e Serviços Ltda")
        self.assertEqual(company.trade_name, "Alpha Tech")
        self.assertEqual(company.opening_date, date(2026, 4, 15))
        self.assertEqual(company.share_capital_brl, Decimal("10000.00"))
        self.assertEqual(company.provenance.source, OfficialSource.RECEITA_FEDERAL_CNPJ)
        self.assertEqual(len(company.natural_key), 64)

        # Immutability
        with self.assertRaises(AttributeError):
            company.legal_name = "Novo Nome"  # type: ignore[misc]

        # Rejection of invalid CNPJ
        with self.assertRaises(ValueError):
            CuratedCompanyRegistrationRecord.create_validated(
                cnpj_raw="11.111.111/0001-11",  # inválido
                legal_name="Empresa Inválida",
                opening_date=date(2026, 1, 1),
                share_capital_raw="5000.00",
                provenance=prov,
            )

    def test_recent_company_creation_rule_detects_young_company(self) -> None:
        """`FR-031`, `NFR-017`, `AC-055`: Detects contracts or expenses with companies created less than 180 days prior."""
        rfb_sha = "1" * 64
        pncp_sha = "2" * 64
        prov_rfb = _make_rfb_provenance("RFB-YOUNG", sha=rfb_sha)
        prov_pncp = _make_pncp_provenance("PNCP-YOUNG", sha=pncp_sha)

        # Empresa aberta em 01/06/2026
        company = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="11.222.333/0001-81",
            legal_name="Beta Logística e Soluções Ltda",
            opening_date=date(2026, 6, 1),
            share_capital_raw="50000.00",
            provenance=prov_rfb,
        )

        # Contrato assinado em 01/08/2026 (61 dias após abertura, < 180 dias)
        contract = CuratedPublicContract.create_validated(
            pncp_control_number="00000000000191-1-000099/2026",
            organ_cnpj_raw="00.000.000/0001-91",
            organ_name="MINISTERIO DA SAUDE",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Beta Logística e Soluções Ltda",
            modality_name="Dispensa de Licitacao",
            contract_object="Fornecimento de equipamentos de suporte hospitalar",
            signature_date=date(2026, 8, 1),
            initial_amount_raw="850000.00",
            current_amount_raw="850000.00",
            addendum_count=0,
            provenance=prov_pncp,
        )

        signals = evaluate_recent_company_creation_rule(
            companies=[company],
            contracts=[contract],
            max_age_days=180,
            min_amount_threshold=Decimal("50000.00"),
        )

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-CORP-RECENT-CREATION")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.STATISTICAL_ANOMALY)
        self.assertEqual(sig.metric_name, "company_age_days_at_contract")
        self.assertEqual(sig.metric_value, Decimal("61"))
        self.assertEqual(sig.threshold_value, Decimal("180"))
        self.assertEqual(sig.audited_amount, Decimal("850000.00"))
        self.assertIn(rfb_sha, sig.provenance_hashes)
        self.assertIn(pncp_sha, sig.provenance_hashes)
        self.assertIn("Beta Logística", sig.official_fact_summary)
        self.assertIn("61 dias", sig.official_fact_summary)

    def test_low_capital_outlier_rule_detects_extreme_ratio(self) -> None:
        """`FR-031`, `NFR-017`, `AC-056`: Detects contract/expense amounts exceeding 50x share capital."""
        rfb_sha = "3" * 64
        ceap_sha = "4" * 64
        prov_rfb = _make_rfb_provenance("RFB-CAP", sha=rfb_sha)
        prov_ceap = _make_ceap_provenance("CEAP-CAP", sha=ceap_sha)

        # Empresa com capital social de R$ 5.000,00
        company = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="33.000.167/0001-01",
            legal_name="Gama Consultoria Estratégica Eireli",
            opening_date=date(2022, 1, 10),
            share_capital_raw="5000.00",
            provenance=prov_rfb,
        )

        # 3 despesas somando R$ 350.000,00 (razão 350.000 / 5.000 = 70x, > 50x)
        expense1 = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=7,
            issue_date=date(2026, 7, 10),
            sphere="FEDERAL",
            organ_code="CAMARA_DEPUTADOS",
            organ_name="Câmara dos Deputados",
            public_agent_id="DEP-5555",
            public_agent_name="Deputado Investigado",
            party_sigla="PART_A",
            state_uf="DF",
            expense_category="CONSULTORIAS_E_PESQUISAS",
            supplier_raw_doc="33.000.167/0001-01",
            supplier_name="Gama Consultoria Estratégica Eireli",
            document_number="NF-701",
            gross_amount_raw=Decimal("150000.00"),
            net_amount_raw=Decimal("150000.00"),
            document_evidence_url=None,
            provenance=prov_ceap,
        )
        expense2 = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=8,
            issue_date=date(2026, 8, 10),
            sphere="FEDERAL",
            organ_code="CAMARA_DEPUTADOS",
            organ_name="Câmara dos Deputados",
            public_agent_id="DEP-5555",
            public_agent_name="Deputado Investigado",
            party_sigla="PART_A",
            state_uf="DF",
            expense_category="CONSULTORIAS_E_PESQUISAS",
            supplier_raw_doc="33.000.167/0001-01",
            supplier_name="Gama Consultoria Estratégica Eireli",
            document_number="NF-702",
            gross_amount_raw=Decimal("200000.00"),
            net_amount_raw=Decimal("200000.00"),
            document_evidence_url=None,
            provenance=prov_ceap,
        )

        signals = evaluate_low_capital_outlier_rule(
            companies=[company],
            expenses=[expense1, expense2],
            max_ratio_threshold=Decimal("50.00"),
            min_amount_threshold=Decimal("100000.00"),
        )

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-CORP-LOW-CAPITAL-OUTLIER")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.STATISTICAL_ANOMALY)
        self.assertEqual(sig.metric_name, "contract_to_share_capital_ratio")
        self.assertEqual(sig.metric_value, Decimal("70.00"))
        self.assertEqual(sig.threshold_value, Decimal("50.00"))
        self.assertEqual(sig.audited_amount, Decimal("350000.00"))
        self.assertIn(rfb_sha, sig.provenance_hashes)
        self.assertIn(ceap_sha, sig.provenance_hashes)
        self.assertIn("70.0", sig.official_fact_summary)

    def test_rules_ignore_mature_companies_and_sound_capital(self) -> None:
        """`FR-031`, `AC-057`: Rules do not emit signals for mature companies or sound capital ratios."""
        prov_rfb = _make_rfb_provenance("RFB-MATURE")
        prov_pncp = _make_pncp_provenance("PNCP-MATURE")

        # Empresa aberta há 5 anos, com capital de R$ 1.000.000,00
        mature_company = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="11.222.333/0001-81",
            legal_name="Empresa Madura S.A.",
            opening_date=date(2021, 1, 1),
            share_capital_raw="1000000.00",
            provenance=prov_rfb,
        )

        # Contrato de R$ 200.000,00 assinado em 2026 (razão 0.2x < 50x; idade > 180 dias)
        contract = CuratedPublicContract.create_validated(
            pncp_control_number="00000000000191-1-000088/2026",
            organ_cnpj_raw="00.000.000/0001-91",
            organ_name="MINISTERIO DA EDUCACAO",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Empresa Madura S.A.",
            modality_name="Pregao Eletronico",
            contract_object="Fornecimento de materiais didáticos",
            signature_date=date(2026, 5, 20),
            initial_amount_raw="200000.00",
            current_amount_raw="200000.00",
            addendum_count=0,
            provenance=prov_pncp,
        )

        signals_age = evaluate_recent_company_creation_rule(
            companies=[mature_company],
            contracts=[contract],
        )
        self.assertEqual(len(signals_age), 0)

        signals_cap = evaluate_low_capital_outlier_rule(
            companies=[mature_company],
            contracts=[contract],
        )
        self.assertEqual(len(signals_cap), 0)


if __name__ == "__main__":
    unittest.main()
