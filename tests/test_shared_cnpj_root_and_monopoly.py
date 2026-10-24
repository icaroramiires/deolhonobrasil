"""TDD Unit & Integration Tests for `SPEC-0009` — Shared CNPJ Root & Monopolistic Supplier Rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import (
    evaluate_monopolistic_supplier_category_rule,
    evaluate_shared_cnpj_root_rule,
    extract_cnpj_root,
)
from deolhonobrasil.pipeline.models import (
    CuratedPublicExpense,
    EpistemicClassification,
    OfficialSource,
    ProvenanceMetadata,
)


def _make_expense(
    expense_id: str,
    amount_str: str,
    issue_date: date,
    organ_code: str = "MIN_SAUDE",
    organ_name: str = "MINISTERIO DA SAUDE",
    supplier_raw_doc: str = "11.222.333/0001-81",
    supplier_name: str = "FORNECEDOR MATRIZ LTDA",
    category: str = "MEDICAMENTOS",
    sha: str = "a" * 64,
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
        organ_code=organ_code,
        organ_name=organ_name,
        public_agent_id="AGENT-01",
        public_agent_name="Fiscal Teste",
        party_sigla="PART_A",
        state_uf="DF",
        expense_category=category,
        supplier_raw_doc=supplier_raw_doc,
        supplier_name=supplier_name,
        document_number=f"DOC-{expense_id}",
        gross_amount_raw=amount_str,
        net_amount_raw=amount_str,
        document_evidence_url=None,
        provenance=prov,
    )


class TestSharedCnpjRootAndMonopolyRules(unittest.TestCase):
    """Tests `FR-020`, `FR-021`, `NFR-012`, `DATA-011`, `SEC-012`, and `AC-034..037`."""

    def test_extract_cnpj_root_validates_14_digits_and_rejects_cpf(self) -> None:
        """`FR-020`, `NFR-012`, `AC-034`: Extracts 8-digit root from valid 14-digit CNPJs; rejects masked CPFs or invalid strings."""
        # CNPJ formatado ou apenas dígitos
        self.assertEqual(extract_cnpj_root("11.222.333/0001-81"), "11222333")
        self.assertEqual(extract_cnpj_root("11222333000262"), "11222333")
        self.assertEqual(extract_cnpj_root("00.000.000/0001-91"), "00000000")

        # CPF mascarado (LGPD) ou strings inválidas devem retornar None
        self.assertIsNone(extract_cnpj_root("***.456.789-**"))
        self.assertIsNone(extract_cnpj_root("123.456.789-00"))  # 11 dígitos (CPF)
        self.assertIsNone(extract_cnpj_root(""))
        self.assertIsNone(extract_cnpj_root("INVALIDO"))

    def test_shared_cnpj_root_rule_detects_multiple_branches_for_same_organ(self) -> None:
        """`FR-020`, `DATA-011`, `SEC-012`, `AC-035`: Detects disbursements distributed across multiple branches of same CNPJ root to same organ."""
        # 3 filiais do mesmo grupo (raiz 11.222.333):
        # Filial 0001: R$ 60.000
        # Filial 0002: R$ 50.000
        # Filial 0003: R$ 40.000
        # Total = R$ 150.000 >= R$ 100.000
        expenses = [
            _make_expense(
                expense_id="EXP-F1",
                amount_str="60000.00",
                issue_date=date(2026, 3, 10),
                supplier_raw_doc="11.222.333/0001-81",
                supplier_name="GRUPO ALFA MATRIZ",
                sha="sha_root_1" + "0" * 54,
            ),
            _make_expense(
                expense_id="EXP-F2",
                amount_str="50000.00",
                issue_date=date(2026, 3, 15),
                supplier_raw_doc="11.222.333/0002-62",
                supplier_name="GRUPO ALFA FILIAL SP",
                sha="sha_root_2" + "0" * 54,
            ),
            _make_expense(
                expense_id="EXP-F3",
                amount_str="40000.00",
                issue_date=date(2026, 3, 20),
                supplier_raw_doc="11.222.333/0003-43",
                supplier_name="GRUPO ALFA FILIAL RJ",
                sha="sha_root_3" + "0" * 54,
            ),
        ]

        signals = evaluate_shared_cnpj_root_rule(
            expenses=expenses,
            min_branches=2,
            min_aggregate_amount=Decimal("100000.00"),
        )

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-SHARED-CNPJ-ROOT")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.STATISTICAL_ANOMALY)
        self.assertEqual(sig.audited_amount, Decimal("150000.00"))
        self.assertEqual(sig.threshold_value, Decimal("100000.00"))
        self.assertEqual(sig.metric_value, Decimal("3.00"))  # 3 filiais distintas
        self.assertTrue(sig.requires_human_review)
        self.assertEqual(len(sig.provenance_hashes), 3)
        self.assertIn("11222333", sig.official_fact_summary)
        self.assertIn("3 filiais", sig.statistical_inference_summary)
        self.assertIn("grupo econômico", sig.scope_limitation_summary)

    def test_shared_cnpj_root_rule_ignores_single_branch_or_unrelated_cnpjs(self) -> None:
        """`FR-020`, `AC-035`: Does not emit signal when only a single branch operates or when CNPJs have distinct roots."""
        # Caso 1: 3 despesas, mas todas para a mesma filial única (0001)
        single_branch_expenses = [
            _make_expense(
                expense_id=f"EXP-SB-{i}",
                amount_str="40000.00",
                issue_date=date(2026, 3, 10 + i),
                supplier_raw_doc="11.222.333/0001-81",
            )
            for i in range(3)
        ]
        self.assertEqual(
            len(evaluate_shared_cnpj_root_rule(single_branch_expenses, min_branches=2)),
            0,
        )

        # Caso 2: 3 fornecedores com raízes de CNPJ completamente diferentes
        distinct_roots_expenses = [
            _make_expense(
                expense_id="EXP-D1",
                amount_str="50000.00",
                issue_date=date(2026, 3, 10),
                supplier_raw_doc="00.360.305/0001-04",
            ),
            _make_expense(
                expense_id="EXP-D2",
                amount_str="50000.00",
                issue_date=date(2026, 3, 11),
                supplier_raw_doc="33.592.510/0001-54",
            ),
            _make_expense(
                expense_id="EXP-D3",
                amount_str="50000.00",
                issue_date=date(2026, 3, 12),
                supplier_raw_doc="33.657.248/0001-89",
            ),
        ]
        self.assertEqual(
            len(evaluate_shared_cnpj_root_rule(distinct_roots_expenses, min_branches=2)),
            0,
        )

    def test_monopolistic_supplier_category_rule_detects_dominance(self) -> None:
        """`FR-021`, `DATA-011`, `SEC-012`, `AC-036`, `AC-037`: Detects dominance (>= 80%) by a single corporate root in a category/organ with >= R$ 100.000."""
        # Categoria "MEDICAMENTOS": Total R$ 200.000,00
        # Fornecedor dominante (raiz 33.000.167 - Petrobras matriz e filial): R$ 170.000,00 (85% >= 80%)
        # Outro fornecedor (raiz 00.360.305 - Caixa): R$ 30.000,00 (15%)
        expenses = [
            _make_expense(
                expense_id="MONOP-01",
                amount_str="85000.00",
                issue_date=date(2026, 2, 1),
                supplier_raw_doc="33.000.167/0001-01",
                supplier_name="DISTRIBUIDORA NACIONAL LTDA",
                category="MEDICAMENTOS",
                sha="sha_m1" + "0" * 58,
            ),
            _make_expense(
                expense_id="MONOP-02",
                amount_str="85000.00",
                issue_date=date(2026, 2, 15),
                supplier_raw_doc="33.000.167/0002-92",
                supplier_name="DISTRIBUIDORA NACIONAL FILIAL",
                category="MEDICAMENTOS",
                sha="sha_m2" + "0" * 58,
            ),
            _make_expense(
                expense_id="MONOP-03",
                amount_str="30000.00",
                issue_date=date(2026, 2, 20),
                supplier_raw_doc="00.360.305/0001-04",
                supplier_name="OUTRA FARMA LTDA",
                category="MEDICAMENTOS",
                sha="sha_m3" + "0" * 58,
            ),
        ]

        signals = evaluate_monopolistic_supplier_category_rule(
            expenses=expenses,
            dominance_share_threshold=Decimal("0.80"),
            min_total_amount=Decimal("100000.00"),
            min_transactions=3,
        )

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-PROCUREMENT-MONOPOLISTIC-SUPPLIER")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.STATISTICAL_ANOMALY)
        self.assertGreaterEqual(sig.metric_value, Decimal("0.80"))
        self.assertEqual(sig.audited_amount, Decimal("170000.00"))
        self.assertEqual(sig.threshold_value, Decimal("0.80"))
        self.assertTrue(sig.requires_human_review)
        self.assertEqual(len(sig.provenance_hashes), 2)
        self.assertIn("MEDICAMENTOS", sig.official_fact_summary)
        self.assertIn("85.00%", sig.statistical_inference_summary)
        self.assertIn("especialização técnica", sig.scope_limitation_summary)


if __name__ == "__main__":
    unittest.main()
