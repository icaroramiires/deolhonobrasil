"""TDD Unit Tests for `SPEC-0015` — Incompatibilidade entre CNAE (Receita Federal) e Objeto de Contratos Públicos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import evaluate_cnae_contract_incompatibility_rule
from deolhonobrasil.pipeline.models import (
    CuratedCompanyRegistrationRecord,
    CuratedPublicContract,
    EpistemicClassification,
    OfficialSource,
    ProvenanceMetadata,
    normalize_cnae_code,
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


class TestCnaeContractIncompatibilityRules(unittest.TestCase):
    """Test suite validating CNAE model validation and SPEC-0015 audit rules."""

    def test_cnae_model_validation_and_code_normalization(self) -> None:
        """`FR-032`, `DATA-017`, `SEC-018`, `AC-058`: Validates CNAE normalization, main and secondary codes."""
        # Helper normalization test
        self.assertEqual(normalize_cnae_code("42.11-1-01"), "4211101")
        self.assertEqual(normalize_cnae_code("6201-5/01"), "6201501")
        with self.assertRaises(ValueError):
            normalize_cnae_code("12345")  # menos de 7 dígitos

        prov = _make_rfb_provenance("RFB-CNAE-01")
        company = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="11.222.333/0001-81",
            legal_name="Comércio e Construções Alpha Ltda",
            opening_date=date(2024, 1, 10),
            share_capital_raw="500000.00",
            provenance=prov,
            cnae_main_code="42.11-1-01",
            secondary_cnae_codes=["43.13-4-00", "4120400"],
            registration_status="ATIVA",
        )

        self.assertEqual(company.cnae_main_code, "4211101")
        self.assertEqual(company.main_cnae_code, "4211101")
        self.assertEqual(company.secondary_cnae_codes, ("4313400", "4120400"))
        self.assertEqual(len(company.natural_key), 64)

        # Rejection of invalid secondary CNAE code
        with self.assertRaises(ValueError):
            CuratedCompanyRegistrationRecord.create_validated(
                cnpj_raw="11.222.333/0001-81",
                legal_name="Empresa Teste",
                opening_date=date(2024, 1, 10),
                share_capital_raw="10000.00",
                provenance=prov,
                cnae_main_code="4211101",
                secondary_cnae_codes=["123"],  # inválido
            )

    def test_cnae_incompatibility_rule_detects_mismatch(self) -> None:
        """`FR-033`, `NFR-018`, `AC-059`: Detects contract requiring heavy civil engineering awarded to retail stationery company."""
        prov_rfb = _make_rfb_provenance("RFB-MISMATCH", sha="1" * 64)
        prov_pncp = _make_pncp_provenance("PNCP-MISMATCH", sha="2" * 64)

        # Empresa com CNAE exclusivo de comércio varejista de artigos de papelaria (Divisão 47)
        company = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="12.345.678/0001-95",
            legal_name="Papelaria e Armarinho Estrela Ltda",
            opening_date=date(2021, 5, 20),
            share_capital_raw="20000.00",
            provenance=prov_rfb,
            cnae_main_code="47.61-0-03",  # Comércio varejista
            secondary_cnae_codes=[],
        )

        # Contrato de R$ 350.000,00 para pavimentação asfáltica e drenagem de vias públicas (Divisões 41, 42, 43)
        contract = CuratedPublicContract.create_validated(
            pncp_control_number="00000000000191-1-000088/2026",
            organ_cnpj_raw="00.000.000/0001-91",
            organ_name="Prefeitura Municipal Conveniada",
            supplier_raw_doc="12.345.678/0001-95",
            supplier_name="Papelaria e Armarinho Estrela Ltda",
            modality_name="Concorrencia Eletronica",
            contract_object="Contratação de obras de pavimentação asfáltica e drenagem pluvial urbana",
            signature_date=date(2026, 8, 14),
            initial_amount_raw="350000.00",
            current_amount_raw="350000.00",
            addendum_count=0,
            provenance=prov_pncp,
        )

        signals = evaluate_cnae_contract_incompatibility_rule(
            contracts=[contract],
            companies=[company],
            min_contract_threshold=Decimal("50000.00"),
        )

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-CORP-CNAE-INCOMPATIBLE")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.STATISTICAL_ANOMALY)
        self.assertEqual(sig.metric_name, "cnae_sectoral_incompatibility_flag")
        self.assertEqual(sig.metric_value, Decimal("1.00"))
        self.assertEqual(sig.audited_amount, Decimal("350000.00"))
        self.assertTrue(sig.requires_human_review)
        self.assertEqual(set(sig.provenance_hashes), {"1" * 64, "2" * 64})
        self.assertIn("4761003", sig.official_fact_summary)
        self.assertIn("pavimentação asfáltica", sig.official_fact_summary)
        self.assertIn("A divergência cadastral não comprova incapacidade", sig.scope_limitation_summary)

    def test_cnae_incompatibility_rule_respects_secondary_cnaes(self) -> None:
        """`FR-033`, `AC-060`: Discards signal when any secondary CNAE covers the required sector."""
        prov_rfb = _make_rfb_provenance("RFB-SEC")
        prov_pncp = _make_pncp_provenance("PNCP-SEC")

        # Empresa com CNAE principal de papelaria (47), mas CNAE secundário de construção de rodovias (42)
        company = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="12.345.678/0001-95",
            legal_name="Comercial e Engenharia Estrela Ltda",
            opening_date=date(2021, 5, 20),
            share_capital_raw="500000.00",
            provenance=prov_rfb,
            cnae_main_code="47.61-0-03",  # Varejo
            secondary_cnae_codes=["42.11-1-01"],  # Construção de rodovias e ferrovias (compatível!)
        )

        contract = CuratedPublicContract.create_validated(
            pncp_control_number="00000000000191-1-000089/2026",
            organ_cnpj_raw="00.000.000/0001-91",
            organ_name="Prefeitura Municipal Conveniada",
            supplier_raw_doc="12.345.678/0001-95",
            supplier_name="Comercial e Engenharia Estrela Ltda",
            modality_name="Concorrencia Eletronica",
            contract_object="Serviços de pavimentação asfáltica de vias públicas",
            signature_date=date(2026, 8, 14),
            initial_amount_raw="400000.00",
            current_amount_raw="400000.00",
            addendum_count=0,
            provenance=prov_pncp,
        )

        signals = evaluate_cnae_contract_incompatibility_rule(
            contracts=[contract],
            companies=[company],
            min_contract_threshold=Decimal("50000.00"),
        )

        self.assertEqual(len(signals), 0, "Deveria descartar sinal devido ao CNAE secundário compatível.")

    def test_cnae_rule_ignores_compatible_or_low_value_contracts(self) -> None:
        """`FR-033`, `AC-061`: Ignores contracts below R$ 50.000,00 or with fully compatible main CNAE."""
        prov_rfb = _make_rfb_provenance("RFB-OK")
        prov_pncp = _make_pncp_provenance("PNCP-OK")

        # Empresa de software (Divisão 62)
        company = CuratedCompanyRegistrationRecord.create_validated(
            cnpj_raw="33.000.167/0001-01",
            legal_name="Sistemas Avançados de TI Ltda",
            opening_date=date(2022, 3, 10),
            share_capital_raw="100000.00",
            provenance=prov_rfb,
            cnae_main_code="62.01-5-01",
            secondary_cnae_codes=[],
        )

        # Caso 1: Contrato de TI compatível (R$ 150.000,00)
        contract_ti = CuratedPublicContract.create_validated(
            pncp_control_number="00000000000191-1-000090/2026",
            organ_cnpj_raw="00.000.000/0001-91",
            organ_name="Ministério da Ciência e Tecnologia",
            supplier_raw_doc="33.000.167/0001-01",
            supplier_name="Sistemas Avançados de TI Ltda",
            modality_name="Dispensa de Licitacao",
            contract_object="Desenvolvimento e manutenção de software em nuvem",
            signature_date=date(2026, 9, 1),
            initial_amount_raw="150000.00",
            current_amount_raw="150000.00",
            addendum_count=0,
            provenance=prov_pncp,
        )

        signals_ti = evaluate_cnae_contract_incompatibility_rule(
            contracts=[contract_ti],
            companies=[company],
            min_contract_threshold=Decimal("50000.00"),
        )
        self.assertEqual(len(signals_ti), 0)

        # Caso 2: Contrato incompatível mas abaixo do limiar (R$ 35.000,00 < R$ 50.000,00)
        contract_low = CuratedPublicContract.create_validated(
            pncp_control_number="00000000000191-1-000091/2026",
            organ_cnpj_raw="00.000.000/0001-91",
            organ_name="Ministério dos Transportes",
            supplier_raw_doc="33.000.167/0001-01",
            supplier_name="Sistemas Avançados de TI Ltda",
            modality_name="Dispensa de Licitacao",
            contract_object="Obras de pavimentação asfáltica de estacionamento",
            signature_date=date(2026, 9, 10),
            initial_amount_raw="35000.00",
            current_amount_raw="35000.00",  # abaixo de R$ 50.000,00
            addendum_count=0,
            provenance=prov_pncp,
        )

        signals_low = evaluate_cnae_contract_incompatibility_rule(
            contracts=[contract_low],
            companies=[company],
            min_contract_threshold=Decimal("50000.00"),
        )
        self.assertEqual(len(signals_low), 0)


if __name__ == "__main__":
    unittest.main()
