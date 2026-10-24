# ADR-0008: Detecção de Fracionamento de Despesas e Avaliação da Lei de Benford

- **Status:** Aceito e Implementado
- **Data:** 2026-10-24
- **Especificação Relacionada:** [`SPEC-0008-benford-and-split-expense-rules`](../../specs/SPEC-0008-benford-and-split-expense-rules/spec.md)
- **Requisitos Atendidos:** `FR-018`, `FR-019`, `NFR-011`, `DATA-010`, `SEC-011`, `AC-030..033`

---

## 1. Contexto

A auditoria cívica de compras e gastos públicos depara-se com dois padrões críticos de análise:
1. **Desvios de Distribuição Populacional (Lei de Benford):** Em conjuntos volumosos de despesas financeiras sem intervenção artificial, o primeiro dígito significativo costuma obedecer à distribuição logarítmica de Benford ($P(d) = \log_{10}(1 + 1/d)$). Anomalias acentuadas no Desvio Médio Absoluto (MAD > 0.01500 segundo Nigrini) indicam agregação atípica de valores (ex.: concentração em dígitos 7, 8, 9 ou valores repetitivos artificiais).
2. **Fracionamento de Despesas (Dispensa de Licitação):** O art. 75 da Lei nº 14.133/2021 estabelece limites anuais para compras diretas sem licitação (dispensa de valor). Práticas de fracionamento ocorrem quando múltiplas compras individuais abaixo do teto são emitidas em curto período de tempo para o mesmo fornecedor pelo mesmo órgão, acumulando um montante superior ao limite legal.

---

## 2. Decisão Arquitetural

1. **Regra Determinística de Benford em Lote (`R-STAT-BENFORD-DEVIATION`):**
   - Implementada na função `evaluate_benford_distribution_rule`.
   - Exige amostra mínima de 50 despesas estritamente positivas para assegurar relevância estatística.
   - Aplica os critérios de conformidade de Nigrini baseados em MAD: emite `AuditSignal` somente quando `MAD > Decimal("0.01500")` (`NAO_CONFORME`).
   - Classificação epistêmica: `EpistemicClassification.STATISTICAL_INFERENCE`.
2. **Regra Determinística de Janela Móvel de Fracionamento (`R-SPLIT-EXPENSE-THRESHOLD`):**
   - Implementada na função `evaluate_split_expense_rule`.
   - Agrupa despesas por chave única `(organ_code, supplier_doc_normalized)`.
   - Ordena temporalmente as transações em $O(N \log N)$ e aplica uma janela deslizante de 90 dias (`window_days`).
   - Se o conjunto contiver ao menos 3 transações (`min_count`), cada uma inferior ao teto individual (`single_limit`, ex: R$ 50.000), e o total acumulado na janela atingir ou superar o teto agregado (`aggregate_threshold`, ex: R$ 100.000), emite `AuditSignal`.
   - Classificação epistêmica: `EpistemicClassification.AUDIT_HYPOTHESIS`.
3. **Imutabilidade e Limitação Epistêmica (`SEC-011`):**
   - Ambas as regras agregam todos os hashes `SHA-256` dos lotes brutos em `provenance_hashes`.
   - O sumário de limitação explicita que desvios estatísticos ou acúmulo de compras não comprovam irregularidade, pois podem corresponder a tabelas de diárias/passagens, compras emergenciais ou objetos contratuais legalmente distintos.

---

## 3. Consequências

- **Positivas:** Permite triagem automatizada, matematicamente fundamentada e auditável de irregularidades potenciais de licitação e anomalias numéricas em larga escala, mantendo a proteção legal e epistêmica contra acusações temerárias.
