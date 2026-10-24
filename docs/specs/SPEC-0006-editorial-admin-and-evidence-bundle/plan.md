# Technical Design Plan — SPEC-0006

## 1. Arquitetura Geral
O SPEC-0006 adiciona três componentes principais ao backend em Python (`src/deolhonobrasil/`):
1. **`CivicAuditAPIService`**: Novas rotas FastAPI protegidas para aprovação (`POST /api/v1/admin/dossiers/approve`), retificação (`POST /api/v1/admin/dossiers/rectify`), consulta de trilha de auditoria (`GET /api/v1/admin/audit-trail`) e exportação de pacote de evidências (`GET /api/v1/dossiers/evidence-bundle`).
2. **`VerifiableEvidenceBundle`**: Objeto imutável (`frozen=True`, Pydantic v2 / dataclass) que empacota o dossiê aprovado, as 3 camadas epistêmicas, o Direito de Resposta e calcula o manifesto `bundle_sha256` utilizando serialização canônica (`json.dumps(..., sort_keys=True, ensure_ascii=False)`).
3. **`CivicLakehouseStorage` / Audit Ledger**: Repositório imutável append-only para registrar eventos de revisão humana e retificações materiais.

## 2. Decisões Arquiteturais (ADRs Relacionadas)
- Uso de chaves simétricas via `hmac.compare_digest` para autenticação rápida de administradores sem sobrecarga de infraestrutura OAuth2 pesada em ambiente isolado.
- Imutabilidade rigorosa em estruturas de evidência (`frozen=True`) para prevenir adulteração de hashes.
