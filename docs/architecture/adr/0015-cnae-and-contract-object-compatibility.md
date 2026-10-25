# ADR 0015 — Incompatibilidade entre Atividade Econômica Declarada (CNAE/Receita Federal) e Objeto de Contratações Públicas

## Status
Aprovado

## Data
2026-10-25

## Contexto
No ecossistema de compras públicas brasileiras (regido pela Lei nº 14.133/2021 e fiscalizado por TCU, CGU e Tribunais de Contas Estaduais), uma das tipologias de fraude e desvio mais severas e recorrentes consiste na contratação de pessoas jurídicas cujo ramo de atividade econômica formal perante a Receita Federal do Brasil (RFB) — expresso na Classificação Nacional de Atividades Econômicas (CNAE) — não guarda nenhuma relação de pertinência temática com o objeto adjudicado.

Exemplos típicos apontados em relatórios de auditoria governamentais envolvem:
1. Empresas com atividade única de comércio varejista (ex.: papelarias, confecções ou armarinhos) vencendo certames para execução de obras de engenharia rodoviária, terraplanagem ou reformas hospitalares complexas;
2. Empresas com CNAE restrito a serviços administrativos ou reprografia recebendo contratos vultosos para locação de aeronaves ou desenvolvimento de software de alta densidade técnica;
3. Empresas registradas exclusivamente no setor primário (agropecuária) contratadas para prestação de serviços de segurança armada ou saúde especializada.

O desafio arquitetural e epistêmico consiste em:
- Estruturar a modelagem cadastral de pessoas jurídicas para registrar de forma normalizada tanto o CNAE principal (`main_cnae_code`) quanto os códigos de CNAE secundários (`secondary_cnae_codes`) com 7 dígitos numéricos estritos (`\d{7}`);
- Implementar uma matriz de compatibilidade setorial determinística em memória baseada nas divisões oficiais da CNAE (os dois primeiros dígitos da subclasse, de 01 a 99) e palavras-chave semânticas essenciais do objeto contratual (`CuratedPublicContract.contract_object`), operando em $O(1)$ sem dependência de APIs externas de classificação;
- Assegurar que, se **qualquer** código secundário da empresa pertencer à divisão exigida pelo objeto, a contratação é considerada compatível, evitando falsos positivos grosseiros em empresas multisetoriais;
- Preservar rigorosamente a vedação a termos acusatórios (`assert_non_accusatory_language`), explicitando no bloco de limitações que o código CNAE tem finalidade prioritariamente fiscal/estatística e que a empresa pode ter capacidade técnica pretérita, atestados de capacidade ou estar em fase de atualização cadastral perante a Junta Comercial.

## Decisão
1. **Modelagem Cadastral e Normalização:**
   - Em `CuratedCompanyRegistrationRecord` (`src/deolhonobrasil/pipeline/models.py`), incluir:
     - `main_cnae_code`: string de 7 dígitos numéricos (`\d{7}`);
     - `secondary_cnae_codes`: tupla imutável de strings de 7 dígitos numéricos (`tuple[str, ...]`);
     - Validação estrita via método de fábrica `create_validated()`.
2. **Matriz de Incompatibilidade Setorial de Alto Risco:**
   - Mapear termos-chave de alta especificidade de contratações públicas para suas divisões CNAE legítimas:
     - Obras e Engenharia Civil (`"pavimentacao"`, `"terraplanagem"`, `"drenagem"`, `"reforma predial"`, `"construcao"`): Divisões `41` (Construção de edifícios), `42` (Obras de infraestrutura) e `43` (Serviços especializados para construção);
     - Tecnologia da Informação (`"software"`, `"sistema de informacao"`, `"computacao em nuvem"`, `"desenvolvimento web"`): Divisões `62` (Atividades dos serviços de tecnologia da informação) e `63` (Atividades de prestação de serviços de informação);
     - Transporte e Locação de Aeronaves / Embarcações (`"aeronave"`, `"helicoptero"`, `"fretamento aereo"`): Divisões `51` (Transporte aéreo) e `77` (Aluguéis não imobiliários e gestão de ativos intangíveis não financeiros);
     - Saúde e Serviços Médicos (`"medico"`, `"hospitalar"`, `"laboratorial"`, `"enfermagem"`): Divisão `86` (Atividades de atenção à saúde humana).
3. **Regra Determinística de Auditoria:**
   - Criar `evaluate_cnae_contract_incompatibility_rule` (`R-CORP-CNAE-INCOMPATIBLE`):
     - Filtra contratos com valor $\ge$ R$ 50.000,00;
     - Analisa o texto do objeto contratual; se o objeto demandar divisão setorial específica e nem o CNAE principal nem nenhum CNAE secundário cobrir essa divisão (e o CNAE da empresa for de setor antagônico, como comércio varejista ou serviços gerais não afins), emite sinal de anomalia;
     - Classificação epistêmica: `EpistemicClassification.STATISTICAL_ANOMALY`;
     - `requires_human_review = True`.
4. **Governança Editorial e Direitos:**
   - O sumário de limitações esclarece expressamente a hipótese de conformidade: objeto social registrado em estatuto/contrato social que pode ser mais amplo que o cadastro CNAE resumido da RFB, além do Direito de Resposta para apresentação de Atestado de Capacidade Técnica (ACT).

## Consequências
### Positivas
- Provê cobertura direta a uma das mais emblemáticas vulnerabilidades de compras públicas brasileiras (empresas de fachada com desvio de atividade).
- Respeito integral aos CNAEs secundários evita a armadilha de falsos positivos em empresas diversificadas.
- Execução determinística em memória e testes unitários 100% reproduzíveis no Python stdlib.

### Negativas / Mitigações
- Descrições de objetos contratuais extremamente sintéticas ou ambíguas no edital público podem impedir a extração da divisão setorial requerida; nestes casos, a regra não emite falso alerta (conservadorismo estatístico).
