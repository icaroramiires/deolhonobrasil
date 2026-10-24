# Roadmap Incremental por Checkpoints — De Olho no Brasil

O desenvolvimento segue Checkpoints formais governados pelo workflow **Spec-Driven Development (SDD)** e rastreados no Jira (`DONB-1` a `DONB-15`):

| Checkpoint | Épico Jira | Especificações SDD | Entregáveis Principais | Status Atual |
| :--- | :--- | :--- | :--- | :--- |
| **Checkpoint 1** | `DONB-1` (`DONB-5`, `DONB-12`) | [`SPEC-0001-data-pipeline`](../specs/SPEC-0001-data-pipeline/spec.md)<br>[`SPEC-0005-live-http-collectors`](../specs/SPEC-0005-live-http-collectors/spec.md) | Fundação técnica (`AGPL-3.0-or-later`, `SECURITY.md`, `TRADEMARK.md`), privacidade LGPD, 4 conectores federais (CEAP, CEAPS, CGU, PNCP), coletores HTTP resilientes com guarda Anti-SSRF (`https://` + `.gov.br`/`.leg.br`) e reconciliação exata em `Decimal`. | **Verificado (`100%`)** |
| **Checkpoint 2** | `DONB-2` (`DONB-6`, `DONB-7`, `DONB-13`, `DONB-14`, `DONB-15`) | [`SPEC-0002-audit-and-laya`](../specs/SPEC-0002-audit-and-laya/spec.md)<br>[`SPEC-0003-editorial-governance`](../specs/SPEC-0003-editorial-governance/spec.md)<br>[`SPEC-0006-editorial-admin-and-evidence-bundle`](../specs/SPEC-0006-editorial-admin-and-evidence-bundle/spec.md)<br>[`SPEC-0007-cross-source-sanctions-and-divergence`](../specs/SPEC-0007-cross-source-sanctions-and-divergence/spec.md)<br>[`SPEC-0008-benford-and-split-expense-rules`](../specs/SPEC-0008-benford-and-split-expense-rules/spec.md) | Estatística em `Decimal` (`Z-Score`, `MAD`, `HHI`, `Benford`), 7 regras determinísticas (incluindo cruzamento `CEIS/CNEP`, divergência de emendas, fracionamento de despesa em janela móvel e desvio de Benford em lotes), motor *System 1* `Laya`, `GroundedDossierNarrator`, governança híbrida RLS, Direito de Resposta, API administrativa e `VerifiableEvidenceBundle` (`SHA-256`). | **Verificado (`100%`)** |
| **Transversal (ECC SDD)** | `DONB-3` (`DONB-8`) | Todas (`SPEC-0001` a `SPEC-0008`) | Configuração do workflow SDD de 8 fases, roteamento de subagentes em 3 tiers (`flash_lite`, `flash`, `pro`), `runner.py` e matriz de rastreabilidade. | **Verificado (`100%`)** |
| **Checkpoint 3** | `DONB-4` (`DONB-9`, `DONB-10`) | [`SPEC-0004-web-and-api`](../specs/SPEC-0004-web-and-api/spec.md) | Interface interativa `achromatic-ledger` (`DONB-9`) integrada em tempo real com API WSGI/REST (`CivicAuditHTTPApp`: `/api/v1/dossiers`, `/expenses`, `/reconciliation`, `/sanctions`, `/right-of-reply`) + comando `serve` (`DONB-10`). | **Verificado (`100%`)** |
| **Checkpoint 4** | `DONB-4` (`DONB-11`) | [`SPEC-0004-web-and-api`](../specs/SPEC-0004-web-and-api/spec.md) | Endurecimento de infraestrutura (`Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, rate limiting, headers de segurança, execução non-root) e revisão adversarial dupla (`santa-method`). | **Verificado (`100%`)** |




