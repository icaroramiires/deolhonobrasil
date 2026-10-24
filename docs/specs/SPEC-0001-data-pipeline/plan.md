# Plan: SPEC-0001 — Pipeline de Dados Públicos e Lakehouse

## 1. Arquitetura do Lakehouse (`Raw -> Quarantine -> Curated`)
- **Raw:** Armazenamento imutável dos payloads originais coletados das fontes com hash `SHA-256`.
- **Quarantine:** Destino para registros com falhas de validação estrutural ou chaves inválidas.
- **Curated:** Dados limpos, mascarados (LGPD), validados e prontos para consumo analítico e de auditoria.

## 2. Estratégia de Migração e Rollback
- Scripts idempotentes baseados em Pydantic e SQLite/DuckDB.
- Rollback garantido por transações atômicas e imutabilidade dos dados brutos em `Raw`.

## 3. Observabilidade
- Emissão de logs estruturados e `BatchReconciliationReport` por execução de ETL.
