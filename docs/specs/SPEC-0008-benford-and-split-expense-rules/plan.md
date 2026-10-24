# Technical Design Plan — SPEC-0008

## 1. Overview
This technical design defines the implementation details for `evaluate_benford_distribution_rule` and `evaluate_split_expense_rule` inside `src/deolhonobrasil/audit/rules.py`.

## 2. Module Changes
- **`src/deolhonobrasil/audit/rules.py`**:
  - Add `evaluate_benford_first_digit(values: list[float]) -> dict`
  - Add `evaluate_benford_distribution_rule(expenses: list[dict]) -> AuditSignal | None`
  - Add `evaluate_split_expense_rule(expenses: list[dict], window_days: int = 90, aggregate_threshold: float = 50000.0) -> list[AuditSignal]`

## 3. Algorithm Details
- **Benford Rule (`R-STAT-BENFORD-DEVIATION`)**: Extract first significant digit from each expense amount, compute empirical frequency vs theoretical Benford log10(1 + 1/d), calculate MAD, and emit signal if MAD > 0.01500 and $N \ge 50$.
- **Split Expense Rule (`R-SPLIT-EXPENSE-THRESHOLD`)**: Sort expenses chronologically by date per supplier and organ, maintain a sliding window of `window_days`, sum values of transactions below single-dispensing limit, and trigger an `AuditSignal` when the window sum exceeds `aggregate_threshold`.

## 4. Error Handling & Edge Cases
- Handle empty lists, zero or negative values gracefully.
- Ensure time complexity remains $O(N \log N)$ due to sorting.
