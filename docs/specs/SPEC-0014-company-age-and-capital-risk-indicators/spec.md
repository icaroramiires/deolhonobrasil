# SPEC-0014 — Indicadores Cadastrais de Risco Operacional: Empresas Recém-Abertas e Capital Social Desproporcional em Contratações Públicas

**Identificador:** SPEC-0014  
**Status:** Verificado  
**Versão:** 1.0.0  
**Data de Atualização:** 2026-10-25  

---

## 1. Identificador e Título
`SPEC-0014 — Indicadores Cadastrais de Risco Operacional: Empresas Recém-Abertas e Capital Social Desproporcional em Contratações Públicas`

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.0.0`

## 3. Problema e Motivação
A contratação pública de empresas constituídas poucos dias ou semanas antes de certames licitatórios e o descompasso abissal entre o capital social integralizado/declarado e o volume de recursos públicos contratados constituem tipologias clássicas de risco operacional e indícios de vulnerabilidade apontados por órgãos de controle externo (como TCU e CGU). Tais padrões podem sinalizar o uso de empresas de fachada ou veículos recém-criados sem capacidade técnico-operacional real para executar contratos de grande vulto.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Modelar de forma imutável os registros cadastrais de pessoas jurídicas oriundos de fontes oficiais (`Receita Federal / CNPJ`).
- Implementar regras de auditoria determinísticas para identificar empresas recém-abertas em contratações de relevância e desproporção entre capital social e valor contratado.
- Garantir rastreabilidade estrita por meio de hashes `SHA-256` e conformidade com a política de linguagem não-acusatória.

### Não-Objetivos
- Emitir julgamento sumário de culpa, fraude ou ilicitude por parte das empresas auditadas.
- Substituir a análise fiscal ou a diligência prévia obrigatória dos pregoeiros e gestores públicos.

## 5. Atores e Permissões
- **Auditor Automatizado / Motor de Regras (`Laya`):** Executa as validações cadastrais em batch ou tempo de ingestão.
- **Analista de Controle Interno:** Revisa os achados gerados em ambiente restrito (`EM_TRIAGEM_INTERNA`).
- **Leitor Público (`public_reader`):** Acede apenas a dados agregados ou desprovidos de restrições de sigilo e triagem (conforme RLS).

## 6. Fluxos Principais
1. Ingestão do payload cadastral bruto da Receita Federal com extração de data de abertura e capital social.
2. Construção e validação do registro imutável `CuratedCompanyRegistrationRecord` com cálculo de hash `SHA-256`.
3. Execução das regras de auditoria `evaluate_recent_company_creation_rule` e `evaluate_low_capital_outlier_rule`.
4. Emissão de sinais estruturados de risco com separação epistêmica de camadas.

## 7. Cenários Alternativos e de Erro
- **Empresas antigas com alteração recente de filial ou razão social:** O sistema prioriza a data original de abertura cadastral (`opening_date`), evitando falsos positivos decorrentes de meras alterações cadastrais secundárias.
- **Empresas de intermediação ou corretagem com baixo capital admitido em lei:** O analista humano verifica se o modelo de negócio justifica o capital reduzido no âmbito da triagem.
- **Fornecedores com capital social não informado ou nulo:** O sistema trata de forma segura evitando divisão por zero e registra alerta de dado incompleto.

## 8. Requisitos Funcionais
- **`FR-030`:** Ingestão, validação e modelagem imutável de dados cadastrais de pessoa jurídica (`CuratedCompanyRegistrationRecord` / `OfficialSource.RECEITA_FEDERAL_CNPJ`) com proveniência `SHA-256`, data de abertura cadastral (`opening_date`), capital social em Decimal (`share_capital_brl`) e situação cadastral ativa.
- **`FR-031`:** O motor de auditoria deve implementar as regras determinísticas:
  - `evaluate_recent_company_creation_rule` (`R-CORP-RECENT-CREATION`): detecção de contratação ou despesa relevante (>= R$ 50.000,00) com empresa constituída há menos de 180 dias da data do contrato ou emissão do documento fiscal.
  - `evaluate_low_capital_outlier_rule` (`R-CORP-LOW-CAPITAL-OUTLIER`): detecção de contratação pública com valor desproporcional ao capital social declarado (razão montante_contratado / capital_social >= 50x, para contratos >= R$ 100.000,00 e capital social > 0).

## 9. Requisitos Não Funcionais
- **`NFR-017`:** Execução determinística em memória e ordenação temporal sem bibliotecas externas adicionais, com proteção contra divisão por zero em capital social nulo.

## 10. Regras de Negócio e Dados
- **`DATA-016`:** Modelo `CuratedCompanyRegistrationRecord` imutável (`frozen=True`) e proveniência estrita `OfficialSource.RECEITA_FEDERAL_CNPJ`.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-017`:** Vedação absoluta a linguagem acusatória (`assert_non_accusatory_language`), explicitando expressamente no bloco de limitações que a abertura recente de empresa para atender nichos de mercado emergentes e a constituição com capital inicial reduzido são práticas lícitas permitidas pelo Código Civil e pela Lei das S/A e Ltda., não constituindo por si só indício de inidoneidade.

## 12. Critérios de Aceite (`AC-054` a `AC-057`)
- **`AC-054`:** `CuratedCompanyRegistrationRecord` valida campos obrigatórios, data de abertura, capital social e calcula chave natural com SHA-256.
- **`AC-055`:** `evaluate_recent_company_creation_rule` detecta contratação acima do limiar com empresa de abertura recente (< 180 dias) e emite sinal com proveniência combinada.
- **`AC-056`:** `evaluate_low_capital_outlier_rule` detecta quando o valor contratado supera 50x o capital social declarado e emite sinal com indicador da razão calculada.
- **`AC-057`:** Regras ignoram empresas estabelecidas há mais de 180 dias e fornecedores com capital social compatível.

## 13. Dependências
- `SPEC-0001`, `SPEC-0002`, `SPEC-0003`, `SPEC-0009`, `SPEC-0013`

## 14. Riscos e Limitações
A abertura recente de empresa para atender nichos de mercado emergentes e a constituição com capital inicial reduzido são práticas lícitas permitidas pelo ordenamento jurídico brasileiro (Código Civil e Lei das S/A / Ltda.). Tais indicadores representam exclusivamente alertas estatísticos de risco operacional para triagem interna, não constituindo prova de inidoneidade ou irregularidade.

## 15. Estratégia de Testes e Test Anchors
Os testes automatizados devem ser implementados no arquivo `tests/test_company_age_and_capital_risk.py` cobrindo os seguintes test anchors:
- `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_company_registration_model_validation`
- `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_recent_company_creation_rule_detects_young_company`
- `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_low_capital_outlier_rule_detects_extreme_ratio`
- `tests/test_company_age_and_capital_risk.py::TestCompanyAgeAndCapitalRiskRules::test_rules_ignore_mature_companies_and_sound_capital`

## 16. Questões Pendentes
`Nenhuma.`
