# ADR-0024 — Protocolo de contestação

- **Status:** Aceito
- **Data:** 2026-10-26
- **Especificação:** `SPEC-0023`

## Contexto

O direito de resposta já existe para um dossiê publicado. O pedido de produto também exige fluxos separados para erro factual, documento, dado pessoal, direito autoral, texto que precisa de revisão, metodologia e solicitação de autoridade. Esses pedidos não podem ser publicados sozinhos nem apagar auditoria.

## Decisão

Uma tabela de protocolos e uma tabela de eventos imutáveis registram o pedido. A API pública devolve estado e prazo interno. O texto fica na leitura autenticada. CPF válido é mascarado na entrada. A meta de 2 ou 15 dias corridos é operacional e está rotulada como tal.

## Alternativas consideradas

- Reusar só o direito de resposta: não cobre pedido sem dossiê publicado.
- Publicar a contestação ao lado do registro no ato do envio: republicaria alegação ainda não revista.
- Apagar o registro quando a decisão for procedente: perderia a trilha. A correção de um dossiê continua no fluxo editorial já existente.

## Consequências

Não há operador nomeado para a fila. O protocolo não significa que uma pessoa já analisou o caso.
