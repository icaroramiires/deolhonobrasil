# ADR-0023 — Cobertura observada e perguntas determinísticas

- **Status:** Aceito
- **Data:** 2026-10-26
- **Especificação:** `SPEC-0022`

## Contexto

A página pública já exibia cifras de exemplo do wireframe, como “R$ 154,20 mi”, em cartões que podiam ser lidos como totais oficiais do ambiente. O catálogo de fontes também declara `last_sync_utc` no código. Esses carimbos não são o resultado de uma coleta executada no ambiente que responde a API.

O pedido pedia uma página inicial com quanto foi analisado, em qual período, e respostas em linguagem natural citando fontes. Um modelo de linguagem não deve calcular soma financeira.

## Decisão

1. `GET /api/v1/public-coverage` agrega somente linhas do SQLite local, em centavos inteiros, com ledgers separados para despesas, contratos, emendas e sanções.
2. `POST /api/v1/questions` reconhece um conjunto fechado de intenções e responde com SQL. Sem linha suficiente, a conclusão é `ANALISE_INCONCLUSIVA`.
3. O campo `uses_language_model` é sempre `false` nesses dois contratos. `model_id` é `null`.
4. Dossiês em `EM_TRIAGEM_INTERNA` não entram no texto nem nos identificadores dessas respostas.
5. O wireframe mantém a série ilustrativa usada pelo `console.assert` do gráfico, com rótulo explícito de amostra. A cobertura do ambiente é outro bloco, preenchido pela API quando a página é servida pelo aplicativo.

## Alternativas consideradas

- Somar despesas, contratos e emendas num único “total analisado”: rejeitada. Os conjuntos se sobrepõem conceitualmente e a soma induziria dupla contagem.
- Responder perguntas com um LLM ancorado no lakehouse: rejeitada neste incremento. Não há provedor configurado, não houve avaliação no domínio de despesa pública e o cálculo financeiro já é determinístico.
- Apagar as cifras ilustrativas do wireframe: adiada. Elas sustentam a reconciliação visual da amostra de desenho. O rótulo passa a separá-las da cobertura observada.

## Consequências

Um ambiente sem ingestão responde zero e declara que zero significa ausência de linha local. O catálogo continua listando oito fontes; a cobertura informa quais identificadores do catálogo não têm linha local. Não se afirma que uma fonte externa foi sincronizada.
