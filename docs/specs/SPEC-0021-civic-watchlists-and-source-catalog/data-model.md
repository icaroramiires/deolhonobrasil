# Data Model: SPEC-0021

## 1. Modelos de Domínio (`models.py`)

### 1.1 `CivicWatchlistSubscription`
Entidade imutável (`frozen=True`) representando o acompanhamento configurado por um cidadão ou pesquisador.

```python
@dataclass(frozen=True)
class CivicWatchlistSubscription:
    subscription_id: str
    entity_type: str         # FORNECEDOR, MANDATARIO, ORGAO, CONTRATO, DOSSIE
    entity_id: str           # CNPJ, CPF mascarado, código de órgão, ID de contrato/dossiê
    entity_name: str
    monitored_events: tuple  # NOVO_DOCUMENTO, ALTERACAO_VALOR, NOVO_PAGAMENTO, NOVA_ANALISE, RESPOSTA_CONTESTACAO
    frequency: str           # IMEDIATA, DIARIA, SEMANAL
    channel: str             # NAVEGADOR_LOCAL, WEBHOOK_CADASTRADO
    is_active: bool = True
    created_at: str = ""     # ISO-8601 UTC
    sha256: str = ""         # Hash SHA-256 canônico
```

### 1.2 `CivicWatchlistEvent`
Entidade imutável (`frozen=True`) representando um evento de ato público ou análise detectado para a entidade acompanhada.

```python
@dataclass(frozen=True)
class CivicWatchlistEvent:
    event_id: str
    subscription_id: str
    entity_type: str
    entity_id: str
    event_type: str          # NOVO_DOCUMENTO, ALTERACAO_VALOR, NOVO_PAGAMENTO, NOVA_ANALISE, RESPOSTA_CONTESTACAO
    title: str               # Título descritivo neutro e factual
    description: str         # Descrição detalhada sem termos acusatórios
    occurred_at: str         # ISO-8601 UTC
    payload_sha256: str      # Hash SHA-256 do documento ou registro oficial gerador
    is_read: bool = False
```

### 1.3 `DataSourceSpecification`
Entidade imutável (`frozen=True`) definindo as características técnicas, sanitizações e limitações metodológicas de uma fonte de dados oficial.

```python
@dataclass(frozen=True)
class DataSourceSpecification:
    source_id: str              # Ex: CAMARA_CEAP, SENADO_CEAPS, CGU_EMENDAS, etc.
    name: str                   # Nome formal da base
    governing_body: str         # Órgão público custodiante
    official_url: str           # URL oficial do portal governamental
    temporal_coverage: str      # Período disponível (ex: 2018-2026)
    geographic_coverage: str    # Abrangência (Nacional, Federal, etc.)
    sync_frequency: str         # Frequência de atualização oficial / coleta
    key_fields: tuple           # Campos essenciais consumidos
    privacy_sanitizations: tuple# Tratamentos LGPD aplicados (mascaramento CPF, hashing)
    epistemic_limitations: tuple# Limitações conhecidas e premissas analíticas
    version: str                # Versão do adaptador de ingestão
    last_sync_utc: str          # Carimbo da última coleta bem-sucedida
```

---

## 2. Esquema Relacional no Lakehouse SQLite (`storage.py`)

```sql
CREATE TABLE IF NOT EXISTS lakehouse_watchlist_subscriptions (
    subscription_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    monitored_events TEXT NOT NULL,  -- JSON array serializado
    frequency TEXT NOT NULL,
    channel TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    sha256 TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_watchlist_subs_entity 
ON lakehouse_watchlist_subscriptions(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS lakehouse_watchlist_events (
    event_id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(subscription_id) REFERENCES lakehouse_watchlist_subscriptions(subscription_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_watchlist_events_sub 
ON lakehouse_watchlist_events(subscription_id, occurred_at);
```

---

## 3. Contratos de API REST (`CivicAuditHTTPApp`)

### 3.1 `GET /api/v1/watchlists`
- **Resposta 200 OK:**
```json
{
  "total": 1,
  "subscriptions": [
    {
      "subscription_id": "sub_8f4a12",
      "entity_type": "FORNECEDOR",
      "entity_id": "12.345.678/0001-90",
      "entity_name": "Tecnologia e Serviços Brasil Ltda",
      "monitored_events": ["NOVO_DOCUMENTO", "ALTERACAO_VALOR"],
      "frequency": "DIARIA",
      "channel": "NAVEGADOR_LOCAL",
      "is_active": true,
      "created_at": "2026-10-26T18:00:00Z",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "unread_events_count": 2
    }
  ],
  "recent_events": [
    {
      "event_id": "evt_991823",
      "subscription_id": "sub_8f4a12",
      "entity_type": "FORNECEDOR",
      "entity_id": "12.345.678/0001-90",
      "event_type": "ALTERACAO_VALOR",
      "title": "Termo Aditivo Publicado",
      "description": "Publicação de termo aditivo com alteração de valor contratual registrado no PNCP.",
      "occurred_at": "2026-10-26T14:30:00Z",
      "payload_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
      "is_read": false
    }
  ]
}
```

### 3.2 `POST /api/v1/watchlists`
- **Requisição:**
```json
{
  "entity_type": "FORNECEDOR",
  "entity_id": "12.345.678/0001-90",
  "entity_name": "Tecnologia e Serviços Brasil Ltda",
  "monitored_events": ["NOVO_DOCUMENTO", "ALTERACAO_VALOR"],
  "frequency": "DIARIA",
  "channel": "NAVEGADOR_LOCAL"
}
```
- **Resposta 201 Created:** Objeto `CivicWatchlistSubscription` serializado com `subscription_id` e `sha256`.

### 3.3 `PUT /api/v1/watchlists/{id}`
- **Requisição:**
```json
{
  "is_active": false,
  "frequency": "SEMANAL"
}
```
- **Resposta 200 OK:** Objeto atualizado.

### 3.4 `DELETE /api/v1/watchlists/{id}`
- **Resposta 200 OK:** `{"status": "deleted", "subscription_id": "sub_8f4a12"}`.

### 3.5 `GET /api/v1/sources/catalog`
- **Resposta 200 OK:**
```json
{
  "total_sources": 8,
  "sources": [
    {
      "source_id": "PNCP_CONTRATOS",
      "name": "Portal Nacional de Contratações Públicas - Contratos e Editais",
      "governing_body": "Ministério da Gestão e da Inovação em Serviços Públicos (MGI)",
      "official_url": "https://pncp.gov.br",
      "temporal_coverage": "2021-2026",
      "geographic_coverage": "Nacional (União, Estados e Municípios)",
      "sync_frequency": "Diária",
      "key_fields": ["numeroControlePNCP", "valorGlobal", "objetoContrato", "cnpjContratado"],
      "privacy_sanitizations": ["Mascaramento de CPF de representantes", "Cálculo de SHA-256 do JSON de origem"],
      "epistemic_limitations": ["Adesão gradual de municípios de pequeno porte", "Possível retificação a posteriori"],
      "version": "1.4.0",
      "last_sync_utc": "2026-10-26T06:00:00Z"
    }
  ]
}
```
