## 1. Rastreabilidade SDD

- **Especificação Relacionada (`SPEC-NNNN`):** `docs/specs/SPEC-____/`
- **IDs dos Requisitos Atendidos (`FR-*`, `NFR-*`, `SEC-*`, `DATA-*`, `AI-*`):**
- **Critérios de Aceite (`AC-*`):**
- **Tarefa (`tasks.md` / Jira `DONB-*`):**

## 2. Resumo da Mudança

- O que mudou e por que esta alteração é necessária?

## 3. Verificação e Evidências (`Definition of Done`)

- [ ] A especificação (`spec.md` e `review.md`) está aprovada e sem bloqueadores críticos.
- [ ] Ciclo TDD (`RED -> GREEN -> REFACTOR`) executado e novos testes adicionados em `tests/`.
- [ ] Harness SDD executado (`PYTHONPATH=src python3 -m deolhonobrasil.harness.runner --checkpoint 2 --trials 3`) com saída `overall_passed: true`.
- [ ] Linguagem estritamente não-acusatória (`assert_non_accusatory_language`) e mascaramento LGPD (`***.XXX.XXX-**`) preservados.
- [ ] Matriz de rastreabilidade (`docs/quality/traceability-matrix.md`) atualizada.

### Saída dos Comandos de Verificação
```text
# Cole aqui o resumo da execução do runner.py / unittest / lint.mjs
```

## 4. Impactos e Riscos Residuais

- **Mudanças de Banco de Dados / Políticas RLS:** Sim / Não (detalhar migração e rollback)
- **Mudanças de Infraestrutura ou Custos Operacionais:** Sim / Não
- **Riscos Residuais Documentados:**
