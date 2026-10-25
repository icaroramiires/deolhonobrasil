# Data Model Contracts — SPEC-0017

## 1. CuratedCompanyRegistrationRecord
- `cnpj`: str (14 dígitos)
- `corporate_name`: str
- `postal_code`: str (8 dígitos normalizados)
- `street`: str
- `number`: str
- `complement`: Optional[str]
- `provenance_sha256`: str

## 2. Address Key Normalization
- `compute_normalized_address_key(postal_code, street, number) -> str`: Retorna hash SHA-256 da string normalizada (sem pontuação, maiúsculas, abreviações padronizadas).

## 3. AuditSignal Structure
- `signal_id`: str
- `rule_code`: `"R-CORP-SHARED-ADDRESS"`
- `severity`: float
- `provenance_sources`: List[str]
- `metadata`: Dict[str, Any]
