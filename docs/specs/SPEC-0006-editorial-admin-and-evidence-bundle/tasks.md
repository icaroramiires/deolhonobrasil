# Decomposição de Tarefas — SPEC-0006 (Jira: DONB-13)

- **`TASK-0601`**: Implementar modelo imutável `VerifiableEvidenceBundle` com serialização canônica JSON (`sort_keys=True`) e cálculo determinístico de `bundle_sha256` (`DATA-008`, `NFR-009`, `AC-025`).
- **`TASK-0602`**: Implementar rotas administrativas autenticadas via `hmac.compare_digest` (`POST /api/v1/admin/dossiers/approve`, `POST /api/v1/admin/dossiers/rectify`, `GET /api/v1/admin/audit-trail`) com validação de linguagem não-acusatória nas retificações (`FR-014`, `SEC-009`, `AC-022`, `AC-024`).
- **`TASK-0603`**: Implementar o endpoint de exportação `GET /api/v1/dossiers/evidence-bundle` com bloqueio RLS/filtro para dossiês em `EM_TRIAGEM_INTERNA` para perfis `public_reader` (`FR-015`, `SEC-009`, `AC-023`).
