# SPEC-0021 — Sistema de Acompanhamentos Cívicos (Watchlists/Alertas de Eventos Públicos) e Catálogo Interativo de Metodologia e Fontes de Dados

## 1. Identificador e Título
- **ID:** `SPEC-0021`
- **Título:** Sistema de Acompanhamentos Cívicos (Watchlists/Alertas de Eventos Públicos) e Catálogo Interativo de Metodologia e Fontes de Dados

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.0.0`

## 3. Problema e Motivação
Acompanhamento proativo de entidades públicas e eventos por cidadãos e pesquisadores, juntamente com a transparência ativa sobre a proveniência, cobertura, limitações e changelog de cada uma das 8 fontes oficiais integradas, cumprindo os itens P1 de `docs/design/screens.md` e Fluxo 4 de `docs/design/flows.md`.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Disponibilizar sistema de monitoramento cívico proativo (Watchlists) para acompanhamento contínuo de entidades públicas e seus atos oficiais.
- Emitir eventos de auditoria e movimentação pública estruturados e imutáveis com rastreabilidade SHA-256.
- Fornecer catálogo estruturado e interativo das 8 fontes oficiais integradas, com proveniência, cobertura, sanitizações e limitações metodológicas.
- Assegurar conformidade estrita com LGPD (mascaramento de CPF) e proibição absoluta de termos acusatórios.

### Não-Objetivos
- Realizar julgamentos criminais ou acusatórios de qualquer natureza.
- Enviar mensagens não solicitadas ou spam (uso restrito a inbox local no navegador e webhooks configurados pelo próprio usuário).
- Alterar dados nas fontes custodiantes governamentais externas.

## 5. Atores e Permissões
- `public_reader`: Leitura do catálogo de fontes e metodologia; gerenciamento de seus próprios acompanhamentos cívicos e visualização de eventos notificados.
- `reviewer_admin`: Acesso gerencial, supervisão de integridade das fontes de dados, publicação de novos changelogs de ingestão e monitoramento analítico.

## 6. Fluxos Principais
1. **Criação de Acompanhamento:** Usuário navega até perfil de entidade (fornecedor, mandatário, órgão) ou modal de contrato/despesa, clica em "Acompanhar", seleciona eventos de interesse e frequência, confirmando a criação da assinatura.
2. **Recebimento de Alertas de Eventos:** Eventos públicos monitorados geram notificações persistidas no lakehouse com hash de rastreabilidade, alimentando o feed/inbox de acompanhamentos.
3. **Gerenciamento da Lista de Acompanhamentos:** Usuário visualiza suas assinaturas ativas na visão de Acompanhamentos, podendo pausar, reativar, editar frequência e excluir inscrições.
4. **Consulta Interativa ao Catálogo de Fontes e Metodologia:** Usuário consulta as especificações detalhadas das 8 fontes governamentais integradas, visualizando custodiantes, periodicidade, campos, sanitizações e limitações epistêmicas.

## 7. Cenários Alternativos e de Erro
- **Entidade Inexistente ou Inválida:** Retorno de erro HTTP 400/404 com payload explicativo padronizado sem degradar a interface.
- **Assinatura Duplicada:** Detecção de assinatura preexistente para a mesma entidade e canal, oferecendo atualização dos eventos monitorados de forma idempotente.
- **Fonte Externa Temporariamente Indisponível:** Apresentação transparente do status no catálogo de fontes com carimbo temporal da última coleta íntegra e indicação de contingência.
- **Eventos Sem Novos Dados:** Exibição amigável de estado vazio informativo no feed de notificações ("Nenhum novo evento para esta entidade no período").

## 8. Requisitos Funcionais
- **`FR-046`**: O sistema deve disponibilizar modelo imutável e armazenamento lakehouse para Assinaturas de Acompanhamento Cívico (`CivicWatchlistSubscription`) e Eventos Monitorados (`CivicWatchlistEvent`), com suporte a 5 tipos de entidades (`FORNECEDOR`, `MANDATARIO`, `ORGAO`, `CONTRATO`, `DOSSIE`), 5 tipos de eventos monitorados (`NOVO_DOCUMENTO`, `ALTERACAO_VALOR`, `NOVO_PAGAMENTO`, `NOVA_ANALISE`, `RESPOSTA_CONTESTACAO`), 3 frequências (`IMEDIATA`, `DIARIA`, `SEMANAL`), estados (`ATIVO`, `PAUSADO`), e canais (`NAVEGADOR_LOCAL`, `WEBHOOK_CADASTRADO`).
- **`FR-047`**: O sistema deve disponibilizar o Catálogo Estruturado de Fontes de Dados Oficiais (`OfficialDataSourceCatalog` / `DataSourceSpecification`) documentando 8 fontes governamentais integradas (`CAMARA_CEAP`, `SENADO_CEAPS`, `CGU_EMENDAS`, `PNCP_CONTRATOS`, `CGU_CEIS`, `CGU_CNEP`, `TSE_ELEICOES`, `RECEITA_FEDERAL_CNPJ`), com cobertura temporal e geográfica, frequência de sincronização, campos chave, sanitizações aplicadas (LGPD/SHA-256), limitações explícitas e changelog de versões.
- **`FR-048`**: A API WSGI (`CivicAuditHTTPApp`) e a interface web devem expor endpoints e componentes de gerenciamento: `GET /api/v1/watchlists`, `POST /api/v1/watchlists`, `PUT /api/v1/watchlists/{id}`, `DELETE /api/v1/watchlists/{id}` e `GET /api/v1/sources/catalog`.

## 9. Requisitos Não Funcionais
- **`NFR-024`**: Execução determinística em memória e persistência SQLite no lakehouse com integridade referencial e resposta dos endpoints de acompanhamento e catálogo em tempo sub-50ms no WSGI `CivicAuditHTTPApp`.

## 10. Regras de Negócio e Dados
- **`DATA-023`**: Modelagem imutável (`frozen=True`) para `CivicWatchlistSubscription`, `CivicWatchlistEvent` e `DataSourceSpecification`, com hash canônico `SHA-256` gerado para cada assinatura e evento.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-024`**: Vedação absoluta a termos acusatórios (`assert_non_accusatory_language`), mascaramento compulsório de CPF (`***.XXX.XXX-**`) em assinaturas e eventos, e sanitização estrita de entradas contra injeção e XSS.

## 12. Critérios de Aceite
- **`AC-082`**: Modelo `CivicWatchlistSubscription` valida tipos de entidades, eventos e frequências, persistindo assinaturas e gerando chave SHA-256.
- **`AC-083`**: Lakehouse e API expõem operações completas de CRUD (listar, criar, atualizar status e deletar) para acompanhamentos com isolamento por identificador de entidade.
- **`AC-084`**: `OfficialDataSourceCatalog` fornece metadados completos das 8 fontes oficiais com cobertura, frequência, sanitizações e limitações epistêmicas.
- **`AC-085`**: Interface e endpoints implementam acessibilidade, segurança e ausência total de termos acusatórios.

## 13. Dependências
- `SPEC-0001` a `SPEC-0020`, `docs/design/*`

## 14. Riscos e Limitações
- Volume acumulado de eventos cívicos em clientes locais mitigado por paginação, índices SQLite dedicados e expiração configurável.
- Variações nas APIs custodiantes tratadas com resiliência, isolamento em lakehouse e histórico de versões documentado no catálogo de fontes.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_civic_watchlists_and_source_catalog.py::TestCivicWatchlistsAndSourceCatalog::test_watchlist_subscription_model_and_event_generation`
- `tests/test_civic_watchlists_and_source_catalog.py::TestCivicWatchlistsAndSourceCatalog::test_storage_watchlist_crud_lifecycle_and_events`
- `tests/test_civic_watchlists_and_source_catalog.py::TestCivicWatchlistsAndSourceCatalog::test_api_watchlist_and_sources_catalog_endpoints`
- `tests/test_civic_watchlists_and_source_catalog.py::TestCivicWatchlistsAndSourceCatalog::test_ui_watchlist_and_catalog_markup_and_interactions`

## 16. Questões Pendentes
- Nenhuma.
