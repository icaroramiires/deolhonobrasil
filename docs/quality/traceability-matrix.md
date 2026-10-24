# De Olho no Brasil — Matriz de Rastreabilidade Oficial (SDD ↔ Jira ↔ Código ↔ Testes)

**Versão:** 1.1.0  
**Status:** 100% Verificada (`SPEC-0001..0004`, `50/50` testes, `45/45` Test Anchors, `pass^3 = 1.0`)

---

## 1. Visão Geral dos Pacotes de Especificação (`docs/specs/`)

| Spec ID | Pacote SDD | Épico / Tasks Jira | Status no Ciclo de Vida |
| :--- | :--- | :--- | :--- |
| **`SPEC-0001`** | [`docs/specs/SPEC-0001-data-pipeline/`](../specs/SPEC-0001-data-pipeline/spec.md) | `DONB-1`, `DONB-5` (`TASK-0101..0104`) | **Verificado** (`11/11` Test Anchors verdes) |
| **`SPEC-0002`** | [`docs/specs/SPEC-0002-audit-and-laya/`](../specs/SPEC-0002-audit-and-laya/spec.md) | `DONB-2`, `DONB-6` (`TASK-0201..0204`) | **Verificado** (`14/14` Test Anchors verdes) |
| **`SPEC-0003`** | [`docs/specs/SPEC-0003-editorial-governance/`](../specs/SPEC-0003-editorial-governance/spec.md) | `DONB-2`, `DONB-7` (`TASK-0301..0304`) | **Verificado** (`12/12` Test Anchors verdes) |
| **`SPEC-0004`** | [`docs/specs/SPEC-0004-web-and-api/`](../specs/SPEC-0004-web-and-api/spec.md) | `DONB-3`, `DONB-4`, `DONB-9`, `DONB-10`, `DONB-11` (`TASK-0401..0403`) | **Verificado** (`8/8` Test Anchors verdes) |

---

## 2. Matriz Completa: Requisito $\rightarrow$ Critério de Aceite $\rightarrow$ Tarefa $\rightarrow$ Código $\rightarrow$ Teste $\rightarrow$ Status

| Spec | Req ID | Tipo | Critério (`AC-*`) | Task / Jira | Implementação (`src/` ou raiz) | Teste Automatizado (`tests/`) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `SPEC-0001` | `FR-001` | Funcional | `AC-001` | `TASK-0101` (`DONB-1`) | `src/deolhonobrasil/pipeline/connectors.py` | `test_camara_ceap_connector_validates_and_quarantines`, `test_cgu_amendments_and_pncp_contracts_connectors` | **Verificado** |
| `SPEC-0001` | `FR-002` | Funcional | `AC-001`, `AC-003` | `TASK-0101` (`DONB-1`) | `src/deolhonobrasil/pipeline/models.py`, `privacy.py` | `test_valid_cnpj_and_invalid_cnpj`, `test_senado_ceaps_connector_validates_and_quarantines_missing_amount` | **Verificado** |
| `SPEC-0001` | `FR-003` | Funcional | `AC-004` | `TASK-0103` (`DONB-5`) | `src/deolhonobrasil/pipeline/storage.py` | `test_lakehouse_idempotency_and_reconciliation` | **Verificado** |
| `SPEC-0001` | `FR-004` | Funcional | `AC-005` | `TASK-0104` (`DONB-5`) | `src/deolhonobrasil/pipeline/cli.py` | `test_end_to_end_cli_sample_pipeline` | **Verificado** |
| `SPEC-0001` | `DATA-001` | Dados | `AC-003` | `TASK-0102` (`DONB-1`) | `src/deolhonobrasil/pipeline/privacy.py` (`parse_strict_monetary_value`) | `test_missing_monetary_value_never_becomes_zero` | **Verificado** |
| `SPEC-0001` | `DATA-002` | Dados | `AC-004` | `TASK-0103` (`DONB-5`) | `src/deolhonobrasil/pipeline/storage.py` | `test_lakehouse_idempotency_and_reconciliation` | **Verificado** |
| `SPEC-0001` | `DATA-003` | Dados | `AC-004` | `TASK-0103` (`DONB-5`) | `src/deolhonobrasil/pipeline/models.py` (`ReconciliationReport`) | `test_lakehouse_idempotency_and_reconciliation` | **Verificado** |
| `SPEC-0001` | `SEC-001` | Segurança/LGPD | `AC-002` | `TASK-0102` (`DONB-1`) | `src/deolhonobrasil/pipeline/privacy.py` (`normalize_and_protect_document`) | `test_cpf_lgpd_masking_on_normalization`, `test_already_masked_cgu_cpf_is_preserved` | **Verificado** |
| `SPEC-0001` | `SEC-002` | Segurança | `AC-002` | `TASK-0102` (`DONB-1`) | `src/deolhonobrasil/pipeline/privacy.py`, `models.py` | `test_prompt_injection_and_control_chars_sanitization`, `test_editorial_policy_blocks_accusatory_language` | **Verificado** |
| `SPEC-0001` | `NFR-001`, `NFR-002` | Não Funcional | `AC-004`, `AC-005` | `TASK-0103` (`DONB-5`) | `src/deolhonobrasil/pipeline/storage.py` | `test_lakehouse_idempotency_and_reconciliation` | **Verificado** |
| `SPEC-0002` | `FR-005` | Funcional | `AC-006` | `TASK-0201` (`DONB-6`) | `src/deolhonobrasil/audit/statistics.py` | `test_parametric_z_score_calculation`, `test_mad_z_score_calculation`, `test_hhi_concentration`, `test_benford_first_digit_evaluation` | **Verificado** |
| `SPEC-0002` | `FR-006` | Funcional | `AC-006`, `AC-007` | `TASK-0202` (`DONB-6`) | `src/deolhonobrasil/audit/rules.py` | `test_contract_overpricing_rule`, `test_supplier_concentration_rule`, `test_ceap_quota_outlier_rule` | **Verificado** |
| `SPEC-0002` | `FR-007` | Funcional | `AC-008`, `AC-009` | `TASK-0203`, `TASK-0204` (`DONB-6`) | `src/deolhonobrasil/audit/laya_engine.py`, `rag_narrator.py` | `test_adapter_satisfies_protocol`, `test_narrator_generates_three_epistemic_blocks` | **Verificado** |
| `SPEC-0002` | `AI-001`, `AI-002` | IA / Decisão | `AC-008` | `TASK-0203` (`DONB-6`) | `src/deolhonobrasil/audit/laya_engine.py` | `test_high_severity_routes_to_human_review`, `test_system1_never_auto_publishes_nominal_accusation`, `test_official_reply_discount` | **Verificado** |
| `SPEC-0002` | `AI-003`, `DATA-004` | IA / Dados | `AC-009` | `TASK-0204` (`DONB-6`) | `src/deolhonobrasil/audit/rag_narrator.py` | `test_narrator_generates_three_epistemic_blocks`, `test_narrator_refuses_empty_provenance` | **Verificado** |
| `SPEC-0002` | `SEC-003`, `NFR-003`, `NFR-004` | Segurança / NFR | `AC-007` | `TASK-0202` (`DONB-6`) | `src/deolhonobrasil/audit/rules.py` | `test_audit_signal_non_accusatory_enforcement` | **Verificado** |
| `SPEC-0003` | `FR-008` | Funcional | `AC-011` | `TASK-0302` (`DONB-7`) | `src/deolhonobrasil/governance/right_of_reply.py`, `dossiers.py` | `test_right_of_reply_attachment_and_clarification`, `test_right_of_reply_persistence_and_clarification` | **Verificado** |
| `SPEC-0003` | `FR-009` | Funcional | `AC-012` | `TASK-0302` (`DONB-7`) | `src/deolhonobrasil/governance/dossiers.py` | `test_rectify_material_error`, `test_material_error_rectification_persistence` | **Verificado** |
| `SPEC-0003` | `DATA-005`, `NFR-005` | Dados / NFR | `AC-013` | `TASK-0303` (`DONB-7`) | `src/deolhonobrasil/pipeline/storage.py`, `rls_policies.sql` | `test_editorial_audit_trail_immutability`, `test_cli_run_audit_pipeline` | **Verificado** |
| `SPEC-0003` | `SEC-004`, `SEC-005` | Segurança / RLS | `AC-010` | `TASK-0301`, `TASK-0304` (`DONB-7`) | `src/deolhonobrasil/governance/dossiers.py`, `rls_policies.sql` | `test_visibility_governance_rls`, `test_published_dossier_requires_reviewer`, `test_rls_sql_file_exists_and_contains_policies`, `test_dossier_upsert_and_role_visibility_filtering`, `test_right_of_reply_prompt_injection_sanitization`, `test_right_of_reply_rejects_accusatory_text` | **Verificado** |
| `SPEC-0004` | `FR-010`, `NFR-006`, `DATA-006` | Funcional / UI / Dados | `AC-014` | `TASK-0401` (`DONB-9`) | `wireframe_de_olho_no_brasil.html`, `.taste-skill/direction.json` | `test_wireframe_passes_achromatic_ledger_structural_invariants` + `lint.mjs` / `inspect.mjs` | **Verificado** |
| `SPEC-0004` | `FR-011`, `SEC-006`, `SEC-007` | Funcional / API / Segurança | `AC-015`, `AC-016`, `AC-017` | `TASK-0402` (`DONB-10`) | `src/deolhonobrasil/api/service.py` | `test_health_and_security_headers`, `test_get_dossiers_enforces_rls_for_public_vs_admin`, `test_get_expenses_and_reconciliation_decimal_totals`, `test_post_right_of_reply_creates_protocol_and_masks_cpf`, `test_post_right_of_reply_blocks_accusatory_and_sanitizes_injection`, `test_rate_limiter_blocks_excessive_requests_with_429` | **Verificado** |
| `SPEC-0004` | `NFR-007` | DevSecOps / CI/CD | `AC-017` | `TASK-0403` (`DONB-11`) | `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml` | `test_dockerfile_compose_and_github_ci_exist_and_run_harness` | **Verificado** |
