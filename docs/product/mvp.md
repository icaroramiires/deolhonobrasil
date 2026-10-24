# Escopo do MVP — De Olho no Brasil

## 1. Estratégia de Recorte Inicial (Redução de Risco Técnico, Financeiro e Jurídico)

Para garantir alta precisão contábil, baixo custo operacional e segurança jurídica desde o primeiro dia, o MVP concentra-se em **quatro fontes primárias federais estruturadas**:

| Fonte Oficial | Escopo de Dados no MVP | Chave Natural & Controle | Especificação SDD |
| :--- | :--- | :--- | :--- |
| **1. Câmara dos Deputados (`CAMARA_CEAP`)** | Cota para o Exercício da Atividade Parlamentar (notas fiscais, reembolsos, fornecedores PJ/PF) | `SHA-256(fonte + doc_id + ano + mes + doc_fornecedor)` | [`SPEC-0001`](../specs/SPEC-0001-data-pipeline/spec.md) |
| **2. Senado Federal (`SENADO_CEAPS`)** | Cota para o Exercício da Atividade Parlamentar dos Senadores | `SHA-256(fonte + doc_id + ano + mes + doc_fornecedor)` | [`SPEC-0001`](../specs/SPEC-0001-data-pipeline/spec.md) |
| **3. Portal da Transparência / CGU (`CGU_EMENDAS`)** | Emendas parlamentares federais (empenho, pagamento, município IBGE e favorecido) | `SHA-256(fonte + cod_emenda + ano + ibge + favorecido)` | [`SPEC-0001`](../specs/SPEC-0001-data-pipeline/spec.md) |
| **4. Portal Nacional de Contratações Públicas (`PNCP_CONTRATOS`)** | Contratos públicos federais, valores iniciais/globais e termos aditivos | `SHA-256(fonte + num_controle_pncp + doc_fornecedor)` | [`SPEC-0001`](../specs/SPEC-0001-data-pipeline/spec.md) |

## 2. Capacidades Entregues no MVP

1. **Ingestão Idempotente, Quarentena e Reconciliação (`SPEC-0001`):**
   - Validação matemática de CNPJ (14 dígitos) e CPF (11 dígitos) com mascaramento LGPD (`***.XXX.XXX-**`).
   - Isolamento automático em quarentena (`QuarantinedRecord`) para registros sem identificador ou com valor monetário nulo/ausente (proibido converter valor ausente em `R$ 0,00`).
   - Reconciliação centavo a centavo (`BatchReconciliationReport`) em `decimal.Decimal`.
2. **Regras Determinísticas, Motor *System 1* `Laya` e Grounded RAG (`SPEC-0002`):**
   - Avaliadores `R-PNCP-OVERPRICE-Z3` (sobrepreço estatístico contratual), `R-CGU-HHI-CONCENTRATION` (concentração de fornecedores via Índice HHI) e `R-CEAP-OUTLIER-Z3` (atipicidade em cotas parlamentares).
   - Triagem rápida via `LayaSystem1Adapter` (`DecisionEnginePort`) que encaminha qualquer `score >= 0.70` ou sinal nominal para `REVISAO_HUMANA`.
   - Explicação textual em português gerada pelo `GroundedDossierNarrator` estritamente ancorada nos hashes `SHA-256` e estruturada nas 3 camadas epistêmicas.
3. **Governança Editorial Híbrida, Direito de Resposta e RLS (`SPEC-0003`):**
   - Ciclo de vida de dossiês (`EM_TRIAGEM_INTERNA`, `PUBLICADO_COM_REVISAO`, `ESCLARECIDO_COM_PROVA`, `ERRO_MATERIAL_RETIFICADO`).
   - Políticas Row-Level Security (`rls_policies.sql`) e filtros de aplicação impedindo que leitores públicos acessem dossiês não revisados.
   - Direito de Resposta lado a lado com paridade visual e trilha de auditoria editorial imutável (`editorial_audit_trail`).
4. **Interface Cívica `achromatic-ledger` e API Pública (`SPEC-0004`):**
   - Interface de alta legibilidade (`wireframe_de_olho_no_brasil.html`) validada sem erros ou alertas em `1440px`, `768px` e `390px`.
   - Endpoints REST públicos e de contraditório (Checkpoint 3).

## 3. Fora do Escopo do MVP Inicial
- Scraping de portais municipais sem API ou em PDFs escaneados sem camada de texto confiável.
- Publicação automática de dossiês nominais sem revisão humana.
- Julgamento autônomo de mérito jurídico por modelos generativos.
