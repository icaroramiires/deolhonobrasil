# SPEC-0005 — Coletores HTTP Resilientes de Fontes Oficiais, Proteção SSRF e Manifesto SHA-256 em Streaming

## 1. Identificador e Título
- **ID:** SPEC-0005
- **Título:** Coletores HTTP Resilientes de Fontes Oficiais, Proteção SSRF e Manifesto SHA-256 em Streaming
- **Subsistema:** Core HTTP Pipeline & Lakehouse Ingestion

## 2. Status e Versão
- **Status:** Verificado
- **Versão:** 1.0.0
- **Data:** 2026-10-24

## 3. Problema e Motivação
As APIs públicas dos portais governamentais brasileiros (Câmara dos Deputados, Senado Federal, CGU e PNCP) frequentemente sofrem de instabilidade transiente (erros HTTP 502/503/504, limitação de taxa 429), timeouts e potenciais vulnerabilidades de requisição acidental ou maliciosa via Server-Side Request Forgery (SSRF). O sistema **De Olho no Brasil** exige um cliente HTTP altamente resiliente (`ResilientGovernmentHTTPClient`) e um serviço de ingestão ao vivo (`LiveGovernmentIngestionService`) que apliquem validação estrita de domínios oficiais (`.gov.br` / `.leg.br`), limite de bytes em streaming para evitar esgotamento de memória, política de retentativas exponenciais com backoff e geração imutável de manifestos de proveniência (`SHA-256`).

## 4. Objetivos e Não-Objetivos
### Objetivos
- Implementar proteção robusta contra SSRF exigindo HTTPS e allowlist estrita de domínios `.gov.br` e `.leg.br`.
- Assegurar recuperação automática de erros transientes (HTTP 429, 502, 503, 504) via backoff exponencial determinístico.
- Controlar o consumo de memória através de limite máximo de bytes de resposta em streaming (`max_response_bytes`).
- Gerar e persistir manifestos de proveniência imutáveis (`HTTPFetchManifest`) com hash `SHA-256` imediato dos bytes recebidos.
- Integrar os coletores ao `CivicLakehouseStorage` e à interface CLI (`fetch-live`).

### Não-Objetivos
- Web scraping de portais legados sem API estruturada JSON/CSV (tratado em especificações futuras).
- Processamento assíncrono distribuído em larga escala via Celery/Redis (mantido no orquestrador síncrono/transacional do lakehouse).

## 5. Atores e Permissões
- **Orquestrador de Ingestão HTTP:** Executa coletas agendadas ou sob demanda via CLI.
- **Auditor / Administrador:** Verifica integridade dos manifestos e executa relatórios de reconciliação de lote.

## 6. Fluxos Principais
1. **Validação de URL (SSRF Guard):** O cliente valida se o URL possui esquema `https://` e se o host termina estritamente em `.gov.br` ou `.leg.br`.
2. **Execução com Retentativa:** Requisição HTTP executada com timeouts configuráveis e retentativas exponenciais para códigos HTTP transientes.
3. **Streaming e Hash SHA-256:** Leitura da resposta em blocos para calcular o hash SHA-256 e assegurar que o limite de bytes não seja excedido.
4. **Persistência no Lakehouse:** Armazenamento do payload bruto na camada `Raw` acompanhado do `HTTPFetchManifest` imutável.

## 7. Cenários Alternativos e de Erro
- **Domínio Não Autorizado / Esquema Inseguro:** O `ResilientGovernmentHTTPClient` rejeita imediatamente a requisição lançando exceção de segurança SSRF.
- **Erros Transientes (502/503/504/429):** O mecanismo de retry aplica backoff exponencial até o número máximo de tentativas antes de despachar para a quarentena.
- **Excedência de Limite de Bytes (`max_response_bytes`):** Interrupção imediata do streaming e rejeição do payload para evitar exaustão de memória.

## 8. Requisitos Funcionais
- **FR-012:** O cliente `ResilientGovernmentHTTPClient` deve coletar lotes das APIs oficiais (Câmara CEAP, Senado CEAPS, CGU e PNCP) calculando `SHA-256` imediato dos bytes recebidos.
- **FR-013:** O orquestrador `LiveGovernmentIngestionService` e o comando CLI `fetch-live` devem integrar a coleta HTTP diretamente ao `CivicLakehouseStorage`.

## 9. Requisitos Não Funcionais
- **NFR-008:** Retry exponencial determinístico para erros transitórios (`HTTP 429`, `502`, `503`, `504`) e limite máximo configurável de tamanho de resposta (`max_response_bytes`).

## 10. Regras de Negócio e Dados
- **DATA-007:** Todo payload coletado via HTTP gera `HTTPFetchManifest` imutável (`frozen=True`) com `url`, `status_code`, `sha256_hex`, `byte_length`, `fetched_at_utc` e `attempts`.

## 11. Requisitos de Segurança e Privacidade
- **SEC-008:** Proteção estrita contra SSRF (Server-Side Request Forgery): exigir esquema `https://` e permitir exclusivamente hosts terminados em `.gov.br` ou `.leg.br` na allowlist oficial.

## 12. Critérios de Aceite
- **AC-018:** O bloqueio SSRF recusa URLs com http://, localhost ou domínios externos não oficiais.
- **AC-019:** O limite de bytes impede o carregamento de payloads gigantescos em memória.
- **AC-020:** O retry exponencial recupera com sucesso após falhas transientes HTTP 503.
- **AC-021:** O `LiveGovernmentIngestionService` persiste com sucesso e reconcilia lotes coletados ao vivo via CLI.

## 13. Dependências
- `SPEC-0001` (Pipeline de Dados Públicos e Lakehouse Storage).

## 14. Riscos e Limitações
- Instabilidade prolongada das APIs federais (mitigada por cache local e quarentena de falhas).

## 15. Estratégia de Testes e Test Anchors
### Test Anchors
- `tests/test_http_collectors.py::TestResilientGovernmentHTTPCollectors::test_ssrf_guard_blocks_non_https_and_untrusted_hosts`
- `tests/test_http_collectors.py::TestResilientGovernmentHTTPCollectors::test_payload_size_limit_prevents_memory_exhaustion`
- `tests/test_http_collectors.py::TestResilientGovernmentHTTPCollectors::test_exponential_retry_recovers_from_transient_503`
- `tests/test_http_collectors.py::TestResilientGovernmentHTTPCollectors::test_live_ingestion_service_persists_and_reconciles_batches`
- `tests/test_http_collectors.py::TestResilientGovernmentHTTPCollectors::test_cli_fetch_live_subcommand_executes_cleanly`

## 16. Questões Pendentes
Nenhuma.
