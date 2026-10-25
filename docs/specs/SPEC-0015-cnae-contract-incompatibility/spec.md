# SPEC-0015 — Incompatibilidade entre Atividade Econômica Declarada (CNAE/Receita Federal) e Objeto de Contratações Públicas

## 1. Identificador e Título
- **ID:** `SPEC-0015`
- **Título:** Incompatibilidade entre Atividade Econômica Declarada (CNAE/Receita Federal) e Objeto de Contratações Públicas
- **Área:** Motor de Auditoria e Integridade Corporativa (`donb.audit`)

---

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.0.0`
- **Data de Atualização:** 2026-10-25

---

## 3. Problema e Motivação
A contratação de empresas cuja Classificação Nacional de Atividades Econômicas (CNAE) não guarda aderência com o objeto do certame é uma das tipologias clássicas de empresas de fachada ou desvio de finalidade apontadas por TCU e CGU. Exemplos incluem empresas de comércio varejista de vestuário contratadas para obras de engenharia pesada ou fornecimento de equipamentos médicos hospitalares de alta complexidade. 

O sistema *De Olho no Brasil* necessita de uma regra determinística e auditável para verificar automaticamente a compatibilidade entre os ramos econômicos declarados (principal e secundários) de uma empresa junto à Receita Federal e o objeto descrito em contratos públicos firmados com a administração.

---

## 4. Objetivos e Não-Objetivos

### Objetivos
- Ingerir e modelar de forma imutável e verificada por SHA-256 os dados de registro e CNAEs de pessoas jurídicas (`CuratedCompanyRegistrationRecord`).
- Implementar a regra de auditoria determinística `evaluate_cnae_contract_incompatibility_rule` (`R-CORP-CNAE-INCOMPATIBLE`).
- Respeitar estritamente a separação epistêmica, evitando linguagem acusatória e contextualizando o escopo tributário e estatístico do CNAE.

### Não-Objetivos
- Substituir a análise fiscal humana ou emitir sanções automáticas (o sistema opera em triagem interna `EM_TRIAGEM_INTERNA`).
- Julgar a capacidade financeira ou balanços contábeis da empresa (escopo de outras especificações).

---

## 5. Atores e Permissões
- **Auditor Automatizado (`system`):** Executa o motor `Laya` e aplica regras de auditoria sobre contratos e cadastros.
- **Analista Humano (`human_analyst`):** Revisa achados gerados pelo motor antes de qualquer publicação pública.
- **Leitor Público (`public_reader`):** Acessa apenas dados auditados e aprovados após triagem institucional.

---

## 6. Fluxos Principais
1. **Ingestão Cadastral:** O pipeline ingestor coleta dados de CNPJ da Receita Federal contendo o CNAE principal e lista de CNAEs secundários.
2. **Associação Contratual:** O contrato público é vinculado ao registro da empresa contratada.
3. **Avaliação Determinística:** O motor avalia o valor do contrato e compara as divisões do CNAE da empresa com o objeto/categoria exigida pelo contrato.
4. **Geração de Sinal:** Caso haja divergência material em contrato de valor relevante ($\ge R\$ 50.000,00$), um `AuditSignal` é emitido com status pendente de triagem.

---

## 7. Cenários Alternativos e de Erro
- **Múltiplos CNAEs secundários:** A empresa possui atividade principal atípica, mas um CNAE secundário cobre plenamente o objeto licitado (a regra descarta o sinal de incompatibilidade).
- **Objetos genéricos ou mistos:** Contratos com descrições amplas que exigem análise contextual suplementar.
- **Contratos de baixo valor:** Contratos com valor inferior a $R\$ 50.000,00$ são ignorados pela regra para evitar falsos positivos em pequenas despesas de pronta entrega.

---

## 8. Requisitos Funcionais
- **`FR-032`**: Ingestão, validação e modelagem imutável de dados de atividade econômica de pessoa jurídica (`CuratedCompanyRegistrationRecord` / `OfficialSource.RECEITA_FEDERAL_CNPJ`) incluindo código CNAE principal de 7 dígitos (`main_cnae_code`) e tupla de códigos secundários (`secondary_cnae_codes`).
- **`FR-033`**: O motor de auditoria deve implementar a regra determinística `evaluate_cnae_contract_incompatibility_rule` (`R-CORP-CNAE-INCOMPATIBLE`), comparando os setores/divisões CNAE cadastrados da empresa contratada com o objeto do contrato público (`CuratedPublicContract`) e emitindo `AuditSignal` quando houver incompatibilidade material entre o ramo econômico declarado e o objeto contratado (para contratos $\ge R\$ 50.000,00$).

---

## 9. Requisitos Não Funcionais
- **`NFR-018`**: Mapeamento setorial determinístico em memória em $O(1)$ por código de divisão CNAE (2 primeiros dígitos), sem dependência de serviços externos de taxonomia.

---

## 10. Regras de Negócio e Dados
- **`DATA-017`**: Códigos CNAE normalizados como strings numéricas de 7 dígitos (`\d{7}`) e proveniência estrita `OfficialSource.RECEITA_FEDERAL_CNPJ`.

---

## 11. Requisitos de Segurança e Privacidade
- **`SEC-018`**: Vedação absoluta a linguagem acusatória (`assert_non_accusatory_language`), explicitando no bloco de limitações que o código CNAE tem finalidade primordial tributária/estatística e que uma empresa pode desempenhar atividades atípicas correlatas ou estar em processo de alteração cadastral, não constituindo por si só indício de inidoneidade.

---

## 12. Critérios de Aceite
- **`AC-058`**: Modelo valida código CNAE principal e secundários de 7 dígitos numéricos e proveniência SHA-256.
- **`AC-059`**: `evaluate_cnae_contract_incompatibility_rule` detecta quando o objeto do contrato exige divisão econômica incompatível com o CNAE principal e secundários e emite sinal.
- **`AC-060`**: `evaluate_cnae_contract_incompatibility_rule` descarta o sinal se qualquer CNAE secundário cobrir a divisão exigida pelo objeto do contrato.
- **`AC-061`**: `evaluate_cnae_contract_incompatibility_rule` ignora contratos com valor abaixo de $R\$ 50.000,00$ ou cujo objeto seja plenamente compatível com o CNAE da empresa.

---

## 13. Dependências
- `SPEC-0001` (Arquitetura Geral e Ingestão de Dados)
- `SPEC-0002` (Motor de Auditoria e Sinais)
- `SPEC-0003` (Governança de Dados e Padrões de Criptografia SHA-256)
- `SPEC-0014` (Modelagem de Contratos Públicos e Licitações)

---

## 14. Riscos e Limitações
- **Falsos Positivos por Agrupamento Setorial:** Divisões amplas do CNAE podem agrupar atividades heterogêneas.
- **Atualização Cadastral Tardia:** Empresas podem atuar em novas frentes antes da formalização da alteração de CNAE na Receita Federal.

---

## 15. Estratégia de Testes e Test Anchors
Os testes unitários e de integração obrigatórios cobrindo esta especificação localizam-se em:
- `tests/test_cnae_contract_incompatibility.py::TestCnaeContractIncompatibilityRules::test_cnae_model_validation_and_code_normalization`
- `tests/test_cnae_contract_incompatibility.py::TestCnaeContractIncompatibilityRules::test_cnae_incompatibility_rule_detects_mismatch`
- `tests/test_cnae_contract_incompatibility.py::TestCnaeContractIncompatibilityRules::test_cnae_incompatibility_rule_respects_secondary_cnaes`
- `tests/test_cnae_contract_incompatibility.py::TestCnaeContractIncompatibilityRules::test_cnae_rule_ignores_compatible_or_low_value_contracts`

---

## 16. Questões Pendentes
- `Nenhuma.`
