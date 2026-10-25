# ADR 0016 — Conflito de Interesses e Impedimento Legal: Identificação de Agentes Públicos e Dirigentes no Quadro Societário de Fornecedores do Próprio Órgão

## Status
Aprovado

## Data
2026-10-25

## Contexto
No ordenamento jurídico brasileiro que rege a administração pública e as aquisições governamentais, o conflito de interesses entre a função pública e o benefício econômico privado em contratos públicos é expressamente vedado por normas de ordem pública e pela jurisprudência pacífica dos órgãos de controle externo:
1. **Lei nº 14.133/2021 (Nova Lei de Licitações e Contratos Administrativos), art. 9º, § 1º:**
   Veda a participação em licitação ou na execução de contrato, direta ou indiretamente, de dirigentes, servidores ou agentes públicos que mantenham vínculo técnico, econômico, comercial, trabalhista ou societário com a pessoa jurídica licitante ou contratada pelo órgão.
2. **Súmula TCU nº 269:**
   "É vedada a participação em licitação de empresa da qual participe sócio ou administrador que seja servidor público do órgão ou entidade licitante."
3. **Lei nº 8.112/1990 (Regime Jurídico Único dos Servidores Públicos Civis da União), art. 117, inciso X:**
   Proíbe ao servidor público participar da gerência ou administração de sociedade privada, ou exercer o comércio, exceto na qualidade de acionista, cotista ou comanditário (sem ingerência administrativa).

A identificação de tais situações constitui uma das trilhas de auditoria mais críticas para a integridade pública e prevenção ao desvio de finalidade. Contudo, cruzar bases cadastrais de agentes públicos com o Quadro de Sócios e Administradores (QSA) e contratos/despesas públicas impõe desafios técnicos e epistêmicos rigorosos:
- **Proteção à Privacidade e LGPD:** Servidores públicos têm CPFs públicos divulgados de forma mascarada (`***.XXX.XXX-**`) em portais de transparência; o mesmo ocorre no QSA aberto da Receita Federal;
- **Mitigação de Homonímia:** Nomes civis comuns geram elevado risco de colisão de homônimos se o cruzamento for puramente nominal ou ignorar a vinculação institucional;
- **Segregação Estrita por Órgão Contratante:** O impedimento legal do art. 9º, § 1º da Lei 14.133/2021 e da Súmula TCU nº 269 incide especificamente quando o servidor atua no **mesmo órgão** contratante (`organ_code` / `organ_cnpj`). Um servidor federal lotado em autarquia de educação que seja cotista de gráfica não comete impedimento direto ao vender para outro órgão municipal ou federal independente, salvo se houver influência direta ou gerência ilícita;
- **Vedação a Pré-julgamentos e Linguagem Não-Acusatória:** A condição de sócio cotista/acionista sem administração é admitida em lei; além disso, servidores podem estar em licença para tratar de interesses particulares (sem remuneração). Qualquer achado deve ser classificado como `CROSS_SOURCE_DIVERGENCE` e submetido à revisão humana interna (`EM_TRIAGEM_INTERNA`).

## Decisão
1. **Modelagem de Agentes Públicos (`CuratedPublicAgentRecord`):**
   - Criar `@dataclass(frozen=True, slots=True) class CuratedPublicAgentRecord` em `src/deolhonobrasil/pipeline/models.py`;
   - Incluir `agent_id`, `organ_code`, `organ_name`, `agent_name`, `agent_doc_masked` (formato `***.XXX.XXX-**`), `position_title`, `status`, `provenance: ProvenanceMetadata`;
   - Adicionar fonte `OfficialSource.PORTAL_TRANSPARENCIA_SERVIDORES = "PORTAL_TRANSPARENCIA_SERVIDORES"`;
   - Validar chave natural SHA-256 e método de fábrica `create_validated()`.

2. **Regra Determinística de Auditoria (`R-CROSS-PUBLIC-AGENT-SUPPLIER`):**
   - Implementar `evaluate_public_agent_supplier_crossmatch_rule` em `src/deolhonobrasil/audit/rules.py`;
   - Critérios cumulativos determinísticos de correspondência:
     a) Normalização e sanitização estrita de nomes (sem acentos, lowercase, stripped);
     b) Equivalência do CPF mascarado (`agent_doc_masked == member_doc_masked`);
     c) **Vínculo institucional estrito:** O órgão do agente público deve coincidir com o órgão contratante (`agent.organ_code == contract.organ_cnpj` ou `agent.organ_code == expense.organ_code`);
   - Se o órgão não for idêntico, a regra determinística **descarta o sinal**, evitando falsos positivos e ruído de conformidade fora do escopo legal de impedimento direto;
   - Agrega as proveniências SHA-256 de todas as fontes cruzadas (Servidor + QSA + Contrato/Despesa).

3. **Governança Epistêmica e Editorial:**
   - Classificação epistêmica obrigatória: `EpistemicClassification.CROSS_SOURCE_DIVERGENCE` (`DIVERGENCIA_ENTRE_REGISTROS`);
   - Requer triagem humana obrigatória (`requires_human_review = True`);
   - Aplicação rigorosa de `assert_non_accusatory_language`, detalhando expressamente no sumário de limitações as hipóteses legais de admissibilidade (participação societária como mero cotista sem gestão, licenças não remuneradas e necessidade de conferência presencial de homonímia).

## Consequências
### Positivas
- Automatiza a verificação de uma das exigências mais importantes da Lei 14.133/2021 e da Súmula TCU nº 269.
- Salvaguarda anti-homonímia multicritério (Nome + CPF Mascarado + Órgão de Lotação) elimina falsos positivos grosseiros.
- Rastreabilidade integral com tripla cadeia de proveniência criptográfica (Portal da Transparência + Receita Federal + PNCP/Despesas).
- Conformidade 100% com Python 3.14 stdlib e sem bibliotecas de terceiros.

### Negativas / Mitigações
- Servidores que possuam nomes abreviados de formas distintas nos portais podem não colidir perfeitamente pelo nome normalizado; nesses casos, a regra opta pelo conservadorismo epistêmico para priorizar precisão zero-falso-positivo em detrimento de cobertura ruidosa.
