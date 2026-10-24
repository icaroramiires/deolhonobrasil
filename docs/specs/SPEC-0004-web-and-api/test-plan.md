# Plano de Testes: SPEC-0004

## 1. Matriz de Testes de Contrato, Segurança e UI

| Método de Teste (`Test Anchor`) | Requisitos Cobertos | O que Verifica |
| :--- | :--- | :--- |
| `tests/test_harness.py::TestLoopEngineeringHarness::test_wireframe_passes_achromatic_ledger_structural_invariants` | `FR-010`, `NFR-006`, `AC-014` | Presença dos 3 selos epistêmicos, `tabular-nums`, `SHA-256` e ausência de termos proibidos no HTML. |
| `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_health_and_security_headers` | `FR-011`, `SEC-006`, `AC-017` | Status `200 OK` em `/api/v1/health` e presença de `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options` e `Referrer-Policy`. |
| `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_get_dossiers_enforces_rls_for_public_vs_admin` | `FR-011`, `SEC-004`, `SEC-006`, `AC-015` | `public_reader` vê `0` dossiês em `EM_TRIAGEM_INTERNA`; tentativa de usar `role=reviewer_admin` sem token válido retorna `403`; com token válido retorna a fila interna; após aprovação humana, `public_reader` vê o dossiê publicado. |
| `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_get_expenses_and_reconciliation_decimal_totals` | `FR-011`, `DATA-006`, `AC-015` | `/api/v1/expenses` e `/api/v1/reconciliation` retornam somas exatas em `Decimal` reconciliadas com o Lakehouse. |
| `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_post_right_of_reply_creates_protocol_and_masks_cpf` | `FR-011`, `SEC-001`, `SEC-007`, `AC-016` | `POST /api/v1/right-of-reply` retorna `201 Created`, mascara CPF para `***.456.789-**` e define `equal_visual_prominence=True`. |
| `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_post_right_of_reply_blocks_accusatory_and_sanitizes_injection` | `SEC-002`, `SEC-003`, `SEC-007`, `AC-016` | Rejeita termos acusatórios com `422 Unprocessable Entity` e neutraliza payloads de *prompt injection* (`IGNORE ALL PREVIOUS INSTRUCTIONS`). |
| `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_rate_limiter_blocks_excessive_requests_with_429` | `SEC-006`, `AC-017` | `SlidingWindowRateLimiter` bloqueia rajadas acima do limite com `429 Too Many Requests` e header `Retry-After`. |
| `tests/test_api_and_ops.py::TestDevSecOpsAndCICDArtifacts::test_dockerfile_compose_and_github_ci_exist_and_run_harness` | `NFR-007`, `AC-017` | Existência e validade estrutural de `Dockerfile`, `docker-compose.yml` e `.github/workflows/ci.yml`. |
