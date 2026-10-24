# ADR-0004: API Pública Hexagonal (Stdlib WSGI/HTTP + Adaptador FastAPI), Rate Limiting e Headers de Segurança

- **Status:** Aceito
- **Data:** 2026-10-23
- **Decisores:** Arquitetura De Olho no Brasil (`SPEC-0004`)
- **Requisitos Relacionados:** `FR-010`, `FR-011`, `NFR-006`, `NFR-007`, `DATA-006`, `SEC-006`, `SEC-007`

---

## Contexto e Problema

O Checkpoint 3 (`DONB-10`) e o Checkpoint 4 (`DONB-11`) exigem que a plataforma **De Olho no Brasil** exponha uma API REST pública e segura (`/api/v1/dossiers`, `/api/v1/expenses`, `/api/v1/reconciliation`, `POST /api/v1/right-of-reply`) conectada ao `CivicLakehouseStorage`, além de empacotamento reprodutível (`Dockerfile`, `docker-compose.yml` e pipeline `.github/workflows/ci.yml`).

Assim como observado no `ADR-0002` (motor `Laya`), o ambiente de verificação contínua e testes locais em Python 3.14 deve ser capaz de executar 100% dos testes de integração HTTP, validação de schemas, rate limiting, Row-Level Security (RLS) e headers de segurança **sem depender de rede externa ou pacotes binários ausentes**, ao mesmo tempo em que suporta montagem nativa em `FastAPI` quando instalado em produção.

---

## Decisão

Adotamos uma **Arquitetura Hexagonal de API REST (`src/deolhonobrasil/api/`)** composta por:

1. **Núcleo de Aplicação Independente de Framework (`CivicAuditAPIService`):**
   - Recebe `CivicLakehouseStorage` por injeção de dependência.
   - Implementa paginação determinística (`limit`, `offset`), filtragem de despesas (`year`, `uf`, `organ_code`), relatório de reconciliação em `Decimal` (`GET /api/v1/reconciliation`) e submissão validada de Direito de Resposta (`POST /api/v1/right-of-reply`).
   - Impede vazamento de dossiês em `EM_TRIAGEM_INTERNA`: requisições sem token administrativo validado operam estritamente sob `AccessRole.PUBLIC_READER`.
2. **Camada de Segurança, Rate Limiting e Headers (`SEC-006` / `SEC-007`):**
   - Rate limiter em memória por IP (`SlidingWindowRateLimiter`) configurável para bloquear abuso (`HTTP 429 Too Many Requests`).
   - Injeção automática de headers de segurança em todas as respostas:
     - `Content-Security-Policy: default-src 'self'`
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`
     - `Referrer-Policy: strict-origin-when-cross-origin`
     - `Cache-Control: no-store` (para rotas de mutação/admin)
3. **Adaptador Duplo (WSGI/HTTP Nativo + FastAPI):**
   - `CivicAuditASGIOrWSGIApp` permite execução imediata via `wsgiref` / `http.server` e testes síncronos de contrato sem dependências externas.
   - `create_fastapi_app(storage)` monta automaticamente as mesmas rotas e contratos em uma instância `FastAPI` caso o pacote esteja instalado no ambiente.

---

## Consequências

- **Positivas:** 100% dos contratos HTTP, códigos de status (`200`, `201`, `400`, `403`, `404`, `422`, `429`), políticas RLS, sanitização de *prompt injection* e headers de segurança são testados deterministicamente em milissegundos pela suíte `unittest` e pelo `runner.py`.
- **Negativas / Trade-offs:** Manutenção de um adaptador leve de roteamento HTTP padrão junto à fábrica `create_fastapi_app`.
