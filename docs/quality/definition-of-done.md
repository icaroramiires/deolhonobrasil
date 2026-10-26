# De Olho no Brasil — Definition of Done (DoD)

**Versão:** 2.0.0  
**Status:** Obrigatório para todos os Checkpoints e Pull Requests

---

Uma funcionalidade, correção ou Checkpoint no **De Olho no Brasil** **só pode ser considerada concluída (`Verificado`)** quando **todos** os 13 critérios abaixo forem comprovados com evidências executáveis:

1. **Especificação Aprovada (`SPEC-XXXX`):** Existe pacote SDD atualizado em `docs/specs/SPEC-XXXX-*/` com requisitos tipados (`FR-*`, `NFR-*`, `SEC-*`, `DATA-*`, `AI-*`, `AC-*`).
2. **Spec Review Gate Aprovado (`review.md`):** Nenhuma questão crítica ou de alta severidade aberta (`Gate Status: APPROVED`).
3. **Design Técnico e ADRs (`plan.md` + `docs/architecture/adr/`):** Decisões arquiteturais registradas e contratos de dados/APIs documentados.
4. **Rastreabilidade Ponta a Ponta (`docs/quality/traceability-matrix.md`):** Todo requisito implementado está vinculado a tarefa (`TASK-*` / Jira `DONB-*`), módulo de código (`src/*`) e teste automatizado (`tests/*`).
5. **TDD e Suíte de Testes 100% Verde:** Todos os testes unitários, de integração e de contrato passam (`PYTHONPATH=src:.agents/loop python3 -m unittest discover -s tests -v`), respeitando o piso anti-regressão `MIN_EXPECTED_UNIT_TESTS >= 121` do GateGuard.
6. **Invariantes Epistêmicas e Léxicas (Zero Linguagem Acusatória):** Separação explícita nas 3 camadas (`[DADO OFICIAL]`, `[INFERÊNCIA ESTATÍSTICA]`, `[HIPÓTESE DE AUDITORIA / LIMITAÇÃO]`) e zero ocorrências de `FORBIDDEN_ACCUSATORY_TERMS`.
7. **LGPD e Proveniência Criptográfica:** CPFs de pessoas físicas mascarados (`***.XXX.XXX-**`) na ingestão e `SHA-256` preservado em 100% dos registros e sinais de auditoria.
8. **Reconciliação Contábil Exata:** `BatchReconciliationReport` no backend com `difference == Decimal("0.00")` e `console.assert` no frontend.
9. **Governança Editorial e RLS:** Dossiês em `EM_TRIAGEM_INTERNA` estritamente ocultos para `public_reader` e trilha `editorial_audit_trail` imutável.
10. **Qualidade Visual e Acessibilidade (`achromatic-ledger`):** Quando houver alteração de UI, `0 FAIL, 0 WARN` em `lint.mjs --app` e `inspect.mjs --app` nos viewports `1440x900`, `768x1024` e `390x844`.
11. **Eval Harness e Verification Loop (`pass^3 = 1.0`):** Execução limpa de `PYTHONPATH=src python3 -m deolhonobrasil.harness.runner --checkpoint 4 --trials 3` com `overall_passed: true` abrangendo todos os 4 gates de verificação formal.
12. **Revisão Adversarial Independente (`santa-method`):** Convergência `PASS` + `PASS` nas revisões de código, conformidade léxica (`donb-compliance-linter`) e segurança/arquitetura (`security-reviewer`) com zero apontamentos Críticos/Altos abertos.
13. **Antigravity Engineering Loop 100% Concluído:** Máquina de estados em `.agents/loop/state.json` no estado `COMPLETED` (`python3 scripts/run_loop.py status`), validação E2E via `agent-browser` (`scripts/run_e2e_browser.py`) e auditoria estática de DevSecOps com 0 falhas (`scripts/run_security_audit.py`).
