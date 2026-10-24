# Arquitetura de Loop Engineering, Spec-Driven Development (SDD) e Eval Harness — De Olho no Brasil

Este documento define o fluxo oficial de engenharia assistida por agentes (**Loop Engineering**), **Spec-Driven Development (SDD)** e **Eval-Driven Development (EDD)** do projeto **De Olho no Brasil**, integrando as skills do pacote `ecc-universal@2.2.0` (`intent-driven-development`, `spec-miner`, `gateguard`, `loop-design-check`, `verification-loop`, `eval-harness`, `santa-method`, `delivery-gate` e `architecture-decision-records`).

---

## 1. Visão Geral do Ciclo (`Plan -> Spec -> GateGuard -> Build -> Verify -> Judge -> Ship`)

Seguindo os princípios cibernéticos da skill **`loop-design-check`** (separação estrita entre **Execução** pela máquina e **Julgamento** pelo humano, com três papéis independentes: **Plan**, **Build** e **Judge**), nenhum código entra em produção sem atravessar as 7 etapas determinísticas abaixo:

```mermaid
flowchart TD
    A["1. PLAN & INTENT<br/>(product-lens + intent-driven-development)"] --> B["2. SPEC-DRIVEN CONTRACT<br/>(openspec/specs/*/spec.md + .agents/evals/*.md)"]
    B --> C["3. GATEGUARD PRE-ACTION<br/>(gateguard: Schemas, Importers & Anti-Goodhart Floor)"]
    C --> D["4. TIERED BUILD & TDD<br/>(tdd-workflow + Model Routing flash_lite / flash / pro)"]
    D --> E["5. 6-PHASE VERIFICATION LOOP<br/>(deolhonobrasil.harness.runner)"]
    E -->|Falha Determinística| D
    E -->|100% Green| F["6. SANTA METHOD DUAL REVIEW<br/>(Reviewer B + Reviewer C Independentes)"]
    F -->|NAUGHTY (Achados)| D
    F -->|NICE (Duplo PASS)| G["7. DELIVERY GATE & HUMAN CHECKPOINT<br/>(delivery-gate + Jira DONB / Confluence DDS Sync)"]
```

---

## 2. Mapeamento de Skills ECC por Etapa do Loop

| Etapa do Loop | Skill ECC Ativada (`.agents/skills/`) | Artefato / Comando Executável | Subagente & Modelo (`AGENTS.md`) | Critério de Saída Decidível por Máquina |
| :--- | :--- | :--- | :--- | :--- |
| **1. Planejamento & Escopo** | `intent-driven-development`, `product-lens`, `architecture-decision-records` | `docs/adr/000N-*.md`, Épicos e Histórias no Jira (`DONB`) | `planner` / `architect` (`pro`) | Escopo `In/Out`, restrições de negócio explícitas e ADR registrado |
| **2. Spec-Driven Development (SDD)** | `spec-miner`, `contract-first`, `eval-harness` | `openspec/specs/<cap>/spec.md` + `.agents/evals/checkpoint-N.md` | `donb-audit-ai-architect` (`pro`) | Todo `REQ-*`, `AC-*` e `INV-*` possui `Test Anchor` explícito |
| **3. GateGuard (Pre-Action Gate)** | `gateguard`, `loop-design-check` | `verify_gateguard_boundaries()` em `src/deolhonobrasil/harness/runner.py` | `donb-compliance-linter` (`flash_lite`) | Entidades de domínio `frozen=True` e piso de testes $\ge 39$ preservado |
| **4. Implementação Orientada a Testes (TDD)** | `tdd-workflow`, `python-patterns`, `python-testing`, `design-taste-frontend` | `src/deolhonobrasil/**` + `tests/test_*.py` | `donb-etl-builder` / `donb-ui-builder` (`flash`) | Testes falham antes (`RED`) e passam após a implementação (`GREEN`) |
| **5. Loop de Verificação em 6 Fases** | `verification-loop`, `agent-browser`, `browser-qa` | `PYTHONPATH=src python3 -m deolhonobrasil.harness.runner --checkpoint 2 --trials 3` | `donb-compliance-linter` (`flash_lite`) + `donb-browser-qa` (`flash`) | `overall_passed == true`, `pass@1 == 1.0`, `pass^3 == 1.0`, `0 FAIL / 0 WARN` |
| **6. Julgamento Adversarial Duplo** | `santa-method`, `security-review` | Revisão independente dupla sem contexto compartilhado | `security-reviewer` (`pro`) + `python-reviewer` (`pro`) | Convergência `PASS + PASS = NICE` (máximo 3 rodadas antes de escalar ao humano) |
| **7. Delivery Gate & Sincronização** | `delivery-gate`, `agent-self-evaluation` | Atualização de `docs/adr/`, Jira (`DONB`) e Confluence (`DDS`) | `doc-updater` (`flash_lite`) | Código de saída `0`, documentação atualizada e aprovação humana do Checkpoint |

---

## 3. Especificação Técnica do Harness Executável (`deolhonobrasil.harness.runner`)

O pacote [`src/deolhonobrasil/harness/runner.py`](../src/deolhonobrasil/harness/runner.py) consolida os verificadores determinísticos em um único comando CLI auditável:

```bash
PYTHONPATH=src python3 -m deolhonobrasil.harness.runner --checkpoint 2 --trials 3
```

### Gates Executados pelo `runner.py`

1. **`GATE-01-OPENSPEC` (`verify_openspec_traceability`):**
   - Inspeciona `openspec/specs/01-data-pipeline/spec.md`, `02-audit-and-laya/spec.md`, `03-editorial-governance/spec.md` e `04-web-and-api/spec.md`.
   - Extrai todos os identificadores `REQ-*`, `AC-*`, `INV-*` e âncoras `tests/test_*.py::Class::test_method`.
   - Importa dinamicamente os módulos de teste e comprova que 100% das âncoras apontam para métodos de teste reais.

2. **`GATE-02-GATEGUARD` (`verify_gateguard_boundaries`):**
   - Comprova que todas as 9 entidades centrais de domínio (`ProvenanceMetadata`, `CuratedPublicExpense`, `CuratedPublicContract`, `ReconciliationReport`, `AuditSignal`, `System1Decision`, `GroundedDossierSection`, `AuditDossier`, `RightOfReplySubmission`) permanecem imutáveis (`@dataclass(frozen=True)`).
   - Comprova a presença das 4 suítes de avaliação em `.agents/evals/`.

3. **`GATE-03-VERIFICATION-LOOP` (`verify_six_phase_loop`):**
   - **Fase 1 (Build):** Compila todos os arquivos `.py` de `src/` e `tests/` via `py_compile`.
   - **Fase 2 (Types):** Inspeciona assinaturas (`inspect.signature`) de todas as funções públicas garantindo anotações de retorno explícitas.
   - **Fase 3 (Lexical, LGPD, RLS & UI):** Verifica tokens obrigatórios em `rls_policies.sql`, marcadores das 3 camadas epistêmicas e `tabular-nums` em `wireframe_de_olho_no_brasil.html`, e ausência total de padrões acusatórios (`FORBIDDEN_ACCUSATORY_PATTERNS`).
   - **Fase 4 (Test Suite & Anti-Goodhart Boundary):** Executa toda a suíte `unittest` e bloqueia caso o número de testes caia abaixo de `MIN_EXPECTED_UNIT_TESTS` (`39+`).
   - **Fase 5 (Financial & Editorial Reconciliation):** Executa `run_audit_pipeline(..., verify_reconciliation=True)` em diretório isolado e exige `status == "OK"` e `unreviewed_visible_to_public_reader == 0`.
   - **Fase 6 (Delivery Gate):** Valida a existência de `docs/adr/README.md`, `docs/LOOP_ENGINEERING_SDD_HARNESS.md` e espaço em disco seguro.

---

## 4. Prevenção dos 5 Modos de Falha de Loops (`loop-design-check`)

| # | Modo de Falha (`loop-design-check`) | Anticorpo Implementado no De Olho no Brasil |
| :--- | :--- | :--- |
| **1** | Meta vaga ("melhore a auditoria") $\rightarrow$ loop infinito queimando tokens | Critério de parada 100% binário (`exit code 0` em `deolhonobrasil.harness.runner` + `lint.mjs` + `inspect.mjs`). |
| **2** | O próprio agente construtor julga seu trabalho ("parece bom") | Separação **Build** (`donb-etl-builder` / `donb-ui-builder`) vs **Judge** (`deolhonobrasil.harness.runner` + `santa-method` com 2 revisores independentes). |
| **3** | Agente apaga ou enfraquece testes para fazer a suíte passar (Goodhart) | Fronteira explícita em `GATE-01-OPENSPEC` (âncoras obrigatórias) e `GATE-03` (`testsRun >= MIN_EXPECTED_UNIT_TESTS` + entidades `frozen=True`). |
| **4** | Agente encontra ambiguidade de negócio no meio do loop e adivinha errado | **Front-loading** via `intent-driven-development` e `grill-me` antes da codificação; regras jurídicas e de governança congeladas em `openspec/specs/`. |
| **5** | Contexto inchado ou memória obsoleta degradando iterações | ADRs enxutos em `docs/adr/`, specs modulares por capacidade em `openspec/specs/` e delegação em subagentes com contexto limpo. |
