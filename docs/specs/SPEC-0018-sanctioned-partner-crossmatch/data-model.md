# Data Model & Schemas — SPEC-0018

## Models
- `CuratedCorporateMemberRecord`: Represents a member/administrator in the QSA table (CNPJ, masked CPF `***.XXX.XXX-**`, sanitized name, role).
- `CuratedSanctionRecord`: Represents an active administrative sanction in CEIS/CNEP (sanctioned entity/person CPF/CNPJ, name, start_date, end_date, provenance_hash).
- `AuditSignal`: Emitted signal carrying `R-CROSS-SANCTIONED-PARTNER`, `provenance_hashes` (triple SHA-256), severity, and epistemic classification `CROSS_SOURCE_DIVERGENCE`.
