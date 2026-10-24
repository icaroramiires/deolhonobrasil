# Architecture Decision Records (ADRs) — De Olho no Brasil

Este diretório registra as decisões arquiteturais estruturantes do projeto **De Olho no Brasil**, seguindo a skill `architecture-decision-records` do ECC.

## Índice de ADRs

| ID | Título | Status | Data | Especificações Relacionadas |
| :--- | :--- | :--- | :--- | :--- |
| [ADR-0001](0001-ecc-loop-engineering-sdd-and-eval-harness.md) | Arquitetura Medallion Lakehouse (SQLite/Parquet), Proveniência SHA-256 e Quarentena Estrita | Aceito | 2026-10-23 | `SPEC-0001` |
| [ADR-0002](0002-tiered-subagent-model-routing-token-economy.md) | Motor de Decisão System 1 (`Laya` Adapter) e Roteamento de Subagentes por Tier | Aceito | 2026-10-23 | `SPEC-0002` |
| [ADR-0003](0003-three-layer-epistemic-governance-and-laya-system1.md) | Governança Epistêmica em 3 Camadas, Direito de Resposta Lado a Lado e Row-Level Security (RLS) | Aceito | 2026-10-23 | `SPEC-0003`, `SPEC-0004` |
| [ADR-0004](0004-hexagonal-rest-api-and-security-headers.md) | API Pública Hexagonal (Stdlib WSGI/HTTP + Adaptador FastAPI), Rate Limiting e Headers de Segurança | Aceito | 2026-10-23 | `SPEC-0004` |
| [ADR-0005](0005-resilient-government-http-collectors-and-ssrf-guard.md) | Coletores HTTP Resilientes de Fontes Governamentais, Proteção SSRF (`.gov.br`/`.leg.br`) e Transporte Injetável | Aceito | 2026-10-23 | `SPEC-0005` |
| [ADR-0006](0006-verifiable-evidence-bundles-and-editorial-admin-api.md) | Fluxo Administrativo de Revisão Humana via API e Pacote de Evidências Verificável (`SHA-256`) | Aceito | 2026-10-23 | `SPEC-0006` |
| [ADR-0007](0007-cross-source-ceis-cnep-sanctions-and-divergence-rules.md) | Cruzamento Multicritério CEIS/CNEP, Divergência entre Fontes e Prevenção de Homonímia LGPD | Aceito | 2026-10-23 | `SPEC-0007` |
| [ADR-0008](0008-benford-distribution-and-split-expense-audit-rules.md) | Detecção de Fracionamento de Despesas e Avaliação da Lei de Benford em Lotes | Aceito | 2026-10-24 | `SPEC-0008` |
