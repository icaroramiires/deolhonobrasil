# Plano de Testes — SPEC-0009

## Mapeamento de Requisitos para Test Anchors
- `FR-020`, `NFR-012`, `AC-034`:
  - `tests/test_shared_cnpj_root_and_monopoly.py::TestSharedCnpjRootAndMonopolyRules::test_extract_cnpj_root_validates_14_digits_and_rejects_cpf`
- `FR-020`, `DATA-011`, `AC-035`:
  - `tests/test_shared_cnpj_root_and_monopoly.py::TestSharedCnpjRootAndMonopolyRules::test_shared_cnpj_root_rule_detects_multiple_branches_for_same_organ`
- `FR-020`, `AC-036`:
  - `tests/test_shared_cnpj_root_and_monopoly.py::TestSharedCnpjRootAndMonopolyRules::test_shared_cnpj_root_rule_ignores_single_branch_or_unrelated_cnpjs`
- `FR-021`, `SEC-012`, `AC-036`:
  - `tests/test_shared_cnpj_root_and_monopoly.py::TestSharedCnpjRootAndMonopolyRules::test_monopolistic_supplier_category_rule_detects_dominance`
