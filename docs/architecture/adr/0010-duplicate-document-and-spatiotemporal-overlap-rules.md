# ADR-0010: Detecção de Documentos Fiscais em Duplicidade e Sobreposição Espaço-Temporal

- **Status:** Aceito e Implementado
- **Data:** 2026-10-24
- **Especificação Relacionada:** [`SPEC-0010-duplicate-and-overlap-expenses`](../../specs/SPEC-0010-duplicate-and-overlap-expenses/spec.md)
- **Requisitos Atendidos:** `FR-022`, `FR-023`, `NFR-013`, `DATA-012`, `SEC-013`, `AC-038..041`

---

## 1. Contexto

A prestação de contas de verbas indenizatórias parlamentares (CEAP/CEAPS) e ressarcimentos da administração pública está sujeita a dois tipos críticos de inconsistências contábeis e operacionais:
1. **Reembolsos em Duplicidade do Mesmo Documento Fiscal:** Apresentação da mesma nota fiscal (`document_number`) emitida pelo mesmo fornecedor (`supplier_doc_normalized`) mais de uma vez em competências ou por agentes públicos distintos.
2. **Sobreposição Espaço-Temporal Concomitante:** Registro de despesas de presença física indispensável (combustível, refeições, hospedagem) em diferentes Unidades da Federação na mesma data por um único agente público.

---

## 2. Decisão Arquitetural

1. **Regra de Documento Fiscal Duplicado (`R-DUPLICATE-EXPENSE-DOCUMENT`):**
   - Agrupa despesas por par canônico `(supplier_doc_normalized, document_number)`.
   - Ignora números genéricos de documento (`"S/N"`, `"-"`, `"0"`, `"SEM NUMERO"`, vazios) para prevenir falsos positivos.
   - Quando $\ge 2$ despesas compartilham o mesmo documento e fornecedor válido, emite `AuditSignal` com proveniência encadeada e classificação `EpistemicClassification.CROSS_SOURCE_DIVERGENCE`.
2. **Regra de Sobreposição Espaço-Temporal (`R-TEMPORAL-GEOGRAPHIC-OVERLAP`):**
   - Agrupa despesas presenciais (categorias: `"COMBUSTIVEL"`, `"ALIMENTACAO"`, `"HOSPEDAGEM"`, `"LOCACAO DE VEICULOS"`) por `(public_agent_id, issue_date)`.
   - Se um mesmo agente público apresentar despesas presenciais em $\ge 2$ estados distintos (`state_uf`) na mesma data de emissão, emite `AuditSignal` com classificação `EpistemicClassification.STATISTICAL_ANOMALY`.
   - Exclui categorias remotas ou de divulgação institucional (ex.: `"DIVULGACAO"`, `"ASSINATURA"`).
3. **Limitações Epistêmicas e Não-Acusatórias (`SEC-013`):**
   - Explicita nos limites epistêmicos que documentos fiscais com numeração idêntica podem decorrer de séries fiscais distintas não capturadas no schema ou de estornos no SIAFI.
   - Esclarece que despesas em estados distintos no mesmo dia podem refletir gastos de assessores técnicos credenciados em missão oficial autorizada pelo Ato da Mesa Diretora do órgão.

---

## 3. Consequências

- **Positivas:** Identifica com rigor e auditabilidade $O(N)$ erros materiais ou duplicidades de pagamentos públicos, resguardando os direitos dos agentes públicos via governança epistêmica e política editorial não-acusatória.
