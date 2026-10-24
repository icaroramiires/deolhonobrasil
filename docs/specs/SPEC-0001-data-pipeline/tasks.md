# Tasks: SPEC-0001 — Pipeline de Dados Públicos

## Tarefas Verificáveis

- **TASK-0101 (Vinculada a DONB-1):** Implementar o módulo de fundação com cálculo SHA-256, mascaramento LGPD de CPF (`***.XXX.XXX-**`), sanitização de prompt injection e validação de CNPJ/CPF.
- **TASK-0102 (Vinculada a DONB-1):** Desenvolver conectores robustos para Câmara (CEAP), Senado (CEAPS), CGU (Emendas) e PNCP (Contratos).
- **TASK-0103 (Vinculada a DONB-5):** Implementar o armazenamento em Lakehouse (`Raw`, `Quarantine`, `Curated`) com isolamento de registros inválidos e tratamento estrito de valores nulos (`Decimal`).
- **TASK-0104 (Vinculada a DONB-5):** Implementar o relatório de reconciliação de lote (`BatchReconciliationReport`) e testes de integração end-to-end via CLI.
