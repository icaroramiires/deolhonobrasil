# Architecture Decision Records (ADRs) — De Olho no Brasil

Este diretório registra as decisões arquiteturais estruturantes do projeto **De Olho no Brasil**, seguindo a skill `architecture-decision-records` do ECC.

## Índice de ADRs

| ID | Título | Status | Data | Especificações Relacionadas |
| :--- | :--- | :--- | :--- | :--- |
| [ADR-0001](0001-medallion-lakehouse-and-sha256-provenance.md) | Arquitetura Medallion Lakehouse (SQLite/Parquet), Proveniência SHA-256 e Quarentena Estrita | Aceito | 2026-10-23 | `SPEC-0001` |
| [ADR-0002](0002-laya-system1-adapter-and-deterministic-rules.md) | Motor de Decisão System 1 (`Laya` Adapter) Combinado com Regras Estatísticas Determinísticas | Aceito | 2026-10-23 | `SPEC-0002` |
| [ADR-0003](0003-three-tier-epistemic-governance-and-rls.md) | Governança Epistêmica em 3 Camadas, Direito de Resposta Lado a Lado e Row-Level Security (RLS) | Aceito | 2026-10-23 | `SPEC-0003`, `SPEC-0004` |
| [ADR-0004](0004-hexagonal-rest-api-and-security-headers.md) | API Pública Hexagonal (Stdlib WSGI/HTTP + Adaptador FastAPI), Rate Limiting e Headers de Segurança | Aceito | 2026-10-23 | `SPEC-0004` |
