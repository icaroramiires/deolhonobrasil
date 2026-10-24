# SPEC-0012 — Cruzamento entre Fornecedores Públicos e Doadores de Campanha Eleitoral (TSE)

## 1. Identificador e Título
- **ID:** `SPEC-0012`
- **Título:** Cruzamento entre Fornecedores Públicos e Doadores de Campanha Eleitoral (TSE)

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.0.0`

## 3. Problema e Motivação
A transparência nos gastos públicos de mandatos parlamentares e executivos exige a capacidade de cruzar despesas de custeio com doações declaradas à Justiça Eleitoral (TSE). A motivação é identificar e dar transparência quando fornecedores de bens e serviços contratados com verbas públicas (ex.: CEAP, CEAPS) constam simultaneamente como doadores de campanha para o mesmo mandatário ou chapa, garantindo proveniência estrita e estrita conformidade legal (evitando qualquer juízo de valor ou presunção de irregularidade).

## 4. Objetivos e Não-Objetivos
### Objetivos
- Modelar e persistir doações eleitorais declaradas de forma imutável (`CuratedElectoralDonation`).
- Implementar regra de cruzamento automatizado (`R-CROSS-ELECTORAL-DONOR-SUPPLIER`) entre despesas públicas e doadores.
- Garantir mascaramento de CPF (`***.XXX.XXX-**`) e proveniência estrita com hash `SHA-256`.

### Não-Objetivos
- Acusar ou julgar criminalmente doações legais declaradas ao TSE.
- Realizar cruzamentos baseados em CPFs de pessoas físicas comuns sem CNPJ corporativo (vedado por risco de homonímia).

## 5. Atores e Permissões
- **Auditor / Pesquisador:** Consulta os sinais gerados pelo cruzamento.
- **Sistema de ETL / Auditoria (Automated Engine):** Processa os arquivos do TSE e executa a regra `R-CROSS-ELECTORAL-DONOR-SUPPLIER`.

## 6. Fluxos Principais
1. **Ingestão de Doações:** O sistema ingere dados de doações eleitorais do TSE, mascara CPFs de pessoas físicas e gera registros imutáveis (`CuratedElectoralDonation`).
2. **Execução do Cruzamento:** O motor compara o CNPJ dos fornecedores públicos (`CuratedPublicExpense`) com o CNPJ dos doadores de campanha para o mesmo parlamentar.
3. **Emissão de Sinal:** Caso haja coincidência de CNPJ, um `AuditSignal` do tipo `CROSS_SOURCE_DIVERGENCE` é emitido com duplo `SHA-256`.

## 7. Cenários Alternativos e de Erro
- **Doações com CPF mascarado sem CNPJ de 14 dígitos:** Ignoradas pelo motor automatizado de cruzamento por CNPJ, prevenindo falsos positivos por homonímia (`NFR-015`).
- **Fornecedores de anos distintos sem correlação:** Nenhuma divergência ou sinal emitido.
- **Fornecedores sem doações registradas:** Nenhuma divergência ou sinal emitido.

## 8. Requisitos Funcionais
- **`FR-026`:** Ingestão, validação e modelagem imutável de doações eleitorais declaradas (`CuratedElectoralDonation` / `OfficialSource.TSE_ELEICOES`) com mascaramento de CPF e proveniência `SHA-256`.
- **`FR-027`:** O motor de auditoria deve implementar `evaluate_electoral_donor_supplier_crossmatch_rule` (`R-CROSS-ELECTORAL-DONOR-SUPPLIER`), cruzando despesas públicas (`CuratedPublicExpense`) com doações eleitorais declaradas do mesmo mandatário (`public_agent_id` ou identificador de candidatura) e emitindo `AuditSignal` com proveniência dupla `SHA-256` e classificação `CROSS_SOURCE_DIVERGENCE`.

## 9. Requisitos Não Funcionais
- **`NFR-015`:** Vedação estrita a falso positivo por homonímia de CPF mascarado (`***.XXX.XXX-**`): o cruzamento automatizado nominal aplica-se exclusivamente a CNPJ completo de 14 dígitos.

## 10. Regras de Negócio e Dados
- **`DATA-014`:** Modelo `CuratedElectoralDonation` imutável (`frozen=True`) e proveniência estrita.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-015`:** Vedação absoluta a linguagem acusatória (`assert_non_accusatory_language`), explicitando expressamente no bloco de limitações que doações de campanha declaradas à Justiça Eleitoral e fornecimento de bens/serviços de apoio parlamentar constituem atos legais e legítimos, não havendo presunção automática de irregularidade ou favorecimento indevido.

## 12. Critérios de Aceite
- **`AC-046`:** Modelo `CuratedElectoralDonation` valida campos obrigatórios, mascara CPF e calcula chave natural com SHA-256.
- **`AC-047`:** `evaluate_electoral_donor_supplier_crossmatch_rule` detecta quando um fornecedor (CNPJ) doou para a campanha do parlamentar e emite sinal com duplo SHA-256.
- **`AC-048`:** `evaluate_electoral_donor_supplier_crossmatch_rule` descarta doações com CPF mascarado para evitar falsos positivos por homonímia.
- **`AC-049`:** `evaluate_electoral_donor_supplier_crossmatch_rule` não emite sinal para fornecedores sem registro de doação para o mandatário.

## 13. Dependências
- `SPEC-0001`, `SPEC-0002`, `SPEC-0003`, `SPEC-0007`

## 14. Riscos e Limitações
Doações de campanha declaradas à Justiça Eleitoral e fornecimento de bens/serviços de apoio parlamentar constituem atos legais e legítimos previstos em lei. A correlação apresentada tem caráter puramente estatístico e de transparência, não havendo presunção automática de irregularidade, favorecimento indevido ou ilegalidade.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_electoral_campaign_donations.py::TestElectoralCampaignDonationsCrossmatch::test_electoral_donation_model_validation_and_masking`
- `tests/test_electoral_campaign_donations.py::TestElectoralCampaignDonationsCrossmatch::test_electoral_crossmatch_rule_detects_donor_as_supplier`
- `tests/test_electoral_campaign_donations.py::TestElectoralCampaignDonationsCrossmatch::test_electoral_crossmatch_rule_ignores_masked_cpf_homonym`
- `tests/test_electoral_campaign_donations.py::TestElectoralCampaignDonationsCrossmatch::test_electoral_crossmatch_rule_ignores_unrelated_supplier`

## 16. Questões Pendentes
Nenhuma.
