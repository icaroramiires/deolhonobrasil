# Tasks: SPEC-0005 — Coletores HTTP Resilientes e Ingestão ao Vivo

## Tarefas Verificáveis

- **TASK-0501 (Vinculada a DONB-12):** Implementar `HTTPCollectorConfig`, `HTTPFetchManifest` e `ResilientGovernmentHTTPClient` com proteção estrita contra SSRF (`.gov.br` / `.leg.br`), streaming de bytes com hash `SHA-256`, controle de tamanho máximo de resposta e retentativa exponencial.
- **TASK-0502 (Vinculada a DONB-12):** Desenvolver o `LiveGovernmentIngestionService` para persistência no `CivicLakehouseStorage` e emissão de relatórios de reconciliação.
- **TASK-0503 (Vinculada a DONB-12):** Adicionar o subcomando CLI `fetch-live` em `src/deolhonobrasil/cli.py` e criar a suíte de testes unitários e de integração em `tests/test_http_collectors.py`.
