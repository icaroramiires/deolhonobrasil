# Test Plan: SPEC-0021

## 1. Visão Geral da Estratégia de Testes
Este plano de testes estabelece o mapeamento estrito entre os requisitos funcionais (`FR-046` a `FR-048`), não funcionais (`NFR-024`), regras de dados (`DATA-023`), segurança (`SEC-024`) e critérios de aceite (`AC-082` a `AC-085`) para a suíte de testes automatizados do `SPEC-0021`.

Arquivo de testes de destino: `tests/test_civic_watchlists_and_source_catalog.py`
Classe de testes: `TestCivicWatchlistsAndSourceCatalog`

---

## 2. Mapeamento de Requisitos e Test Anchors

### 2.1 Test Anchor 1: Modelos e Geração de Eventos
- **Método de Teste:**
  `tests/test_civic_watchlists_and_source_catalog.py::TestCivicWatchlistsAndSourceCatalog::test_watchlist_subscription_model_and_event_generation`
- **Requisitos Cobertos:** `FR-046`, `DATA-023`, `AC-082`
- **Verificações:**
  - Validação de imutabilidade (`frozen=True`) para `CivicWatchlistSubscription` e `CivicWatchlistEvent`.
  - Conformidade com os 5 tipos de entidades (`FORNECEDOR`, `MANDATARIO`, `ORGAO`, `CONTRATO`, `DOSSIE`).
  - Conformidade com os 5 tipos de eventos monitorados (`NOVO_DOCUMENTO`, `ALTERACAO_VALOR`, `NOVO_PAGAMENTO`, `NOVA_ANALISE`, `RESPOSTA_CONTESTACAO`).
  - Suporte às 3 frequências (`IMEDIATA`, `DIARIA`, `SEMANAL`) e 2 canais (`NAVEGADOR_LOCAL`, `WEBHOOK_CADASTRADO`).
  - Geração canônica de hash `SHA-256` para cada assinatura e verificação de payload de evento.

### 2.2 Test Anchor 2: Ciclo de Vida CRUD e Persistência no Lakehouse
- **Método de Teste:**
  `tests/test_civic_watchlists_and_source_catalog.py::TestCivicWatchlistsAndSourceCatalog::test_storage_watchlist_crud_lifecycle_and_events`
- **Requisitos Cobertos:** `FR-046`, `AC-083`, `NFR-024`
- **Verificações:**
  - Criação determinística das tabelas `lakehouse_watchlist_subscriptions` e `lakehouse_watchlist_events` em SQLite.
  - Ciclo de vida completo: inserção de assinatura, consulta por ID, listagem de ativas, pausa/reativação (`is_active`) e deleção com integridade referencial.
  - Inserção e recuperação de eventos associados à subscrição com ordenação temporal e controle de leitura (`is_read`).
  - Isolamento por identificador de entidade e ausência de efeitos colaterais.

### 2.3 Test Anchor 3: Endpoints REST WSGI e Catálogo de Fontes
- **Método de Teste:**
  `tests/test_civic_watchlists_and_source_catalog.py::TestCivicWatchlistsAndSourceCatalog::test_api_watchlist_and_sources_catalog_endpoints`
- **Requisitos Cobertos:** `FR-047`, `FR-048`, `NFR-024`, `AC-084`
- **Verificações:**
  - Resposta das rotas `GET /api/v1/watchlists`, `POST /api/v1/watchlists`, `PUT /api/v1/watchlists/{id}`, `DELETE /api/v1/watchlists/{id}` via WSGI `CivicAuditHTTPApp`.
  - Consulta a `GET /api/v1/sources/catalog` retornando as 8 fontes oficiais obrigatórias (`CAMARA_CEAP`, `SENADO_CEAPS`, `CGU_EMENDAS`, `PNCP_CONTRATOS`, `CGU_CEIS`, `CGU_CNEP`, `TSE_ELEICOES`, `RECEITA_FEDERAL_CNPJ`).
  - Metadados completos: órgãos custodiantes, periodicidade, campos chave, sanitizações e limitações epistêmicas.
  - Verificação de desempenho com tempo de resposta sub-50ms conforme `NFR-024`.

### 2.4 Test Anchor 4: Interface Cívica, Acessibilidade e Invariantes de Segurança
- **Método de Teste:**
  `tests/test_civic_watchlists_and_source_catalog.py::TestCivicWatchlistsAndSourceCatalog::test_ui_watchlist_and_catalog_markup_and_interactions`
- **Requisitos Cobertos:** `FR-048`, `SEC-024`, `AC-085`
- **Verificações:**
  - Presença e integridade das seções `#screen-inbox` / `#view-acompanhamentos` e do Catálogo de Fontes no HTML.
  - Acessibilidade WCAG 2.2 AA nos modais de criação de acompanhamento (`role="dialog"`, `aria-modal="true"`, foco acessível e tecla `Esc`).
  - Aplicação estrita da asserção de linguagem não-acusatória (`assert_non_accusatory_language`) em toda a interface e textos gerados.
  - Mascaramento mandatório de CPFs (`***.XXX.XXX-**`) exibidos em assinaturas ou feeds de eventos.
