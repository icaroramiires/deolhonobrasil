# Requisitos do produto — De Olho no Brasil

Este documento traduz o pedido de plataforma pública de fiscalização para o sistema que já existe neste repositório. O nome de trabalho Verba Clara não foi adotado ([ADR-0022](../architecture/adr/0022-retain-de-olho-no-brasil-name.md)).

## Problema

Dados oficiais de gasto público estão dispersos, usam formatos diferentes e não separam, para o leitor geral, fato documentado, anomalia estatística e hipótese. O produto reduz essa distância sem transformar pontuação algorítmica em acusação.

## Requisitos já cobertos pelo código atual

| Tema | Onde está |
| :--- | :--- |
| Conectores CEAP, CEAPS, emendas CGU, contratos PNCP e sanções | `src/deolhonobrasil/pipeline/connectors/` |
| SHA-256 do lote, quarentena e centavos inteiros | `pipeline/storage.py`, `pipeline/privacy.py` |
| Regras determinísticas e separação epistêmica | `audit/rules.py`, `pipeline/models.py` |
| Triagem com revisão humana antes de publicação nominal | `audit/laya_engine.py`, `governance/dossiers.py` |
| Direito de resposta e trilha editorial | `governance/right_of_reply.py` |
| API, limite por IP e cabeçalhos de segurança | `api/service.py` |
| RLS de referência para PostgreSQL | `governance/rls_policies.sql` |
| Interface cívica | `wireframe_de_olho_no_brasil.html` |
| Acompanhamentos e catálogo declarado de fontes | `SPEC-0021` |

## Requisito acrescentado nesta alteração

| ID | Enunciado |
| :--- | :--- |
| `FR-049` | Qualquer total exibido como cobertura deste ambiente sai das linhas persistidas e declara o que não representa |
| `FR-050` | Perguntas em linguagem simples usam somente essas linhas e terminam em inconclusão quando elas não bastam |

## Requisitos ainda não implementados

- Portal em Next.js. A interface atual é HTML servido pelo aplicativo Python. Trocar a stack exigiria um produto novo, não um ajuste.
- PostgreSQL Supabase em execução. O `.env.example` tem variáveis vazias. Não há projeto verificado.
- Terraform e Cloud Run. Não há provedor de nuvem configurado e nenhum recurso pago foi criado.
- OCR, PDF digitalizado e conectores municipais.
- Notificação externa de acompanhamentos. O canal implementado é local ou webhook informado pelo próprio registro, sem provedor de e-mail configurado.
- Contestação como fluxo distinto do direito de resposta já existente, com prazos legais operados por pessoas autorizadas. O protocolo técnico existe; a operação humana não foi ensaiada.
- Sincronização com Jira e Confluence. O MCP Atlassian desta execução pedia autenticação.

## Critério de pronto de um requisito novo

Há especificação com âncora de teste, revisão sem bloqueador crítico, teste executado nesta árvore e ausência de cifra ou integração declarada sem evidência.
