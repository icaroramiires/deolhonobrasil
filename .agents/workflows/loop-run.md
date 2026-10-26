# Workflow: Execução do Engineering Loop Autônomo (`/loop-run`)

Procedimento operacional para conduzir uma mudança no repositório através do Engineering Loop.

---

## 1. Inicialização

1. Inspecione o status atual da máquina de estados:
   ```bash
   python3 scripts/run_loop.py status
   ```
2. Se estiver iniciando nova tarefa ou feature:
   ```bash
   python3 scripts/run_loop.py reset --task <TASK-ID> --spec <SPEC-ID> --title "<Título>"
   ```

---

## 2. Fases de Descoberta e Especificação (Gates 1 a 3)

1. Conduza a inspeção de contexto sem editar arquivos.
2. Registre o veredito do `GATE-01-DISCOVERY`:
   ```bash
   python3 scripts/run_loop.py record-gate --gate GATE-01-DISCOVERY --passed --evidence "Contexto inspecionado e documentado"
   ```
3. Elabore o pacote SDD completo de 6 arquivos em `docs/specs/<SPEC-ID>/`.
4. Registre o veredito do `GATE-02-SPECIFICATION`:
   ```bash
   python3 scripts/run_loop.py record-gate --gate GATE-02-SPECIFICATION --passed --evidence "SDD 6 arquivos aprovado sem apontamentos"
   ```
5. Elabore o plano técnico e ADR correspondente.
6. Registre o veredito do `GATE-03-PLAN`:
   ```bash
   python3 scripts/run_loop.py record-gate --gate GATE-03-PLAN --passed --evidence "Plano técnico e ADR estruturados"
   ```

---

## 3. Gate de Aprovação Humana (Gate 4)

1. Apresente o resumo do plano ao usuário e aguarde confirmação explícita.
2. Registre a autorização:
   ```bash
   python3 scripts/run_loop.py approve-plan --approver "<Nome do Usuário>" --notes "Aprovado via chat"
   ```

---

## 4. Implementação e Testes (Gates 5 a 8)

1. Execute TDD Red-Green-Refactor.
2. Ao concluir a implementação:
   ```bash
   python3 scripts/run_loop.py record-gate --gate GATE-05-IMPLEMENTATION --passed --evidence "Código implementado via TDD"
   ```
3. Execute o gate de testes unitários:
   ```bash
   python3 scripts/run_loop.py run-gate GATE-06-TEST
   ```
4. Execute o gate de E2E real no navegador:
   ```bash
   python3 scripts/run_loop.py run-gate GATE-07-E2E
   ```
5. Execute o gate de auditoria de segurança e conformidade:
   ```bash
   python3 scripts/run_loop.py run-gate GATE-08-SECURITY
   ```

---

## 5. Revisão, Verificação e Entrega (Gates 9 a 11)

1. Submeta para a revisão independente (Santa Method) e registre:
   ```bash
   python3 scripts/run_loop.py record-gate --gate GATE-09-REVIEW --passed --evidence "Revisão independente PASS"
   ```
2. Execute o harness de verificação determinístico:
   ```bash
   python3 scripts/run_loop.py run-gate GATE-10-VERIFY
   ```
3. Valide o Definition of Done e encerre:
   ```bash
   python3 scripts/run_loop.py record-gate --gate GATE-11-ACCEPT --passed --evidence "DoD validado, pronto para release"
   ```
