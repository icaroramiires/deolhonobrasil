"""TDD Unit & Integration Tests for `SPEC-0010` — Duplicate Expense Document & Spatiotemporal Overlap Rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import (
    evaluate_duplicate_expense_document_rule,
    evaluate_temporal_geographic_overlap_rule,
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
    organ_code: str = "CAMARA_DEPUTADOS",
    organ_name: str = "CAMARA DOS DEPUTADOS",
    public_agent_id: str = "DEP-101",
    public_agent_name: str = "Deputado Auditor",
    state_uf: str = "DF",
    category: str = "COMBUSTIVEL",
    supplier_raw_doc: str = "33.000.167/0001-01",
    supplier_name: str = "POSTO CAPITAL LTDA",
    document_number: str = "NF-998877",
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
        public_agent_id=public_agent_id,
        public_agent_name=public_agent_name,
        party_sigla="PART_A",
        state_uf=state_uf,
        expense_category=category,
        supplier_raw_doc=supplier_raw_doc,
        supplier_name=supplier_name,
        document_number=document_number,
        gross_amount_raw=amount_str,
        net_amount_raw=amount_str,
        document_evidence_url=None,
        provenance=prov,
    )


class TestDuplicateAndOverlapExpensesRules(unittest.TestCase):
    """Tests `FR-022`, `FR-023`, `NFR-013`, `DATA-012`, `SEC-013`, and `AC-038..041`."""

    def test_duplicate_expense_document_rule_detects_identical_invoice(self) -> None:
        """`FR-022`, `DATA-012`, `SEC-013`, `AC-038`: Detects identical document_number for same supplier reimbursed more than once."""
        # Duas despesas reembolsadas com a mesma nota fiscal NF-998877 e mesmo CNPJ 33.000.167/0001-01
        exp1 = _make_expense(
            expense_id="EXP-DUP-1",
            amount_str="1500.00",
            issue_date=date(2026, 4, 10),
            document_number="NF-998877",
            sha="sha_dup_1" + "0" * 55,
        )
        exp2 = _make_expense(
            expense_id="EXP-DUP-2",
            amount_str="1500.00",
            issue_date=date(2026, 4, 10),
            document_number="NF-998877",
            sha="sha_dup_2" + "0" * 55,
        )

        signals = evaluate_duplicate_expense_document_rule([exp1, exp2])

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-DUPLICATE-EXPENSE-DOCUMENT")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.CROSS_SOURCE_DIVERGENCE)
        self.assertEqual(sig.audited_amount, Decimal("3000.00"))
        self.assertEqual(sig.metric_value, Decimal("2.00"))  # 2 ocorrências do documento
        self.assertTrue(sig.requires_human_review)
        self.assertEqual(len(sig.provenance_hashes), 2)
        self.assertIn("NF-998877", sig.official_fact_summary)
        self.assertIn("POSTO CAPITAL", sig.official_fact_summary)
        self.assertIn("séries fiscais distintas", sig.scope_limitation_summary)

    def test_duplicate_expense_document_rule_ignores_generic_or_different_suppliers(self) -> None:
        """`FR-022`, `AC-039`: Ignores generic document numbers ('S/N', '0', '-') or same document number under different suppliers."""
        # Caso 1: Documentos genéricos 'S/N' para o mesmo fornecedor
        generic_expenses = [
            _make_expense(
                expense_id="EXP-GEN-1",
                amount_str="200.00",
                issue_date=date(2026, 4, 10),
                document_number="S/N",
            ),
            _make_expense(
                expense_id="EXP-GEN-2",
                amount_str="300.00",
                issue_date=date(2026, 4, 12),
                document_number="S/N",
            ),
            _make_expense(
                expense_id="EXP-GEN-3",
                amount_str="150.00",
                issue_date=date(2026, 4, 15),
                document_number="0",
            ),
        ]
        self.assertEqual(len(evaluate_duplicate_expense_document_rule(generic_expenses)), 0)

        # Caso 2: Mesmo número de nota fiscal NF-100, mas de fornecedores com CNPJs distintos
        diff_suppliers_expenses = [
            _make_expense(
                expense_id="EXP-DIFF-1",
                amount_str="500.00",
                issue_date=date(2026, 4, 10),
                supplier_raw_doc="33.000.167/0001-01",
                document_number="NF-100",
            ),
            _make_expense(
                expense_id="EXP-DIFF-2",
                amount_str="500.00",
                issue_date=date(2026, 4, 10),
                supplier_raw_doc="00.360.305/0001-04",
                document_number="NF-100",
            ),
        ]
        self.assertEqual(len(evaluate_duplicate_expense_document_rule(diff_suppliers_expenses)), 0)

    def test_temporal_geographic_overlap_rule_detects_same_day_distinct_states(self) -> None:
        """`FR-023`, `DATA-012`, `SEC-013`, `AC-040`: Detects spatiotemporal conflict where same agent has physical-presence expenses in distinct states on same day."""
        # Mesmo agente DEP-101 no dia 2026-05-15:
        # Despesa 1: Abastecimento em SP
        # Despesa 2: Hospedagem no DF
        exp_sp = _make_expense(
            expense_id="EXP-GEO-SP",
            amount_str="450.00",
            issue_date=date(2026, 5, 15),
            public_agent_id="DEP-101",
            state_uf="SP",
            category="COMBUSTIVEL",
            sha="sha_sp" + "0" * 58,
        )
        exp_df = _make_expense(
            expense_id="EXP-GEO-DF",
            amount_str="1200.00",
            issue_date=date(2026, 5, 15),
            public_agent_id="DEP-101",
            state_uf="DF",
            category="HOSPEDAGEM",
            sha="sha_df" + "0" * 58,
        )

        signals = evaluate_temporal_geographic_overlap_rule([exp_sp, exp_df])

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-TEMPORAL-GEOGRAPHIC-OVERLAP")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.STATISTICAL_ANOMALY)
        self.assertEqual(sig.audited_amount, Decimal("1650.00"))
        self.assertEqual(sig.metric_value, Decimal("2.00"))  # 2 UFs distintas
        self.assertTrue(sig.requires_human_review)
        self.assertEqual(len(sig.provenance_hashes), 2)
        self.assertIn("DEP-101", sig.official_fact_summary)
        self.assertIn("2026-05-15", sig.official_fact_summary)
        self.assertIn("assessores autorizados", sig.scope_limitation_summary)

    def test_temporal_geographic_overlap_rule_ignores_same_state_or_online_categories(self) -> None:
        """`FR-023`, `AC-041`: Ignores expenses in same state on same day, or non-physical/remote categories."""
        # Caso 1: 2 despesas no mesmo dia, mas ambas em SP
        same_state = [
            _make_expense(
                expense_id="EXP-SAME-1",
                amount_str="300.00",
                issue_date=date(2026, 5, 15),
                public_agent_id="DEP-101",
                state_uf="SP",
                category="COMBUSTIVEL",
            ),
            _make_expense(
                expense_id="EXP-SAME-2",
                amount_str="250.00",
                issue_date=date(2026, 5, 15),
                public_agent_id="DEP-101",
                state_uf="SP",
                category="ALIMENTACAO",
            ),
        ]
        self.assertEqual(len(evaluate_temporal_geographic_overlap_rule(same_state)), 0)

        # Caso 2: Despesas em estados diferentes, mas uma delas é categoria remota/online
        online_expense = [
            _make_expense(
                expense_id="EXP-ON-1",
                amount_str="450.00",
                issue_date=date(2026, 5, 15),
                public_agent_id="DEP-101",
                state_uf="SP",
                category="COMBUSTIVEL",
            ),
            _make_expense(
                expense_id="EXP-ON-2",
                amount_str="5000.00",
                issue_date=date(2026, 5, 15),
                public_agent_id="DEP-101",
                state_uf="DF",
                category="DIVULGACAO DA ATIVIDADE PARLAMENTAR",  # Categoria que não exige presença física
            ),
        ]
        self.assertEqual(len(evaluate_temporal_geographic_overlap_rule(online_expense)), 0)


if __name__ == "__main__":
    unittest.main()
