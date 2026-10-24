# ADR-0006: Fluxo Administrativo de Revisão Humana via API e Pacote de Evidências Verificável (`SHA-256`)

- **Status:** Aceito e Implementado
- **Data:** 2026-10-23
- **Especificação Relacionada:** [`SPEC-0006-editorial-admin-and-evidence-bundle`](../../specs/SPEC-0006-editorial-admin-and-evidence-bundle/spec.md)
- **Requisitos Atendidos:** `FR-014`, `FR-015`, `NFR-009`, `DATA-008`, `SEC-009`, `AC-022..025`

---

## 1. Contexto

O modelo de Governança Editorial Híbrida (`SPEC-0003`) determina que nenhum achado nominal de alta severidade (`score >= 0.70` no motor `Laya`) pode ser publicado sem revisão humana (`reviewer_admin`). Além disso, jornalistas investigativos, cidadãos e órgãos de controle necessitam exportar dossiês publicados em um formato autocontido e criptograficamente auditável offline.

---

## 2. Decisão Arquitetural

1. **Endpoints Administrativos Protegidos por `hmac.compare_digest` (`FR-014`, `SEC-009`):**
   - `POST /api/v1/admin/dossiers/approve`: Transiciona um dossiê de `EM_TRIAGEM_INTERNA` para `PUBLICADO_COM_REVISAO`, exigindo `X-Admin-Token` válido e identificando o `reviewer_id`.
   - `POST /api/v1/admin/dossiers/rectify`: Transiciona um dossiê para `ERRO_MATERIAL_RETIFICADO` com nota de retificação sanitizada e validada por `assert_non_accusatory_language`.
   - `GET /api/v1/admin/audit-trail`: Consulta a tabela append-only `editorial_audit_trail` com filtro opcional por `dossier_id`.
2. **Pacote de Evidências Verificável (`VerifiableEvidenceBundle` — `FR-015`, `NFR-009`, `DATA-008`):**
   - Entidade imutável (`@dataclass(frozen=True, slots=True)`) exportada via `GET /api/v1/dossiers/evidence-bundle?dossier_id=...`.
   - Contém os 3 blocos epistêmicos obrigatórios (`[DADO OFICIAL]`, `[INFERÊNCIA ESTATÍSTICA]`, `[HIPÓTESE DE AUDITORIA / LIMITAÇÃO]`), os hashes `SHA-256` dos lotes primários, o protocolo de Direito de Resposta lado a lado (quando presente) e um manifesto `bundle_sha256` calculado sobre o JSON canônico (`json.dumps(..., sort_keys=True, separators=(",", ":"))`).
   - Respeita estritamente o RLS: leitores públicos (`public_reader`) não podem exportar pacotes de dossiês em `EM_TRIAGEM_INTERNA` (`HTTP 404`).

---

## 3. Consequências

- **Positivas:** Fecha o ciclo operacional completo de revisão humana via API REST e permite auditoria cidadã independente offline com verificação criptográfica determinística.
- **Limitações / Mitigações:** As operações administrativas exigem `X-Admin-Token` em tempo constante (`hmac.compare_digest`) e registram cada transição de estado na tabela imutável `editorial_audit_trail`.
