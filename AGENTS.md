# De Olho no Brasil — Diretrizes de Agentes, Orquestração de Modelos e Workflow SDD (`ecc-universal@2.2.3`)

Este arquivo define as regras permanentes do repositório para roteamento de subagentes por complexidade de tarefa (economia de tokens), automação de navegador via `agent-browser`, governança epistêmica/jurídica e o **Workflow Spec-Driven Development (SDD) de 8 Fases** do **De Olho no Brasil**.

---

## 1. Política de Delegação de Subagentes e Economia de Tokens (`Model Routing`)

**Regra Obrigatória:** Ao invocar qualquer subagente via `invoke_subagent`, **SEMPRE** especifique explicitamente o parâmetro `Model` (`flash_lite`, `flash` ou `pro`) correspondente à complexidade real da tarefa. **É proibido usar `pro` ou `inherit` (quando o agente pai for pesado) para tarefas mecânicas, buscas, lints ou implementações diretas.**

### Matriz de Roteamento Tarefa $\rightarrow$ Subagente $\rightarrow$ Modelo

| Tier de Custo | Modelo (`invoke_subagent`) | Subagentes Recomendados | Escopo de Tarefas Autorizado |
| :--- | :--- | :--- | :--- |
| **Tier 1 · Ultra-Leve** | **`flash_lite`** | `donb-compliance-linter`, `donb-portal-scout`, `docs-lookup`, `doc-updater`, `comment-analyzer` | • Verificação léxica de linguagem não-acusatória (`assert_non_accusatory_language`)<br>• Validação de mascaramento de CPF (`***.XXX.XXX-**`) e presença de `SHA-256`<br>• Execução de linters estáticos (`lint.mjs --app`, `ruff`, checagem de links)<br>• Leitura rápida de schemas de APIs públicas (`CGU`, `PNCP`, `CEAP`, `CEAPS`)<br>• Atualização de `README.md`, `docs/specs/*`, `CODEMAPS` e documentação |
| **Tier 2 · Padrão** | **`flash`** | `donb-etl-builder`, `donb-ui-builder`, `donb-browser-qa`, `tdd-guide`, `e2e-runner`, `build-error-resolver`, `code-explorer`, `code-simplifier` | • Implementação de conectores de dados públicos, persistência SQLite/DuckDB/Parquet e reconciliação financeira (`BatchReconciliationReport`)<br>• Construção de telas e gráficos SVG seguindo `.taste-skill/direction.json` (`achromatic-ledger`)<br>• Escrita e execução de testes unitários e de integração (`unittest` / `pytest`)<br>• Automação de navegador e QA visual com `agent-browser` e `inspect.mjs --app`<br>• Resolução cirúrgica de erros de build ou tipagem |
| **Tier 3 · Raciocínio Profundo** | **`pro`** | `donb-audit-ai-architect`, `security-reviewer`, `python-reviewer`, `database-reviewer`, `architect`, `planner` | • Projeto de regras matemáticas de auditoria (`Z-Score`, `Lei de Benford`, `Índice HHI`)<br>• Integração e calibração do motor de decisão *System 1* `Laya` (`Choice`, `Score`, `Noul`) e RAG *grounded*<br>• Políticas de *Row-Level Security* (RLS), criptografia e proteção contra *prompt injection* indireto<br>• Revisão adversarial final de segurança, privacidade (LGPD) e arquitetura antes de fechar um Checkpoint |

---

## 2. Automação de Navegador (`agent-browser`)

Use o CLI nativo em Rust **`agent-browser`** (`/opt/homebrew/bin/agent-browser`, skill em `.agents/skills/agent-browser/SKILL.md`) para automação web, inspeção de portais governamentais e testes E2E com baixo consumo de tokens (`~200-400` tokens por snapshot de acessibilidade vs `3000-5000` de DOM bruto).

### Fluxo Padrão (`Snapshot + @ref`)
1. `agent-browser skills get core` (ou ler `.agents/skills/agent-browser/references/core.md`)
2. `agent-browser open <url>` — Navegar para a página ou arquivo servido localmente
3. `agent-browser snapshot -i` — Obter árvore de acessibilidade com referências determinísticas (`@e1`, `@e2`, ...)
4. `agent-browser click @e1` / `agent-browser fill @e2 "texto"` — Interagir via `@ref`
5. `agent-browser screenshot <caminho.png>` e `agent-browser close` ao concluir.

---

## 3. Invariantes Inegociáveis do Produto (De Olho no Brasil)

1. **Separação Epistêmica em 3 Camadas:** Todo dossiê ou tela deve separar explicitamente `[DADO OFICIAL]`, `[INFERÊNCIA ESTATÍSTICA]` e `[HIPÓTESE DE AUDITORIA / LIMITAÇÃO]`.
2. **Proibição de Linguagem Acusatória:** Nunca emitir termos como `"fraude comprovada"`, `"corrupção"`, `"roubo"`, `"desvio intencional"`, `"culpado"`, `"criminoso"` ou `"superfaturamento comprovado"`.
3. **LGPD por Padrão:** CPFs de pessoas físicas comuns devem ser mascarados (`***.XXX.XXX-**`) na camada de ingestão antes da persistência pública.
4. **Rastreabilidade e Reconciliação:** Todo registro deve carregar `SHA-256` do payload bruto e toda soma exibida deve fechar centavo a centavo com suas partes (`BatchReconciliationReport` no backend e `console.assert` no frontend).
5. **Governança Editorial Híbrida e RLS:** Nenhum achado nominal de alta severidade (`score >= 0.70` no motor `Laya`) é publicado automaticamente; nasce em `EM_TRIAGEM_INTERNA` (oculto para `public_reader` via RLS) até revisão humana.

---

## 4. Workflow Spec-Driven Development (SDD) de 8 Fases (`ecc-universal@2.2.3`)

Nenhuma funcionalidade não-trivial deve ser implementada sem percorrer as **8 fases obrigatórias** documentadas em [`docs/LOOP_ENGINEERING_SDD_HARNESS.md`](docs/LOOP_ENGINEERING_SDD_HARNESS.md):

1. **Fase 1 — Discovery (`intent-driven-development` + `product-lens`):** Compreender problema, atores, premissas, restrições e riscos em `docs/product/`.
2. **Fase 2 — Specification (`spec-miner`):** Criar/atualizar `docs/specs/SPEC-XXXX-<slug>/spec.md` com as 16 seções obrigatórias e IDs estáveis (`FR-*`, `NFR-*`, `SEC-*`, `DATA-*`, `AI-*`, `AC-*`).
3. **Fase 3 — Spec Review (`council` / `security-review`):** Auditar ambiguidades, casos de erro, LGPD, custos e riscos de IA em `docs/specs/SPEC-XXXX-<slug>/review.md`. **Gate obrigatório:** implementação bloqueada enquanto houver achado Crítico/Alto aberto (`Gate Status: APPROVED`).
4. **Fase 4 — Design Técnico (`architect` + `architecture-decision-records`):** Produzir `plan.md`, `data-model.md`, `api-contracts.md`, `test-plan.md` e ADRs em `docs/architecture/adr/`.
5. **Fase 5 — Planejamento e Decomposição (`planner` + Atlassian MCP):** Decompor em tarefas atômicas e verificáveis em `tasks.md` e sincronizar épicos/tasks no Jira (`DONB`).
6. **Fase 6 — Implementação Orientada por Testes (`gateguard` + `tdd-workflow`):** Ciclo **Red → Green → Refactor** respeitando os limites do GateGuard (`MIN_EXPECTED_UNIT_TESTS`, `frozen=True`).
7. **Fase 7 — Revisão Independente e Verificação (`verification-loop` + `santa-method` + `eval-harness`):** Revisão adversarial dupla (`python-reviewer` / `security-reviewer` + `donb-compliance-linter`) e execução do harness:
   ```bash
   PYTHONPATH=src python3 -m deolhonobrasil.harness.runner --checkpoint 2 --trials 3
   ```
8. **Fase 8 — Documentação, Rastreabilidade e Entrega (`living-docs-governance` + `delivery-gate`):** Atualizar [`docs/quality/traceability-matrix.md`](docs/quality/traceability-matrix.md), validar o [`docs/quality/definition-of-done.md`](docs/quality/definition-of-done.md) e sincronizar o Confluence (`DDS`).

### Estados do Ciclo de Vida do Requisito
`Proposto` $\rightarrow$ `Especificado` $\rightarrow$ `Revisado` $\rightarrow$ `Aprovado` $\rightarrow$ `Em implementação` $\rightarrow$ `Em revisão` $\rightarrow$ `Verificado` $\rightarrow$ `Documentado`.

### Controle de Mudanças e Proporcionalidade
- Qualquer descoberta durante a codificação que altere comportamento, contrato de dados ou segurança exige atualização prévia de `spec.md`, `review.md` e `traceability-matrix.md`.
- Correções triviais (typos, ajustes cosméticos sem impacto funcional) seguem fluxo simplificado, mas continuam sujeitas à execução do harness (`runner.py`).
