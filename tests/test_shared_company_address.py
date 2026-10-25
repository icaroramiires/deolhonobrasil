"""TDD Unit Tests for `SPEC-0017` — Indícios de Conluio e Empresas de Fachada: Compartilhamento de Endereço Físico Cadastral."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import evaluate_shared_company_address_rule
from deolhonobrasil.pipeline.models import (
    CuratedCompanyRegistrationRecord,
    CuratedPublicContract,
    CuratedPublicExpense,
    EpistemicClassification,
    OfficialSource,
    ProvenanceMetadata,
    assert_non_accusatory_language,
    compute_normalized_address_key,
    extract_autonomous_unit,
    normalize_address_number,
    normalize_postal_code,
    normalize_street_address,
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


class TestSharedCompanyAddressRules(unittest.TestCase):
    """Test suite validating company address model, normalization, and SPEC-0017 audit rules."""

    def test_company_address_model_validation_and_normalization(self) -> None:
        """`FR-036`, `NFR-020`, `DATA-019`, `AC-066`: Validates address normalization, key hashing, and model immutability."""
        # Helper normalization tests
        self.assertEqual(normalize_postal_code("70000-000"), "70000000")
        self.assertEqual(normalize_postal_code("70.000-000"), "70000000")
        self.assertEqual(normalize_postal_code("70000000"), "70000000")
        self.assertEqual(normalize_postal_code(""), "00000000")
        self.assertEqual(normalize_postal_code("123"), "00000123")
        with self.assertRaises(ValueError):
            normalize_postal_code("123456789")  # 9 dígitos

        self.assertEqual(normalize_street_address("R. das Flores, nº 100"), "RUA DAS FLORES 100")
        self.assertEqual(normalize_street_address("Av. Paulista"), "AVENIDA PAULISTA")
        self.assertEqual(normalize_street_address(""), "N/A")

        self.assertEqual(normalize_address_number("S/N"), "SN")
        self.assertEqual(normalize_address_number("s.n."), "SN")
        self.assertEqual(normalize_address_number("100-A"), "100A")

        self.assertEqual(extract_autonomous_unit("Sala 101"), "SALA 101")
        self.assertEqual(extract_autonomous_unit("Sl 204 B"), "SALA 204")
        self.assertEqual(extract_autonomous_unit("Andar 5"), "ANDAR 5")
        self.assertIsNone(extract_autonomous_unit(None))
        self.assertIsNone(extract_autonomous_unit("N/A"))

        key1 = compute_normalized_address_key("70000-000", "Rua das Flores", "123", "Sala 101")
        key2 = compute_normalized_address_key("70000000", "R. das Flores", "123", "Sl 101")
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 64)

        prov = _make_rfb_provenance("RFB-ADDR-01")
        company = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="11.222.333/0001-81",
            legal_name="Alpha Serviços e Comércio Ltda",
            opening_date=date(2023, 5, 20),
            share_capital_raw="200000.00",
            provenance=prov,
            postal_code="70.000-000",
            street_address="Rua das Flores",
            address_number="123",
            address_complement="Sala 101",
            district="Asa Sul",
            city="Brasília",
            state_uf="DF",
        )

        self.assertEqual(company.postal_code, "70000000")
        self.assertEqual(company.street_address, "Rua das Flores")
        self.assertEqual(company.address_number, "123")
        self.assertEqual(company.address_complement, "Sala 101")
        self.assertEqual(company.district, "Asa Sul")
        self.assertEqual(company.city, "Brasília")
        self.assertEqual(company.state_uf, "DF")
        self.assertEqual(company.normalized_address_key, key1)
        self.assertEqual(len(company.base_building_address_key), 64)

        # Imutabilidade
        with self.assertRaises(AttributeError):
            company.street_address = "Outra Rua"  # type: ignore[misc]

    def test_shared_address_rule_detects_multiple_suppliers_at_same_address(self) -> None:
        """`FR-037`, `AC-067`, `SEC-020`: Detects multiple suppliers at the same address contracted by the same organ."""
        rfb_sha1 = "1" * 64
        rfb_sha2 = "2" * 64
        pncp_sha = "3" * 64
        ceap_sha = "4" * 64

        prov_rfb1 = _make_rfb_provenance("RFB-01", sha=rfb_sha1)
        prov_rfb2 = _make_rfb_provenance("RFB-02", sha=rfb_sha2)
        prov_pncp = _make_pncp_provenance("PNCP-01", sha=pncp_sha)
        prov_ceap = _make_ceap_provenance("CEAP-01", sha=ceap_sha)

        comp1 = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="11.222.333/0001-81",
            legal_name="Empresa Alpha Construcoes Ltda",
            opening_date=date(2022, 1, 10),
            share_capital_raw="300000.00",
            provenance=prov_rfb1,
            postal_code="70000-000",
            street_address="Rua das Flores",
            address_number="123",
            address_complement=None,
            city="Brasilia",
            state_uf="DF",
        )

        comp2 = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="33.000.167/0001-01",
            legal_name="Beta Manutencao e Obras Ltda",
            opening_date=date(2023, 2, 15),
            share_capital_raw="250000.00",
            provenance=prov_rfb2,
            postal_code="70.000-000",
            street_address="R. das Flores",
            address_number="123",
            address_complement=None,
            city="Brasilia",
            state_uf="DF",
        )

        # Ambas contratadas pelo Ministério da Saúde (00.394.452/0001-03)
        organ_cnpj = "00.394.452/0001-03"
        organ_name = "Ministerio da Saude"

        contract1 = CuratedPublicContract.create_validated(
            pncp_control_number="00394452000103-1-000001/2026",
            organ_cnpj_raw=organ_cnpj,
            organ_name=organ_name,
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Empresa Alpha Construcoes Ltda",
            modality_name="Pregão Eletrônico",
            contract_object="Reforma predial e infraestrutura hospitalar",
            signature_date=date(2026, 3, 1),
            initial_amount_raw="350000.00",
            current_amount_raw="350000.00",
            addendum_count=0,
            provenance=prov_pncp,
        )

        expense2 = CuratedPublicExpense.create_validated(
            competence_year=2026,
            competence_month=4,
            issue_date=date(2026, 4, 10),
            sphere="FEDERAL",
            organ_code=organ_cnpj,
            organ_name=organ_name,
            public_agent_id="DEP-01",
            public_agent_name="Deputado Teste",
            party_sigla="PART",
            state_uf="DF",
            expense_category="SERVICOS DE ENGENHARIA",
            supplier_raw_doc="33.000.167/0001-01",
            supplier_name="Beta Manutencao e Obras Ltda",
            document_number="NF-1020",
            gross_amount_raw="120000.00",
            net_amount_raw="120000.00",
            document_evidence_url=None,
            provenance=prov_ceap,
        )

        signals = evaluate_shared_company_address_rule(
            companies=[comp1, comp2],
            contracts=[contract1],
            expenses=[expense2],
        )

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-CORP-SHARED-ADDRESS")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.CROSS_SOURCE_DIVERGENCE)
        self.assertEqual(sig.metric_name, "shared_address_suppliers_count")
        self.assertEqual(sig.metric_value, Decimal("2"))
        self.assertEqual(sig.audited_amount, Decimal("470000.00"))
        self.assertTrue(sig.requires_human_review)

        # Conformidade léxica e epistemologia
        assert_non_accusatory_language(sig.title)
        assert_non_accusatory_language(sig.official_fact_summary)
        assert_non_accusatory_language(sig.statistical_inference_summary)
        assert_non_accusatory_language(sig.scope_limitation_summary)

        self.assertIn("11222333000181", sig.official_fact_summary)
        self.assertIn("33000167000101", sig.official_fact_summary)
        self.assertIn("Ministerio da Saude", sig.official_fact_summary)
        self.assertIn("Rua das Flores", sig.official_fact_summary)

        # Proveniência completa encadeada
        expected_hashes = {rfb_sha1, rfb_sha2, pncp_sha, ceap_sha}
        self.assertTrue(expected_hashes.issubset(set(sig.provenance_hashes)))

    def test_shared_address_rule_ignores_different_address_or_autonomous_units(self) -> None:
        """`AC-068`, `SEC-020`: Rule discards signals when suppliers have different addresses or distinct autonomous units."""
        prov = _make_rfb_provenance("RFB-DISTINCT")
        prov_pncp = _make_pncp_provenance("PNCP-DISTINCT")
        organ_cnpj = "00.394.452/0001-03"

        # Cenário 1: Endereços completamente distintos
        comp_a = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="11.222.333/0001-81",
            legal_name="Companhia Alpha Ltda",
            opening_date=date(2020, 1, 1),
            share_capital_raw="100000.00",
            provenance=prov,
            postal_code="70000-000",
            street_address="Rua Alfa",
            address_number="10",
        )
        comp_b = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="33.000.167/0001-01",
            legal_name="Companhia Beta Ltda",
            opening_date=date(2020, 1, 1),
            share_capital_raw="100000.00",
            provenance=prov,
            postal_code="71000-000",
            street_address="Avenida Beta",
            address_number="20",
        )
        c1 = CuratedPublicContract.create_validated(
            pncp_control_number="00394452000103-1-000001/2026",
            organ_cnpj_raw=organ_cnpj,
            organ_name="Orgao Central",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Companhia Alpha Ltda",
            modality_name="Pregão Eletrônico",
            contract_object="Serviços A",
            signature_date=date(2026, 1, 1),
            initial_amount_raw="50000.00",
            current_amount_raw="50000.00",
            addendum_count=0,
            provenance=prov_pncp,
        )
        c2 = CuratedPublicContract.create_validated(
            pncp_control_number="00394452000103-1-000002/2026",
            organ_cnpj_raw=organ_cnpj,
            organ_name="Orgao Central",
            supplier_raw_doc="33.000.167/0001-01",
            supplier_name="Companhia Beta Ltda",
            modality_name="Pregão Eletrônico",
            contract_object="Serviços B",
            signature_date=date(2026, 1, 1),
            initial_amount_raw="60000.00",
            current_amount_raw="60000.00",
            addendum_count=0,
            provenance=prov_pncp,
        )

        signals_diff_addr = evaluate_shared_company_address_rule(
            companies=[comp_a, comp_b],
            contracts=[c1, c2],
        )
        self.assertEqual(len(signals_diff_addr), 0)

        # Cenário 2: Mesmo condomínio corporativo / edifício, mas em salas autônomas declaradas distintas (AC-068)
        comp_unit1 = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="11.222.333/0001-81",
            legal_name="Companhia Alpha Ltda",
            opening_date=date(2020, 1, 1),
            share_capital_raw="100000.00",
            provenance=prov,
            postal_code="70000-000",
            street_address="Edificio Central Tower, Setor Comercial",
            address_number="100",
            address_complement="Sala 101",
        )
        comp_unit2 = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="33.000.167/0001-01",
            legal_name="Companhia Beta Ltda",
            opening_date=date(2020, 1, 1),
            share_capital_raw="100000.00",
            provenance=prov,
            postal_code="70000-000",
            street_address="Edificio Central Tower, Setor Comercial",
            address_number="100",
            address_complement="Sala 902",
        )

        signals_units = evaluate_shared_company_address_rule(
            companies=[comp_unit1, comp_unit2],
            contracts=[c1, c2],
        )
        self.assertEqual(len(signals_units), 0)

    def test_shared_address_rule_ignores_different_organs(self) -> None:
        """`AC-069`: Discards signal when suppliers at the same address serve completely different public organs."""
        prov = _make_rfb_provenance("RFB-DIFF-ORG")
        prov_pncp1 = _make_pncp_provenance("PNCP-ORG1")
        prov_pncp2 = _make_pncp_provenance("PNCP-ORG2")

        # Duas empresas no mesmo endereço exato
        comp1 = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="11.222.333/0001-81",
            legal_name="Alpha Tech Ltda",
            opening_date=date(2021, 6, 1),
            share_capital_raw="100000.00",
            provenance=prov,
            postal_code="70000-000",
            street_address="Rua dos Empresarios",
            address_number="500",
        )
        comp2 = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="33.000.167/0001-01",
            legal_name="Beta Digital Ltda",
            opening_date=date(2021, 6, 1),
            share_capital_raw="100000.00",
            provenance=prov,
            postal_code="70000-000",
            street_address="Rua dos Empresarios",
            address_number="500",
        )

        # Contratadas por órgãos distintos
        c_saude = CuratedPublicContract.create_validated(
            pncp_control_number="00394452000103-1-000001/2026",
            organ_cnpj_raw="00.394.452/0001-03",
            organ_name="Ministerio da Saude",
            supplier_raw_doc="11.222.333/0001-81",
            supplier_name="Alpha Tech Ltda",
            modality_name="Pregão Eletrônico",
            contract_object="Sistemas de Saude",
            signature_date=date(2026, 1, 1),
            initial_amount_raw="80000.00",
            current_amount_raw="80000.00",
            addendum_count=0,
            provenance=prov_pncp1,
        )

        c_educacao = CuratedPublicContract.create_validated(
            pncp_control_number="12345678000195-1-000002/2026",
            organ_cnpj_raw="12.345.678/0001-95",
            organ_name="Ministerio da Educacao",
            supplier_raw_doc="33.000.167/0001-01",
            supplier_name="Beta Digital Ltda",
            modality_name="Pregão Eletrônico",
            contract_object="Plataforma de EAD",
            signature_date=date(2026, 1, 1),
            initial_amount_raw="95000.00",
            current_amount_raw="95000.00",
            addendum_count=0,
            provenance=prov_pncp2,
        )

        signals = evaluate_shared_company_address_rule(
            companies=[comp1, comp2],
            contracts=[c_saude, c_educacao],
        )

        # Como cada órgão contratou apenas 1 fornecedor, não há colisão concorrencial no certame
        self.assertEqual(len(signals), 0)


if __name__ == "__main__":
    unittest.main()
