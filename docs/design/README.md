# De Olho no Brasil — Handoff para Antigravity

## Objetivo

Referência de produto, UX/UI e implementação para uma plataforma de transparência pública. O produto deve transformar dados oficiais complexos em informação acessível, contextualizada e rastreável.

## Princípios inegociáveis

1. Anomalia não é prova de fraude.
2. Separar fato documentado, divergência, padrão incomum, hipótese e conclusão humana.
3. Exibir fonte, data de atualização, limitações e indisponibilidade.
4. Nunca apresentar dados demonstrativos como reais.
5. Toda visualização deve possuir alternativa textual ou tabular.
6. Interface neutra, não partidária e não sensacionalista.

## Conteúdo deste pacote

- `information-architecture.md`: arquitetura, navegação e permissões.
- `flows.md`: jornadas e decisões.
- `screens.md`: especificação das telas e prioridades.
- `design-system.md`: fundamentos e componentes.
- `design-tokens.json`: tokens portáveis.
- `interactions-accessibility.md`: interações, responsividade e WCAG.
- `data-rules-acceptance.md`: dados, regras de negócio e critérios de aceite.

## Estado do protótipo

### Implementado

Início, pesquisa, despesas, contratos, análises, evidências, acompanhamentos, tema claro/escuro, filtros mobile e navegação responsiva.

### Próximas etapas

Detalhes completos de despesa, perfis, contribuição cidadã, contestação, conta e administração. Essas áreas estão especificadas, mas não devem ser consideradas implementadas.

## Arquivos técnicos

- Aplicação editável: `src/`
- HTML compilado: `site/index.html`
- Estilos e tokens em uso: `src/index.css`
- Componente principal: `src/App.tsx`

## Orientação ao Antigravity

Preservar arquitetura, semântica dos status e rastreabilidade. Reutilizar componentes e tokens antes de criar variações. Validar visualmente nos breakpoints de 1440, 1024, 768 e 390 px. Conectar dados reais somente após definir contratos de API, proveniência, atualização e tratamento de falhas.
