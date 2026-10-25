# Test Plan — SPEC-0013

## Mapped Requirements & Test Anchors
- `FR-028`, `DATA-015`, `AC-050` $\rightarrow$ `tests/test_qsa_and_corporate_members.py::TestCorporateMembersAndQSACrossmatch::test_corporate_member_model_validation_and_masking`
- `FR-029`, `AC-051` $\rightarrow$ `tests/test_qsa_and_corporate_members.py::TestCorporateMembersAndQSACrossmatch::test_qsa_shared_partner_rule_detects_common_partners_in_same_organ`
- `FR-029`, `AC-052` $\rightarrow$ `tests/test_qsa_and_corporate_members.py::TestCorporateMembersAndQSACrossmatch::test_qsa_individual_donor_rule_detects_partner_donation_to_mandatario`
- `AC-053` $\rightarrow$ `tests/test_qsa_and_corporate_members.py::TestCorporateMembersAndQSACrossmatch::test_qsa_rules_ignore_unrelated_companies_or_non_donors`

## Execution Command
```bash
PYTHONPATH=src pytest tests/test_qsa_and_corporate_members.py
```
