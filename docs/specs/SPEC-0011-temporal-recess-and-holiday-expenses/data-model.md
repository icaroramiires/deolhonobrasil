# Data Model — SPEC-0011

## 1. Estruturas de Dados
- **TemporalAuditSignal:**
  - `rule_id`: string (`R-TEMPORAL-WEEKEND-HOLIDAY` ou `R-TEMPORAL-PARLIAMENTARY-RECESS`)
  - `severity`: string (`STATISTICAL_ANOMALY`)
  - `provenance_hashes`: list of str (SHA-256 hashes)
  - `metadata`: dict contendo contagens, valores totais e datas de ocorrência.
