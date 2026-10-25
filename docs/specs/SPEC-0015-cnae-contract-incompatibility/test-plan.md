# Test Plan — SPEC-0015

## 1. Mapeamento de Requisitos para Test Anchors
- **`FR-032`, `DATA-017`, `AC-058`** $\rightarrow$ `tests/test_cnae_contract_incompatibility.py::TestCnaeContractIncompatibilityRules::test_cnae_model_validation_and_code_normalization`
- **`FR-033`, `AC-059`** $\rightarrow$ `tests/test_cnae_contract_incompatibility.py::TestCnaeContractIncompatibilityRules::test_cnae_incompatibility_rule_detects_mismatch`
- **`FR-033`, `AC-060`** $\rightarrow$ `tests/test_cnae_contract_incompatibility.py::TestCnaeContractIncompatibilityRules::test_cnae_incompatibility_rule_respects_secondary_cnaes`
- **`FR-033`, `NFR-018`, `AC-061`** $\rightarrow$ `tests/test_cnae_contract_incompatibility.py::TestCnaeContractIncompatibilityRules::test_cnae_rule_ignores_compatible_or_low_value_contracts`

---

## 2. Critérios de Execução
Todos os testes devem ser executados através do harness padrão do projeto com cobertura mínima superior a 80%.
