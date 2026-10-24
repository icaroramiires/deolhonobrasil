# De Olho no Brasil — Arquitetura de Segurança, Privacidade (LGPD) e Proteção Jurídica

**Versão:** 1.0.0  
**Referências SDD:** `SPEC-0001`, `SPEC-0002`, `SPEC-0003`, `SPEC-0004`, `ADR-0003`

---

## 1. Controles de Segurança e Privacidade (`SEC-001` a `SEC-006`)

| ID | Controle | Implementação no Repositório | Verificação Automatizada |
| :--- | :--- | :--- | :--- |
| **`SEC-001`** | **LGPD por Padrão (Mascaramento de CPF na Ingestão)** | `mask_cpf_for_lgpd` e `normalize_creditor_document` em `src/deolhonobrasil/pipeline/privacy.py` convertem CPFs de 11 dígitos para `***.XXX.XXX-**` antes da persistência. | `test_cpf_lgpd_masking_on_normalization` |
| **`SEC-002`** | **Defesa contra Prompt Injection Indireto** | `sanitize_untrusted_public_text` neutraliza padrões como `IGNORE ALL PREVIOUS INSTRUCTIONS`, `SYSTEM PROMPT:`, `<script>` e caracteres de controle ASCII em descrições de notas fiscais e manifestações de Direito de Resposta. | `test_prompt_injection_and_control_chars_sanitization`, `test_right_of_reply_prompt_injection_sanitization` |
| **`SEC-003`** | **Bloqueio Léxico de Linguagem Acusatória** | `assert_non_accusatory_language` bloqueia a criação de qualquer `AuditSignal`, `System1Decision`, `GroundedDossierSection` ou `RightOfReplySubmission` que contenha termos de juízo penal (`"fraude comprovada"`, `"corrupção"`, `"roubo"`, `"desvio intencional"`, `"criminoso"`, `"culpado"`, `"superfaturamento comprovado"`). | `test_editorial_policy_blocks_accusatory_language`, `test_audit_signal_non_accusatory_enforcement` |
| **`SEC-004`** | **Governança Híbrida de Publicação (Zero Acusação Automática)** | O motor `LayaSystem1Adapter` nunca publica dossiês nominais de alta severidade diretamente; scores $\ge 0.70$ recebem `TriageAction.REVISAO_HUMANA` e nascem em `EM_TRIAGEM_INTERNA`. | `test_high_severity_routes_to_human_review`, `test_system1_never_auto_publishes_nominal_accusation` |
| **`SEC-005`** | **Isolamento por Row-Level Security (RLS)** | No código (`is_visible_to_role` e `list_dossiers_for_role`) e no banco (`src/deolhonobrasil/governance/rls_policies.sql`), o perfil `public_reader` / `anon` só visualiza dossiês com `reviewer_id IS NOT NULL` e status pós-revisão. | `test_visibility_governance_rls`, `test_dossier_upsert_and_role_visibility_filtering`, `test_rls_sql_file_exists_and_contains_policies` |
| **`SEC-006`** | **Segurança de API e Segredos** | Nenhuma credencial é versionada no repositório; rotas de revisão e moderação exigem autenticação com MFA e trilha de auditoria append-only (`editorial_audit_trail`). | Fase 4 do Harness (`verify_six_phase_loop`) |
