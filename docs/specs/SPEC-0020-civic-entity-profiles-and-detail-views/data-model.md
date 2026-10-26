# Data Model: SPEC-0020

## 1. `CivicEntityProfile`
- `entity_id`: `str`
- `entity_type`: `str` (supplier, mandatary, organ)
- `name`: `str`
- `identifier`: `str` (CNPJ / masked CPF)
- `metadata`: `dict`
- `sha256`: `str`

## 2. `ContractTimelineEvent`
- `contract_id`: `str`
- `event_type`: `str` (initial, amendment, suspension)
- `date`: `str`
- `value`: `float`
- `description`: `str`

## 3. `ExpenseDetailPayload`
- `expense_id`: `str`
- `committed`: `float`
- `liquidated`: `float`
- `paid`: `float`
- `voucher_sha256`: `str`
