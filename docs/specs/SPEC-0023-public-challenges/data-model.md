# Modelo de dados — SPEC-0023

## `civic_challenges`

| Campo | Regra |
| :--- | :--- |
| `challenge_id` | `cont-` + 12 hex. Imutável |
| `category` | Uma das sete categorias. Imutável |
| `status` | Nasce `RECEBIDO`. Só a decisão autenticada muda |
| `related_record_ref` | Opcional, higienizado, até 180 caracteres. Imutável |
| `statement_text` | Texto higienizado, CPF válido mascarado, até 4000 caracteres. Imutável |
| `contact_channel` | E-mail ou `nao_informado`. Fora da resposta pública |
| `received_at_utc` | UTC. Imutável |
| `internal_target_review_by_utc` | Recebimento mais 2 ou 15 dias corridos |
| `sha256` | Hash do identificador, da categoria, do texto e do instante |

## `civic_challenge_events`

Append-only. O primeiro evento é `RECEBIDO` com ator `public_submitter`. Decisões seguintes guardam o ator informado pelo revisor, o status novo e a nota.

Não há exclusão em cascata que apague o protocolo.
