# ADR 0019 — Interface Web Cívica, Design System Unificado (Tokens, Temas Claro/Escuro, Responsividade P0) e Visualização de Evidências Rastreáveis

## Status
Aprovado

## Data
2026-10-26

## Contexto
O projeto **De Olho no Brasil** consolidou 18 especificações com 22 regras determinísticas de auditoria cívica, motor de decisão calibrado *System 1* `Laya`, reconciliação contábil em centavos e triagem editorial com RLS. Contudo, a experiência do cidadão e do auditor necessita de uma interface web contemporânea, acessível, neutra e altamente responsiva que materialize o pacote de handoff documentado em `docs/design/`.

Os desafios arquiteturais e de produto para a interface cívica compreendem:
1. **Fidelidade ao Design System e Tokens:** Adotar rigorosamente a paleta de cores institucional neutra (verde profundo `--brand: #12654c`, destaque em verde-lima `--accent: #d3f05b` reservado a foco e pequenos indicadores, superfícies claras `#ffffff` e modo escuro `#14201c` / `#0e1714`), com tipografia legível (`Manrope` para display, `DM Sans` para leitura e monoespaçada para identificadores e hashes SHA-256);
2. **Arquitetura de Navegação em 7 Visões P0:** Estruturar a navegação nas 7 visões essenciais:
   - *Início (Visão Geral):* Apresentação da missão, métricas consolidadas, proposta de valor e aviso de dados demonstrativos/reais;
   - *Pesquisa:* Busca global com atalho universal `Ctrl/⌘ + K`, sugestões agrupadas por tipo (órgão, fornecedor, parlamentar, contrato), filtros persistidos e estados vazios com caminhos de recuperação;
   - *Despesas:* Tabela analítica com distinção expressa entre estágios contábeis (empenhado, liquidado e pago), filtros por UF/ano, paginação e reconciliação matemática;
   - *Contratos:* Relação de certames e fornecedores, vigência, aditivos contratuais e valores inicial, atualizado e pago;
   - *Análises:* Catálogo dos 22 sinais de auditoria com o banner obrigatório *"IA apoia, pessoas verificam"*, separação em 3 camadas epistêmicas, método matemático e limitações;
   - *Evidências:* Visualização de completude dos dados, grafo SVG acessível acompanhado de tabela equivalente e manifesto criptográfico SHA-256 offline;
   - *Acompanhamentos:* Gestão de monitoramento cidadão com frequência, canais e regras de notificação;
3. **Acessibilidade e Responsividade WCAG 2.2 AA:** Garantir conformidade nos 4 breakpoints prioritários (1440px wide, 1050px desktop, 768px tablet e 390px mobile), alvos de toque mínimos de 24×24px (44×44px em mobile), contraste mínimo de 4.5:1, link *"Pular para o conteúdo"*, captura de foco em modais e respeito a `prefers-reduced-motion`;
4. **Resiliência e Zero Dependências Externas Frágeis:** O frontend deve ser entregue em pacote autocontido (HTML5/CSS3/Vanilla JS moderno) servido diretamente pelo servidor WSGI `CivicAuditHTTPApp`, funcionando perfeitamente em ambientes sandbox/offline sem depender de conexões a CDNs de terceiros para seu funcionamento essencial.

## Decisão
1. **Unificação dos Tokens em CSS Variables:**
   - Implementar os design tokens de `docs/design/design-tokens.json` em `:root` e no seletor `[data-theme="dark"]`, suportando alternância dinâmica e persistência em `localStorage`;
   - Implementar classes semânticas para os badges epistêmicos:
     - Fato documentado (`--info: #265b9b`, fundo `--info-soft`);
     - Divergência / Padrão incomum (`--warning: #a55b12`, fundo `--warning-soft`);
     - Hipótese (`--muted`, com texto explícito de limitação);
     - Revisado (`--brand: #12654c`, com ícone e identificação de auditor humano).

2. **Renderização Integrada no Servidor WSGI (`CivicAuditHTTPApp`):**
   - Atualizar a aplicação HTTP para servir a interface com headers de segurança (`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`);
   - Manter a compatibilidade com a rota raiz `GET /` e `GET /index.html`.

3. **Arquitetura de Estados de Interface:**
   - Toda tela deve tratar formalmente os 6 estados obrigatórios: Carregando (*skeleton*), Carregamento parcial, Vazio inicial / zero resultados, Erro recuperável, Dados incompletos / fonte indisponível e Sem permissão (RLS).

## Consequências
### Positivas
- Experiência do usuário moderna, rápida e em total harmonia com o handoff de design de `docs/design/`.
- Plena conformidade com as diretrizes de acessibilidade WCAG 2.2 AA e navegação via teclado (`Ctrl+K`, setas, Tab, Esc).
- Eliminação do risco de quebra de layout por CDNs indisponíveis em ambiente de auditoria offline.
- Reconciliação contábil contínua com asserções em tempo de execução (`console.assert`).

### Negativas / Mitigações
- Um único arquivo autocontido ou assets inline podem atingir tamanho moderado (~150-200 KB). A mitigação consiste em compressão gzip/deflate e cache HTTP estático nos cabeçalhos (`Cache-Control: public, max-age=3600`).
