# SPEC-0007 — Cruzamento Multicritério CEIS/CNEP, Divergência entre Fontes e Persistência de Sanções Administrativas

**Identificador:** SPEC-0007
**Título:** Cruzamento Multicritério CEIS/CNEP, Divergência entre Fontes e Persistência de Sanções Administrativas
**Status:** Verificado
**Versão:** 1.0.0
**Data de Última Atualização:** 2026-10-24

---

## 1. Identificador e Título
SPEC-0007 — Cruzamento Multicritério CEIS/CNEP, Divergência entre Fontes e Persistência de Sanções Administrativas.

## 2. Status e Versão
- **Status:** Verificado
- **Versão:** 1.0.0

## 3. Problema e Motivação
O ecossistema de controle social e fiscalização de recursos públicos *De Olho no Brasil* necessita integrar e cruzar dados de sanções administrativas do Portal da Transparência (CGU - CEIS / CNEP) com contratos e emendas parlamentares. Atualmente, existem lacunas na identificação de fornecedores sancionados que continuam recebendo repasses públicos ou celebrando aditivos, bem como riscos de falsos positivos decorrentes de homonímias em CPFs e falta de quarentena para registros malformados. Esta especificação define o pipeline de ingestão, validação, mascaramento LGPD, persistência imutável e motor de regras de cruzamento de fontes para sanções administrativas.

## 4. Objetivos e Não-Objetivos
### Objetivos
1. Ingerir lotes de dados do CEIS/CNEP via conector padronizado do Civic Lakehouse.
2. Mascarar CPFs de pessoas físicas comuns (`***.XXX.XXX-**`) e persistir hashes `SHA-256` dos payloads brutos.
3. Isolar registros inválidos ou sem data inicial em quarentena.
4. Implementar regras de auditoria determinísticas para detecção de fornecedores sancionados ativos e divergências entre aditivos e execução (`R-CROSS-CEIS-SANCTIONED-SUPPLIER` e `R-CROSS-AMENDMENT-EXECUTION-GAP`).
5. Expor consulta pública via endpoint `GET /api/v1/sanctions`.

### Não-Objetivos
1. Emitir juízo de valor, qualificação criminal ou condenação automática de corrupção.
2. Cruzamento automático nominal de CPFs mascarados para evitar falsos positivos por homonímia.

## 5. Atores e Permissões
- **Cidadão / Leitor Público (`public_reader`):** Acesso de leitura aos registros públicos curados de sanções via API e painéis.
- **Auditor Interno / Sistema (`system_auditor`):** Execução do pipeline de ingestão, reconciliação e motor de regras Laya.

## 6. Fluxos Principais
1. **Ingestão e Curadoria:** O conector `parse_cgu_ceis_cnep_json_batch` recebe o arquivo bruto, calcula o `SHA-256`, valida a estrutura temporal e documental, mascara CPFs e persiste no `CivicLakehouseStorage` (`curated_sanctions`).
2. **Quarentena:** Registros sem data inicial ou com documento corrompido são desviados para tabela/estado de quarentena.
3. **Cruzamento de Regras:** O motor avalia fornecedores ativos no CEIS/CNEP contra contratos vigentes, emitindo `AuditSignal` com classificação `CROSS_SOURCE_DIVERGENCE`.
4. **Consulta Pública:** A API REST expõe os dados filtrados e paginados em `GET /api/v1/sanctions`.

## 7. Cenários Alternativos e de Erro
- **Quarentena de Sanção:** Registro sem `start_date` ou com CNPJ/CPF inválido é rejeitado da tabela principal e gravado com status de quarentena e razão de falha.
- **Homonímia de CPF:** CPFs mascarados (`***.XXX.XXX-**`) não disparam cruzamento nominal automático (exigência exclusiva de CNPJ de 14 dígitos).
- **Vigência Temporal:** Sanções com `end_date` expirado anterior à data do contrato são desconsideradas para o motor de alerta ativo.

## 8. Requisitos Funcionais
- **`FR-016`:** O conector `parse_cgu_ceis_cnep_json_batch` e o `CivicLakehouseStorage` devem ingerir, validar, mascarar CPFs (`***.XXX.XXX-**`) e persistir lotes de sanções administrativas (`CuratedSanctionRecord` / `CGU_CEIS_CNEP`) com reconciliação e quarentena, expondo consulta pública em `GET /api/v1/sanctions`.
- **`FR-017`:** O motor de regras determinísticas deve implementar `evaluate_ceis_cnep_sanctioned_supplier_rule` (`R-CROSS-CEIS-SANCTIONED-SUPPLIER`) e `evaluate_amendment_execution_divergence_rule` (`R-CROSS-AMENDMENT-EXECUTION-GAP`), emitindo sinais com classificação epistêmica `CROSS_SOURCE_DIVERGENCE` (`DIVERGENCIA_ENTRE_REGISTROS`) e encadeando os hashes `SHA-256` de ambas as fontes cruzadas.

## 9. Requisitos Não Funcionais
- **`NFR-010`:** Cruzamento temporal exato (`date`) e vedação a falso positivo por CPF mascarado (cruzamento automático nominal só ocorre para CNPJ completo de 14 dígitos).

## 10. Regras de Negócio e Dados
- **`DATA-009`:** `CuratedSanctionRecord` deve ser imutável (`frozen=True`) e exigir `ProvenanceMetadata` com `OfficialSource.CGU_CEIS_CNEP`.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-010`:** Proibição estrita de linguagem acusatória no cruzamento CEIS/CNEP (`assert_non_accusatory_language`), explicitando no bloco de limitação que a existência de registro no CEIS/CNEP não comprova irregularidade automática (podendo haver decisão liminar suspensiva, abrangência restrita ao órgão sancionador ou exceção legal).

## 12. Critérios de Aceite
- **`AC-026`:** Conector ingere lote CGU CEIS/CNEP, mascara CPF e valida hashes SHA-256 corretamente.
- **`AC-027`:** Registros malformados ou sem data inicial são isolados em quarentena.
- **`AC-028`:** Regras `R-CROSS-CEIS-SANCTIONED-SUPPLIER` e `R-CROSS-AMENDMENT-EXECUTION-GAP` disparam sinais válidos com dupla evidência SHA-256.
- **`AC-029`:** Endpoint `GET /api/v1/sanctions` retorna registros curados com paginação e conformidade LGPD.

## 13. Dependências
- `SPEC-0001` (Lakehouse Storage & Provenance)
- `SPEC-0002` (Auditing Rules & Laya Engine)
- `SPEC-0003` (API Contracts & Security RLS)

## 14. Riscos e Limitações
- Falsos positivos por alteração cadastral de CNPJ ou decisões judiciais liminares não refletidas imediatamente na base pública. Mitigado pela exigência de triagem interna e camada epistêmica de limitação.

## 15. Estratégia de Testes e Test Anchors
Os testes unitários e de integração encontram-se em:
- `tests/test_cross_source_sanctions.py::TestCrossSourceSanctionsAndDivergence::test_ceis_cnep_connector_validates_masks_cpf_and_quarantines_invalid`
- `tests/test_cross_source_sanctions.py::TestCrossSourceSanctionsAndDivergence::test_cross_source_ceis_rule_detects_active_cnpj_sanction_with_dual_sha256`
- `tests/test_cross_source_sanctions.py::TestCrossSourceSanctionsAndDivergence::test_cross_source_ceis_rule_ignores_expired_sanction_or_masked_cpf_homonym`
- `tests/test_cross_source_sanctions.py::TestCrossSourceSanctionsAndDivergence::test_amendment_execution_divergence_rule_flags_discrepancy`
- `tests/test_cross_source_sanctions.py::TestCrossSourceSanctionsAndDivergence::test_lakehouse_and_api_sanctions_endpoint_roundtrip`

## 16. Questões Pendentes
Nenhuma.
