## EVAL DEFINITION: checkpoint-2-audit-governance

**Status:** Active (Implemented & Passing)
**Spec Reference:** `openspec/specs/02-audit-and-laya/spec.md`, `openspec/specs/03-editorial-governance/spec.md`

### Capability Evals
- [ ] **CAP-CP2-01 (Statistical Anomaly Engine):** Compute parametric `Z-Score`, non-parametric `MAD Z-Score`, `HHI` concentration index (`0..10000`), and `Benford` first-digit distribution in `Decimal`.
- [ ] **CAP-CP2-02 (Deterministic Audit Rules):** Trigger `R-PNCP-OVERPRICE-Z3`, `R-CGU-HHI-CONCENTRATION`, and `R-CEAP-OUTLIER-Z3` with 3-layer epistemic summaries and provenance hashes.
- [ ] **CAP-CP2-03 (Laya System 1 Triage Adapter):** Route signals with `score >= 0.70` or `requires_human_review == True` strictly to `TriageAction.REVISAO_HUMANA` (`PRIORIDADE_ALTA_AUDITORIA`).
- [ ] **CAP-CP2-04 (Grounded RAG Narrator):** Generate 3-block epistemic narrative (`[DADO OFICIAL]`, `[INFERÊNCIA ESTATÍSTICA]`, `[HIPÓTESE DE AUDITORIA / LIMITAÇÃO]`) citing `SHA-256` hashes and rejecting empty provenance.
- [ ] **CAP-CP2-05 (Hybrid Publication Governance & RLS):** Hide `EM_TRIAGEM_INTERNA` dossiers from `PUBLIC_READER` while exposing them to `REVIEWER_ADMIN`; enforce PostgreSQL RLS policies (`rls_policies.sql`).
- [ ] **CAP-CP2-06 (Right of Reply & Immutable Editorial Audit Trail):** Attach `RightOfReplySubmission` with `equal_visual_prominence == True`, transition status to `ESCLARECIDO_COM_PROVA` or `ERRO_MATERIAL_RETIFICADO`, and block `UPDATE`/`DELETE` on `editorial_audit_trail`.

### Regression Evals
- [ ] **REG-CP2-01:** Zero Checkpoint 1 tests regress (`test_pipeline_e2e.py` remains 100% green).
- [ ] **REG-CP2-02:** `unreviewed_visible_to_public_reader == 0` in `cli.py run-audit --verify-reconciliation`.

### Success Metrics
- `pass@1 == 100%` and `pass^3 == 100%` via `PYTHONPATH=src python3 -m deolhonobrasil.harness.runner --checkpoint 2`.
