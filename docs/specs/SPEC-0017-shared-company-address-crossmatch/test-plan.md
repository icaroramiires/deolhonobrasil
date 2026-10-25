# Test Plan — SPEC-0017

## 1. Mapeamento de Requisitos para Test Anchors
- **`FR-036`, `NFR-020`, `DATA-019`, `AC-066`** $\rightarrow$ `tests/test_shared_company_address.py::TestSharedCompanyAddressRules::test_company_address_model_validation_and_normalization`
- **`FR-037`, `AC-067`** $\rightarrow$ `tests/test_shared_company_address.py::TestSharedCompanyAddressRules::test_shared_address_rule_detects_multiple_suppliers_at_same_address`
- **`AC-068`, `SEC-020`** $\rightarrow$ `tests/test_shared_company_address.py::TestSharedCompanyAddressRules::test_shared_address_rule_ignores_different_address_or_autonomous_units`
- **`AC-069`** $\rightarrow$ `tests/test_shared_company_address.py::TestSharedCompanyAddressRules::test_shared_address_rule_ignores_different_organs`

## 2. Critérios de Execução
Todos os testes devem ser executados via pytest com cobertura mínima de 80% e validação de conformidade com os princípios éticos e não-acusatórios.
