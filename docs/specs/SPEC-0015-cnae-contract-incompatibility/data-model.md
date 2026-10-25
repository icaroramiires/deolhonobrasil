# Data Model — SPEC-0015

## 1. Entidades de Dados

### `CuratedCompanyRegistrationRecord`
- `cnpj`: `str` (formato validado)
- `legal_name`: `str`
- `main_cnae_code`: `str` (regex `^\d{7}$`)
- `secondary_cnae_codes`: `tuple[str, ...]` (cada elemento regex `^\d{7}$`)
- `raw_payload_hash`: `str` (SHA-256)
- `source`: `OfficialSource.RECEITA_FEDERAL_CNPJ`

### `CuratedPublicContract`
- `contract_id`: `str`
- `supplier_cnpj`: `str`
- `value`: `float`
- `object_description`: `str`
- `required_cnae_division`: `str` (divisão de 2 dígitos ou mapeada do objeto)

### `AuditSignal`
- `rule_code`: `"R-CORP-CNAE-INCOMPATIBLE"`
- `severity`: `AuditSeverity`
- `status`: `AuditStatus.EM_TRIAGEM_INTERNA`
- `evidence`: `dict`
