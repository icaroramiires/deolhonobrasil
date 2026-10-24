# Test Plan — SPEC-0011

## 1. Mapeamento de Requisitos para Test Anchors
- `FR-024`, `AC-042`: `tests/test_temporal_recess_and_holiday_expenses.py::TestTemporalRecessAndHolidayExpenseRules::test_weekend_holiday_expense_rule_detects_weekend_or_holiday`
- `FR-024`, `AC-043`: `tests/test_temporal_recess_and_holiday_expenses.py::TestTemporalRecessAndHolidayExpenseRules::test_weekend_holiday_expense_rule_ignores_weekday_or_remote_category`
- `FR-025`, `AC-044`: `tests/test_temporal_recess_and_holiday_expenses.py::TestTemporalRecessAndHolidayExpenseRules::test_parliamentary_recess_rule_detects_cluster_above_threshold`
- `FR-025`, `AC-045`: `tests/test_temporal_recess_and_holiday_expenses.py::TestTemporalRecessAndHolidayExpenseRules::test_parliamentary_recess_rule_ignores_below_threshold_or_outside_recess`
