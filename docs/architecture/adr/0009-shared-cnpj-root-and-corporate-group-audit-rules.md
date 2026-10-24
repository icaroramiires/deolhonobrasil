# ADR-0009: Detecção de Vínculo Societário por Radical de CNPJ Compartilhado e Monopólio de Fornecedores

- **Status:** Aceito e Implementado
- **Data:** 2026-10-24
- **Especificação Relacionada:** [`SPEC-0009-supplier-network-and-shared-patterns`](../../specs/SPEC-0009-supplier-network-and-shared-patterns/spec.md)
- **Requisitos Atendidos:** `FR-020`, `FR-021`, `NFR-012`, `DATA-011`, `SEC-012`, `AC-034..037`

---

## 1. Contexto

No ecossistema de compras e gastos públicos brasileiros, grupos empresariais frequentemente operam sob um mesmo radical societário (os 8 primeiros dígitos do CNPJ, `RR.RRR.RRR/FFFF-DD`), diferenciando-se apenas pelo sufixo de filial (`/0001`, `/0002`, `/0003`, etc.).

Dois riscos de conformidade relevantes decorrem dessa estrutura:
1. **Dispersão Artificial entre Filiais do Mesmo Grupo:** Despesas ou compras diretas fracionadas entre filiais distintas para contornar limites de dispensa de licitação ou limites de concentração (`HHI`), que passam despercebidas se os sistemas analisarem exclusivamente o CNPJ completo de 14 dígitos.
2. **Dependência Monopolística em Categoria de Despesa:** Órgãos ou categorias onde um único grupo econômico (mesmo radical) captura percentual desproporcional ($\ge 80\%$) dos pagamentos liquidados.

---

## 2. Decisão Arquitetural

1. **Extração Estrita de Radical Societário (`extract_cnpj_root`):**
   - Extrai os 8 primeiros dígitos do CNPJ apenas quando o documento possui exatamente 14 dígitos válidos.
   - Retorna `None` para CPFs mascarados (`***.XXX.XXX-**`) ou documentos inválidos (`NFR-012`), preservando a salvaguarda contra falsos positivos por homonímia.
2. **Regra de Radical Compartilhado (`R-SHARED-CNPJ-ROOT`):**
   - Agrupa transações por `(organ_code, cnpj_root)`.
   - Se o conjunto contiver $\ge 2$ filiais com CNPJs distintos de 14 dígitos e a soma consolidada for $\ge \text{R\$} 100.000,00$, emite `AuditSignal` com classificação `EpistemicClassification.STATISTICAL_ANOMALY`.
3. **Regra de Monopólio de Fornecedor por Categoria (`R-PROCUREMENT-MONOPOLISTIC-SUPPLIER`):**
   - Analisa o volume total gasto em uma categoria ou órgão com volume $\ge \text{R\$} 100.000,00$ e $\ge 3$ transações.
   - Se um único radical societário responder por $\ge 80\%$ do montante, emite `AuditSignal` com classificação `EpistemicClassification.STATISTICAL_ANOMALY`.
4. **Governança e Política Editorial (`SEC-012`):**
   - Nenhuma emissão de termos acusatórios.
   - Limitação explícita: filiais são entidades legalmente habilitadas e a concentração pode decorrer de especialização técnica exclusiva ou fornecimento em localidade sem outros concorrentes viáveis.

---

## 3. Consequências

- **Positivas:** Permite visão corporativa consolidada de grupos econômicos nos gastos públicos, fechando a lacuna de fiscalização entre filiais sem violar a privacidade de pessoas físicas nem gerar falsos positivos com CPFs mascarados.
