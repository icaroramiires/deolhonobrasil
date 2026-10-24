# De Olho no Brasil — Arquitetura de Dados e Linhagem Criptográfica

**Versão:** 1.0.0  
**Referências SDD:** `SPEC-0001`, `ADR-0001`

---

## 1. Topologia Medallion / Lakehouse Cívico

| Camada | Tabela / Artefato | Propósito | Regra de Imutabilidade e Qualidade |
| :--- | :--- | :--- | :--- |
| **Raw / Bronze** | Payloads de origem (`CEAP`, `CEAPS`, `CGU`, `PNCP`) | Captura exata do dado oficial | Calculado hash `SHA-256` canônico antes de qualquer transformação (`compute_canonical_payload_sha256`). |
| **Quarantine** | `quarantined_records` | Isolamento de registros com falha estrutural | Valor monetário ausente/inválido (`PARSE_DECIMAL_ERROR`), CNPJ inválido (`INVALID_CNPJ`) ou data corrompida **jamais** viram `R$ 0,00`; vão para quarentena auditável. |
| **Curated / Gold** | `curated_expenses`, `curated_contracts`, `curated_amendments` | Dados validados, normalizados e prontos para auditoria | CPFs de pessoas físicas mascarados (`***.XXX.XXX-**`), chaves naturais idempotentes (`UNIQUE`) e valores em `Decimal` (`cents`). |
| **Reconciliation** | `batch_reconciliation_reports` | Fechamento contábil do lote | Invariante: `gross_input_total == curated_Valid_total + quarantined_total` (`difference == Decimal("0.00")`). |
| **Governance** | `audit_dossiers`, `right_of_reply_protocols`, `editorial_audit_trail` | Triagem, publicação revisada e Direito de Resposta | `editorial_audit_trail` é estritamente *append-only* (protegida por triggers `BEFORE UPDATE/DELETE`). |

---

## 2. Regras de Ouro de Dados (`DATA-001` a `DATA-006`)

1. **`DATA-001` (Proibição de Zero Silencioso):** Campos monetários vazios, nulos ou não numéricos disparam `MonetaryParseError` e são roteados para `quarantined_records`.
2. **`DATA-002` (Idempotência Determinística):** A reexecução do mesmo lote com as mesmas chaves naturais não duplica linhas nem altera totais reconciliados.
3. **`DATA-003` (Reconciliação Exata em `Decimal`):** Toda aritmética financeira utiliza `decimal.Decimal` com quantização explícita de 2 casas decimais (`0.01`). É proibido usar `float` para valores monetários.
4. **`DATA-004` (Exigência de Proveniência em Sinais de IA):** Nenhum `AuditSignal` ou seção de dossiê pode ser gerado sem ao menos um `SHA-256` válido em `provenance_hashes`.
5. **`DATA-005` (Trilha Editorial Imutável):** Toda mudança de status de dossiê gera registro perpétuo em `editorial_audit_trail`.
6. **`DATA-006` (Reconciliação de Totais na UI):** Toda tabela financeira na interface pública valida via `console.assert` que a soma das linhas renderizadas coincide com o total exibido no `<tfoot>`.
