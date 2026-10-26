# Tasks Breakdown: SPEC-0021

- [ ] `TASK-2101`: Implementar modelos de domínio imutáveis (`CivicWatchlistSubscription`, `CivicWatchlistEvent`, `DataSourceSpecification`, `OfficialDataSourceCatalog`) com hashing SHA-256 canônico e validação estrita de enums (`DONB-29`).
- [ ] `TASK-2102`: Implementar persistência SQLite no lakehouse (`storage.py`) com criação das tabelas `lakehouse_watchlist_subscriptions` e `lakehouse_watchlist_events`, índices e operações CRUD completas.
- [ ] `TASK-2103`: Implementar rotas REST (`/api/v1/watchlists`, `/api/v1/sources/catalog`) no servidor WSGI `CivicAuditHTTPApp` e componentes da interface cívica web (`wireframe_de_olho_no_brasil.html`).
- [ ] `TASK-2104`: Construir suíte de testes automatizados em `tests/test_civic_watchlists_and_source_catalog.py` cobrindo integralmente os 4 test anchors do SDD.
