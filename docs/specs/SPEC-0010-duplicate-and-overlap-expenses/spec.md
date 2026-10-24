# SPEC-0010 — Detecção de Reembolsos Duplicados de Despesas Públicas e Sobreposição Espaço-Temporal

## 1. Identificador e Título
- **ID:** `SPEC-0010`
- **Título:** Detecção de Reembolsos Duplicados de Despesas Públicas e Sobreposição Espaço-Temporal

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.0.0`

## 3. Problema e Motivação
Na fiscalização de verbas indenizatórias parlamentares e despesas públicas (como CEAP/CEAPS), riscos comuns de descontrole ou irregularidade envolvem o reembolso duplicado de um mesmo documento fiscal (mesmo CNPJ de fornecedor e número de nota fiscal) em lotes diferentes, bem como a sobreposição espaço-temporal impossível, onde o mesmo agente público possui despesas presenciais registradas em unidades federativas distintas na mesma data. O `SPEC-0010` estabelece regras de auditoria automatizadas para detectar essas anomalias com rigor analítico, separação epistêmica rigorosa e estrita neutralidade linguística.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Implementar regra de detecção de duplicidade documental de despesas (`R-DUPLICATE-EXPENSE-DOCUMENT`).
- Implementar regra de detecção de sobreposição espaço-temporal (`R-TEMPORAL-GEOGRAPHIC-OVERLAP`).
- Garantir rastreabilidade integral com agregação de hashes `SHA-256` (`DATA-012`).
- Assegurar conformidade absoluta com a vedação de linguagem acusatória (`SEC-013`).

### Não-Objetivos
- Emitir juízo de valor ou declarar culpabilidade de agentes públicos ou fornecedores.
- Substituir a análise pericial humana de séries fiscais e estornos contábeis.

## 5. Atores e Permissões
- **Sistema / Motor de Auditoria (`AuditEngine`):** Executa as regras de forma autônoma e determinística.
- **Auditor Humano / Analista (`public_reader` / `admin`):** Visualiza os sinais gerados em modo `EM_TRIAGEM_INTERNA` para validação posterior.

## 6. Fluxos Principais
1. Ingestão de despesas públicas validadas com proveniência em cache/banco.
2. Execução da varredura linear em $O(N)$ para colisão de documentos fiscais (`supplier_doc_normalized`, `document_number`).
3. Execução da varredura temporal e agrupamento por agente e data para identificar UFs distintas em despesas presenciais.
4. Emissão de `AuditSignal` contendo proveniência combinada, severidade calculada e explicações neutras.

## 7. Cenários Alternativos e de Erro
- **Notas fiscais com números genéricos (`S/N`, `0`, vazios):** Devem ser ignoradas pela regra de duplicidade documental para evitar falsos positivos massivos.
- **Compras online ou não-presenciais / despesas na mesma UF:** Despesas sem exigência de deslocamento físico ou na mesma UF não disparam sobreposição geográfica.

## 8. Requisitos Funcionais
- `FR-022`: O motor de auditoria deve implementar `evaluate_duplicate_expense_document_rule` (`R-DUPLICATE-EXPENSE-DOCUMENT`), identificando quando o mesmo par `(supplier_doc_normalized, document_number)` é reembolsado mais de uma vez na base pública, emitindo `AuditSignal` com proveniência dupla e classificação `CROSS_SOURCE_DIVERGENCE`.
- `FR-023`: O motor de auditoria deve implementar `evaluate_temporal_geographic_overlap_rule` (`R-TEMPORAL-GEOGRAPHIC-OVERLAP`), identificando quando o mesmo agente público (`public_agent_id`) possui despesas presenciais (combustível, refeições, hospedagem) registradas em UFs distintas na mesma data (`issue_date`), emitindo `AuditSignal` com proveniência combinada e classificação `STATISTICAL_ANOMALY`.

## 9. Requisitos Não Funcionais
- `NFR-013`: Execução determinística em $O(N)$ para busca de duplicidade documental e $O(N \log N)$ para ordenação temporal, sem dependências externas.

## 10. Regras de Negócio e Dados
- `DATA-012`: Agregação estrita de proveniência (`provenance_hashes`) contendo todos os hashes `SHA-256` das despesas que compuseram a colisão documental ou a sobreposição geográfica.

## 11. Requisitos de Segurança e Privacidade
- `SEC-013`: Vedação absoluta a linguagem acusatória (`assert_non_accusatory_language`), explicitando nas limitações que notas com mesma numeração podem decorrer de séries fiscais distintas ou estornos posteriores, e que a concomitância geográfica pode corresponder a despesas de assessores de gabinete autorizados pela mesa diretora em nome do titular.

## 12. Critérios de Aceite
- `AC-038`: `evaluate_duplicate_expense_document_rule` detecta colisão exata de CNPJ normalizado e número de documento válido (> 0 e diferente de 'S/N').
- `AC-039`: `evaluate_duplicate_expense_document_rule` descarta documentos genéricos ou fornecedores distintos.
- `AC-040`: `evaluate_temporal_geographic_overlap_rule` sinaliza quando ocorrem despesas presenciais em UFs distintas no mesmo dia para o mesmo agente.
- `AC-041`: `evaluate_temporal_geographic_overlap_rule` ignora despesas na mesma UF ou categorias não presenciais/isentas.

## 13. Dependências
- `SPEC-0001`, `SPEC-0002`, `SPEC-0003`, `SPEC-0008`, `SPEC-0009`

## 14. Riscos e Limitações
- Possibilidade de homonímia numérica em séries de notas fiscais de fornecedores distintos com CNPJs diferentes (mitigado pela exigência de igualdade no CNPJ do fornecedor).
- Despesas executadas por assessores em viagem oficial simultânea em nome do parlamentar (mitigado pelas notas explicativas de limitação epistêmica).

## 15. Estratégia de Testes e Test Anchors
- `tests/test_duplicate_and_overlap_expenses.py::TestDuplicateAndOverlapExpensesRules::test_duplicate_expense_document_rule_detects_identical_invoice`
- `tests/test_duplicate_and_overlap_expenses.py::TestDuplicateAndOverlapExpensesRules::test_duplicate_expense_document_rule_ignores_generic_or_different_suppliers`
- `tests/test_duplicate_and_overlap_expenses.py::TestDuplicateAndOverlapExpensesRules::test_temporal_geographic_overlap_rule_detects_same_day_distinct_states`
- `tests/test_duplicate_and_overlap_expenses.py::TestDuplicateAndOverlapExpensesRules::test_temporal_geographic_overlap_rule_ignores_same_state_or_online_categories`

## 16. Questões Pendentes
- Nenhuma.
