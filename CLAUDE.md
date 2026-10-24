# CLAUDE.md — De Olho no Brasil (ECC & SDD Entrypoint)

Este arquivo é o ponto de entrada padrão do **Everything Claude Code (`ecc-universal@2.2.0`)** para o projeto **De Olho no Brasil** e complementa as diretrizes permanentes de [`AGENTS.md`](AGENTS.md).

## 1. Fluxo Obrigatório Spec-Driven Development (SDD) em 8 Fases

Toda funcionalidade ou alteração deve percorrer de forma rastreável e proporcional à complexidade:

1. **Fase 1 — Discovery:** Compreender o problema, restrições jurídicas/negócio e riscos (`/grill-me`, `intent-driven-development`, `product-lens`).
2. **Fase 2 — Specification:** Escrever ou atualizar `docs/specs/SPEC-NNNN-<slug>/spec.md` com as 16 seções canônicas e IDs tipados (`FR-*`, `NFR-*`, `SEC-*`, `DATA-*`, `AI-*`, `AC-*`).
3. **Fase 3 — Spec Review:** Revisar ambiguidades, segurança/LGPD, falsos positivos de IA e limitações das fontes em `review.md`. **Gate obrigatório:** zero bloqueadores críticos abertos antes de implementar.
4. **Fase 4 — Design Técnico:** Produzir `plan.md`, `data-model.md` / `api-contracts.md` e ADRs em [`docs/architecture/adr/`](docs/architecture/adr/README.md).
5. **Fase 5 — Planejamento e Decomposição:** Decompor em tarefas atômicas e independentes em `tasks.md` e `test-plan.md`.
6. **Fase 6 — Aprovação:** Gate humano obrigatório para mudanças de arquitetura, schema, regras de auditoria, políticas RLS, publicação pública ou custos.
7. **Fase 7 — Implementação com TDD:** Ciclo `RED -> GREEN -> REFACTOR` (`tdd-workflow`, `gateguard`), sem apagar ou enfraquecer testes existentes.
8. **Fase 8 — Revisão Independente, Verificação e Entrega:** Executar o Harness determinístico (`runner.py`), revisão adversarial dupla (`santa-method`) e atualizar a [`docs/quality/traceability-matrix.md`](docs/quality/traceability-matrix.md).

## 2. Comandos Rápidos de Verificação

```bash
# Executar o Harness SDD + Loop Engineering completo (3 trials para pass@1 e pass^3)
PYTHONPATH=src python3 -m deolhonobrasil.harness.runner --checkpoint 2 --trials 3

# Executar suíte completa de testes unitários e de integração
PYTHONPATH=src python3 -m unittest discover -s tests -v

# Executar pipeline de ingestão + auditoria determinística + governança RLS
PYTHONPATH=src python3 -m deolhonobrasil.pipeline.cli run-audit --verify-reconciliation

# Executar linter estático de UI (achromatic-ledger)
node .agents/skills/design-taste-frontend/scripts/lint.mjs --app wireframe_de_olho_no_brasil.html
```

## 3. Mapa da Documentação Versionada

- **Diretrizes de Agentes e Model Routing (`flash_lite`, `flash`, `pro`):** [`AGENTS.md`](AGENTS.md)
- **Visão de Produto, MVP e Roadmap:** [`docs/product/vision.md`](docs/product/vision.md), [`docs/product/mvp.md`](docs/product/mvp.md), [`docs/product/roadmap.md`](docs/product/roadmap.md)
- **Arquitetura, Dados, Segurança e ADRs:** [`docs/architecture/system-context.md`](docs/architecture/system-context.md), [`docs/architecture/data-architecture.md`](docs/architecture/data-architecture.md), [`docs/architecture/security.md`](docs/architecture/security.md), [`docs/architecture/adr/README.md`](docs/architecture/adr/README.md)
- **Especificações SDD (`SPEC-0001` a `SPEC-0004`):** [`docs/specs/`](docs/specs/)
- **Qualidade, Definition of Done e Matriz de Rastreabilidade:** [`docs/quality/definition-of-done.md`](docs/quality/definition-of-done.md), [`docs/quality/test-strategy.md`](docs/quality/test-strategy.md), [`docs/quality/traceability-matrix.md`](docs/quality/traceability-matrix.md)
