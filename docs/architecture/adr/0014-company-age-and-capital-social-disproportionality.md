# ADR 0014 — Indicadores Cadastrais de Risco Operacional: Empresas Recém-Abertas e Capital Social Desproporcional em Contratações Públicas

## Status
Aprovado

## Data
2026-10-25

## Contexto
No controle externo de compras públicas no Brasil (TCU, CGU, Tribunais de Contas Estaduais e Ministério Público), duas das tipologias mais frequentes de empresas de fachada ("empresas-fantasma") e de contratações temerárias envolvem dados cadastrais básicos da Receita Federal do Brasil (RFB):
1. **Empresas Recém-Constituídas:** Pessoas jurídicas formalmente abertas semanas ou poucos meses antes da publicação de editais de licitação vultosos ou de dispensas emergenciais de licitação, vencendo contratos expressivos sem possuir histórico operacional prévio ou capacidade instalada consolidada.
2. **Capital Social Desproporcional:** Pessoas jurídicas constituídas com capital social integralizado irrisório (ex.: R$ 1.000,00 ou R$ 5.000,00) que celebram contratos de centenas de milhares ou milhões de reais com o poder público. Embora o art. 67, § 4º da Lei nº 14.133/2021 limite a exigência editalícia de capital social a no máximo 10% do valor estimado da contratação, descompassos extremos (razão contrato/capital superior a 50x ou 100x) configuram sinal objetivo de alto risco de inadimplemento contratual e incapacidade econômico-financeira.

O desafio técnico e epistêmico consiste em:
- Modelar de forma imutável os atributos cadastrais de empresas (`opening_date`, `share_capital_brl`, `legal_nature`, `registration_status`) a partir da base aberta oficial do CNPJ da RFB (`OfficialSource.RECEITA_FEDERAL_CNPJ`);
- Calcular a diferença em dias entre a data de constituição da empresa e a data de contratação ou primeira despesa (`delta_days = (contract_date - opening_date).days`);
- Calcular a razão entre o montante contratado/despendido e o capital social declarado (`ratio = contract_amount / share_capital`);
- Respeitar rigorosamente a separação epistêmica em 3 camadas e a vedação à linguagem acusatória (`assert_non_accusatory_language`), explicitando nas limitações que empresas recém-abertas podem reunir profissionais experientes e que capitais reduzidos são admissíveis em atividades intelectuais e de serviços sem exigir bens físicos intensivos.

## Decisão
1. **Modelo de Dados Imutável:**
   - Criar `CuratedCompanyRegistrationRecord` em `src/deolhonobrasil/pipeline/models.py` (`frozen=True`, `slots=True`):
     - `cnpj_normalized`: CNPJ de 14 dígitos validado;
     - `corporate_root_cnpj`: raiz de 8 dígitos;
     - `legal_name`: razão social limpa e sanitizada;
     - `trade_name`: nome fantasia (se houver);
     - `opening_date`: data de abertura cadastral na Receita Federal (`date`);
     - `share_capital_brl`: capital social integralizado em `Decimal`;
     - `cnae_main_code`: código de atividade econômica principal;
     - `registration_status`: situação cadastral (ex.: ATIVA, BAIXADA, SUSPENSA);
     - `provenance`: `ProvenanceMetadata` com `OfficialSource.RECEITA_FEDERAL_CNPJ`.
2. **Regras Determinísticas de Auditoria:**
   - `evaluate_recent_company_creation_rule` (`R-CORP-RECENT-CREATION`):
     - Identifica despesas ou contratos com valor relevante ($\ge$ R$ 50.000,00) firmados com empresas cuja data de abertura seja inferior a 180 dias da data de emissão/celebração.
     - Emite `AuditSignal` com proveniência combinada (RFB + Contrato/Despesa), métrica `company_age_days_at_contract` e classificação `EpistemicClassification.STATISTICAL_ANOMALY`.
   - `evaluate_low_capital_outlier_rule` (`R-CORP-LOW-CAPITAL-OUTLIER`):
     - Identifica contratos públicos ou gastos agregados relevantes ($\ge$ R$ 100.000,00) com empresas cujo capital social integralizado resulte em razão contratada/capital $\ge 50.00$ (cinquenta vezes).
     - Protege contra divisão por zero e descarta empresas com capital social nulo ou negativo.
     - Emite `AuditSignal` com métrica `contract_to_share_capital_ratio` e classificação `EpistemicClassification.STATISTICAL_ANOMALY`.
3. **Governança Epistêmica e Editorial:**
   - Ambas as regras exigem revisão humana (`requires_human_review=True`).
   - O sumário de limitações esclarece os cenários legais de conformidade: startups de tecnologia, consultorias de inteligência ou empresas formadas por consórcios de especialistas que operam regularmente com estruturas enxutas.

## Consequências
### Positivas
- Provê alertas cadastrais objetivos de risco operacional amplamente alinhados aos manuais de fiscalização do TCU e CGU.
- Reutiliza a fonte de proveniência `OfficialSource.RECEITA_FEDERAL_CNPJ` consolidada na SPEC-0013.
- Processamento determinístico em Python puro sem dependência de bibliotecas externas.

### Negativas / Mitigações
- Empresas que passam por reorganização societária ou cisão podem gerar novos CNPJs embora guardem acervo técnico pregresso; o bloco de limitações epistêmicas e o Direito de Resposta lado a lado mitigam eventuais distorções de contexto.
