# Data Model & API Contracts — SPEC-0008

## 1. Audit Signal Structures
### Benford Deviation Signal
- `rule_id`: `R-STAT-BENFORD-DEVIATION`
- `metrics`:
  - `sample_size`: int ($N \ge 50$)
  - `mad`: float (Mean Absolute Deviation)
  - `chi_square`: float
- `provenance_hashes`: `list[str]` (SHA-256 hashes of input batches)

### Split Expense Signal
- `rule_id`: `R-SPLIT-EXPENSE-THRESHOLD`
- `metrics`:
  - `supplier_doc_normalized`: str
  - `window_days`: int
  - `total_aggregated_amount`: float
  - `transaction_count`: int
- `provenance_hashes`: `list[str]`

## 2. Pydantic Models & TypedDicts
All structures integrate with existing `AuditSignal` and provenance validators in `src/deolhonobrasil/audit/models.py`.
