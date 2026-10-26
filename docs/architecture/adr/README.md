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
| [ADR-0009](0009-shared-cnpj-root-and-corporate-group-audit-rules.md) | Detecção de Vínculo Societário por Radical de CNPJ Compartilhado e Monopólio de Fornecedores | Aceito | 2026-10-24 | `SPEC-0009` |
| [ADR-0010](0010-duplicate-document-and-spatiotemporal-overlap-rules.md) | Detecção de Documentos Fiscais em Duplicidade e Sobreposição Espaço-Temporal | Aceito | 2026-10-24 | `SPEC-0010` |
| [ADR-0011](0011-temporal-recess-and-holiday-expense-audit-rules.md) | Detecção de Despesas em Fins de Semana, Feriados Nacionais e Recessos Parlamentares | Aceito | 2026-10-24 | `SPEC-0011` |
| [ADR-0012](0012-electoral-campaign-donations-crossmatch.md) | Cruzamento entre Fornecedores Públicos e Doadores de Campanha Eleitoral (TSE) | Aceito | 2026-10-24 | `SPEC-0012` |
| [ADR-0013](0013-corporate-members-qsa-and-individual-donor-crossmatch.md) | Quadro de Sócios (QSA/RFB): Sócios Comuns e Doações Eleitorais de Pessoas Físicas | Aceito | 2026-10-24 | `SPEC-0013` |
| [ADR-0014](0014-company-age-and-capital-social-disproportionality.md) | Empresas Recém-Abertas e Capital Social Desproporcional | Aceito | 2026-10-25 | `SPEC-0014` |
| [ADR-0015](0015-cnae-and-contract-object-compatibility.md) | Incompatibilidade entre Atividade Econômica (CNAE/RFB) e Objeto Contratual | Aceito | 2026-10-25 | `SPEC-0015` |
| [ADR-0016](0016-public-agent-supplier-conflict-of-interest.md) | Conflito de Interesses: Servidores no QSA de Fornecedores do Próprio Órgão | Aceito | 2026-10-25 | `SPEC-0016` |
| [ADR-0017](0017-shared-company-address-and-collusion-risk.md) | Indícios de Conluio: Fornecedores com Mesmo Endereço Físico Cadastral | Aceito | 2026-10-25 | `SPEC-0017` |
| [ADR-0018](0018-sanctioned-partner-qsa-crossmatch.md) | Burla à Sanção Administrativa: Sócios (QSA) com Sanção Ativa no CEIS/CNEP | Aceito | 2026-10-26 | `SPEC-0018` |
| [ADR-0019](0019-civic-ui-and-design-system-integration.md) | Interface Web Cívica, Design System Unificado (Tokens, Temas, Responsividade P0) | Aceito | 2026-10-26 | `SPEC-0019` |


