# ADR-0002: Orquestração de Subagentes em 3 Tiers de Modelos (`flash_lite`, `flash`, `pro`)

**Date**: 2026-10-23
**Status**: accepted
**Deciders**: Ícaro Ramires, Antigravity Agent Harness

## Context

A execução de fluxos multi-agentes com verificação adversarial (`santa-method`), inspeção de portais governamentais e construção de código pode consumir um volume elevado de tokens caso todas as subtarefas herdem indiscriminadamente o modelo mais pesado (`pro` / `inherit`).

## Decision

Estabelecemos uma política estrita de **Model Routing em 3 Tiers** documentada em [`AGENTS.md`](../../AGENTS.md) e [`.agents/rules/subagent-model-routing.md`](../../.agents/rules/subagent-model-routing.md):
- **Tier 1 (`flash_lite`):** `donb-compliance-linter`, `donb-portal-scout`, `docs-lookup`, `doc-updater`, `comment-analyzer` (lints léxicos, verificação de CPF/SHA-256, documentação).
- **Tier 2 (`flash`):** `donb-etl-builder`, `donb-ui-builder`, `donb-browser-qa`, `tdd-guide`, `e2e-runner`, `code-explorer` (implementação de conectores ETL, UI `achromatic-ledger`, testes e automação com `agent-browser`).
- **Tier 3 (`pro`):** `donb-audit-ai-architect`, `security-reviewer`, `python-reviewer`, `database-reviewer`, `architect`, `planner` (regras matemáticas de auditoria, motor `Laya`, políticas RLS e revisão adversarial final).

## Alternatives Considered

### Alternative 1: Usar `Model="inherit"` em todas as invocações de subagentes
- **Pros**: Configuração zero.
- **Cons**: Desperdício de 60%–80% do orçamento de tokens em tarefas mecânicas de lint e formatação.
- **Why not**: Viola a meta de eficiência de custo operacional do projeto.

## Consequences

### Positive
- Redução drástica no consumo de tokens mantendo raciocínio profundo (`pro`) onde há risco matemático, jurídico ou de segurança.
- Uso do binário nativo `agent-browser` (Rust) reduz snapshots de interface para ~200–400 tokens.

### Negative
- Exige que o agente orquestrador selecione explicitamente o parâmetro `Model` em cada chamada `invoke_subagent`.
