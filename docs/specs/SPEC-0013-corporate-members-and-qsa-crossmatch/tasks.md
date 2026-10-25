# Task Breakdown — SPEC-0013 (Jira: DONB-20)

- **`TASK-1301`**: Implement `CuratedCorporateMemberRecord` model with `frozen=True`, CPF masking, and SHA-256 provenance calculation.
- **`TASK-1302`**: Implement `evaluate_qsa_shared_partner_rule` (`R-CROSS-QSA-SHARED-PARTNER`) for detecting shared partners/administrators across contractors in the same organ.
- **`TASK-1303`**: Implement `evaluate_qsa_individual_donor_rule` (`R-CROSS-QSA-DONOR-SUPPLIER`) for correlating QSA partners with TSE personal electoral donations to mandataries.
- **`TASK-1304`**: Write comprehensive unit tests (`tests/test_qsa_and_corporate_members.py`) covering all 4 test anchors and verify with pytest.
