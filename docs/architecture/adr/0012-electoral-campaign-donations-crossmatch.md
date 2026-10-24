# ADR-0012: Cruzamento entre Fornecedores Públicos e Doadores de Campanha Eleitoral (TSE)

- **Status:** Aceito e Em Implementação
- **Data:** 2026-10-24
- **Especificação Relacionada:** [`SPEC-0012-electoral-campaign-donations`](../../specs/SPEC-0012-electoral-campaign-donations/spec.md)
- **Requisitos Atendidos:** `FR-026`, `FR-027`, `NFR-015`, `DATA-014`, `SEC-015`, `AC-046..049`

---

## 1. Contexto

A auditoria de integridade de gastos públicos exige a transparência de vínculos de interesse prévios entre agentes públicos contratantes e pessoas jurídicas ou físicas contratadas ou reembolsadas:
1. **Dados Eleitorais do TSE:** A Justiça Eleitoral disponibiliza a prestação de contas oficial de campanhas eleitorais, contendo o registro detalhado de todas as doações financeiras recebidas por candidatos e comitês.
2. **Conexão Fornecedor-Doador:** A ocorrência de pagamentos por meio de verbas públicas (cota parlamentar ou contratos de compras públicas) a fornecedores que constam como doadores declarados de campanha do próprio mandatário beneficiário é um indicador relevante de governança democrática.

---

## 2. Decisão Arquitetural

1. **Modelo de Doação Eleitoral Curada (`CuratedElectoralDonation`):**
   - Entidade imutável (`frozen=True`) contendo `candidate_id`, `candidate_name`, `donor_doc_normalized`, `donor_name`, `donation_amount`, `donation_date` e proveniência `ProvenanceMetadata` vinculada à fonte `OfficialSource.TSE_ELEICOES`.
2. **Regra de Cruzamento Fornecedor-Doador (`R-CROSS-ELECTORAL-DONOR-SUPPLIER`):**
   - Cruza a base de despesas públicas (`CuratedPublicExpense` e contratos `CuratedPublicContract`) com a base de doações do TSE vinculadas ao mesmo mandatário (`public_agent_id` ou identificador de candidatura).
   - Realiza a correspondência exata sobre `donor_doc_normalized` e `supplier_doc_normalized`.
   - **Guarda Anti-Homonímia LGPD:** O cruzamento automático nominal exige documento inequívoco (CNPJ completo de 14 dígitos). Doações e despesas com CPFs mascarados (`***.XXX.XXX-**`) não sofrem correspondência automática por identidade para prevenir falsos positivos graves decorrentes de homonímia.
3. **Classificação Epistêmica e Proveniência Criptográfica:**
   - Classificação epistêmica obrigatória: `EpistemicClassification.CROSS_SOURCE_DIVERGENCE`.
   - Agregação de proveniência com duplo `SHA-256`: hash do lote bruto do TSE e hash do lote bruto da despesa auditada.
4. **Salvaguardas Editoriais e Linguagem Não-Acusatória (`SEC-015`):**
   - Aplicação estrita de `assert_non_accusatory_language`.
   - Explicitação mandante no bloco de limitação de que doações eleitorais declaradas à Justiça Eleitoral e fornecimento de bens ou serviços previstos em regulamento de cota parlamentar constituem atos legais e legítimos, não havendo presunção automática de irregularidade ou favoritismo.

---

## 3. Consequências

- **Positivas:** Permite ao cidadão e aos órgãos de controle auditar relações de financiamento político com fornecedores públicos de forma automatizada, rastreável e juridicamente segura.
