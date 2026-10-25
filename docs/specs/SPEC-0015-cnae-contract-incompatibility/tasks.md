# Task Breakdown & Tracking — SPEC-0015

Vinculado ao épico Jira **`DONB-22`**.

- [x] **`TASK-1501`**: Implementar modelo Pydantic `CuratedCompanyRegistrationRecord` com validação de códigos CNAE de 7 dígitos e hash SHA-256 (`FR-032`, `DATA-017`, `AC-058`).
- [x] **`TASK-1502`**: Implementar regra determinística `evaluate_cnae_contract_incompatibility_rule` (`R-CORP-CNAE-INCOMPATIBLE`) considerando limiar de R$ 50.000,00 e checagem de CNAE principal e secundários (`FR-033`, `NFR-018`, `AC-059`, `AC-060`, `AC-061`).
- [x] **`TASK-1503`**: Assegurar conformidade estrita com linguagem não-acusatória e limitações contextuais (`SEC-018`).
- [x] **`TASK-1504`**: Escrever e validar os 4 testes âncora em `tests/test_cnae_contract_incompatibility.py`.
