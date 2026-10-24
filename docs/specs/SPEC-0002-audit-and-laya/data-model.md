# Data Model: SPEC-0002 — Auditoria e Motor Laya

## Contratos Principais

### 1. `AuditSignal`
- `signal_id`: `str`
- `rule_code`: `str`
- `severity`: `str`
- `description`: `str` (livre de termos acusatórios)
- `provenance_hashes`: `List[str]`

### 2. `TriageAction`
- `action_type`: `str` (`REVISAO_HUMANA`, `AUTO_DISMISS`, etc.)
- `confidence_score`: `float`
- `rationale`: `str`

### 3. `System1Decision`
- `decision_id`: `str`
- `score`: `float`
- `recommended_action`: `TriageAction`
- `requires_human_review`: `bool`

### 4. `GroundedDossierSection`
- `official_data_block`: `str`
- `statistical_inference_block`: `str`
- `audit_hypothesis_block`: `str`
- `provenance_hashes`: `List[str]`
