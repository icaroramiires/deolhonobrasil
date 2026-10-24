# Modelo de Dados: SPEC-0003

## Entidades e Tabelas

### 1. `audit_dossiers`
- `id` (VARCHAR, PK)
- `title` (TEXT)
- `content` (TEXT)
- `status` (VARCHAR) — `EM_TRIAGEM_INTERNA`, `PENDING_REVIEW`, `PUBLISHED`, `RECTIFIED`
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### 2. `right_of_reply_protocols`
- `id` (VARCHAR, PK)
- `dossier_id` (VARCHAR, FK -> audit_dossiers.id)
- `responder_name` (TEXT)
- `reply_text` (TEXT)
- `equal_visual_prominence` (BOOLEAN DEFAULT TRUE)
- `status` (VARCHAR)

### 3. `editorial_audit_trail` (Append-Only)
- `event_id` (VARCHAR, PK)
- `target_type` (VARCHAR)
- `target_id` (VARCHAR)
- `action` (VARCHAR)
- `payload_hash` (VARCHAR)
- `actor` (VARCHAR)
- `timestamp` (TIMESTAMP)
