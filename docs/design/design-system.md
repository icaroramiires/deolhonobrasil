# Design system

## Direção visual

Institucional contemporânea, neutra e analítica. Verde profundo comunica estabilidade sem apropriação partidária; verde-lima é reservado a foco e pequenos destaques. Superfícies claras, bordas discretas e densidade intermediária.

## Tipografia

- Display: Manrope 500–700.
- Interface e leitura: DM Sans 400–700.
- Identificadores: fonte monoespaçada do sistema.
- Títulos usam espaçamento levemente negativo; textos longos preservam altura de linha mínima de 1,5.

## Grid e espaçamento

- Unidade base: 4.
- Escala: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64.
- Conteúdo desktop: máximo 1360.
- Sidebar desktop: 252; reduzida para 220 em tablet.
- Mobile: margem lateral 16.

## Componentes

### Navegação

Sidebar, topbar, breadcrumb, tabs e navegação mobile. Estados: padrão, hover, foco, ativo, bloqueado e recolhido.

### Ações

Botão primário, secundário, textual e destrutivo. Estados: padrão, hover, pressed, foco, loading e disabled. Uma ação primária por área decisória.

### Entrada

Busca global, busca contextual, input, select, textarea, checkbox, radio e upload. Rótulo sempre visível em formulários complexos; erro junto ao campo.

### Dados

Tabela, tabela responsiva, paginação, ordenação, filtros, chips, métricas, gráficos e exportação. Números alinhados à direita e status nunca comunicado apenas por cor.

### Confiança

Badge epistemológico, fonte, data, completude, aviso de limitação, documento, evidência e trilha de revisão.

Classificações:

- Fato documentado — azul informativo.
- Divergência — âmbar.
- Padrão incomum — âmbar.
- Hipótese — neutro com texto explícito.
- Revisado — verde acompanhado de ícone/texto.

### Feedback

Toast, alerta inline, banner, skeleton, vazio, erro e modal. Mensagens dizem o que ocorreu, impacto e próxima ação.

## Temas

Claro e escuro compartilham semântica. Não inverter imagens/documentos. Gráficos devem recalcular contraste. Preferência é persistida e pode seguir o sistema em evolução futura.

## Ícones

Traço 1,8; tamanhos 16, 18, 20 e 24. Sempre acompanhados de texto quando representam ação ambígua. Ícones decorativos usam `aria-hidden`.

## Uso de cards

Cards agrupam uma unidade real de informação ou decisão. Evitar card por métrica quando uma linha ou tabela comunicar melhor.
