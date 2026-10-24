# Plan: SPEC-0005 — Coletores HTTP Resilientes e Ingestão ao Vivo

## 1. Arquitetura de Implementação
- **`src/deolhonobrasil/pipeline/http_client.py`**: Contém `HTTPCollectorConfig`, `HTTPFetchManifest`, e `ResilientGovernmentHTTPClient` com validação SSRF, streaming por blocos, cálculo de SHA-256 e retentativa exponencial.
- **`src/deolhonobrasil/pipeline/live_service.py`**: Contém `LiveGovernmentIngestionService` integrando o cliente HTTP ao `CivicLakehouseStorage`.
- **`src/deolhonobrasil/cli.py`**: Adiciona o subcomando CLI `fetch-live` para execução direta de coleta e reconciliação.

## 2. Estratégia de Testes
- Implementação de suíte dedicada em `tests/test_http_collectors.py` cobrindo todos os 5 Test Anchors especificados.
