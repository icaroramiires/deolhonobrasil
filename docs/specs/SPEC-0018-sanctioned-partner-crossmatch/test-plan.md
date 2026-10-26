# Test Plan — SPEC-0018

## Mapping Requirements to Test Anchors
- `FR-038`, `FR-039`, `AC-070` -> `tests/test_sanctioned_partner_crossmatch.py::TestSanctionedPartnerCrossmatchRules::test_sanctioned_partner_rule_detects_active_sanction_in_qsa`
- `FR-038`, `FR-039`, `NFR-021`, `AC-071` -> `tests/test_sanctioned_partner_crossmatch.py::TestSanctionedPartnerCrossmatchRules::test_sanctioned_partner_rule_ignores_expired_sanction`
- `SEC-021`, `AC-072` -> `tests/test_sanctioned_partner_crossmatch.py::TestSanctionedPartnerCrossmatchRules::test_sanctioned_partner_rule_ignores_masked_cpf_homonym_without_name_match`
- `AC-073` -> `tests/test_sanctioned_partner_crossmatch.py::TestSanctionedPartnerCrossmatchRules::test_sanctioned_partner_rule_ignores_unrelated_suppliers`
