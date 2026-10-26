# Engineering Loop & Autonomous Quality Gates Rule (`engineering-loop.md`)

Este documento estabelece as regras permanentes e mandatórias de engenharia autônoma para o repositório **De Olho no Brasil**.

---

## 1. Ciclo Obrigatório de 11 Estados

Toda mudança de código não-trivial deve percorrer a máquina de estados finita:

$$\text{DISCOVER} \rightarrow \text{SPECIFY} \rightarrow \text{PLAN} \rightarrow \text{APPROVAL} \rightarrow \text{IMPLEMENT} \rightarrow \text{TEST} \rightarrow \text{E2E} \rightarrow \text{SECURITY} \rightarrow \text{REVIEW} \rightarrow \text{VERIFY} \rightarrow \text{ACCEPT}$$

### Transição e Bloqueio
- Nenhuma transição de estado ocorre sem que o Quality Gate associado esteja no veredito `PASSED`.
- O estado de aprovação (`APPROVAL` / `GATE-04-APPROVAL`) **exige expressa autorização humana** registrada via CLI (`python3 scripts/run_loop.py approve-plan --approver "<Nome>"`). É terminantemente proibido autoaprovar planos ou iniciar escrita de código sem essa validação.
- O circuit breaker entra em ação após 3 falhas consecutivas no mesmo gate (`max_retries_per_gate: 3`), transitando o sistema para `BLOCKED` e exigindo intervenção humana.

---

## 2. Invariantes de Qualidade por Gate

| Gate | Estado | Tipo | Critério de Sucesso |
| :--- | :--- | :--- | :--- |
| **`GATE-01-DISCOVERY`** | `DISCOVER` | Análise | Contexto, arquitetura e convenções inspecionados sem alteração de arquivos. |
| **`GATE-02-SPECIFICATION`** | `SPECIFY` | SDD | 16 seções completas, IDs de requisitos estáveis (`FR-*`, `NFR-*`, `DATA-*`, `SEC-*`, `AC-*`) e âncoras de teste. |
| **`GATE-03-PLAN`** | `PLAN` | Arquitetura | Tarefas atômicas em `tasks.md`, contratos de API/dados e ADR aprovado. |
| **`GATE-04-APPROVAL`** | `APPROVAL` | **Humano** | Confirmação explícita do usuário registrada no estado do loop. |
| **`GATE-05-IMPLEMENTATION`**| `IMPLEMENT` | TDD | Ciclo Red-Green-Refactor concluído, imutabilidade (`frozen=True`) preservada. |
| **`GATE-06-TEST`** | `TEST` | Testes | 100% dos testes unitários passando (`python3 -m unittest discover tests`), total $\ge 117$. |
| **`GATE-07-E2E`** | `E2E` | Navegador | Validação real da UI e endpoints via `agent-browser` (`scripts/run_e2e_browser.py`). |
| **`GATE-08-SECURITY`** | `SECURITY` | SAST/LGPD | Zero segredos, zero CPFs desmascarados, zero termos acusatórios, timing attack guard verificado (`scripts/run_security_audit.py`). |
| **`GATE-09-REVIEW`** | `REVIEW` | Santa Method | Revisão dupla independente (`python-reviewer`/`security-reviewer` + `donb-compliance-linter`) com zero apontamentos Críticos/Altos. |
| **`GATE-10-VERIFY`** | `VERIFY` | Harness | Execução do harness de avaliação com `pass^3 = 1.0` (`runner.py --checkpoint 4 --trials 3`). |
| **`GATE-11-ACCEPT`** | `ACCEPT` | DoD | Definition of Done 100% cumprida, rastreabilidade atualizada, entrega pronta. |

---

## 3. Comandos de Operação

```bash
# Ver status do loop
python3 scripts/run_loop.py status

# Executar gate específico
python3 scripts/run_loop.py run-gate GATE-06-TEST

# Aprovar plano (apenas após sinal explícito do usuário)
python3 scripts/run_loop.py approve-plan --approver "Usuário" --notes "Plano aprovado"

# Gerar relatório de diagnóstico em caso de falha
python3 scripts/run_loop.py report --gate GATE-08-SECURITY
```
