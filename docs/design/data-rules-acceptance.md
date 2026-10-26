# Dados, regras e critérios de aceite

## Dados necessários

Toda entidade deve guardar identificador estável, origem, URL da fonte, data de coleta, data de atualização, cobertura, licença, versão do transformador e estado de disponibilidade.

Análises adicionam: método, versão do modelo/regra, parâmetros, conjunto comparável, evidências, limitações, explicações alternativas, revisão, contestação e histórico.

## Regras de negócio

1. Dados demonstrativos exibem rótulo persistente.
2. Fonte ausente nunca é convertida em valor zero.
3. Valores em estágios contábeis distintos não são somados sem explicação.
4. Uma análise automática não recebe estado “conclusão”.
5. Revisões e contestações preservam histórico.
6. Relação entre entidades exige evidência citável.
7. Alertas informam evento, frequência, canal e forma de cancelamento.
8. Exportações incluem filtros, data e proveniência.

## Critérios de aceite globais

- Navegação completa por teclado.
- Layout funcional em 390, 768, 1024 e 1440 px.
- Temas claro e escuro sem perda semântica.
- Estados loading, vazio, erro, incompleto e sem permissão disponíveis.
- Nenhuma anomalia é apresentada como fraude.
- Fonte e atualização acessíveis em detalhes.
- Gráficos possuem alternativa textual/tabular.
- Retorno à lista preserva contexto.
- Componentes usam tokens documentados.
- Dados fictícios são claramente rotulados.

## Critérios por fluxo P0

### Pesquisa

- Sugestões agrupadas por tipo.
- Filtros removíveis e estado refletido na URL quando houver roteamento real.
- Zero resultados oferece recuperação.

### Despesa

- Estágio contábil e valor inequívocos.
- Fonte abre em nova guia com aviso.
- Divergências exibem ambas as versões.

### Contrato

- Valor inicial, atualizado e pago são distinguíveis.
- Aditivos aparecem na linha do tempo.
- Documento indisponível reduz completude.

### Análise

- Método, evidências, limitações e revisão aparecem antes de compartilhar.
- Contestação gera protocolo.
- Linguagem respeita a classificação epistemológica.

## Validação de handoff

O Antigravity deve comparar a implementação com o protótipo em cada breakpoint, executar auditoria automatizada de acessibilidade, testar teclado manualmente e revisar conteúdo com especialista em transparência pública antes de conectar produção.
