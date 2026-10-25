# Test Plan — SPEC-0014

## Requirements Traceability Matrix
- `FR-030` -> `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_company_registration_model_validation`
- `FR-031` (Recent Creation) -> `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_recent_company_creation_rule_detects_young_company`
- `FR-031` (Low Capital Outlier) -> `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_low_capital_outlier_rule_detects_extreme_ratio`
- `NFR-017`, `DATA-016`, `SEC-017`, `AC-054..057` -> All test anchors combined.

## Test Anchors
1. `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_company_registration_model_validation`
2. `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_recent_company_creation_rule_detects_young_company`
3. `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_low_capital_outlier_rule_detects_extreme_ratio`
4. `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_rules_ignore_mature_companies_and_sound_capital`
