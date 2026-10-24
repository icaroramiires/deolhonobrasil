# Tasks — SPEC-0007 (Jira: DONB-14)

- [ ] **TASK-0701**: Implement `CuratedSanctionRecord` model and `curated_sanctions` lakehouse table schema (`DATA-009`).
- [ ] **TASK-0702**: Implement `parse_cgu_ceis_cnep_json_batch` connector with CPF masking, SHA-256 generation, and quarantine isolation (`FR-016`).
- [ ] **TASK-0703**: Implement deterministic rules `evaluate_ceis_cnep_sanctioned_supplier_rule` (`R-CROSS-CEIS-SANCTIONED-SUPPLIER`) and `evaluate_amendment_execution_divergence_rule` (`R-CROSS-AMENDMENT-EXECUTION-GAP`) with dual SHA-256 provenance (`FR-017`, `NFR-010`, `SEC-010`).
- [ ] **TASK-0704**: Implement FastAPI endpoint `GET /api/v1/sanctions` and test suite in `tests/test_cross_source_sanctions.py` covering all 5 test anchors (`AC-026` to `AC-029`).
