# Tasks Breakdown — SPEC-0014 (Jira: DONB-21)

- [ ] **`TASK-1401`**: Implement `CuratedCompanyRegistrationRecord` frozen dataclass with SHA-256 provenance and validation.
- [ ] **`TASK-1402`**: Implement `evaluate_recent_company_creation_rule` (`R-CORP-RECENT-CREATION`) for threshold < 180 days and contract >= R$ 50.000,00.
- [ ] **`TASK-1403`**: Implement `evaluate_low_capital_outlier_rule` (`R-CORP-LOW-CAPITAL-OUTLIER`) for ratio >= 50x and contract >= R$ 100.000,00 with division-by-zero safety.
- [ ] **`TASK-1404`**: Write comprehensive test suite in `tests/test_company_age_and_capital_risk.py` matching all test anchors and verify via test harness.
