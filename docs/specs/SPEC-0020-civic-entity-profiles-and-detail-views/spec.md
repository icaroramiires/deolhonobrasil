# SPEC-0020 — Perfis Cívicos de Entidades (Fornecedor, Mandatário e Órgão), Modais de Detalhe P0 (Despesa, Contrato e Análise) e Linha do Tempo de Aditivos

## 1. Identificador e Título
- **ID:** `SPEC-0020`
- **Título:** Perfis Cívicos de Entidades (Fornecedor, Mandatário e Órgão), Modais de Detalhe P0 (Despesa, Contrato e Análise) e Linha do Tempo de Aditivos

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.0.0`

## 3. Problema e Motivação
Apresentação detalhada e contextualizada das entidades públicas e seus instrumentos de despesa e contratação, materializando os perfis P1 e detalhes P0 especificados no handoff de design em `docs/design/screens.md` e `flows.md`.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Expor perfis completos de Fornecedores, Mandatários e Órgãos Públicos.
- Fornecer modais e telas de detalhe P0 para Despesas, Contratos e Análises.
- Garantir acessibilidade WCAG 2.2 AA e rastreabilidade estrita por SHA-256.

### Não-Objetivos
- Modificação direta de dados cadastrais oficiais em fontes externas (CEIS, TSE, CNPJ).
- Julgamento penal ou emissão de veredictos jurídicos automáticos.

## 5. Atores e Permissões
- `public_reader`: Acesso aos perfis públicos e modais de detalhe em estado verificado.
- `reviewer_admin`: Acesso à triagem e contestação interna de achados analíticos.

## 6. Fluxos Principais
1. **Abertura de Perfil:** Clique em entidade na tabela ou dashboard abre a página de perfil correspondente (Fornecedor, Mandatário ou Órgão).
2. **Detalhe de Despesa:** Clique em despesa exibe modal discriminando estágios contábeis (Empenhado, Liquidado, Pago) e comprovante SHA-256.
3. **Detalhe de Contrato:** Clique em contrato exibe modal com valores inicial, atualizado, vigência e linha do tempo interativa de aditivos.
4. **Detalhe de Análise:** Exibição das 3 camadas epistêmicas e formulário de contestação.

## 7. Cenários Alternativos e de Erro
- **Entidade inexistente:** Retorno de erro HTTP 404 padronizado.
- **Contrato sem aditivos:** Exibição de mensagem informativa na linha do tempo.
- **Despesa sem nota anexada:** Aviso de ausência de comprovante fiscal digitalizado com indicação de origem do lote oficial.

## 8. Requisitos Funcionais
- **`FR-043`**: A interface web e os endpoints WSGI devem expor e renderizar os Perfis Cívicos de Entidades para Fornecedores, Representantes/Mandatários e Órgãos Públicos.
- **`FR-044`**: A interface web deve expor Modais e Telas de Detalhe P0 para Despesas, Contratos e Análises.
- **`FR-045`**: Os modais e painéis de detalhe devem implementar acessibilidade WCAG 2.2 AA (`Esc`, focus trap, `role="dialog"`, `aria-modal="true"`).

## 9. Requisitos Não Funcionais
- **`NFR-023`**: Renderização instantânea dos modais em memória e resposta dos endpoints de detalhe em tempo sub-50ms no WSGI `CivicAuditHTTPApp`.

## 10. Regras de Negócio e Dados
- **`DATA-022`**: Modelagem imutável e contratos de dados para `CivicEntityProfile`, `ContractTimelineEvent`, `ExpenseDetailPayload` e rastreabilidade estrita `SHA-256`.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-023`**: Preservação compulsória de mascaramento de CPF (`***.XXX.XXX-**`), vedação categórica a termos acusatórios (`assert_non_accusatory_language`) e explicitação de que alterações contratuais e doações declaradas constituem atos regulares admitidos em lei.

## 12. Critérios de Aceite
- **`AC-078`**: Perfil de Fornecedor, Representante e Órgão exibem dados consolidados com rastreabilidade, QSA e histórico de contratos/despesas.
- **`AC-079`**: Detalhe de despesa discrimina os estágios contábeis (empenhado, liquidado e pago) e comprovante com SHA-256.
- **`AC-080`**: Detalhe de contrato renderiza a linha do tempo de termos aditivos com comparação de valor inicial vs atualizado.
- **`AC-081`**: Modais respeitam acessibilidade (tecla Esc, focus trap, aria-modal) e detalhe de análise exibe as 3 camadas epistêmicas e contestação.

## 13. Dependências
- `SPEC-0001` a `SPEC-0019`, `docs/design/*`

## 14. Riscos e Limitações
- Divergências temporais entre bases federais e municipais de execução orçamentária.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_civic_entity_profiles_and_details.py::TestCivicEntityProfilesAndDetails::test_entity_profiles_render_supplier_agent_and_organ_data`
- `tests/test_civic_entity_profiles_and_details.py::TestCivicEntityProfilesAndDetails::test_expense_detail_modal_shows_accounting_stages_and_hash`
- `tests/test_civic_entity_profiles_and_details.py::TestCivicEntityProfilesAndDetails::test_contract_detail_modal_renders_amendments_timeline`
- `tests/test_civic_entity_profiles_and_details.py::TestCivicEntityProfilesAndDetails::test_analysis_detail_enforces_epistemic_layers_and_a11y`

## 16. Questões Pendentes
- Nenhuma.
