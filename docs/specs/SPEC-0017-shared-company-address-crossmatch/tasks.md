# Tasks Breakdown — SPEC-0017 (Jira: DONB-24)

- [ ] **TASK-1701**: Implementar `CuratedCompanyRegistrationRecord` e normalização determinística de endereços e CEPs (`FR-036`, `NFR-020`, `DATA-019`).
- [ ] **TASK-1702**: Desenvolver função `compute_normalized_address_key` com hash SHA-256 e testes associados (`AC-066`).
- [ ] **TASK-1703**: Implementar regra de auditoria `evaluate_shared_company_address_rule` (`R-CORP-SHARED-ADDRESS`) para detecção de múltiplos fornecedores no mesmo endereço contratados pelo mesmo órgão (`FR-037`, `AC-067`).
- [ ] **TASK-1704**: Implementar exclusões e tratamento para unidades autônomas, condomínios e órgãos distintos, validando todos os test anchors (`AC-068`, `AC-069`, `SEC-020`).
