# Data Model: SPEC-0001 — Pipeline de Dados Públicos

## Contratos Principais

### 1. `ProvenanceMetadata`
- `raw_payload`: `str`
- `sha256_hash`: `str`
- `source_name`: `str`
- `ingested_at`: `datetime`

### 2. `CuratedPublicExpense`
- `id`: `str`
- `deputy_or_senator_name`: `str`
- `document_value`: `Optional[Decimal]` (nunca convertido em zero se nulo)
- `supplier_cnpj_cpf`: `str` (com LGPD mascarada se aplicável)
- `provenance_hash`: `str`

### 3. `CuratedPublicContract`
- `contract_id`: `str`
- `supplier_cnpj`: `str`
- `contract_value`: `Optional[Decimal]`
- `provenance_hash`: `str`

### 4. `CuratedParliamentaryAmendment`
- `amendment_id`: `str`
- `amount`: `Optional[Decimal]`
- `provenance_hash`: `str`

### 5. `QuarantinedRecord`
- `record_id`: `str`
- `source_name`: `str`
- `error_reason`: `str`
- `raw_payload`: `str`
- `provenance_hash`: `str`

### 6. `BatchReconciliationReport`
- `batch_id`: `str`
- `total_records_read`: `int`
- `total_records_curated`: `int`
- `total_records_quarantined`: `int`
- `sum_curated_values`: `Decimal`
- `sum_source_values`: `Decimal`
- `is_balanced`: `bool`
