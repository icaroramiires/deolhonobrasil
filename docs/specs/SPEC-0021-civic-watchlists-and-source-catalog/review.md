# Formal Spec Review: SPEC-0021

- **Review Date:** 2026-10-26
- **Gate Status:** `APPROVED (0 Critical, 0 High Open)`
- **Reviewers:** `donb-audit-ai-architect`, `security-reviewer`, `python-reviewer`, `council`

## 1. Visão Geral da Revisão
Este documento registra a revisão formal (Fase 3 do SDD) para a especificação `SPEC-0021 — Sistema de Acompanhamentos Cívicos (Watchlists/Alertas de Eventos Públicos) e Catálogo Interativo de Metodologia e Fontes de Dados`. A especificação foi submetida a análise adversarial de conformidade arquitetural, segurança, LGPD, integridade epistêmica e desempenho.

## 2. Análise de Ambiguidades e Casos de Erro
- **Entidades Inexistentes ou Inválidas:** A validação estrita dos 5 tipos de entidades (`FORNECEDOR`, `MANDATARIO`, `ORGAO`, `CONTRATO`, `DOSSIE`) garante que identificadores inconsistentes resultem em erro `400/404` imediato sem criar registros órfãos.
- **Assinaturas Duplicadas:** O design adota chave composta lógica (`entity_type`, `entity_id`, `channel`) gerando comportamento idempotente via `POST /api/v1/watchlists` ou atualização transparente dos eventos monitorados.
- **Falhas de Fontes Oficiais:** O catálogo documenta explicitamente as limitações epistêmicas e latências conhecidas de cada uma das 8 fontes, operando com cache e indicação explícita de temporalidade da última sincronização.

## 3. Segurança, LGPD e Invariantes Epistêmicas
- **LGPD Compulsória (`SEC-024`):** Qualquer CPF de pessoa física associado a mandatários, fornecedores ou criadores de assinaturas é mascarado no formato `***.XXX.XXX-**` antes de ser persistido ou retornado nas rotas de acompanhamento.
- **Linguagem Não-Acusatória (`SEC-024`):** Verificação rigorosa com `assert_non_accusatory_language` em títulos e descrições de eventos. Termos como "fraude", "crime" ou "desvio" são terminantemente vetados; acompanhamentos tratam exclusivamente de fatos públicos verificáveis (e.g., emissão de nota, aditivo contratual, pagamento).
- **Proteção contra Injeção e XSS:** Payloads de entrada e strings de exibição sofrem higienização rigorosa antes de compor JSONs ou fragmentos HTML.

## 4. Integridade de Dados e Modelagem Lakehouse
- **Imutabilidade e Hashing (`DATA-023`):** Dataclasses `CivicWatchlistSubscription`, `CivicWatchlistEvent` e `DataSourceSpecification` utilizam `frozen=True` e geram hash SHA-256 canônico a partir de seus atributos serializados.
- **Integridade Referencial:** Persistência em SQLite lakehouse com índices dedicados em `entity_id` e remoção em cascata controlada dos eventos atrelados a uma assinatura excluída.

## 5. Desempenho e Acessibilidade
- **Tempo de Resposta WSGI (`NFR-024`):** As rotas `/api/v1/watchlists` e `/api/v1/sources/catalog` são servidas pelo `CivicAuditHTTPApp` em tempo sub-50ms sob carga de teste.
- **Acessibilidade:** Componentes de gestão de acompanhamento e consulta ao catálogo implementam navegação total por teclado, contraste WCAG 2.2 AA e estados visuais completos.

## 6. Parecer Final do Gate
- **Achados Críticos Abertos:** 0
- **Achados Altos Abertos:** 0
- **Gate Status:** `APPROVED (0 Critical, 0 High Open)`
