# Test Plan — SPEC-0008

## 1. Test Suite Location
`tests/test_benford_and_split_expenses.py`

## 2. Test Anchors Mapping
- **`AC-030` / `FR-018`**:
  - `test_benford_rule_detects_non_conformant_distribution_and_emits_signal`
- **`AC-031` / `FR-018`**:
  - `test_benford_rule_returns_none_for_conformant_or_small_sample`
- **`AC-032` / `FR-019` / `NFR-011`**:
  - `test_split_expense_rule_detects_clustering_within_rolling_window`
- **`AC-033` / `FR-019` / `DATA-010`**:
  - `test_split_expense_rule_ignores_isolated_transactions_or_below_aggregate_threshold`

## 3. Execution Command
```bash
PYTHONPATH=src pytest tests/test_benford_and_split_expenses.py -v
```
