# Technical Design & Plan — SPEC-0010

## 1. Visão Geral da Arquitetura
Implementação das funções de auditoria `evaluate_duplicate_expense_document_rule` e `evaluate_temporal_geographic_overlap_rule` em `src/deolhonobrasil/audit/rules.py`.

## 2. Algoritmos
- **`evaluate_duplicate_expense_document_rule`**: Agrupa despesas por `(supplier_doc_normalized, document_number)`. Ignora documentos nulos, vazios, `0` ou `S/N`. Se houver mais de uma despesa no grupo com valores/IDs distintos, gera `AuditSignal` do tipo `CROSS_SOURCE_DIVERGENCE` reunindo os hashes `SHA-256`.
- **`evaluate_temporal_geographic_overlap_rule`**: Filtra despesas presenciais elegíveis (combustível, hospedagem, alimentação). Agrupa por `(public_agent_id, issue_date)`. Se houver despesas em UFs (`state`) distintas na mesma data, gera `AuditSignal` do tipo `STATISTICAL_ANOMALY`.

## 3. Estrutura de Arquivos Afetados
- `src/deolhonobrasil/audit/rules.py`
- `tests/test_duplicate_and_overlap_expenses.py`
