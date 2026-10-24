## EVAL DEFINITION: checkpoint-1-foundation-etl

**Status:** Active (Implemented & Passing)
**Spec Reference:** `openspec/specs/01-data-pipeline/spec.md`

### Capability Evals
- [ ] **CAP-CP1-01 (4 Federal Connectors):** Ingest and normalize sample records from CGU, PNCP, CEAP, and CEAPS into `CuratedPublicExpense` and `CuratedPublicContract`.
- [ ] **CAP-CP1-02 (Cryptographic Provenance):** Compute and verify deterministic 64-char `SHA-256` hashes over canonical raw payloads (`ProvenanceMetadata`).
- [ ] **CAP-CP1-03 (LGPD CPF Masking):** Mask all 11-digit CPFs in document fields and free-text descriptions to `***.XXX.XXX-**` while preserving 14-digit CNPJs.
- [ ] **CAP-CP1-04 (Prompt Injection Sanitization):** Strip indirect prompt injection directives (`Ignore previous instructions`, `<script>`, `system:`) from untrusted public text fields.
- [ ] **CAP-CP1-05 (Cent-by-Cent Financial Reconciliation):** Verify `ReconciliationReport.reconciled == True` with `Decimal("0.00")` discrepancy across all 4 sources and persist in `CivicLakehouseStorage`.

### Regression Evals
- [ ] **REG-CP1-01:** `test_reconciliation_fails_on_one_cent_discrepancy` catches a `R$ 0,01` divergence.
- [ ] **REG-CP1-02:** `test_non_accusatory_language_guardrail` blocks forbidden terms (`"fraude comprovada"`, `"corrupção"`, `"roubo"`).

### Success Metrics
- `pass@1 == 100%` and `pass^3 == 100%` via `PYTHONPATH=src python3 -m deolhonobrasil.harness.runner --checkpoint 1`.
