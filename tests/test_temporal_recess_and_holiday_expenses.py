"""TDD Unit & Integration Tests for `SPEC-0011` — Temporal Recess & Holiday Audit Rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from deolhonobrasil.audit.rules import (
    evaluate_parliamentary_recess_expense_rule,
    evaluate_weekend_holiday_expense_rule,
    get_brazilian_national_holidays,
    is_parliamentary_recess,
    is_weekend_or_holiday,
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


class TestTemporalRecessAndHolidayExpenseRules(unittest.TestCase):
    """Test suite validating R-TEMPORAL-WEEKEND-HOLIDAY and R-TEMPORAL-PARLIAMENTARY-RECESS rules."""

    def test_weekend_holiday_expense_rule_detects_weekend_or_holiday(self) -> None:
        """AC-042: evaluate_weekend_holiday_expense_rule detects physical presence on weekends and holidays."""
        # 2026-10-24 is Saturday, 2026-10-25 is Sunday
        saturday_exp = _make_expense("E-SAT", "350.00", date(2026, 10, 24), category="COMBUSTIVEL")
        sunday_exp = _make_expense("E-SUN", "280.00", date(2026, 10, 25), category="ALIMENTACAO")
        # 2026-05-01 is Dia do Trabalho (Friday)
        holiday_exp = _make_expense("E-HOL", "1200.00", date(2026, 5, 1), category="HOSPEDAGEM")

        signals = evaluate_weekend_holiday_expense_rule([saturday_exp, sunday_exp, holiday_exp])
        self.assertEqual(len(signals), 3)

        for sig in signals:
            self.assertEqual(sig.rule_code, "R-TEMPORAL-WEEKEND-HOLIDAY")
            self.assertEqual(sig.epistemic_layer, EpistemicClassification.STATISTICAL_ANOMALY)
            self.assertEqual(sig.threshold_value, Decimal("0.00"))
            self.assertEqual(sig.metric_value, Decimal("1.00"))
            self.assertTrue(sig.requires_human_review)
            self.assertIn("O exercício do mandato parlamentar", sig.scope_limitation_summary)

        # Check holiday detection details
        hol_signal = [s for s in signals if s.audited_amount == Decimal("1200.00")][0]
        self.assertIn("Feriado Nacional", hol_signal.official_fact_summary)

    def test_weekend_holiday_expense_rule_ignores_weekday_or_remote_category(self) -> None:
        """AC-043: evaluate_weekend_holiday_expense_rule ignores ordinary weekdays and remote categories."""
        # 2026-10-21 is Wednesday (business day)
        weekday_exp = _make_expense("E-WED", "400.00", date(2026, 10, 21), category="COMBUSTIVEL")
        # 2026-10-24 is Saturday, but remote category
        remote_exp = _make_expense(
            "E-REMOTE", "5000.00", date(2026, 10, 24), category="DIVULGACAO DA ATIVIDADE PARLAMENTAR"
        )
        subscription_exp = _make_expense(
            "E-SUB", "150.00", date(2026, 10, 25), category="ASSINATURA DE PUBLICACOES"
        )

        signals = evaluate_weekend_holiday_expense_rule([weekday_exp, remote_exp, subscription_exp])
        self.assertEqual(signals, [])

    def test_parliamentary_recess_rule_detects_cluster_above_threshold(self) -> None:
        """AC-044: evaluate_parliamentary_recess_expense_rule detects clusters exceeding recess threshold."""
        # Winter recess: 18 to 31 July
        e1 = _make_expense("R-01", "5000.00", date(2026, 7, 20), public_agent_id="DEP-200")
        e2 = _make_expense("R-02", "6000.00", date(2026, 7, 22), public_agent_id="DEP-200")
        e3 = _make_expense("R-03", "5500.00", date(2026, 7, 25), public_agent_id="DEP-200")

        signals = evaluate_parliamentary_recess_expense_rule(
            [e1, e2, e3],
            recess_threshold_brl=Decimal("15000.00"),
            min_expense_count=3,
        )
        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.rule_code, "R-TEMPORAL-PARLIAMENTARY-RECESS")
        self.assertEqual(sig.epistemic_layer, EpistemicClassification.STATISTICAL_ANOMALY)
        self.assertEqual(sig.audited_amount, Decimal("16500.00"))
        self.assertEqual(sig.threshold_value, Decimal("15000.00"))
        self.assertIn("Recesso de Inverno", sig.official_fact_summary)
        self.assertIn("A ocorrência de despesas no recesso constitucional", sig.scope_limitation_summary)

    def test_parliamentary_recess_rule_ignores_below_threshold_or_outside_recess(self) -> None:
        """AC-045: evaluate_parliamentary_recess_expense_rule ignores non-recess periods or small sums."""
        # Outside recess (March 2026)
        m1 = _make_expense("M-01", "10000.00", date(2026, 3, 10))
        m2 = _make_expense("M-02", "10000.00", date(2026, 3, 15))

        # In recess (January 2026), but below threshold (R$ 4.000 < R$ 15.000)
        j1 = _make_expense("J-01", "2000.00", date(2026, 1, 10))
        j2 = _make_expense("J-02", "2000.00", date(2026, 1, 20))

        signals = evaluate_parliamentary_recess_expense_rule(
            [m1, m2, j1, j2],
            recess_threshold_brl=Decimal("15000.00"),
            min_expense_count=3,
        )
        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
