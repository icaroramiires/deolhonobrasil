# Test Plan: SPEC-0020

## Test Mapping
- `FR-043`, `AC-078`, `DATA-022`: `tests/test_civic_entity_profiles_and_details.py::TestCivicEntityProfilesAndDetails::test_entity_profiles_render_supplier_agent_and_organ_data`
- `FR-044`, `AC-079`, `SEC-023`: `tests/test_civic_entity_profiles_and_details.py::TestCivicEntityProfilesAndDetails::test_expense_detail_modal_shows_accounting_stages_and_hash`
- `FR-044`, `AC-080`: `tests/test_civic_entity_profiles_and_details.py::TestCivicEntityProfilesAndDetails::test_contract_detail_modal_renders_amendments_timeline`
- `FR-045`, `AC-081`: `tests/test_civic_entity_profiles_and_details.py::TestCivicEntityProfilesAndDetails::test_analysis_detail_enforces_epistemic_layers_and_a11y`
- `NFR-023`: Validated via execution benchmark in unit tests ensuring sub-50ms response times.
