# ADR 0021 — Sistema de Acompanhamentos Cívicos (Watchlists/Alertas de Eventos Públicos) e Catálogo Interativo de Metodologia e Fontes de Dados

## Status
Aprovado

## Data
2026-10-26

## Contexto
Após a implementação dos Perfis Cívicos e Modais de Detalhe na `SPEC-0020`, restavam dois módulos fundamentais de prioridade P1 descritos no handoff de design em `docs/design/screens.md` e `docs/design/flows.md`:

1. **Jornada de Acompanhamento Cívico (Watchlists e Alertas de Eventos Públicos — Fluxo 4):**
   - Cidadãos, jornalistas e pesquisadores precisam acompanhar de forma proativa entidades públicas de interesse (fornecedores por CNPJ, mandatários por CPF/ID, órgãos por código/CNPJ, contratos específicos por ID ou dossiês de auditoria).
   - O acompanhamento deve permitir escolher tipos específicos de eventos monitorados:
     - `NOVO_DOCUMENTO`: Emissão de nova nota fiscal, empenho ou publicação de aditivo;
     - `ALTERACAO_VALOR`: Acréscimo ou supressão de valor contratual por termo aditivo;
     - `NOVO_PAGAMENTO`: Liquidação ou ordem bancária emitida para favorecido;
     - `NOVA_ANALISE`: Emissão de novo sinal de auditoria ou dossiê pelo motor Laya;
     - `RESPOSTA_CONTESTACAO`: Protocolo oficial de esclarecimento ou retificação material anexado ao dossiê.
   - O cidadão pode configurar a frequência (`IMEDIATA`, `DIARIA`, `SEMANAL`), o canal de recebimento (`NAVEGADOR_LOCAL`, `WEBHOOK_CADASTRADO`) e gerenciar o ciclo de vida da assinatura (ativar, pausar, editar e excluir).

2. **Catálogo Interativo de Metodologia e Fontes de Dados Oficiais (P1):**
   - Transparência ativa sobre a proveniência dos dados, informando com clareza para cada uma das 8 fontes governamentais integradas (`CAMARA_CEAP`, `SENADO_CEAPS`, `CGU_EMENDAS`, `PNCP_CONTRATOS`, `CGU_CEIS`, `CGU_CNEP`, `TSE_ELEICOES`, `RECEITA_FEDERAL_CNPJ`):
     - Órgão custodiante oficial e link direto para a fonte;
     - Cobertura temporal e abrangência federativa;
     - Frequência de atualização oficial vs frequência de coleta;
     - Campos primários coletados e regras de transformação;
     - Tratamentos de privacidade e segurança (mascaramento LGPD de CPF e cálculo de SHA-256);
     - Limitações metodológicas conhecidas e hipóteses de auditoria;
     - Histórico de versões e changelog de correções da plataforma.

3. **Invariantes Epistêmicas e de Segurança:**
   - Zero linguagem acusatória (`assert_non_accusatory_language`): o acompanhamento é uma ferramenta de cidadania e controle social legítimo, sem imputação de culpa ou suspeição prévia;
   - Proteção estrita de dados pessoais (LGPD): CPFs mascarados (`***.XXX.XXX-**`) em todas as assinaturas e eventos gerados;
   - Funcionamento autocontido e offline no servidor WSGI com tempo de resposta sub-50ms.

## Decisão
1. **Modelagem de Domínio e Persistência no Lakehouse (`storage.py`):**
   - Definir classes imutáveis (`frozen=True`) em `models.py`:
     - `CivicWatchlistSubscription`: assinatura persistida com `subscription_id`, `entity_type`, `entity_id`, `entity_name`, `monitored_events`, `frequency`, `channel`, `is_active`, `created_at`, e hash canônico `sha256`.
     - `CivicWatchlistEvent`: evento gerado com `event_id`, `subscription_id`, `entity_type`, `entity_id`, `event_type`, `title`, `description`, `occurred_at`, `payload_sha256`, `is_read`.
     - `DataSourceSpecification`: especificação estruturada de cada fonte com `source_id`, `name`, `governing_body`, `official_url`, `temporal_coverage`, `geographic_coverage`, `sync_frequency`, `key_fields`, `privacy_sanitizations`, `epistemic_limitations`, `version`, `last_sync_utc`.
   - Adicionar tabelas SQLite dedicadas (`lakehouse_watchlist_subscriptions` e `lakehouse_watchlist_events`) com integridade referencial, índices em `entity_id` e métodos CRUD atômicos.

2. **Rotas REST na API WSGI (`CivicAuditHTTPApp`):**
   - `GET /api/v1/watchlists`: Lista todas as assinaturas com contagem de eventos recentes;
   - `POST /api/v1/watchlists`: Cria nova assinatura validando tipo de entidade e eventos;
   - `PUT /api/v1/watchlists/{id}`: Atualiza status (`is_active`) ou frequência;
   - `DELETE /api/v1/watchlists/{id}`: Remove assinatura e eventos associados;
   - `GET /api/v1/sources/catalog`: Retorna o catálogo completo das 8 fontes com metadados e limitações.

3. **Integração na Interface Web Cívica (`wireframe_de_olho_no_brasil.html`):**
   - Na visão `Acompanhamentos` (`#screen-inbox` / `#view-acompanhamentos`), exibir:
     - Tabela/cartões de assinaturas ativas com controles de alternância (Ativo/Pausado) e exclusão;
     - Feed de eventos recentes disparados com badges e links diretos para as entidades;
     - Botão "+ Novo Acompanhamento" abrindo modal acessível com seleção de eventos e frequência;
   - Adicionar botão de ação rápida "Acompanhar Entidade" dentro dos modais de detalhe e perfis (Fornecedor, Mandatário, Órgão, Contrato);
   - Criar seção/modal "Metodologia e Catálogo de Fontes" navegável com busca e detalhes de cada fonte oficial.

## Consequências
### Positivas
- Fecha integralmente todos os requisitos P1 do handoff de design (`docs/design/screens.md` e `docs/design/flows.md`).
- Fortalece a soberania epistêmica do usuário fornecendo transparência radical sobre as fontes de dados e limitações.
- Permite monitoramento contínuo e rastreável sem necessidade de servidores externos ou banco de dados externo.
- 100% aderente ao padrão de isolamento, determinismo e tolerância a falhas.

### Negativas / Mitigações
- Assinaturas de watchlists precisam ser sincronizadas localmente quando em ambiente cliente estático (localStorage). A mitigação consiste em suportar persistência no SQLite do backend WSGI e sincronização transparente com o estado do cliente.
