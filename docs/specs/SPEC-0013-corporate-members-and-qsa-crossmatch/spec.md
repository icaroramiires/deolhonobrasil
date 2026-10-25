# SPEC-0013 — Cruzamento com Quadro de Sócios e Administradores (QSA/Receita Federal): Sócios Comuns em Contratações e Doações Eleitorais de Pessoas Físicas

## 1. Identificador e Título
- **Identificador:** SPEC-0013
- **Título:** Cruzamento com Quadro de Sócios e Administradores (QSA/Receita Federal): Sócios Comuns em Contratações e Doações Eleitorais de Pessoas Físicas

## 2. Status e Versão
- **Status:** Verificado
- **Versão:** 1.0.0

## 3. Problema e Motivação
A legislação brasileira proíbe doações eleitorais por pessoas jurídicas (Lei 13.165/2015), o que frequentemente estimula a análise de doações de pessoas físicas vinculadas ao quadro societário (QSA) de empresas contratadas pelo poder público. Além disso, a Lei 14.133/2021 veda empresas com sócios administradores comuns em contratações concorrentes de forma vedada. O SPEC-0013 estabelece o rigor técnico, os modelos de dados e as regras determinísticas para a ingestão e cruzamento de sócios e administradores com dados de licitações, contratos e campanhas eleitorais.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Ingerir e modelar de forma imutável o Quadro de Sócios e Administradores (QSA) da Receita Federal.
- Implementar regras de auditoria determinísticas para detecção de sócios comuns em órgãos contratantes e correlação com doações eleitorais de pessoas físicas a mandatários.
- Garantir mascaramento absoluto de CPF (LGPD) e rastreabilidade por SHA-256.

### Não-Objetivos
- Inferir dolo, culpa ou ilegalidade automática com base na mera participação societária ou doação dentro dos limites legais.

## 5. Atores e Permissões
- `public_reader`: Acesso aos achados publicados (após triagem).
- `auditor_user`: Visualização de evidências completas e relatórios de reconciliação.
- `system_etl`: Ingestão automatizada de dados da Receita Federal e TSE.

## 6. Fluxos Principais
1. Ingestão e normalização de registros do QSA (`CuratedCorporateMemberRecord`).
2. Execução das regras de cruzamento: `evaluate_qsa_shared_partner_rule` e `evaluate_qsa_individual_donor_rule`.
3. Emissão de sinais padronizados com proveniência e restrição de linguagem não-acusatória.

## 7. Cenários Alternativos e de Erro
- Sócios com CPF mascarado sem identificação unívoca.
- Empresas de ramos distintos em contratações separadas.
- Homonímia pura tratada por chave natural composta e CNPJ.

## 8. Requisitos Funcionais
- **`FR-028`**: Ingestão, validação e modelagem imutável do Quadro de Sócios e Administradores (`CuratedCorporateMemberRecord` / `OfficialSource.RECEITA_FEDERAL_CNPJ`) com proveniência `SHA-256`, qualificação do sócio e mascaramento LGPD (`***.XXX.XXX-**`).
- **`FR-029`**: O motor de auditoria deve implementar as regras determinísticas:
  - `evaluate_qsa_shared_partner_rule` (`R-CROSS-QSA-SHARED-PARTNER`): detecção de sócios administradores comuns entre empresas contratadas pelo mesmo órgão.
  - `evaluate_qsa_individual_donor_rule` (`R-CROSS-QSA-DONOR-SUPPLIER`): detecção quando sócio (QSA) de fornecedor contratado pelo mandatário efetuou doação eleitoral declarada de pessoa física para a campanha do mandatário (TSE).

## 9. Requisitos Não Funcionais
- **`NFR-016`**: Chave composta para desambiguação de sócios e vedação a falso positivo por homonímia pura de CPF mascarado, exigindo correspondência por chave natural e CNPJ vinculado.

## 10. Regras de Negócio e Dados
- **`DATA-015`**: Modelo `CuratedCorporateMemberRecord` imutável (`frozen=True`) e proveniência estrita.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-016`**: Vedação absoluta a linguagem acusatória (`assert_non_accusatory_language`), explicitando expressamente no bloco de limitações que a participação de sócios em múltiplas empresas e doações de campanha de pessoa física dentro do teto legal de 10% dos rendimentos constituem atos amparados em lei, não havendo presunção de irregularidade.

## 12. Critérios de Aceite
- **`AC-050`**: `CuratedCorporateMemberRecord` valida campos obrigatórios, preserva mascaramento de CPF e calcula chave natural com SHA-256.
- **`AC-051`**: `evaluate_qsa_shared_partner_rule` detecta sócios administradores comuns entre empresas contratadas pelo mesmo órgão e emite sinal com proveniência combinada.
- **`AC-052`**: `evaluate_qsa_individual_donor_rule` detecta quando sócio de fornecedor contratado doou para campanha eleitoral do mandatário e emite sinal com tripla proveniência (RFB + Contrato + TSE).
- **`AC-053`**: Regras ignoram empresas sem sobreposição de sócios ou fornecedores cujos sócios não efetuaram doação ao mandatário.

## 13. Dependências
- `SPEC-0001`, `SPEC-0002`, `SPEC-0003`, `SPEC-0009`, `SPEC-0012`.

## 14. Riscos e Limitações
- Possibilidade de homonímias parciais mitigada por chaves naturais compostas e verificação de CPF mascarado.
- Esclarecimento explícito de que doações de campanha e participações societárias são lícitas per se.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_qsa_and_corporate_members.py::TestCorporateMembersAndQSACrossmatch::test_corporate_member_model_validation_and_masking`
- `tests/test_qsa_and_corporate_members.py::TestCorporateMembersAndQSACrossmatch::test_qsa_shared_partner_rule_detects_common_partners_in_same_organ`
- `tests/test_qsa_and_corporate_members.py::TestCorporateMembersAndQSACrossmatch::test_qsa_individual_donor_rule_detects_partner_donation_to_mandatario`
- `tests/test_qsa_and_corporate_members.py::TestCorporateMembersAndQSACrossmatch::test_qsa_rules_ignore_unrelated_companies_or_non_donors`

## 16. Questões Pendentes
- Nenhuma.
