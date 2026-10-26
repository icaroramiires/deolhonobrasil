# Contratos — SPEC-0022

## `GET /api/v1/public-coverage`

Resposta 200. Campos estáveis:

- `product`: `De Olho no Brasil`
- `currency`: `BRL`
- `amount_unit`: `centavos`
- `represents_national_spending`: `false`
- `ledgers_are_additive`: `false`
- `uses_language_model`: `false`
- `expenses`, `contracts`, `amendments`: contagem, centavos, período e `by_source`
- `sanctions`: somente contagem
- `observed_sources`
- `catalog_source_ids_without_local_rows`
- `limitations`

Não existe campo de total único entre ledgers.

## `POST /api/v1/questions`

Corpo: `{"question": "<texto até 500 caracteres>"}`.

- 200 e `conclusion` = `INFORMACAO_VERIFICADA` quando a consulta encontra as linhas necessárias.
- 200 e `conclusion` = `ANALISE_INCONCLUSIVA` quando a intenção é suportada, mas faltam linhas ou identificadores. `evidence.net_amount_cents` fica `null` nesse caso de gasto sem linhas.
- 422 `EDITORIAL_POLICY` quando o texto contém termo vedado. O termo não é ecoado.
- 422 `VALIDATION_ERROR` quando o texto é vazio ou passa de 500 caracteres.

`model_id` é `null`. `method` é `consulta_sql_deterministica` nas respostas 200.
