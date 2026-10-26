# Technical Design Plan: SPEC-0021

## 1. Visão Geral de Arquitetura
O design técnico para o `SPEC-0021` estabelece a infraestrutura necessária para monitoramento cívico contínuo e transparência ativa de metodologia e fontes oficiais de dados no projeto *De Olho no Brasil*.

O sistema é dividido em três camadas funcionais:
1. **Domínio e Modelagem Imutável (`models.py`):** Dataclasses congeladas (`frozen=True`) para inscrições de acompanhamento (`CivicWatchlistSubscription`), eventos notificados (`CivicWatchlistEvent`) e especificações de fontes oficiais (`DataSourceSpecification`), com hashes criptográficos SHA-256 e validação de invariantes cívicas.
2. **Persistência Lakehouse SQLite (`storage.py`):** Tabelas relacionais com integridade referencial, métodos atômicos de CRUD e consultas otimizadas por índice para subscrições e eventos.
3. **Serviços HTTP e Interface WSGI (`app.py` e `wireframe_de_olho_no_brasil.html`):** Roteamento RESTful na API WSGI `CivicAuditHTTPApp` retornando payloads em tempo sub-50ms e componentes de interface WCAG 2.2 AA para visualização de feed de eventos, gestão de assinaturas e navegação no catálogo de fontes.

```
+---------------------------------------------------------------------------------+
|                        Interface Cívica Web (HTML / JS)                         |
|  - Painel de Acompanhamentos (#view-acompanhamentos)                            |
|  - Feed de Eventos Públicos e Botão "+ Novo Acompanhamento"                     |
|  - Catálogo Interativo de Fontes Oficiais e Metodologia                         |
+---------------------------------------------------------------------------------+
                                       |
                                       | HTTP REST (JSON)
                                       v
+---------------------------------------------------------------------------------+
|                         WSGI App (CivicAuditHTTPApp)                            |
|  - GET/POST /api/v1/watchlists                                                  |
|  - PUT/DELETE /api/v1/watchlists/{id}                                           |
|  - GET /api/v1/sources/catalog                                                  |
+---------------------------------------------------------------------------------+
                                       |
                                       | Invocações determinísticas
                                       v
+---------------------------------------------------------------------------------+
|                         Domínio & Lakehouse Storage                             |
|  - Models: CivicWatchlistSubscription, CivicWatchlistEvent, DataSourceSpec      |
|  - SQLite: lakehouse_watchlist_subscriptions, lakehouse_watchlist_events        |
|  - Invariantes: LGPD (***.XXX.XXX-**), SHA-256, assert_non_accusatory_language    |
+---------------------------------------------------------------------------------+
```

## 2. Componentes e Responsabilidades

### 2.1 Módulo de Domínio (`models.py`)
- **`CivicWatchlistSubscription`:**
  - Identificador único (`subscription_id`), tipo de entidade (`entity_type`: `FORNECEDOR`, `MANDATARIO`, `ORGAO`, `CONTRATO`, `DOSSIE`), identificador público da entidade (`entity_id`), nome amigável (`entity_name`), conjunto de eventos monitorados (`monitored_events`: `NOVO_DOCUMENTO`, `ALTERACAO_VALOR`, `NOVO_PAGAMENTO`, `NOVA_ANALISE`, `RESPOSTA_CONTESTACAO`), frequência de atualização (`frequency`: `IMEDIATA`, `DIARIA`, `SEMANAL`), canal de entrega (`channel`: `NAVEGADOR_LOCAL`, `WEBHOOK_CADASTRADO`), estado (`is_active`), data de criação (`created_at`) e `sha256`.
- **`CivicWatchlistEvent`:**
  - Identificador (`event_id`), referência de assinatura (`subscription_id`), `entity_type`, `entity_id`, tipo do evento (`event_type`), título (`title`), descrição neutra e factual (`description`), carimbo de ocorrência (`occurred_at`), hash do payload oficial (`payload_sha256`) e indicador de leitura (`is_read`).
- **`DataSourceSpecification` & `OfficialDataSourceCatalog`:**
  - Metadados completos para as 8 fontes governamentais integradas (`CAMARA_CEAP`, `SENADO_CEAPS`, `CGU_EMENDAS`, `PNCP_CONTRATOS`, `CGU_CEIS`, `CGU_CNEP`, `TSE_ELEICOES`, `RECEITA_FEDERAL_CNPJ`).
  - Atributos: `source_id`, `name`, `governing_body`, `official_url`, `temporal_coverage`, `geographic_coverage`, `sync_frequency`, `key_fields`, `privacy_sanitizations`, `epistemic_limitations`, `version`, `last_sync_utc`.

### 2.2 Camada Lakehouse Storage (`storage.py`)
- Criação das tabelas `lakehouse_watchlist_subscriptions` e `lakehouse_watchlist_events`.
- Índices em `entity_id` e `subscription_id`.
- Métodos de repositório:
  - `save_watchlist_subscription(subscription: CivicWatchlistSubscription) -> None`
  - `get_watchlist_subscription(subscription_id: str) -> Optional[CivicWatchlistSubscription]`
  - `list_watchlist_subscriptions(is_active_only: bool = False) -> List[CivicWatchlistSubscription]`
  - `update_watchlist_subscription_status(subscription_id: str, is_active: bool) -> bool`
  - `delete_watchlist_subscription(subscription_id: str) -> bool`
  - `save_watchlist_event(event: CivicWatchlistEvent) -> None`
  - `list_watchlist_events(subscription_id: Optional[str] = None, limit: int = 50) -> List[CivicWatchlistEvent]`
  - `mark_watchlist_event_read(event_id: str) -> bool`

### 2.3 Camada de API REST (`CivicAuditHTTPApp`)
- `GET /api/v1/watchlists`: Retorna lista serializada de assinaturas ativas e resumo de eventos pendentes.
- `POST /api/v1/watchlists`: Recebe payload JSON, valida enums/tipos, calcula SHA-256 e persiste assinatura.
- `PUT /api/v1/watchlists/{id}`: Permite alternar `is_active` e atualizar frequência.
- `DELETE /api/v1/watchlists/{id}`: Remove assinatura e eventos relacionados.
- `GET /api/v1/sources/catalog`: Retorna o catálogo oficial das 8 fontes estruturado com documentação técnica e epistêmica.

### 2.4 Camada de Interface do Usuário (`wireframe_de_olho_no_brasil.html`)
- Painel de Acompanhamentos com alternância de status, contadores e lista de eventos factuais.
- Modal para configuração de novos acompanhamentos acessível via teclado (`Esc`, foco contido).
- Seção interativa de Catálogo de Metodologia e Fontes com busca textual e tags de cobertura.

## 3. Fluxo de Dados e Ciclo de Vida
1. **Configuração de Acompanhamento:** Usuário define entidade e tipos de evento no modal; a requisição é validada contra o catálogo de entidades e salva no lakehouse.
2. **Disparo de Evento:** Durante ingestão de dados ou atualização analítica, fatos relevantes geram instâncias de `CivicWatchlistEvent` com hash SHA-256.
3. **Consulta de Catálogo:** Usuário acessa `/api/v1/sources/catalog` ou o componente de interface para inspecionar limitações metodológicas e proveniência dos dados oficiais.
