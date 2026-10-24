# Test Plan — SPEC-0010

Mapeamento dos requisitos para os 4 Test Anchors obrigatórios:

1. `FR-022`, `AC-038`, `DATA-012` $\rightarrow$ `tests/test_duplicate_and_overlap_expenses.py::TestDuplicateAndOverlapExpensesRules::test_duplicate_expense_document_rule_detects_identical_invoice`
2. `FR-022`, `AC-039`, `SEC-013` $\rightarrow$ `tests/test_duplicate_and_overlap_expenses.py::TestDuplicateAndOverlapExpensesRules::test_duplicate_expense_document_rule_ignores_generic_or_different_suppliers`
3. `FR-023`, `AC-040`, `NFR-013` $\rightarrow$ `tests/test_duplicate_and_overlap_expenses.py::TestDuplicateAndOverlapExpensesRules::test_temporal_geographic_overlap_rule_detects_same_day_distinct_states`
4. `FR-023`, `AC-041` $\rightarrow$ `tests/test_duplicate_and_overlap_expenses.py::TestDuplicateAndOverlapExpensesRules::test_temporal_geographic_overlap_rule_ignores_same_state_or_online_categories`
