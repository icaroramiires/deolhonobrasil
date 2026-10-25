# SPEC-0016 — Conflito de Interesses e Impedimento Legal: Identificação de Agentes Públicos e Dirigentes no Quadro Societário de Fornecedores do Próprio Órgão (Art. 9º da Lei nº 14.133/2021)

## 1. Identificador e Título
- **ID:** `SPEC-0016`
- **Título:** Conflito de Interesses e Impedimento Legal: Identificação de Agentes Públicos e Dirigentes no Quadro Societário de Fornecedores do Próprio Órgão (Art. 9º da Lei nº 14.133/2021)

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.0.0`

## 3. Problema e Motivação
Nos termos do art. 9º, § 1º da Lei nº 14.133/2021 e Súmula TCU nº 269, é expressamente vedada a participação em licitações e contratações de pessoas jurídicas cujo quadro societário ou diretoria contenha agente público ou dirigente do próprio órgão contratante. O projeto "De Olho no Brasil" necessita de um mecanismo automatizado e auditável para cruzar bases de servidores públicos federais/estaduais/municipais com os quadros societários (QSA) de empresas contratadas e favorecidas por despesas públicas, mitigando riscos de conflito de interesses, nepotismo e desrespeito às vedações legais, sempre preservando o sigilo de dados pessoais conforme a LGPD e a estrita separação epistêmica entre achados preliminares e juízos de culpabilidade.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Ingestão, validação e modelagem imutável de registros de agentes públicos federais, estaduais e municipais.
- Implementação de motor de regras determinístico (`R-CROSS-PUBLIC-AGENT-SUPPLIER`) para cruzar a identidade do agente público com sócios/administradores de empresas fornecedoras do mesmo órgão.
- Emissão de sinais de auditoria com proveniência múltipla (`SHA-256`) e rastreabilidade total.
- Salvaguardas anti-homonímia e respeito absoluto às salvaguardas da LGPD (mascaramento de CPF) e proibição de linguagem acusatória.

### Não-Objetivos
- Emissão automatizada de penalidades, multas ou sanções administrativas (o sistema gera alertas de triagem humana).
- Investigação de sigilo bancário ou fiscal direto de pessoas físicas sem amparo em dados públicos abertos.

## 5. Atores e Permissões
- **Auditor Cidadão / Analista:** Acesso a visualizações agregadas e dossiês de triagem com dados sanitizados.
- **Sistema Automatizado de ETL/Auditoria:** Responsável pela execução das regras de cruzamento e geração de `AuditSignal`.

## 6. Fluxos Principais
1. **Ingestão de Servidores:** O pipeline ingere dados de servidores públicos (`Portal da Transparência` / fontes oficiais), aplicando mascaramento de CPF (`***.XXX.XXX-**`) e gerando hash `SHA-256`.
2. **Cruzamento de QSA e Contratos:** O motor de auditoria verifica se um sócio ou administrador de uma empresa contratada ou favorecida por despesa possui vínculo ativo como agente público no mesmo órgão contratante.
3. **Emissão de Sinal:** Caso confirmado o vínculo no mesmo órgão, emite-se um `AuditSignal` do tipo `CROSS_SOURCE_DIVERGENCE` em status `EM_TRIAGEM_INTERNA`.

## 7. Cenários Alternativos e de Erro
- **Homonímia de CPF mascarado ou nomes comuns:** Tratado por correspondência cumulativa rigorosa de CPF mascarado, nome sanitizado e código do órgão.
- **Servidor lotado em órgão diferente:** O motor descarta o sinal se `agent.organ_code != contract.organ_cnpj`.
- **Participação permitida como mero cotista:** Casos em que a legislação admita participação societária sem gerência (ou licença sem vencimentos) são destacados no bloco de limitações e notas explicativas do dossiê.

## 8. Requisitos Funcionais
- **`FR-034`:** Ingestão, validação e modelagem imutável de registros de agentes públicos e servidores (`CuratedPublicAgentRecord` / `OfficialSource.PORTAL_TRANSPARENCIA_SERVIDORES`) com mascaramento LGPD de CPF (`***.XXX.XXX-**`), proveniência `SHA-256`, vínculo de órgão (`organ_code`, `organ_name`), cargo e situação funcional.
- **`FR-035`:** O motor de auditoria deve implementar a regra determinística `evaluate_public_agent_supplier_crossmatch_rule` (`R-CROSS-PUBLIC-AGENT-SUPPLIER`), cruzando os registros de agentes públicos com os sócios/administradores (QSA) de empresas contratadas (`CuratedPublicContract`) ou favorecidas por despesas (`CuratedPublicExpense`) do próprio órgão (`agent.organ_code == contract.organ_cnpj` ou `agent.organ_code == expense.organ_code`), emitindo `AuditSignal` com proveniência múltipla `SHA-256` e classificação `CROSS_SOURCE_DIVERGENCE`.

## 9. Requisitos Não Funcionais
- **`NFR-019`:** Salvaguarda anti-homonímia determinística em memória exigindo correspondência cumulativa de nome sanitizado, CPF mascarado e identidade institucional do órgão contratante.

## 10. Regras de Negócio e Dados
- **`DATA-018`:** Modelo `CuratedPublicAgentRecord` imutável (`frozen=True`) e proveniência estrita `OfficialSource.PORTAL_TRANSPARENCIA_SERVIDORES`.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-019`:** Vedação absoluta a termos acusatórios (`assert_non_accusatory_language`), explicitando expressamente no bloco de limitações que a legislação admite participação como cotista/acionista sem gerência (art. 117, X da Lei 8.112/90), eventuais cessões funcionais ou licenças sem vencimentos, exigindo apuração preliminar antes de conclusões sancionatórias.

## 12. Critérios de Aceite
- **`AC-062`:** `CuratedPublicAgentRecord` valida campos obrigatórios, preserva mascaramento de CPF e calcula chave natural com SHA-256.
- **`AC-063`:** `evaluate_public_agent_supplier_crossmatch_rule` detecta quando agente público é sócio de empresa contratada pelo seu próprio órgão e emite sinal com tripla proveniência (Servidor + QSA + Contrato/Despesa).
- **`AC-064`:** `evaluate_public_agent_supplier_crossmatch_rule` descarta o sinal caso o agente público pertença a órgão contratante distinto.
- **`AC-065`:** `evaluate_public_agent_supplier_crossmatch_rule` descarta o sinal para sócios sem correspondência funcional.

## 13. Dependências
- `SPEC-0001` (Arquitetura Geral de Ingestão e Provedores de Dados)
- `SPEC-0002` (Motor de Auditoria e Sinais `AuditSignal`)
- `SPEC-0003` (Padrões de Governança e LGPD)
- `SPEC-0013` (Modelagem de Contratos e QSA de Fornecedores)
- `SPEC-0014` (Modelagem de Execução Orçamentária e Despesas)

## 14. Riscos e Limitações
- Possibilidade de homonímias parciais caso fontes primárias apresentem dados cadastrais incompletos.
- Necessidade de verificação humana (triagem) para distinguir sócios administradores de meros investidores minoritários sem poder de gestão.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_public_agent_supplier_crossmatch.py::TestPublicAgentSupplierCrossmatchRules::test_public_agent_model_validation_and_masking`
- `tests/test_public_agent_supplier_crossmatch.py::TestPublicAgentSupplierCrossmatchRules::test_public_agent_supplier_rule_detects_conflict_in_same_organ`
- `tests/test_public_agent_supplier_crossmatch.py::TestPublicAgentSupplierCrossmatchRules::test_public_agent_supplier_rule_ignores_different_organ`
- `tests/test_public_agent_supplier_crossmatch.py::TestPublicAgentSupplierCrossmatchRules::test_public_agent_supplier_rule_ignores_unrelated_members`

## 16. Questões Pendentes
- Nenhuma.
