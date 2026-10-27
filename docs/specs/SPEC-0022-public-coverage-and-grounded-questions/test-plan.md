# Plano de testes — SPEC-0022

| Critério | Teste | O que prova |
| :--- | :--- | :--- |
| `AC-086` | `test_empty_lakehouse_coverage_is_zero_and_states_the_limitation` | Zero local não é apresentado como ausência de gasto público |
| `AC-087` | `test_persisted_expense_totals_reconcile_by_source_in_cents` | 10,00 + 15,50 + 4,00 fecham em 2950 centavos por fonte |
| `AC-088` | `test_grounded_question_returns_category_total_from_stored_rows` | Categoria, comparação e documento saem das linhas inseridas |
| `AC-089` | `test_unknown_category_and_prompt_injection_stay_inconclusive` | Instrução embutida não cria valor; termo vedado recebe 422 |
| `AC-090` | `test_public_pending_question_hides_internal_triage_title` | Título de triagem não aparece na resposta pública |
| `AC-091` | `test_http_routes_and_wireframe_label_sample_figures` | Rotas e rótulo de amostra ilustrativa |

Os testes usam SQLite temporário e CNPJ de teste já aceito por `create_validated`. Não chamam rede.
