# Interações, responsividade e acessibilidade

## Interações

- `Ctrl/⌘ + K`: abre e foca a pesquisa global.
- Tabs: setas movem foco; Enter/Espaço selecionam.
- Filtros desktop: painel lateral; mobile: painel inferior modal.
- Expansões documentais preservam somente uma seção aberta por grupo.
- Alterações de rota atualizam título, foco e região `aria-live`.
- Tema é persistido localmente.
- Ações assíncronas desabilitam repetição e exibem progresso.

## Responsividade

### Desktop ≥ 1050

Sidebar fixa, conteúdo até 1360, tabelas completas e detalhe lado a lado.

### Tablet 761–1049

Sidebar compacta, grids reduzidos, detalhes em bloco superior e tabelas com rolagem.

### Mobile ≤ 760

Menu em drawer, margens 16, ações primárias em largura total, filtros em bottom sheet, cards em coluna e tabelas com alternativa resumida. Não ocultar informações críticas; priorizar e expandir.

## WCAG 2.2 AA

- Contraste mínimo 4,5:1 em texto e 3:1 em elementos grandes/controles.
- Foco visível com área e contraste suficientes.
- Alvos mínimos de 24 × 24; preferencialmente 44 × 44 em mobile.
- Ordem de foco acompanha leitura.
- Link “Pular para o conteúdo”.
- Status combina texto, ícone e cor.
- Gráficos possuem nome acessível, resumo e tabela equivalente.
- Modais prendem foco, fecham com Esc e devolvem foco à origem.
- Respeitar `prefers-reduced-motion`.
- Não usar placeholder como único rótulo.
- Mensagens de erro são associadas ao campo e anunciadas.

## Conteúdo

- Evitar “suspeito”, “fraude” ou “irregular” sem conclusão formal documentada.
- Preferir “padrão incomum”, “divergência” ou “requer verificação”.
- Datas em `dd mmm aaaa`; data/hora inclui fuso quando relevante.
- Valores usam BRL e indicam estágio contábil.
- Linguagem direta, sem juridiquês quando houver alternativa.
