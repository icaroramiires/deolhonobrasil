# Contratos da API REST — SPEC-0004 (`v1.1.0`)

Todos os endpoints retornam JSON (`application/json; charset=utf-8`) e incluem obrigatoriamente os headers de segurança (`SEC-006`):
- `Content-Security-Policy: default-src 'self'`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

---

## 1. `GET /api/v1/health`
Verifica a saúde do serviço e conectividade com o Lakehouse.
- **Response `200 OK`:**
```json
{
  "status": "ok",
  "service": "deolhonobrasil-api",
  "version": "0.1.0"
}
```

---

## 2. `GET /api/v1/dossiers`
Lista dossiês de auditoria respeitando a política de Row-Level Security (`SEC-004` / `SEC-005`).
- **Query Params:**
  - `limit` (`int`, default `20`, max `100`)
  - `offset` (`int`, default `0`)
  - `role` (`public_reader` default; `reviewer_admin` exige header `X-Admin-Token` válido, caso contrário retorna `403 Forbidden`)
- **Response `200 OK`:**
```json
{
  "role": "public_reader",
  "total": 1,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "dossier_id": "DOS-SIG-CEAP-06f566c54dda983",
      "rule_code": "R-CEAP-OUTLIER-Z3",
      "title": "Atipicidade estatística em despesa de cota parlamentar",
      "status": "ESCLARECIDO_COM_PROVA",
      "epistemic_layer": "INFERENCIA_ESTATISTICA",
      "official_data_block": "[DADO OFICIAL] ...",
      "statistical_inference_block": "[INFERÊNCIA ESTATÍSTICA] ...",
      "audit_hypothesis_and_limits_block": "[HIPÓTESE DE AUDITORIA / LIMITAÇÃO] ...",
      "provenance_hashes": ["8d41a0607a148e7390c80948a378b0f4318c19e5e28c21ec4d93ad480119405e"],
      "reviewer_id": "rev_ana_silva",
      "right_of_reply": {
        "protocol_id": "REP-DOS-SIG-CEAP-06f566c54dda983",
        "status": "PUBLICADO_LADO_A_LADO",
        "equal_visual_prominence": 1
      }
    }
  ]
}
```

---

## 3. `GET /api/v1/expenses`
Retorna despesas públicas curadas da camada Gold com soma exata em `Decimal` (`DATA-006`).
- **Query Params:** `year` (`int`, opcional), `state_uf` (`str`, opcional), `organ_code` (`str`, opcional), `limit` (`int`, default `50`), `offset` (`int`, default `0`)
- **Response `200 OK`:**
```json
{
  "total_count": 3,
  "total_net_amount_brl": "20110.70",
  "items": [
    {
      "natural_key": "CAMARA_CEAP|2025|...",
      "competence_year": 2025,
      "organ_name": "Câmara dos Deputados",
      "public_agent_name": "Dep. Exemplo Um",
      "supplier_doc_normalized": "11.222.333/0001-81",
      "net_amount_brl": "15200.00",
      "raw_batch_sha256": "8d41a0607a148e7390c80948a378b0f4318c19e5e28c21ec4d93ad480119405e"
    }
  ]
}
```

---

## 4. `GET /api/v1/reconciliation`
Retorna o resumo de reconciliação contábil e integridade do Lakehouse.
- **Response `200 OK`:**
```json
{
  "reconciled": true,
  "lakehouse_summary": {
    "raw_batches_count": 4,
    "quarantined_records_count": 3,
    "curated_expenses_count": 3,
    "curated_expenses_net_total_brl": "20110.70",
    "curated_contracts_count": 1,
    "curated_contracts_current_total_brl": "1820000.00",
    "curated_amendments_count": 1,
    "curated_amendments_paid_total_brl": "250000.00",
    "audit_dossiers_count": 1
  }
}
```

---

## 5. `POST /api/v1/right-of-reply`
Submete uma manifestação oficial ou Direito de Resposta vinculada a um dossiê (`FR-008`, `SEC-007`).
- **Request Body:**
```json
{
  "dossier_id": "DOS-SIG-CEAP-06f566c54dda983",
  "respondent_name": "Assessoria Técnica Parlamentar",
  "respondent_document": "123.456.789-01",
  "institutional_email_domain": "camara.leg.br",
  "statement_text": "Nota técnica oficial esclarecendo o escopo regional do contrato.",
  "attachment_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```
- **Response `201 Created`:**
```json
{
  "protocol_id": "REP-...",
  "dossier_id": "DOS-SIG-CEAP-06f566c54dda983",
  "respondent_document_masked_or_cnpj": "***.456.789-**",
  "status": "RECEBIDO_EM_VALIDACAO",
  "equal_visual_prominence": true
}
```
- **Erros:**
  - `404 Not Found`: Dossiê inexistente.
  - `422 Unprocessable Entity`: Termo acusatório proibido, `attachment_sha256` inválido ou campos obrigatórios vazios.
  - `429 Too Many Requests`: Limite de taxa por IP excedido.
