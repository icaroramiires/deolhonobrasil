# Test Plan — SPEC-0007

## Requirements Mapping
- **`FR-016`**: Covered by `test_ceis_cnep_connector_validates_masks_cpf_and_quarantines_invalid` & `test_lakehouse_and_api_sanctions_endpoint_roundtrip`.
- **`FR-017`**: Covered by `test_cross_source_ceis_rule_detects_active_cnpj_sanction_with_dual_sha256` & `test_amendment_execution_divergence_rule_flags_discrepancy`.
- **`NFR-010` & `DATA-009` & `SEC-010`**: Covered by `test_cross_source_ceis_rule_ignores_expired_sanction_or_masked_cpf_homonym`.

## Test Anchors in `tests/test_cross_source_sanctions.py`
1. `tests/test_cross_source_sanctions.py::TestCrossSourceSanctionsAndDivergence::test_ceis_cnep_connector_validates_masks_cpf_and_quarantines_invalid`
2. `tests/test_cross_source_sanctions.py::TestCrossSourceSanctionsAndDivergence::test_cross_source_ceis_rule_detects_active_cnpj_sanction_with_dual_sha256`
3. `tests/test_cross_source_sanctions.py::TestCrossSourceSanctionsAndDivergence::test_cross_source_ceis_rule_ignores_expired_sanction_or_masked_cpf_homonym`
4. `tests/test_cross_source_sanctions.py::TestCrossSourceSanctionsAndDivergence::test_amendment_execution_divergence_rule_flags_discrepancy`
5. `tests/test_cross_source_sanctions.py::TestCrossSourceSanctionsAndDivergence::test_lakehouse_and_api_sanctions_endpoint_roundtrip`
