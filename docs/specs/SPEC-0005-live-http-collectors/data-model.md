# Data Model: SPEC-0005 — Coletores HTTP Resilientes

## Contratos Principais

### 1. `HTTPCollectorConfig`
- `timeout_seconds`: `int` (default: 30)
- `max_retries`: `int` (default: 3)
- `max_response_bytes`: `int` (default: 10_485_760 - 10MB)

### 2. `HTTPFetchManifest` (frozen=True)
- `url`: `str`
- `status_code`: `int`
- `sha256_hex`: `str`
- `byte_length`: `int`
- `fetched_at_utc`: `str`
- `attempts`: `int`

### 3. `ResilientGovernmentHTTPClient`
- Métodos de validação SSRF e fetch com streaming, SHA-256 e retry exponencial.

### 4. `LiveGovernmentIngestionService`
- Orquestrador de ingestão ao vivo conectando fontes oficiais ao `CivicLakehouseStorage`.
