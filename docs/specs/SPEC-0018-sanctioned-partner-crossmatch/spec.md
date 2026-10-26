# SPEC-0018 — Burla à Sanção Administrativa e Impedimento de Licitar: Identificação de Sócios e Administradores (QSA) de Fornecedores Contratados com Sanção Vigente no CEIS/CNEP

## 1. Identificador e Título
- **ID:** `SPEC-0018`
- **Título:** Burla à Sanção Administrativa e Impedimento de Licitar: Identificação de Sócios e Administradores (QSA) de Fornecedores Contratados com Sanção Vigente no CEIS/CNEP

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.0.0`
- **Data:** 2026-10-26

## 3. Problema e Motivação
A criação de empresas sucessoras ou a utilização de empresas com os mesmos sócios/administradores para disputar contratações e receber recursos públicos visando burlar sanções administrativas ativas aplicadas pela Administração Pública — declaradas no CEIS e CNEP — constitui tipologia reiteradamente censurada pelo TCU nos Acórdãos 2.218/2012, 1.028/2014, 1.986/2016 e 1.637/2021-Plenário e vedada pelo Art. 14, § 1º, II e Art. 160 da Lei nº 14.133/2021.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Cruzar dados do QSA (Quadro de Sócios e Administradores) de fornecedores contratados ou beneficiários de despesas públicas com o cadastro unificado de sanções (CEIS/CNEP).
- Emitir sinais de auditoria com proveniência tripla e classificação rigorosa.

### Não-Objetivos
- Executar desconsideração automática da personalidade jurídica em âmbito judicial ou administrativo.

## 5. Atores e Permissões
- `public_reader`: Acesso apenas a dados agregados e validados por RLS.
- `auditor_analyst`: Acesso aos dossiês em `EM_TRIAGEM_INTERNA`.

## 6. Fluxos Principais
1. Ingestão de Contratos/Despesas e QSA da RFB.
2. Ingestão de Registros CEIS/CNEP.
3. Execução da regra `evaluate_sanctioned_partner_supplier_rule`.
4. Emissão de `AuditSignal` em caso de correspondência ativa.

## 7. Cenários Alternativos e de Erro
- Sanções expiradas antes da contratação.
- Homonímia de CPF mascarado sem nome coincidente.
- Fornecedores com sócios sem impedimentos.
- Empresas sem contratações vigentes.

## 8. Requisitos Funcionais
- `FR-038`: O pipeline e o motor de auditoria devem realizar o cruzamento sistemático entre o Quadro de Sócios e Administradores (`CuratedCorporateMemberRecord` / RFB) de fornecedores contratados (`CuratedPublicContract`) ou recebedores de pagamentos públicos (`CuratedPublicExpense`) e o cadastro de sanções ativas (`CuratedSanctionRecord` / CGU CEIS/CNEP).
- `FR-039`: O motor de auditoria deve implementar a regra determinística `evaluate_sanctioned_partner_supplier_rule` (`R-CROSS-SANCTIONED-PARTNER`), emitindo `AuditSignal` com proveniência tripla `SHA-256` (Sanção + QSA + Contrato/Despesa), gravidade calibrada e classificação epistêmica `CROSS_SOURCE_DIVERGENCE`.

## 9. Requisitos Não Funcionais
- `NFR-021`: Algoritmo de cruzamento e filtragem temporal em memória em $O(N + M)$, assegurando correspondência temporal (`start_date <= contract_date <= end_date` ou `end_date is None`) e proteção anti-homonímia.

## 10. Regras de Negócio e Dados
- `DATA-020`: Encadeamento estrito de proveniência (`provenance_hashes`) agregando a união dos hashes `SHA-256` da sanção, do sócio QSA e do instrumento de contrato ou despesa pública.

## 11. Requisitos de Segurança e Privacidade
- `SEC-021`: Vedação absoluta a termos acusatórios (`assert_non_accusatory_language`), explicitando expressamente no bloco de limitações que, nos termos do Art. 14, § 1º, II e Art. 160 da Lei nº 14.133/2021, a extensão dos efeitos da sanção a pessoa jurídica com sócios comuns depende de procedimento formal prévio de desconsideração da personalidade jurídica, comprovação de poderes de gerência ou identidade fática, admitindo exceções legais (como sócio minoritário sem ingerência administrativa ou decisões judiciais de efeito suspensivo).

## 12. Critérios de Aceite
- `AC-070`: `evaluate_sanctioned_partner_supplier_rule` detecta quando sócio ou administrador de empresa contratada possui sanção ativa no CEIS/CNEP na data do contrato ou despesa e emite sinal de auditoria com proveniência tripla.
- `AC-071`: `evaluate_sanctioned_partner_supplier_rule` ignora sanções expiradas antes da data do contrato ou da emissão da despesa (`end_date < contract_date`).
- `AC-072`: `evaluate_sanctioned_partner_supplier_rule` ignora falso positivo por homonímia pura de CPF mascarado (`***.XXX.XXX-**`) sem correspondência de nome sanitizado.
- `AC-073`: `evaluate_sanctioned_partner_supplier_rule` não emite sinal para fornecedores cujos sócios não possuem sanções vigentes ou para sócios sem relação com a contratação.

## 13. Dependências
- `SPEC-0001`, `SPEC-0002`, `SPEC-0003`, `SPEC-0007`, `SPEC-0013`.

## 14. Riscos e Limitações
- Possibilidade de homonímias parciais tratadas por rigorosa checagem de nome e CPF mascarado. Necessidade de devido processo legal prévio antes de imputação jurídica definitiva.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_sanctioned_partner_crossmatch.py::TestSanctionedPartnerCrossmatchRules::test_sanctioned_partner_rule_detects_active_sanction_in_qsa`
- `tests/test_sanctioned_partner_crossmatch.py::TestSanctionedPartnerCrossmatchRules::test_sanctioned_partner_rule_ignores_expired_sanction`
- `tests/test_sanctioned_partner_crossmatch.py::TestSanctionedPartnerCrossmatchRules::test_sanctioned_partner_rule_ignores_masked_cpf_homonym_without_name_match`
- `tests/test_sanctioned_partner_crossmatch.py::TestSanctionedPartnerCrossmatchRules::test_sanctioned_partner_rule_ignores_unrelated_suppliers`

## 16. Questões Pendentes
- Nenhuma.
