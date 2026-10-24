# Test Plan: SPEC-0005 — Coletores HTTP Resilientes e Ingestão ao Vivo

## Mapeamento de Requisitos para Testes
Os requisitos `FR-012`, `FR-013`, `NFR-008`, `DATA-007`, `SEC-008` e os critérios de aceite `AC-018` a `AC-021` são validados integralmente pelos 5 Test Anchors em `tests/test_http_collectors.py`.

### Test Anchors Executados
1. `tests/test_http_collectors.py::TestResilientGovernmentHTTPCollectors::test_ssrf_guard_blocks_non_https_and_untrusted_hosts`
2. `tests/test_http_collectors.py::TestResilientGovernmentHTTPCollectors::test_payload_size_limit_prevents_memory_exhaustion`
3. `tests/test_http_collectors.py::TestResilientGovernmentHTTPCollectors::test_exponential_retry_recovers_from_transient_503`
4. `tests/test_http_collectors.py::TestResilientGovernmentHTTPCollectors::test_live_ingestion_service_persists_and_reconciles_batches`
5. `tests/test_http_collectors.py::TestResilientGovernmentHTTPCollectors::test_cli_fetch_live_subcommand_executes_cleanly`
