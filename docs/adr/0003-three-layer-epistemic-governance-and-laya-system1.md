# ADR-0003: Governança Epistêmica em 3 Camadas, Motor *System 1* `Laya` e Reconciliação em `Decimal`

**Date**: 2026-10-23
**Status**: accepted
**Deciders**: Ícaro Ramires, Antigravity Agent Harness

## Context

Sistemas automatizados que analisam despesas públicas correm risco jurídico severo (calúnia, difamação, dano moral objetivo) e técnico caso confundam anomalias estatísticas com prova de ilicitude ou apresentem somas financeiras divergentes da fonte oficial.

## Decision

1. **Separação Epistêmica Obrigatória em 3 Camadas:** Todo sinal e dossiê separa estruturalmente `[DADO OFICIAL]`, `[INFERÊNCIA ESTATÍSTICA]` e `[HIPÓTESE DE AUDITORIA / LIMITAÇÃO]`, com bloqueio léxico determinístico (`assert_non_accusatory_language`).
2. **Motor *System 1* `Laya` com Trava Humana:** O adaptador `LayaSystem1Adapter` calcula `choice`, `score` e `noul_classification`, mas qualquer sinal com `score >= 0.70` ou menção nominal é roteado obrigatoriamente para `TriageAction.REVISAO_HUMANA` (`EM_TRIAGEM_INTERNA`), invisível ao `public_reader` tanto na aplicação quanto via PostgreSQL Row-Level Security (`rls_policies.sql`) e SQLite triggers.
3. **Reconciliação Centavo a Centavo em `Decimal`:** Todas as operações financeiras e estatísticas utilizam `decimal.Decimal` e exigem discrepância zero (`R$ 0,00`) no `ReconciliationReport`.

## Alternatives Considered

### Alternative 1: LLM gerando classificação livre de suspeita e publicação imediata
- **Pros**: Fluxo sem fila de moderação.
- **Cons**: Alto risco de alucinação, vulnerabilidade a prompt injection indireto e exposição jurídica imediata.
- **Why not**: Incompatível com os princípios de Rastreabilidade, Confiabilidade e Proteção Jurídica do projeto.

## Consequences

### Positive
- Dossiês auditáveis até o `SHA-256` do payload bruto original, com Direito de Resposta lado a lado em igual destaque visual.
- Trilha editorial imutável (`editorial_audit_trail`) protegida por triggers no banco de dados.

### Negative
- Publicação de dossiês nominais de alta criticidade depende de aprovação humana (`reviewer_admin`).
