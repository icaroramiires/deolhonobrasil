# SPEC-0006 — Fluxo Administrativo de Revisão Humana via API, Trilha de Auditoria e Pacote de Evidências Verificável SHA-256

## 1. Identificador e Título
- **Identificador:** SPEC-0006
- **Título:** Fluxo Administrativo de Revisão Humana via API, Trilha de Auditoria e Pacote de Evidências Verificável SHA-256

## 2. Status e Versão
- **Status:** Verificado
- **Versão:** 1.0.0

## 3. Problema e Motivação
O ecossistema **De Olho no Brasil** processa dados públicos e gera achados de auditoria e dossiês através de motores analíticos e de IA (*System 1* / Laya). Para garantir a conformidade com as diretrizes editoriais híbridas, a governança epistêmica em 3 camadas e a segurança jurídica, nenhum achado de alta severidade pode ser exposto publicamente sem revisão e aprovação humana explícita. Adicionalmente, cidadãos, órgãos de controle e jornalistas exigem uma forma de exportar e auditar independentemente um pacote de evidências autocontido com integridade criptográfica verificável (`SHA-256`).

## 4. Objetivos e Não-Objetivos
### Objetivos
- Estabelecer rotas administrativas seguras (`POST /api/v1/admin/dossiers/approve`, `POST /api/v1/admin/dossiers/rectify` e `GET /api/v1/admin/audit-trail`) para transição de estado editorial (`EM_TRIAGEM_INTERNA` $\rightarrow$ `PUBLICADO_APROVADO`).
- Implementar o endpoint `GET /api/v1/dossiers/evidence-bundle` que gera um `VerifiableEvidenceBundle` serializado de forma canônica (`sort_keys=True`) contendo as 3 camadas epistêmicas, Direito de Resposta e manifesto SHA-256.
- Garantir a imutabilidade e rastreabilidade da trilha de auditoria e dados subjacentes.

### Não-Objetivos
- Edição de dados brutos na fonte governamental original (CGU, PNCP, CEAP).
- Substituição de fluxos de autenticação OAuth2 corporativos nesta fase inicial (utiliza token administrativo simétrico via `hmac.compare_digest`).

## 5. Atores e Permissões
- **`public_reader`**: Cidadão ou cliente sem credenciais administrativas. Pode consultar dossiês aprovados e exportar pacotes de evidências de dossiês publicados. É estritamente bloqueado ao tentar exportar ou acessar dossiês em `EM_TRIAGEM_INTERNA`.
- **`reviewer_admin`**: Auditor humano ou editor autorizado. Possui token administrativo (`X-Admin-Token`) e permissão para aprovar dossiês, registrar retificações materiais e consultar a trilha imutável de auditoria.

## 6. Fluxos Principais
1. **Aprovação Editorial:** Um auditor envia uma requisição `POST /api/v1/admin/dossiers/approve` com o token administrativo válido, promovendo o dossiê de `EM_TRIAGEM_INTERNA` para `PUBLICADO_APROVADO` e registrando o evento na trilha de auditoria.
2. **Geração de Pacote de Evidências:** Um cliente solicita `GET /api/v1/dossiers/evidence-bundle?dossier_id=...`. O sistema verifica se o dossiê está publicado, compila o `VerifiableEvidenceBundle`, aplica serialização canônica JSON e retorna o manifesto `bundle_sha256`.

## 7. Cenários Alternativos e de Erro
- **Tentativa de aprovação sem `X-Admin-Token`:** A API retorna `HTTP 401 Unauthorized` e registra a tentativa falha na trilha de segurança.
- **Tentativa de exportar pacote de dossiê em `EM_TRIAGEM_INTERNA` por `public_reader`:** A API aplica restrição RLS/filtro de acesso e retorna `HTTP 403 Forbidden` (ou `404 Not Found` para evitar enumeração).
- **Tentativa de retificação com linguagem acusatória:** O motor de compliance (`assert_non_accusatory_language`) rejeita a nota de retificação caso contenha termos proibidos (`"fraude"`, `"corrupção"`, etc.), retornando `HTTP 422 Unprocessable Entity`.

## 8. Requisitos Funcionais
- `FR-014`: A API deve expor rotas administrativas autenticadas (`POST /api/v1/admin/dossiers/approve`, `POST /api/v1/admin/dossiers/rectify` e `GET /api/v1/admin/audit-trail`) para transição segura de estado editorial e auditoria da trilha imutável.
- `FR-015`: A API deve expor `GET /api/v1/dossiers/evidence-bundle` gerando um `VerifiableEvidenceBundle` autocontido com as 3 camadas epistêmicas, Direito de Resposta paritário e manifesto criptográfico `bundle_sha256`.

## 9. Requisitos Não Funcionais
- `NFR-009`: Serialização JSON canônica determinística (`sort_keys=True`) para que qualquer cidadão possa recalcular e verificar `bundle_sha256` offline.

## 10. Regras de Negócio e Dados
- `DATA-008`: `VerifiableEvidenceBundle` deve ser imutável (`frozen=True`) e preservar integralmente os hashes `SHA-256` dos lotes brutos e a trilha de revisão humana.

## 11. Requisitos de Segurança e Privacidade
- `SEC-009`: Proteção estrita de rotas administrativas via `hmac.compare_digest` e bloqueio de exportação pública de dossiês em `EM_TRIAGEM_INTERNA` (RLS).

## 12. Critérios de Aceite
- `AC-022`: Rotas administrativas exigem `X-Admin-Token` validado via `hmac.compare_digest`, retornando 401 caso ausente ou inválido.
- `AC-023`: Dossiês em `EM_TRIAGEM_INTERNA` não podem ser exportados por usuários `public_reader`.
- `AC-024`: Notas de retificação que contenham linguagem acusatória são bloqueadas pelo linter de conformidade.
- `AC-025`: O `VerifiableEvidenceBundle` gerado possui `bundle_sha256` verificável por serialização canônica JSON com `sort_keys=True`.

## 13. Dependências
- `SPEC-0003` (Governança Epistêmica e Trilha de Auditoria)
- `SPEC-0004` (Motor de Decisão e Camadas Epistêmicas)

## 14. Riscos e Limitações
- Vazamento do token administrativo simétrico (mitigado por rotação periódica e uso de variáveis de ambiente restritas).
- Divergência de hash por formatação de JSON (mitigado por estrito uso de `json.dumps(..., sort_keys=True, ensure_ascii=False)`).

## 15. Estratégia de Testes e Test Anchors
- `tests/test_admin_and_evidence_bundle.py::TestEditorialAdminAndEvidenceBundle::test_admin_approve_dossier_requires_token_and_publishes_to_public`
- `tests/test_admin_and_evidence_bundle.py::TestEditorialAdminAndEvidenceBundle::test_admin_rectify_material_error_updates_status_and_blocks_accusatory_note`
- `tests/test_admin_and_evidence_bundle.py::TestEditorialAdminAndEvidenceBundle::test_admin_audit_trail_endpoint_returns_immutable_history`
- `tests/test_admin_and_evidence_bundle.py::TestEditorialAdminAndEvidenceBundle::test_evidence_bundle_blocks_unreviewed_dossier_for_public_reader`
- `tests/test_admin_and_evidence_bundle.py::TestEditorialAdminAndEvidenceBundle::test_verifiable_evidence_bundle_canonical_sha256_integrity`

## 16. Questões Pendentes
- `Nenhuma.`
