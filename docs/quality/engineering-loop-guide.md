# De Olho no Brasil — Guia do Antigravity Autonomous Engineering Loop

**Versão:** 1.0.0  
**Status:** Oficial / Produção  
**Público-alvo:** Engenheiros de Software, Arquitetos, DevSecOps e Agentes Autônomos  

---

## 1. Visão Geral e Filosofia

O **Antigravity Autonomous Engineering Loop** é um harness de engenharia persistente, determinístico e autônomo, projetado para governar todo o ciclo de vida de mudanças de software no **De Olho no Brasil**.

Inspirado nas práticas de *Spec-Driven Development* (SDD), *Test-Driven Development* (TDD), *Santa Method* (revisão adversarial dupla) e *Fact-Forcing GateGuards*, o loop garante que nenhuma linha de código seja entregue sem percorrer **11 Quality Gates bloqueantes**:

```
DISCOVER ──> SPECIFY ──> PLAN ──> APPROVAL ──> IMPLEMENT ──> TEST ──> E2E ──> SECURITY ──> REVIEW ──> VERIFY ──> ACCEPT ──> COMPLETED
   │            │          │         │            │          │      │         │          │         │         │
   └────────────┴──────────┴─────────┴────────────┴──────────┴──────┴─────────┴──────────┴─────────┴─────────┘
                                   │ (Falha >= 3x)
                                   ▼
                              [ BLOCKED ] (Circuit Breaker Tripped)
```

### Princípios Cardeais
1. **Zero Sobrecarga de Dependências Externas:** O motor de loop (`.agents/loop/engine.py`), a CLI (`scripts/run_loop.py`) e o auditor de segurança (`scripts/run_security_audit.py`) utilizam **estritamente a biblioteca padrão do Python** (`json`, `subprocess`, `urllib`, `ast`, `re`, `pathlib`, `hashlib`).
2. **Humano no Circuito Inegociável:** O gate `GATE-04-APPROVAL` bloqueia a implementação mecânica até que haja uma aprovação explícita e registrada de stakeholder.
3. **Piso Anti-Goodhart de Testes:** A suíte de testes unitários tem piso rigorosamente validado (`MIN_EXPECTED_UNIT_TESTS = 117`), impedindo aprovação de gates quando testes são deletados ou ignorados.
4. **Governança Epistêmica e Não-Acusatória:** Todas as evidências e mensagens do loop respeitam a separação epistêmica em 3 camadas e a proibição absoluta de termos difamatórios/acusatórios.

---

## 2. A Máquina de Estados e os 11 Quality Gates

| ID do Gate | Estado Alvo | Próximo Estado | Tipo | Mecanismo de Execução | Critério de Aprovação |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`GATE-01-DISCOVERY`** | `DISCOVER` | `SPECIFY` | Análise | Inspecionar repositório e convenções | Diagnóstico completo sem alterações em arquivos de código. |
| **`GATE-02-SPECIFICATION`** | `SPECIFY` | `PLAN` | SDD | `docs/specs/SPEC-XXXX/` | 16 seções completas, IDs de requisitos (`FR-*`, `NFR-*`, `DATA-*`, `SEC-*`, `AC-*`) e âncoras de teste. |
| **`GATE-03-PLAN`** | `PLAN` | `APPROVAL` | Arquitetura | `tasks.md`, `plan.md`, `ADR` | Decomposição em tarefas atômicas e contratos técnicos validados. |
| **`GATE-04-APPROVAL`** | `APPROVAL` | `IMPLEMENT` | **Humano** | `scripts/run_loop.py approve-plan` | Registro formal do aprovador e justificativa; bloqueio de autoaprovação. |
| **`GATE-05-IMPLEMENTATION`**| `IMPLEMENT` | `TEST` | TDD | Red-Green-Refactor | Código implementado, modelos com `frozen=True` e tipagem completa. |
| **`GATE-06-TEST`** | `TEST` | `E2E` | Testes | `python3 -m unittest discover tests` | 100% dos testes unitários passando, total $\ge 117$. |
| **`GATE-07-E2E`** | `E2E` | `SECURITY` | Browser | `scripts/run_e2e_browser.py` | Automação real via `agent-browser` (snapshot, screenshot e endpoints). |
| **`GATE-08-SECURITY`** | `SECURITY` | `REVIEW` | DevSecOps | `scripts/run_security_audit.py` | 0 segredos, 0 termos acusatórios, LGPD preservado, SSRF safe. |
| **`GATE-09-REVIEW`** | `REVIEW` | `VERIFY` | Santa Method | Revisores independentes A + B | Revisão dupla (Compliance Linter + Security Reviewer) com 0 Critical/High. |
| **`GATE-10-VERIFY`** | `VERIFY` | `ACCEPT` | Harness | `runner.py --checkpoint 4 --trials 3` | Execução do harness formal com $pass^3 = 1.0$ em 3 rodadas consecutivas. |
| **`GATE-11-ACCEPT`** | `ACCEPT` | `COMPLETED` | DoD | `scripts/run_loop.py record-gate` | 100% da Definition of Done e matriz de rastreabilidade atendidas. |

---

## 3. Circuit Breaker e Diagnóstico de Falhas

Para impedir loops infinitos e desperdício de tokens, o motor implementa um **Circuit Breaker** com contenção ativa:
- **Limite de Tentativas:** Cada gate possui um orçamento máximo de 3 tentativas consecutivas (`max_retries_per_gate: 3`).
- **Transição para `BLOCKED`:** Se um gate falhar 3 vezes consecutivas, a máquina de estados transita imediatamente para `BLOCKED`, desativando a execução automatizada de novos comandos.
- **Relatório de Introspecção (`engine.generate_introspection_report`):** Gera um diagnóstico estruturado em JSON contendo:
  - `incident_id`: Identificador único do incidente.
  - `gate_id`: Gate onde a falha ocorreu.
  - `retry_count` e `retry_budget_remaining`.
  - `diagnostics`: Saída de erro (stdout/stderr) capturada.
  - `recommended_recovery_action`: Ação recomendada para correção cirúrgica.
- **Desbloqueio Humano (`unblock`):** Exige ação consciente via CLI (`python3 scripts/run_loop.py unblock --reason "<motivo>"`), resetando o contador de retentativas do gate afetado.

---

## 4. Testes E2E de Navegador com `agent-browser`

A automação de interface utiliza o CLI nativo em Rust **`agent-browser`** (`scripts/run_e2e_browser.py`), garantindo baixo overhead de contexto:

1. **Servidor Efêmero WSGI:** O script inicializa uma instância isolada do `CivicAuditHTTPApp` em porta efêmera aleatória (`127.0.0.1:0`), eliminando conflitos de porta em ambientes de CI ou paralelismo.
2. **Lakehouse Temporário:** Cria um diretório temporário isolado populado via `run_sample_pipeline`, fornecendo dados reais curados (despesas, contratos, emendas, dossiês).
3. **Árvore de Acessibilidade (`snapshot -i`):** Captura a árvore determinística com referências acessíveis (`@e1`, `@e2`), gravando o arquivo `.agents/artifacts/e2e/snapshot.txt`.
4. **Captura Visual (`screenshot`):** Produz screenshot verificado da aplicação em `.agents/artifacts/e2e/e2e_verified.png`.
5. **Navegação de API via Browser:** Testa a requisição e renderização de `/api/v1/expenses` pelo browser.
6. **Encerramento Seguro (`finally`):** Garante o encerramento da sessão do navegador (`agent-browser --session <id> close`), desligamento do servidor WSGI e expurgo do diretório temporário.

---

## 5. Auditoria de Segurança Automatizada (`run_security_audit.py`)

O script `scripts/run_security_audit.py` avalia cinco barreiras críticas de segurança estática sem dependências de terceiros:
1. **SAST Secret Scanner:** Detecta chaves privadas RSA/EC, tokens AWS, GitHub PATs, JWTs e chaves genéricas de alta entropia.
2. **Defamatory & Accusatory Language Linter:** Varre arquivos de regras, código e documentação contra termos terminantemente proibidos (`fraude comprovada`, `corrupção`, `superfaturamento comprovado`, `culpado`, `criminoso`).
3. **Constant-Time Token Comparison:** Garante que toda autenticação de token administrativo utilize `hmac.compare_digest` para evitar ataques de temporização (*timing attacks*).
4. **SSRF Guard & Allowlist:** Verifica se clientes HTTP restringem requisições exclusivamente a conexões `https://` em domínios públicos explicitamente autorizados (`dadosabertos.camara.leg.br`, `leg.br`, `comprasgovernamentais.gov.br`, `transparencia.gov.br`, `tse.jus.br`).
5. **Non-Root & Principle of Least Privilege:** Verifica se o `Dockerfile` contém diretiva explícita de usuário sem privilégios (`USER`).

---

## 6. Manual de Comandos da CLI (`scripts/run_loop.py`)

### 6.1. Visualizar Estado Atual
```bash
python3 scripts/run_loop.py status
```

### 6.2. Executar um Gate Automatizado
```bash
python3 scripts/run_loop.py run-gate GATE-06-TEST
python3 scripts/run_loop.py run-gate GATE-07-E2E
python3 scripts/run_loop.py run-gate GATE-08-SECURITY
python3 scripts/run_loop.py run-gate GATE-10-VERIFY
```

### 6.3. Aprovar Plano (Gate Humano Obrigatório)
```bash
python3 scripts/run_loop.py approve-plan --approver "Nome do Stakeholder" --notes "Arquitetura e ADR revisados e aprovados."
```

### 6.4. Registrar Veredito de Gate Manual / Revisão
```bash
python3 scripts/run_loop.py record-gate --gate GATE-09-REVIEW --passed --evidence "Santa Method dual review convergence: PASS + PASS com 0 Critical/High."
python3 scripts/run_loop.py record-gate --gate GATE-11-ACCEPT --passed --evidence "100% DoD cumprido, 117 testes unitários verdes."
```

### 6.5. Gerar Relatório de Gate / Diagnóstico
```bash
python3 scripts/run_loop.py report --gate GATE-11-ACCEPT
```

### 6.6. Desbloquear Circuit Breaker
```bash
python3 scripts/run_loop.py unblock --reason "Correção cirúrgica aplicada no teste com regressão tratada."
```

### 6.7. Reiniciar Ciclo para Nova Tarefa
```bash
python3 scripts/run_loop.py reset --task-id "DONB-FEATURE-02" --spec-id "SPEC-0019" --title "Nova Capacidade"
```

---

## 7. Integração CI/CD no GitHub Actions

O pipeline `.github/workflows/ci.yml` automatiza a verificação do Engineering Loop em cada *pull request* e *push*:
1. Validação do código estático e sintaxe Python.
2. Execução da auditoria de segurança (`scripts/run_security_audit.py`).
3. Execução da suíte completa de testes unitários (`117/117`).
4. Execução do harness formal (`runner.py --checkpoint 4 --trials 3`).
5. Inspeção do estado do loop (`scripts/run_loop.py status`).
