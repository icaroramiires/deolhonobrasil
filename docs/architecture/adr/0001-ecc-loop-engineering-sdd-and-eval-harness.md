# ADR-0001: Fluxo de Loop Engineering, Spec-Driven Development (SDD) e Eval Harness com ECC

**Date**: 2026-10-23
**Status**: accepted
**Deciders**: Ícaro Ramires (Lead Product & Architecture), Antigravity Agent Harness

## Context

Plataformas de auditoria cívica assistidas por IA enfrentam dois riscos críticos no ciclo de engenharia:
1. **Deriva de especificação e alucinação de requisitos:** agentes codificarem funcionalidades que violam invariantes jurídicos (linguagem não-acusatória, LGPD, reconciliação centavo a centavo).
2. **Goodharting de verificadores em loops autônomos (`loop-design-check`):** um agente enfraquecer testes ou pular validações para declarar um checkpoint concluído.

## Decision

Adotamos um fluxo formal de **Loop Engineering + Spec-Driven Development (SDD) + Eval-Driven Development (EDD)** orquestrado pelas skills do pacote `ecc-universal@2.2.0` e executado deterministicamente pelo pacote [`deolhonobrasil.harness.runner`](../../src/deolhonobrasil/harness/runner.py):

1. **Planning & Spec-Driven Development (`intent-driven-development` + `spec-miner`):** Toda capacidade possui especificação formal em `openspec/specs/<capability>/spec.md` com blocos explícitos `REQ-*`, `AC-*`, `INV-*` e `Test Anchors` verificáveis por máquina.
2. **Pre-Action Gate (`gateguard`):** Nenhuma alteração estrutural ocorre sem verificar entidades imutáveis (`frozen=True`), contratos de importação e piso anti-Goodhart de testes (`MIN_EXPECTED_UNIT_TESTS`).
3. **6-Phase Deterministic Verification Loop (`verification-loop` + `delivery-gate`):** Compilação de bytecode (`py_compile`), checagem de anotações de tipo, lint léxico/LGPD/RLS/UI (`lint.mjs --app`), suíte `unittest` completa, reconciliação financeira (`run-audit --verify-reconciliation`) e higiene documental.
4. **Eval Harness & Dual Adversarial Review (`eval-harness` + `santa-method`):** Medição de `pass@1` e `pass^k` e exigência de aprovação independente por dois subagentes revisores antes de fechar qualquer Checkpoint.

## Alternatives Considered

### Alternative 1: Testes unitários ad-hoc sem especificações formais nem Harness
- **Pros**: Menor esforço inicial de escrita de especificações.
- **Cons**: Sem rastreabilidade entre invariantes jurídicos/epistêmicos e testes; vulnerável a regressões silenciosas.
- **Why not**: Incompatível com o rigor jurídico e de confiabilidade exigido pelo De Olho no Brasil.

### Alternative 2: Loop autônomo puro sem fronteiras anti-Goodhart nem trava humana
- **Pros**: Execução contínua sem paradas.
- **Cons**: Risco clássico apontado pela skill `loop-design-check` (exclusão de testes ou auto-aprovação de código defeituoso).
- **Why not**: Viola a separação cibernética entre *Execução* (máquina) e *Julgamento* (humano).

## Consequences

### Positive
- 100% dos requisitos (`REQ-*`) e invariantes (`INV-*`) de cada Checkpoint são verificados por âncoras de teste reais em menos de 2 segundos via `PYTHONPATH=src python3 -m deolhonobrasil.harness.runner`.
- Proteção mecânica contra regressões de LGPD, vocabulário acusatório ou divergência de centavos.

### Negative
- Toda nova funcionalidade exige atualização coordenada da spec em `openspec/specs/` e de sua âncora em `tests/`.
