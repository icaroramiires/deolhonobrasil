"""TDD Unit & Integration Tests for `SPEC-0008` — Benford Distribution & Split Expense Audit Rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import (
    evaluate_benford_distribution_rule,
    evaluate_split_expense_rule,
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
    organ_code: str = "ORGAO_TESTE",
    organ_name: str = "MINISTERIO DA AUDITORIA",
    supplier_raw_doc: str = "11.222.333/0001-81",
    supplier_name: str = "EMPRESA DE TESTE LTDA",
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
        public_agent_name="Servidor Teste",
        party_sigla="PART_A",
        state_uf="DF",
        expense_category="SERVICOS TECNICOS",
        supplier_raw_doc=supplier_raw_doc,
        supplier_name=supplier_name,
        document_number=f"DOC-{expense_id}",
        gross_amount_raw=amount_str,
        net_amount_raw=amount_str,
        document_evidence_url=None,
        provenance=prov,
    )


class TestBenfordAndSplitExpenseRules(unittest.TestCase):
    """Tests `FR-018`, `FR-019`, `NFR-011`, `DATA-010`, `SEC-011`, and `AC-030..033`."""

    def test_benford_rule_detects_non_conformant_distribution_and_emits_signal(self) -> None:
        """`FR-018`, `DATA-010`, `SEC-011`, `AC-030`: Benford rule detects severe departure from Benford distribution (N >= 50, MAD > 0.01500) and emits AuditSignal."""
        # Cria 60 despesas onde todas começam artificialmente com o dígito 9 (900.00 a 990.00)
        # Na Lei de Benford, o dígito 9 deveria ter ~4.57% de frequência. Com 100%, o MAD excede 0.10.
        expenses: list[CuratedPublicExpense] = []
        for i in range(60):
            expenses.append(
                _make_expense(
                    expense_id=f"EXP-BENF-9-{i}",
                    amount_str=f"9{i % 10}0.00",
                    issue_date=date(2026, 3, 1 + (i % 28)),
                    sha=f"sha_benf_{i // 10}" + "0" * 54,
                )
            )

        signal = evaluate_benford_distribution_rule(
            expenses=expenses,
            context_label="Despesas de Tecnologia da Informacao",
            min_sample_size=50,
            mad_threshold=Decimal("0.01500"),
        )

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal.rule_code, "R-STAT-BENFORD-DEVIATION")
        self.assertEqual(signal.epistemic_layer, EpistemicClassification.STATISTICAL_ANOMALY)
        self.assertGreater(signal.metric_value, Decimal("0.01500"))
        self.assertTrue(signal.requires_human_review)
        self.assertGreaterEqual(len(signal.provenance_hashes), 1)
        self.assertIn("Despesas de Tecnologia", signal.official_fact_summary)
        self.assertIn("MAD", signal.statistical_inference_summary)
        self.assertIn("Lei de Benford", signal.scope_limitation_summary)

    def test_benford_rule_returns_none_for_conformant_or_small_sample(self) -> None:
        """`FR-018`, `AC-031`: Returns None when sample size < 50 or when distribution is conformant."""
        # Caso 1: Amostra insuficiente (40 despesas < 50)
        small_sample: list[CuratedPublicExpense] = []
        for i in range(40):
            small_sample.append(
                _make_expense(
                    expense_id=f"EXP-SMALL-{i}",
                    amount_str="950.00",
                    issue_date=date(2026, 3, 1),
                )
            )
        self.assertIsNone(
            evaluate_benford_distribution_rule(small_sample, min_sample_size=50)
        )

        # Caso 2: Amostra de 100 despesas construída para seguir a distribuição de Benford
        # P(1)~30, P(2)~17, P(3)~12, P(4)~9, P(5)~8, P(6)~7, P(7)~6, P(8)~5, P(9)~5
        benford_counts = {1: 30, 2: 17, 3: 12, 4: 10, 5: 8, 6: 7, 7: 6, 8: 5, 9: 5}
        conformant_expenses: list[CuratedPublicExpense] = []
        idx = 0
        for digit, count in benford_counts.items():
            for _ in range(count):
                idx += 1
                conformant_expenses.append(
                    _make_expense(
                        expense_id=f"EXP-CONF-{idx}",
                        amount_str=f"{digit}50.00",
                        issue_date=date(2026, 4, 1),
                    )
                )

        signal = evaluate_benford_distribution_rule(
            expenses=conformant_expenses,
            min_sample_size=50,
            mad_threshold=Decimal("0.01500"),
        )
        self.assertIsNone(signal)

    def test_split_expense_rule_detects_clustering_within_rolling_window(self) -> None:
        """`FR-019`, `NFR-011`, `DATA-010`, `SEC-011`, `AC-032`: Detects repeated dispensa purchases for same supplier in 90-day window exceeding cumulative threshold."""
        # Fornecedor recebe 3 pagamentos de R$ 45.000,00 cada em intervalo de 40 dias (mesmo órgão)
        # Cada pagamento individual < R$ 50.000 (teto unitário de dispensa)
        # Total acumulado = R$ 135.000,00 > R$ 100.000 (limiar cumulativo de alerta)
        expenses = [
            _make_expense(
                expense_id="SPLIT-01",
                amount_str="45000.00",
                issue_date=date(2026, 2, 10),
                organ_code="MIN_OBRAS",
                organ_name="MINISTERIO DAS OBRAS",
                supplier_raw_doc="11.222.333/0001-81",
                supplier_name="CONSTRUTORA MODERNA LTDA",
                sha="sha_split_1" + "0" * 53,
            ),
            _make_expense(
                expense_id="SPLIT-02",
                amount_str="45000.00",
                issue_date=date(2026, 2, 25),
                organ_code="MIN_OBRAS",
                organ_name="MINISTERIO DAS OBRAS",
                supplier_raw_doc="11.222.333/0001-81",
                supplier_name="CONSTRUTORA MODERNA LTDA",
                sha="sha_split_2" + "0" * 53,
            ),
            _make_expense(
                expense_id="SPLIT-03",
                amount_str="45000.00",
                issue_date=date(2026, 3, 20),
                organ_code="MIN_OBRAS",
                organ_name="MINISTERIO DAS OBRAS",
                supplier_raw_doc="11.222.333/0001-81",
                supplier_name="CONSTRUTORA MODERNA LTDA",
                sha="sha_split_3" + "0" * 53,
            ),
        ]

        signals = evaluate_split_expense_rule(
            expenses=expenses,
            single_limit_threshold=Decimal("50000.00"),
            aggregate_threshold=Decimal("100000.00"),
            window_days=90,
            min_count=3,
        )

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-SPLIT-EXPENSE-THRESHOLD")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.UNVALIDATED_HYPOTHESIS)
        self.assertEqual(sig.audited_amount, Decimal("135000.00"))
        self.assertEqual(sig.threshold_value, Decimal("100000.00"))
        self.assertTrue(sig.requires_human_review)
        self.assertEqual(len(sig.provenance_hashes), 3)
        self.assertIn("CONSTRUTORA MODERNA", sig.official_fact_summary)
        self.assertIn("135000.00", sig.statistical_inference_summary)
        self.assertIn("objetos contratados", sig.scope_limitation_summary)

    def test_split_expense_rule_ignores_isolated_transactions_or_below_aggregate_threshold(self) -> None:
        """`FR-019`, `AC-033`: Ignores transactions that are temporally spaced (> 90 days) or do not exceed aggregate threshold."""
        # Caso 1: 3 transações, mas espaçadas em 200 dias (fora da janela de 90 dias)
        spaced_expenses = [
            _make_expense(
                expense_id="SPACED-01",
                amount_str="40000.00",
                issue_date=date(2026, 1, 10),
            ),
            _make_expense(
                expense_id="SPACED-02",
                amount_str="40000.00",
                issue_date=date(2026, 5, 20),
            ),
            _make_expense(
                expense_id="SPACED-03",
                amount_str="40000.00",
                issue_date=date(2026, 9, 30),
            ),
        ]
        self.assertEqual(
            len(
                evaluate_split_expense_rule(
                    spaced_expenses,
                    single_limit_threshold=Decimal("50000.00"),
                    aggregate_threshold=Decimal("100000.00"),
                    window_days=90,
                    min_count=3,
                )
            ),
            0,
        )

        # Caso 2: 3 transações na mesma semana, mas totalizando apenas R$ 15.000 (abaixo de R$ 100.000)
        low_total_expenses = [
            _make_expense(
                expense_id="LOW-01",
                amount_str="5000.00",
                issue_date=date(2026, 2, 10),
            ),
            _make_expense(
                expense_id="LOW-02",
                amount_str="5000.00",
                issue_date=date(2026, 2, 12),
            ),
            _make_expense(
                expense_id="LOW-03",
                amount_str="5000.00",
                issue_date=date(2026, 2, 14),
            ),
        ]
        self.assertEqual(
            len(
                evaluate_split_expense_rule(
                    low_total_expenses,
                    single_limit_threshold=Decimal("50000.00"),
                    aggregate_threshold=Decimal("100000.00"),
                    window_days=90,
                    min_count=3,
                )
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
