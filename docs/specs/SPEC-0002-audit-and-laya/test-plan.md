# Test Plan: SPEC-0002 — Auditoria e Motor Laya

## Mapeamento de Requisitos para Testes
Todos os requisitos do SPEC-0002 são validados pelos 14 métodos de teste presentes em `tests/test_audit_and_governance.py`.

### Test Anchors Executados
1. `tests/test_audit_and_governance.py::TestAuditStatistics::test_parametric_z_score_calculation`
2. `tests/test_audit_and_governance.py::TestAuditStatistics::test_mad_z_score_calculation`
3. `tests/test_audit_and_governance.py::TestAuditStatistics::test_hhi_concentration`
4. `tests/test_audit_and_governance.py::TestAuditStatistics::test_benford_first_digit_evaluation`
5. `tests/test_audit_and_governance.py::TestDeterministicAuditRules::test_audit_signal_non_accusatory_enforcement`
6. `tests/test_audit_and_governance.py::TestDeterministicAuditRules::test_contract_overpricing_rule`
7. `tests/test_audit_and_governance.py::TestDeterministicAuditRules::test_supplier_concentration_rule`
8. `tests/test_audit_and_governance.py::TestDeterministicAuditRules::test_ceap_quota_outlier_rule`
9. `tests/test_audit_and_governance.py::TestLayaSystem1Engine::test_adapter_satisfies_protocol`
10. `tests/test_audit_and_governance.py::TestLayaSystem1Engine::test_high_severity_routes_to_human_review`
11. `tests/test_audit_and_governance.py::TestLayaSystem1Engine::test_system1_never_auto_publishes_nominal_accusation`
12. `tests/test_audit_and_governance.py::TestLayaSystem1Engine::test_official_reply_discount`
13. `tests/test_audit_and_governance.py::TestGroundedRAGNarrator::test_narrator_generates_three_epistemic_blocks`
14. `tests/test_audit_and_governance.py::TestGroundedRAGNarrator::test_narrator_refuses_empty_provenance`
