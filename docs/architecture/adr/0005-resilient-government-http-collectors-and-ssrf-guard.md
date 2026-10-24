# ADR-0005: Coletores HTTP Resilientes de Fontes Governamentais, Proteção SSRF (Allowlist `.gov.br`/`.leg.br`) e Transporte Injetável

- **Status:** Aceito
- **Data:** 2026-10-23
- **Decisores:** Arquitetura De Olho no Brasil (`SPEC-0005`)
- **Requisitos Relacionados:** `FR-012`, `FR-013`, `NFR-008`, `DATA-007`, `SEC-008`

---

## Contexto e Problema

Para alimentar continuamente a camada Raw/Bronze do `CivicLakehouseStorage` a partir dos portais públicos federais (Câmara dos Deputados `dadosabertos.camara.leg.br`, Senado Federal `adm.senado.gov.br`, Portal da Transparência `api.portaldatransparencia.gov.br` e PNCP `pncp.gov.br`), o sistema precisa de um coletor HTTP que:
1. Previna ataques de *Server-Side Request Forgery* (SSRF) caso uma URL de fonte seja parametrizada incorretamente (`SEC-008`);
2. Impeça exaustão de memória (OOM) por respostas gigantescas ou corrompidas (`NFR-008`);
3. Tolere falhas transitórias (`HTTP 429`, `502`, `503`, `504`) comuns em portais governamentais via retry com backoff;
4. Permita testes determinísticos 100% offline na suíte `unittest` e no `runner.py` por meio de injeção de transporte (`TransportCallable`), usando `urllib.request` da biblioteca padrão em produção.

---

## Decisão

Implementamos o módulo [`src/deolhonobrasil/pipeline/http_client.py`](file:///Users/icaroramires/Projects/Python/deolhonobrasil/src/deolhonobrasil/pipeline/http_client.py) contendo:

1. **`HTTPCollectorConfig` e `HTTPFetchManifest` (`frozen=True`):**
   - Configuração imutável com `allowed_host_suffixes=(".gov.br", ".leg.br")`, `max_response_bytes=50 * 1024 * 1024` (50 MB), `max_retries=3` e `timeout_seconds=15.0`.
   - Manifesto imutável registrando `url`, `status_code`, `sha256_hex`, `byte_length`, `content_type`, `fetched_at_utc` e `attempts`.
2. **Guarda Anti-SSRF (`validate_official_government_url`):**
   - Exige esquema `https://`, bloqueia credenciais embutidas na URL, bloqueia IPs literais/localhost e exige que o hostname pertença estritamente aos sufixos `.gov.br` ou `.leg.br`.
3. **`ResilientGovernmentHTTPClient` e `LiveGovernmentIngestionService`:**
   - Suporta injeção de transporte para testes determinísticos de falhas `503`, limites de bytes e reconciliação completa no `CivicLakehouseStorage`.

---

## Consequências

- **Positivas:** Coleta segura contra SSRF e OOM, manifesto criptográfico `SHA-256` gerado no instante da leitura dos bytes na borda HTTP e 100% de testabilidade sem dependência de rede externa durante o CI.
- **Negativas / Trade-offs:** Qualquer nova fonte oficial fora de `.gov.br` ou `.leg.br` exigirá atualização explícita e auditada da allowlist.
