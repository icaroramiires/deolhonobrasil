# Tarefas: SPEC-0004 (`DONB-3`, `DONB-4`, `DONB-9`, `DONB-10`, `DONB-11`)

| ID | Jira | Descrição | Requisitos | Arquivos Afetados | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`TASK-0401`** | `DONB-9` | Implementar wireframe web `wireframe_de_olho_no_brasil.html` com padrão `achromatic-ledger`, 3 camadas epistêmicas, inspetor `SHA-256` e reconciliação client-side via `console.assert`. | `FR-010`, `NFR-006`, `DATA-006`, `AC-014` | `wireframe_de_olho_no_brasil.html`, `.taste-skill/direction.json` | **Verificado** |
| **`TASK-0402`** | `DONB-10` | Construir serviço e servidor de API REST Hexagonal (`CivicAuditAPIService`, `CivicAuditHTTPApp`, `create_fastapi_app`) com RLS, rate limiting, mascaramento LGPD e headers de segurança (Checkpoint 3). | `FR-011`, `DATA-006`, `SEC-006`, `SEC-007`, `AC-015`, `AC-016` | `src/deolhonobrasil/api/__init__.py`, `src/deolhonobrasil/api/service.py`, `tests/test_api_and_ops.py` | **Verificado** |
| **`TASK-0403`** | `DONB-11` | Implementar artefatos de reprodutibilidade e operação segura (`Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`) e validar no harness (Checkpoint 4). | `NFR-007`, `SEC-006`, `AC-017` | `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `tests/test_api_and_ops.py` | **Verificado** |
