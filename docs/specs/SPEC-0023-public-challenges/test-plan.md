# Plano de testes — SPEC-0023

| Critério | Teste |
| :--- | :--- |
| `AC-092` | `test_submission_masks_cpf_and_starts_received` |
| `AC-093` | `test_public_read_hides_statement_even_when_it_quotes_a_forbidden_term` |
| `AC-094` | `test_decision_appends_event_and_received_text_cannot_be_rewritten_or_deleted` |
| `AC-095` | `test_decision_note_rejects_forbidden_language_and_invalid_contact` |
| `AC-096`, `AC-097` | `test_http_routes_require_admin_token_for_the_full_record` |

Os testes usam SQLite temporário e não chamam rede. O arquivo SQL é conferido como texto, não aplicado a um Postgres remoto.
