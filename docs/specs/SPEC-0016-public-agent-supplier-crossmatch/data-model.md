# Data Model & API Contracts — SPEC-0016

## `CuratedPublicAgentRecord`
- `agent_id`: `str` (Natural key hash)
- `name`: `str` (Sanitized full name)
- `cpf_masked`: `str` (Must match format `***.XXX.XXX-**`)
- `organ_code`: `str` (Administrative organ identifier)
- `organ_name`: `str` (Organ display name)
- `position`: `str` (Job title or function)
- `provenance_hash`: `str` (SHA-256 of raw source payload)

## `AuditSignal` (Cross-Match Output)
- `signal_type`: `CROSS_SOURCE_DIVERGENCE`
- `rule_id`: `R-CROSS-PUBLIC-AGENT-SUPPLIER`
- `provenance_hashes`: `List[str]` (Combining agent record, QSA entry, and contract/expense records)
- `confidence_score`: `float`
- `metadata`: Dict containing agent details, company CNPJ, organ code, and non-accusatory explanatory disclaimer.
