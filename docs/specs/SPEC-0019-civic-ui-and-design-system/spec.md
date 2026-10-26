# SPEC-0019 — Interface Web Cívica, Design System Unificado (Tokens, Temas Claro/Escuro, Responsividade P0) e Visualização de Evidências Rastreáveis

## 1. Identificador e Título
- **ID:** `SPEC-0019`
- **Título:** Interface Web Cívica, Design System Unificado (Tokens, Temas Claro/Escuro, Responsividade P0) e Visualização de Evidências Rastreáveis

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.0.0`

## 3. Problema e Motivação
Apresentação transparente e acessível de dados públicos complexos, unificando os 22 sinais de auditoria com a nova direção visual institucional de `docs/design/`, paleta verde profundo `#12654c`, destaque lima `#d3f05b`, 7 visões completas e conformidade WCAG 2.2 AA.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Fornecer uma interface web cívica robusta, autocontida e offline-first integrada ao aplicativo WSGI.
- Implementar o design system com tokens unificados e alternância de temas (claro/escuro).
- Assegurar rastreabilidade com hashes SHA-256 e separação epistêmica rigorosa.

### Não-Objetivos
- Implementar frameworks pesados externos de CDN (utiliza Vanilla JS modular e CSS moderno autocontido).

## 5. Atores e Permissões
- `public_reader`: Leitor público de dossiês validados.
- `reviewer_admin`: Revisor/administrador com acesso a triagens e auditorias avançadas.

## 6. Fluxos Principais
1. **Visão Geral:** Indicadores consolidados de auditoria e métricas de controle social.
2. **Pesquisa (`Ctrl/⌘ + K`):** Busca rápida global de contratos, despesas e entidades.
3. **Despesas:** Acompanhamento nos 3 estágios (empenhado, liquidado, pago) com reconciliação contábil.
4. **Contratos:** Vigência, aditivos e histórico de aditamento.
5. **Análises:** Exibição com as 3 camadas epistêmicas e limites da IA ("IA apoia, pessoas verificam").
6. **Evidências:** Grafos e tabelas validados por manifesto SHA-256.
7. **Acompanhamentos:** Gestão de alertas e monitoramento cívico.

## 7. Cenários Alternativos e de Erro
- **Carregando:** Indicador visual de progresso com animação leve.
- **Vazio:** Mensagem orientativa quando nenhum registro é encontrado.
- **Erro Recuperável:** Alerta com opção de tentar novamente.
- **Dados Incompletos:** Aviso explícito sobre campos faltantes na fonte original.
- **Fonte Indisponível:** Fallback para cache local com indicação temporal.
- **Sem Permissão:** Redirecionamento para autenticação ou aviso de acesso restrito.

## 8. Requisitos Funcionais
- **`FR-040`:** A interface web cívica deve implementar o design system unificado definido em `docs/design/design-tokens.json` e `design-system.md`, suportando temas claro (`#f5f7f6` / `#ffffff`) e escuro (`#0e1714` / `#14201c`), tipografia Manrope/DM Sans, e classes utilitárias de contraste WCAG 2.2 AA.
- **`FR-041`:** A aplicação deve expor 7 visões de navegação completas (Visão Geral/Início, Pesquisa com atalho `Ctrl/⌘ + K`, Despesas com estágios empenhado/liquidado/pago, Contratos com vigência e aditivos, Análises com 3 camadas epistêmicas e limites da IA, Evidências com manifesto SHA-256 e Acompanhamentos).
- **`FR-042`:** A aplicação deve integrar-se diretamente com a API WSGI (`CivicAuditHTTPApp`), consumindo `/api/v1/health`, `/api/v1/dossiers`, `/api/v1/expenses`, `/api/v1/contracts`, `/api/v1/sanctions`, suportando filtros, ordenação e exportação de dados sem dependências externas de CDN em modo offline/sandbox.

## 9. Requisitos Não Funcionais
- **`NFR-022`:** Responsividade estrutural verificada em 4 viewports (1440px wide, 1050px desktop, 768px tablet, 390px mobile) e acessibilidade com alvos mínimos de 24x24 (44x44 mobile), suporte a `reduced-motion` e navegação integral por teclado.

## 10. Regras de Negócio e Dados
- **`DATA-021`:** Rastreabilidade estrita e reconciliação contábil com asserções em tempo de execução (`console.assert`), distinção entre valores empenhado, liquidado e pago, e explicitação de dados demonstrativos.

## 11. Requisitos de Segurança e Privacidade
- **`SEC-022`:** Vedação absoluta a termos acusatórios (`assert_non_accusatory_language`), preservação de mascaramento de CPF (`***.XXX.XXX-**`), sanitização contra injeção e respeito a RLS para visualização de dossiês em triagem.

## 12. Critérios de Aceite
- **`AC-074`:** Interface renderiza tokens e tema claro/escuro com persistência local, tipografia Manrope/DM Sans e cores institucionais.
- **`AC-075`:** Navegação entre as 7 visões preserva estado de filtros, suporta atalho `Ctrl/⌘ + K` e apresenta os 6 estados de carregamento/vazio/erro.
- **`AC-076`:** Despesas exibem separação inequívoca entre estágios empenhado, liquidado e pago, com reconciliação matemática comprovada.
- **`AC-077`:** Análises e dossiês separam rigorosamente as 3 camadas epistêmicas, com banner 'IA apoia, pessoas verificam', e evidências exibem hashes SHA-256 canônicos.

## 13. Dependências
- `SPEC-0001` a `SPEC-0018`, `docs/design/*`

## 14. Riscos e Limitações
- Conectividade limitada de fontes públicas mitigada por cache e modo offline/sandbox.

## 15. Estratégia de Testes e Test Anchors
- `tests/test_civic_ui_and_design_system.py::TestCivicUIAndDesignSystem::test_ui_serves_html_with_design_tokens_and_theme_support`
- `tests/test_civic_ui_and_design_system.py::TestCivicUIAndDesignSystem::test_ui_renders_seven_navigation_views_and_search_shortcut`
- `tests/test_civic_ui_and_design_system.py::TestCivicUIAndDesignSystem::test_ui_enforces_epistemic_badges_and_non_accusatory_language`
- `tests/test_civic_ui_and_design_system.py::TestCivicUIAndDesignSystem::test_ui_handles_loading_empty_and_error_states`

## 16. Questões Pendentes
- Nenhuma.
