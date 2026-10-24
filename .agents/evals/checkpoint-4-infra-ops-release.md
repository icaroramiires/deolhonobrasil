## EVAL DEFINITION: checkpoint-4-infra-ops-release

**Status:** VERIFIED (`pass@1 = 1.0`, `pass^3 = 1.0`)
**Spec Reference:** `docs/specs/SPEC-0004-web-and-api/spec.md`

### Capability Evals
- [x] **CAP-CP4-01 (Container & CI/CD Reproducibility):** `Dockerfile`, `docker-compose.yml`, and `.github/workflows/ci.yml` execute the full Loop Engineering Harness in a clean non-root environment.
- [x] **CAP-CP4-02 (Security, Rate Limiting & Legal Operations):** Validated sliding-window rate-limiting (`HTTP 429`), security headers (`CSP`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`), timing-safe `hmac.compare_digest` admin check, and LGPD CPF masking on `POST /api/v1/right-of-reply`.
- [x] **CAP-CP4-03 (Santa Method Dual Adversarial Sign-Off):** Two independent reviewers (`donb-compliance-linter` + `security-reviewer`) audit the release.

### Regression Evals
- [x] **REG-CP4-01:** 100% of Checkpoints 1, 2, 3, and 4 test suites pass (`50/50` tests, `pass^3 == 100%`).

### Success Metrics
- `pass^3 == 100%` across all gates before production release.
