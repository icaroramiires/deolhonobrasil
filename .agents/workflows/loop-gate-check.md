# Workflow: Verificação Rápida de Quality Gates (`/loop-gate-check`)

Procedimento para checagem isolada de um gate específico da engenharia autônoma.

---

## Comandos Diretos por Gate

### 1. Testes Unitários (`GATE-06-TEST`)
```bash
python3 scripts/run_loop.py run-gate GATE-06-TEST
```
Verifica se todos os testes unitários estão passando e se a contagem não sofreu regressão.

### 2. Automação E2E com `agent-browser` (`GATE-07-E2E`)
```bash
python3 scripts/run_loop.py run-gate GATE-07-E2E
```
Sobe o servidor HTTP local em porta efêmera e interage com a interface usando `@ref` da árvore de acessibilidade do `agent-browser`.

### 3. Auditoria de Segurança e LGPD (`GATE-08-SECURITY`)
```bash
python3 scripts/run_loop.py run-gate GATE-08-SECURITY
```
Analisa todo o repositório em busca de segredos vazados, CPFs desmascarados, termos acusatórios e vulnerabilidades de timing attack.

### 4. Harness de Avaliação Contínua (`GATE-10-VERIFY`)
```bash
python3 scripts/run_loop.py run-gate GATE-10-VERIFY
```
Executa 3 rodadas consecutivas de testes e validação com exigência de taxa de sucesso `pass^3 = 1.0`.

---

## Diagnóstico em Caso de Falha
Se algum gate falhar, inspecione os detalhes imediatos com:
```bash
python3 scripts/run_loop.py report --gate <GATE-ID>
```
