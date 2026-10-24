## EVAL DEFINITION: checkpoint-3-api-and-interface

**Status:** VERIFIED (`pass@1 = 1.0`, `pass^3 = 1.0`)
**Spec Reference:** `docs/specs/SPEC-0004-web-and-api/spec.md`

### Capability Evals
- [x] **CAP-CP3-01 (`achromatic-ledger` Design Lint & Headless QA):** `wireframe_de_olho_no_brasil.html` passes `lint.mjs --app` (`0 FAIL, 0 WARN`) and `inspect.mjs --app` (`0 FAIL, 0 WARN` across `1440px`, `768px`, `390px`).
- [x] **CAP-CP3-02 (Public REST API / Hexagonal Service):** Serves `/api/v1/health`, `/api/v1/dossiers`, `/api/v1/expenses`, `/api/v1/reconciliation`, and `POST /api/v1/right-of-reply` backed by `CivicLakehouseStorage`.
- [x] **CAP-CP3-03 (Interactive Browser QA via `agent-browser`):** Verified filter interactions, 3-layer epistemic tabs, `SHA-256` drawer, and Right of Reply side-by-side comparison.

### Regression Evals
- [x] **REG-CP3-01:** All Checkpoint 1 & Checkpoint 2 tests and reconciliation gates remain 100% green (`50/50` tests).
- [x] **REG-CP3-02:** Zero `console.error` or failed `console.assert` in headless browser verification.

### Success Metrics
- `pass@1 == 100%` for capability evals and `pass^3 == 100%` for regression evals.
