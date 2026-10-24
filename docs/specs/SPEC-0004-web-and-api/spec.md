# SPEC-0004 — Interface Pública (`achromatic-ledger`), API REST Hexagonal e Operação Segura (CI/CD)

## 1. Identificador e Título
- **ID:** `SPEC-0004`
- **Título:** Interface Pública (`achromatic-ledger`), API REST Hexagonal e Operação Segura (CI/CD)
- **Subsistema:** Public Web UI, REST API & DevSecOps

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** `1.1.0`
- **Data:** `2026-10-23`

## 3. Problema e Motivação
Cidadãos, jornalistas e pesquisadores precisam consultar dossiês revisados, despesas curadas e relatórios de reconciliação contábil por meio de uma interface web de alta precisão (`achromatic-ledger`) e de uma API REST auditável, protegida contra abuso (rate limiting), injeção de prompts, vazamento de dados pessoais (LGPD) e exposição acidental de dossiês ainda em triagem interna (`EM_TRIAGEM_INTERNA`). Além disso, o projeto precisa de infraestrutura CI/CD e containers reprodutíveis que executem o *Eval Harness* automaticamente.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Disponibilizar o wireframe interativo `wireframe_de_olho_no_brasil.html` (`achromatic-ledger`, seed `2125632542`) com reconciliação matemática no cliente (`console.assert`).
- Implementar a API REST em `src/deolhonobrasil/api/` servindo `/api/v1/dossiers`, `/api/v1/expenses`, `/api/v1/reconciliation`, `/api/v1/health` e `POST /api/v1/right-of-reply`.
- Garantir isolamento por perfil (`AccessRole.PUBLIC_READER` vs `AccessRole.REVIEWER_ADMIN`), rate limiting (`HTTP 429`), headers de segurança HTTP e validação estrita de Direito de Resposta.
- Prover `Dockerfile`, `docker-compose.yml` e `.github/workflows/ci.yml` executando o harness SDD.

### Não-Objetivos
- Expor endpoints de exclusão física de registros da `editorial_audit_trail` (proibido por `DATA-005`).
- Exibir CPFs desmascarados de pessoas físicas comuns (`SEC-001`).

## 5. Atores e Permissões
- **`public_reader` (Cidadão / Jornalista / Consumidor da API):** Consulta apenas dossiês revisados (`PUBLICADO_COM_REVISAO`, `ESCLARECIDO_COM_PROVA`, `ERRO_MATERIAL_RETIFICADO` com `reviewer_id IS NOT NULL`), despesas curadas e relatórios de reconciliação.
- **`respondent` (Agente Público / Fornecedor Citado):** Submete protocolo de Direito de Resposta via `POST /api/v1/right-of-reply` com hash `SHA-256` de anexo comprobatório.
- **`reviewer_admin` (Revisor Editorial Autenticado):** Acessa fila de triagem interna mediante cabeçalho de autorização administrativa validado.

## 6. Fluxos Principais
1. **Consulta de Dossiês (`GET /api/v1/dossiers`):** Filtra dossiês no `CivicLakehouseStorage` conforme o papel do requisitante e retorna blocos epistêmicos, hashes `SHA-256` e eventual Direito de Resposta lado a lado.
2. **Consulta de Despesas (`GET /api/v1/expenses`):** Lista despesas curadas com filtros opcionais (`year`, `state_uf`, `organ_code`, `limit`, `offset`) e soma líquida reconciliada em `Decimal`.
3. **Verificação de Reconciliação (`GET /api/v1/reconciliation`):** Retorna métricas do Lakehouse e status de reconciliação contábil.
4. **Submissão de Direito de Resposta (`POST /api/v1/right-of-reply`):** Valida payload, mascara CPF se necessário, sanitiza contra *prompt injection*, bloqueia termos acusatórios e registra protocolo `RECEBIDO_EM_VALIDACAO` com `equal_visual_prominence=True`.

## 7. Cenários Alternativos e de Erro
- **Excesso de Requisições (`Rate Limit`):** Retorna `HTTP 429 Too Many Requests` com cabeçalho `Retry-After`.
- **Payload Inválido ou Termo Acusatório no Direito de Resposta:** Retorna `HTTP 422 Unprocessable Entity` detalhando a violação sem persistir o registro.
- **Tentativa de Acesso a Dossiês em Triagem sem Credencial Admin:** Retorna `HTTP 403 Forbidden` (se solicitado papel admin sem token válido) ou oculta estritamente registros `EM_TRIAGEM_INTERNA` no perfil público.

## 8. Requisitos Funcionais
- **FR-010:** A interface `wireframe_de_olho_no_brasil.html` deve implementar a direção `achromatic-ledger` com 3 camadas epistêmicas, `tabular-nums`, inspetor `SHA-256` e comparação lado a lado do Direito de Resposta.
- **FR-011:** A API REST (`src/deolhonobrasil/api/`) deve servir `GET /api/v1/health`, `GET /api/v1/dossiers`, `GET /api/v1/expenses`, `GET /api/v1/reconciliation` e `POST /api/v1/right-of-reply` integrados ao `CivicLakehouseStorage`.

## 9. Requisitos Não Funcionais
- **NFR-006:** Acessibilidade WCAG AA, alinhamento numérico `tabular-nums` e zero erros em `lint.mjs --app` e `inspect.mjs --app` (`1440px`, `768px`, `390px`).
- **NFR-007:** Reprodutibilidade de build e verificação via `Dockerfile`, `docker-compose.yml` e pipeline `.github/workflows/ci.yml`.

## 10. Regras de Negócio e Dados
- **DATA-006:** Reconciliação no cliente (`console.assert` no HTML) e na API (`total_net_amount_brl` em `GET /api/v1/expenses` calculado em `Decimal` exato).

## 11. Requisitos de Segurança e Privacidade
- **SEC-006:** Rate limiting por IP (`SlidingWindowRateLimiter`), autenticação obrigatória para visualização administrativa (`X-Admin-Token`) e headers de segurança (`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`).
- **SEC-007:** Validação LGPD, sanitização de *prompt injection* e bloqueio de linguagem acusatória em todas as entradas de `POST /api/v1/right-of-reply`.

## 12. Critérios de Aceite
- **AC-014:** Wireframe passa nas validações estruturais do `achromatic-ledger` sem termos proibidos.
- **AC-015:** Endpoints da API retornam contratos JSON válidos, respeitando RLS (`public_reader` vê 0 dossiês em `EM_TRIAGEM_INTERNA`).
- **AC-016:** Submissão de Direito de Resposta via API sanitiza *prompt injection*, rejeita linguagem acusatória (`HTTP 422`) e cria protocolo com `equal_visual_prominence=True` (`HTTP 201`).
- **AC-017:** Rate limiter bloqueia excesso de chamadas (`HTTP 429`), headers de segurança estão presentes em todas as respostas e arquivos de CI/CD (`Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`) estão íntegros.

## 13. Dependências
- `SPEC-0001`, `SPEC-0002`, `SPEC-0003`.

## 14. Riscos e Limitações
- Rate limiter em memória é local por processo; em deploy distribuído multi-réplica deve ser acoplado a Redis/Cloudflare WAF.

## 15. Estratégia de Testes e Test Anchors
### Test Anchors
- `tests/test_harness.py::TestLoopEngineeringHarness::test_wireframe_passes_achromatic_ledger_structural_invariants`
- `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_health_and_security_headers`
- `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_get_dossiers_enforces_rls_for_public_vs_admin`
- `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_get_expenses_and_reconciliation_decimal_totals`
- `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_post_right_of_reply_creates_protocol_and_masks_cpf`
- `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_post_right_of_reply_blocks_accusatory_and_sanitizes_injection`
- `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_rate_limiter_blocks_excessive_requests_with_429`
- `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_root_serves_interactive_html_interface`
- `tests/test_api_and_ops.py::TestCivicAuditRESTAPI::test_live_http_server_e2e_ui_and_api_roundtrip`
- `tests/test_api_and_ops.py::TestDevSecOpsAndCICDArtifacts::test_dockerfile_compose_and_github_ci_exist_and_run_harness`

## 16. Questões Pendentes
Nenhuma questão bloqueante pendente.
