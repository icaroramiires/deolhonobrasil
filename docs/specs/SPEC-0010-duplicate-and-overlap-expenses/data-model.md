# Data Model Contracts — SPEC-0010

## 1. Duplicate Document Signal Contract
```json
{
  "rule_code": "R-DUPLICATE-EXPENSE-DOCUMENT",
  "classification": "CROSS_SOURCE_DIVERGENCE",
  "supplier_doc_normalized": "12345678000199",
  "document_number": "000123",
  "provenance_hashes": ["hash1...", "hash2..."],
  "score": 0.85
}
```

## 2. Temporal Geographic Overlap Signal Contract
```json
{
  "rule_code": "R-TEMPORAL-GEOGRAPHIC-OVERLAP",
  "classification": "STATISTICAL_ANOMALY",
  "public_agent_id": "agent-uuid-001",
  "issue_date": "2026-05-10",
  "states": ["SP", "RJ"],
  "provenance_hashes": ["hash3...", "hash4..."],
  "score": 0.80
}
```
