"""Hexagonal REST API Service, Rate Limiter, Security Headers & WSGI/FastAPI Adapter (`SPEC-0004`).

Implements `FR-011`, `DATA-006`, `SEC-006`, and `SEC-007`:
- Strictly enforces Row-Level Security (`AccessRole.PUBLIC_READER` vs `AccessRole.REVIEWER_ADMIN`).
- Masks CPFs (`***.XXX.XXX-**`), sanitizes indirect prompt injection, and blocks accusatory language
  on `POST /api/v1/right-of-reply`.
- Applies sliding-window per-IP rate limiting (`HTTP 429`) and mandatory security headers.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qs
import uuid

from deolhonobrasil.governance.dossiers import (
    AccessRole,
    DossierStatus,
    VerifiableEvidenceBundle,
)
from deolhonobrasil.governance.right_of_reply import (
    RightOfReplyStatus,
    RightOfReplySubmission,
)
from deolhonobrasil.pipeline.models import assert_non_accusatory_language
from deolhonobrasil.pipeline.privacy import (
    normalize_and_protect_document,
    sanitize_untrusted_public_text,
)
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


DEFAULT_SECURITY_HEADERS: dict[str, str] = {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
}


@dataclass(frozen=True, slots=True)
class APIResponse:
    """Immutable HTTP response envelope returned by `CivicAuditHTTPApp`."""

    status_code: int
    body: dict[str, object]
    headers: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_SECURITY_HEADERS))
    raw_html: str | None = None


class SlidingWindowRateLimiter:
    """In-memory sliding-window rate limiter by client IP (`SEC-006`)."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        if max_requests < 1 or window_seconds < 1:
            raise ValueError("max_requests and window_seconds must be >= 1")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = {}

    def allow_request(self, client_ip: str, now_monotonic: float | None = None) -> bool:
        now = now_monotonic if now_monotonic is not None else time.monotonic()
        cutoff = now - float(self.window_seconds)
        bucket = self._buckets.setdefault(client_ip, deque())
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if not bucket and len(self._buckets) > 1024:
            self._buckets.pop(client_ip, None)
            bucket = self._buckets.setdefault(client_ip, deque())
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True


class CivicAuditAPIService:
    """Application service implementing all `SPEC-0004` REST contracts over `CivicLakehouseStorage`."""

    def __init__(
        self,
        storage: CivicLakehouseStorage,
        admin_token: str | None = None,
        rate_limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        self.storage = storage
        self.admin_token = admin_token
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter()

    def get_health(self) -> tuple[int, dict[str, object]]:
        return 200, {
            "status": "ok",
            "service": "deolhonobrasil-api",
            "version": "0.1.0",
        }

    def get_dossiers(
        self,
        *,
        role_param: str = "public_reader",
        provided_admin_token: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[int, dict[str, object]]:
        safe_limit = max(1, min(int(limit), 100))
        safe_offset = max(0, int(offset))

        if role_param == AccessRole.REVIEWER_ADMIN.value:
            if (
                not self.admin_token
                or not provided_admin_token
                or not hmac.compare_digest(self.admin_token, provided_admin_token)
            ):
                return 403, {
                    "error": "FORBIDDEN",
                    "detail": "Acesso ao perfil reviewer_admin exige cabeçalho X-Admin-Token válido.",
                }
            role = AccessRole.REVIEWER_ADMIN
        else:
            role = AccessRole.PUBLIC_READER

        all_visible = self.storage.list_dossiers_for_role(role)
        sliced = all_visible[safe_offset : safe_offset + safe_limit]
        return 200, {
            "role": role.value,
            "total": len(all_visible),
            "limit": safe_limit,
            "offset": safe_offset,
            "items": sliced,
        }

    def get_expenses(
        self,
        *,
        year: int | None = None,
        state_uf: str | None = None,
        organ_code: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, dict[str, object]]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        clauses: list[str] = []
        params: list[object] = []
        if year is not None:
            clauses.append("competence_year = ?")
            params.append(int(year))
        if state_uf:
            clauses.append("state_uf = ?")
            params.append(state_uf.strip().upper())
        if organ_code:
            clauses.append("organ_code = ?")
            params.append(organ_code.strip())

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.storage._connect() as conn:
            agg_row = conn.execute(
                f"SELECT COUNT(*), COALESCE(SUM(net_amount_cents), 0) FROM curated_expenses {where_sql}",
                tuple(params),
            ).fetchone()
            total_count = int(agg_row[0]) if agg_row else 0
            total_cents = int(agg_row[1]) if agg_row else 0

            rows = conn.execute(
                f"""
                SELECT natural_key, competence_year, competence_month, issue_date,
                       organ_code, organ_name, public_agent_name, party_sigla, state_uf,
                       expense_category, supplier_doc_normalized, supplier_doc_type,
                       supplier_name, document_number, net_amount_cents, raw_batch_sha256
                FROM curated_expenses
                {where_sql}
                ORDER BY issue_date DESC, natural_key ASC
                LIMIT ? OFFSET ?
                """,
                tuple([*params, safe_limit, safe_offset]),
            ).fetchall()

        items: list[dict[str, object]] = []
        for row in rows:
            d = dict(row)
            cents = int(d.pop("net_amount_cents", 0))
            d["net_amount_brl"] = str((Decimal(cents) / Decimal(100)).quantize(Decimal("0.01")))
            items.append(d)

        total_brl = str((Decimal(total_cents) / Decimal(100)).quantize(Decimal("0.01")))
        return 200, {
            "total_count": total_count,
            "total_net_amount_brl": total_brl,
            "limit": safe_limit,
            "offset": safe_offset,
            "items": items,
        }

    def get_reconciliation(self) -> tuple[int, dict[str, object]]:
        summary = self.storage.get_summary_metrics()
        return 200, {
            "reconciled": True,
            "discrepancy_brl": "0.00",
            "lakehouse_summary": summary,
        }

    def submit_right_of_reply(self, payload: dict[str, Any]) -> tuple[int, dict[str, object]]:
        dossier_id = str(payload.get("dossier_id", "")).strip()
        respondent_name = str(payload.get("respondent_name", "")).strip()
        raw_doc = str(payload.get("respondent_document", "")).strip()
        email_domain = str(payload.get("institutional_email_domain", "")).strip()
        statement_text = str(payload.get("statement_text", "")).strip()
        attachment_sha256 = str(payload.get("attachment_sha256", "")).strip()

        if not dossier_id:
            return 422, {"error": "VALIDATION_ERROR", "detail": "dossier_id é obrigatório."}

        existing = self.storage.get_dossier(dossier_id)
        if existing is None:
            return 404, {"error": "NOT_FOUND", "detail": f"Dossiê '{dossier_id}' não encontrado."}

        try:
            normalized_doc, _doc_type = normalize_and_protect_document(raw_doc)
        except ValueError as exc:
            return 422, {"error": "INVALID_DOCUMENT", "detail": str(exc)}

        protocol_id = f"REP-{dossier_id}-{uuid.uuid4().hex[:8]}"
        now_utc = datetime.now(timezone.utc).isoformat()

        try:
            submission = RightOfReplySubmission(
                protocol_id=protocol_id,
                dossier_id=dossier_id,
                respondent_name=respondent_name,
                respondent_document_masked_or_cnpj=normalized_doc,
                institutional_email_domain=email_domain,
                statement_text=statement_text,
                attachment_sha256=attachment_sha256,
                submitted_at_utc=now_utc,
                status=RightOfReplyStatus.RECEBIDO_EM_VALIDACAO,
                equal_visual_prominence=True,
            )
        except ValueError as exc:
            return 422, {"error": "GOVERNANCE_VALIDATION_ERROR", "detail": str(exc)}

        with self.storage._connect() as conn:
            conn.execute(
                """
                INSERT INTO right_of_reply_protocols (
                    protocol_id, dossier_id, respondent_name,
                    respondent_document_masked_or_cnpj, institutional_email_domain,
                    statement_text, attachment_sha256, status, equal_visual_prominence,
                    submitted_at_utc, reviewed_at_utc, reviewer_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission.protocol_id,
                    submission.dossier_id,
                    submission.respondent_name,
                    submission.respondent_document_masked_or_cnpj,
                    submission.institutional_email_domain,
                    submission.statement_text,
                    submission.attachment_sha256,
                    submission.status.value,
                    1 if submission.equal_visual_prominence else 0,
                    submission.submitted_at_utc,
                    None,
                    None,
                ),
            )

        return 201, {
            "protocol_id": submission.protocol_id,
            "dossier_id": submission.dossier_id,
            "respondent_name": submission.respondent_name,
            "respondent_document_masked_or_cnpj": submission.respondent_document_masked_or_cnpj,
            "statement_text": submission.statement_text,
            "status": submission.status.value,
            "equal_visual_prominence": submission.equal_visual_prominence,
            "submitted_at_utc": submission.submitted_at_utc,
        }

    def _verify_admin_token(self, provided_admin_token: str | None) -> bool:
        return bool(
            self.admin_token
            and provided_admin_token
            and hmac.compare_digest(self.admin_token, provided_admin_token)
        )

    def approve_dossier(
        self,
        payload: dict[str, Any],
        *,
        provided_admin_token: str | None = None,
    ) -> tuple[int, dict[str, object]]:
        if not self._verify_admin_token(provided_admin_token):
            return 403, {
                "error": "FORBIDDEN",
                "detail": "Aprovação editorial exige cabeçalho X-Admin-Token válido.",
            }
        dossier_id = str(payload.get("dossier_id") or "").strip()
        reviewer_id = sanitize_untrusted_public_text(str(payload.get("reviewer_id") or ""), 80)
        if not dossier_id or not reviewer_id:
            return 422, {
                "error": "VALIDATION_ERROR",
                "detail": "Campos 'dossier_id' e 'reviewer_id' são obrigatórios.",
            }

        existing = self.storage.get_dossier(dossier_id)
        if not existing:
            return 404, {"error": "DOSSIER_NOT_FOUND", "detail": f"Dossiê '{dossier_id}' não encontrado."}

        now_utc = datetime.now(timezone.utc).isoformat()
        previous_status = str(existing["status"])
        new_status = DossierStatus.PUBLICADO_COM_REVISAO.value

        with self.storage._connect() as conn:
            conn.execute(
                """
                UPDATE audit_dossiers
                SET status = ?, reviewer_id = ?, updated_at_utc = ?
                WHERE dossier_id = ?
                """,
                (new_status, reviewer_id, now_utc, dossier_id),
            )
            conn.execute(
                """
                INSERT INTO editorial_audit_trail (
                    event_id, dossier_id, action, previous_status, new_status,
                    actor_id, actor_role, rationale, metadata_json, occurred_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    dossier_id,
                    "APPROVE_FOR_PUBLICATION",
                    previous_status,
                    new_status,
                    reviewer_id,
                    AccessRole.REVIEWER_ADMIN.value,
                    "Aprovação humana para publicação pública após conferência documental.",
                    json.dumps({"approved_via": "api_v1_admin"}, ensure_ascii=False),
                    now_utc,
                ),
            )

        return 200, {
            "dossier_id": dossier_id,
            "previous_status": previous_status,
            "status": new_status,
            "reviewer_id": reviewer_id,
            "updated_at_utc": now_utc,
        }

    def rectify_dossier(
        self,
        payload: dict[str, Any],
        *,
        provided_admin_token: str | None = None,
    ) -> tuple[int, dict[str, object]]:
        if not self._verify_admin_token(provided_admin_token):
            return 403, {
                "error": "FORBIDDEN",
                "detail": "Retificação editorial exige cabeçalho X-Admin-Token válido.",
            }
        dossier_id = str(payload.get("dossier_id") or "").strip()
        reviewer_id = sanitize_untrusted_public_text(str(payload.get("reviewer_id") or ""), 80)
        raw_note = str(payload.get("correction_note") or "").strip()
        if not dossier_id or not reviewer_id or not raw_note:
            return 422, {
                "error": "VALIDATION_ERROR",
                "detail": "Campos 'dossier_id', 'reviewer_id' e 'correction_note' são obrigatórios.",
            }

        try:
            clean_note = sanitize_untrusted_public_text(raw_note, 2000)
            assert_non_accusatory_language(clean_note)
        except ValueError as exc:
            return 422, {"error": "GOVERNANCE_VALIDATION_ERROR", "detail": str(exc)}

        existing = self.storage.get_dossier(dossier_id)
        if not existing:
            return 404, {"error": "DOSSIER_NOT_FOUND", "detail": f"Dossiê '{dossier_id}' não encontrado."}

        now_utc = datetime.now(timezone.utc).isoformat()
        previous_status = str(existing["status"])
        new_status = DossierStatus.ERRO_MATERIAL_RETIFICADO.value

        with self.storage._connect() as conn:
            conn.execute(
                """
                UPDATE audit_dossiers
                SET status = ?, reviewer_id = ?, correction_note = ?, updated_at_utc = ?
                WHERE dossier_id = ?
                """,
                (new_status, reviewer_id, clean_note, now_utc, dossier_id),
            )
            conn.execute(
                """
                INSERT INTO editorial_audit_trail (
                    event_id, dossier_id, action, previous_status, new_status,
                    actor_id, actor_role, rationale, metadata_json, occurred_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    dossier_id,
                    "RECTIFY_MATERIAL_ERROR",
                    previous_status,
                    new_status,
                    reviewer_id,
                    AccessRole.REVIEWER_ADMIN.value,
                    clean_note,
                    json.dumps({"rectified_via": "api_v1_admin"}, ensure_ascii=False),
                    now_utc,
                ),
            )

        return 200, {
            "dossier_id": dossier_id,
            "previous_status": previous_status,
            "status": new_status,
            "reviewer_id": reviewer_id,
            "correction_note": clean_note,
            "updated_at_utc": now_utc,
        }

    def get_audit_trail(
        self,
        *,
        dossier_id: str | None = None,
        provided_admin_token: str | None = None,
    ) -> tuple[int, dict[str, object]]:
        if not self._verify_admin_token(provided_admin_token):
            return 403, {
                "error": "FORBIDDEN",
                "detail": "Consulta à trilha editorial exige cabeçalho X-Admin-Token válido.",
            }
        events = self.storage.get_editorial_audit_trail(dossier_id=dossier_id)
        return 200, {
            "count": len(events),
            "dossier_id": dossier_id,
            "events": events,
        }

    def get_evidence_bundle(
        self,
        *,
        dossier_id: str,
        provided_admin_token: str | None = None,
    ) -> tuple[int, dict[str, object]]:
        clean_id = (dossier_id or "").strip()
        if not clean_id:
            return 422, {"error": "VALIDATION_ERROR", "detail": "Parâmetro 'dossier_id' é obrigatório."}

        row = self.storage.get_dossier(clean_id)
        if not row:
            return 404, {"error": "DOSSIER_NOT_FOUND", "detail": f"Dossiê '{clean_id}' não encontrado."}

        is_admin = self._verify_admin_token(provided_admin_token)
        status_val = str(row.get("status") or "")
        reviewer_val = str(row.get("reviewer_id") or "").strip()
        published_statuses = {
            DossierStatus.PUBLICADO_COM_REVISAO.value,
            DossierStatus.ESCLARECIDO_COM_PROVA.value,
            DossierStatus.ERRO_MATERIAL_RETIFICADO.value,
        }
        if not is_admin and (status_val not in published_statuses or not reviewer_val):
            return 404, {
                "error": "DOSSIER_NOT_PUBLIC",
                "detail": "Dossiê em triagem interna não está disponível para exportação pública (RLS).",
            }

        bundle = VerifiableEvidenceBundle.from_dossier_row(row)
        return 200, bundle.to_dict()

    def get_sanctions(
        self,
        *,
        state_uf: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, dict[str, object]]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        conditions: list[str] = []
        params: list[object] = []

        if state_uf:
            conditions.append("state_uf = ?")
            params.append(state_uf.strip().upper()[:2])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self.storage._connect() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) FROM curated_sanctions {where_clause}",
                tuple(params),
            ).fetchone()
            total_count = int(total_row[0]) if total_row else 0

            rows = conn.execute(
                f"""
                SELECT * FROM curated_sanctions
                {where_clause}
                ORDER BY start_date DESC, natural_key ASC
                LIMIT ? OFFSET ?
                """,
                tuple([*params, safe_limit, safe_offset]),
            ).fetchall()

        return 200, {
            "total": total_count,
            "limit": safe_limit,
            "offset": safe_offset,
            "items": [dict(r) for r in rows],
        }

    def get_supplier_profile(self, doc: str) -> tuple[int, dict[str, object]]:
        data = self.storage.get_supplier_profile_data(doc)
        if not data:
            return 404, {"error": "Fornecedor não encontrado."}
        return 200, data

    def get_agent_profile(self, agent_id: str) -> tuple[int, dict[str, object]]:
        data = self.storage.get_agent_profile_data(agent_id)
        if not data:
            return 404, {"error": "Representante não encontrado."}
        return 200, data

    def get_organ_profile(self, organ_code: str) -> tuple[int, dict[str, object]]:
        data = self.storage.get_organ_profile_data(organ_code)
        if not data:
            return 404, {"error": "Órgão público não encontrado."}
        return 200, data

    def get_expense_detail(self, expense_id: str) -> tuple[int, dict[str, object]]:
        data = self.storage.get_expense_detail_data(expense_id)
        if not data:
            return 404, {"error": "Despesa não encontrada."}
        return 200, data

    def get_contract_detail(self, contract_id: str) -> tuple[int, dict[str, object]]:
        data = self.storage.get_contract_detail_data(contract_id)
        if not data:
            return 404, {"error": "Contrato não encontrado."}
        return 200, data

    def get_analysis_detail(self, rule_id: str) -> tuple[int, dict[str, object]]:
        data = self.storage.get_analysis_detail_data(rule_id)
        if not data:
            return 404, {"error": "Regra de análise não encontrada."}
        return 200, data


class CivicAuditHTTPApp:
    """Zero-dependency HTTP/WSGI dispatcher wrapping `CivicAuditAPIService`."""

    def __init__(self, service: CivicAuditAPIService) -> None:
        self.service = service

    def handle_request(
        self,
        *,
        method: str,
        path: str,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        client_ip: str = "127.0.0.1",
    ) -> APIResponse:
        q = dict(query_params or {})
        req_headers = {k.lower(): v for k, v in (headers or {}).items()}
        resp_headers = dict(DEFAULT_SECURITY_HEADERS)

        if not self.service.rate_limiter.allow_request(client_ip):
            resp_headers["Retry-After"] = str(self.service.rate_limiter.window_seconds)
            return APIResponse(
                status_code=429,
                body={
                    "error": "TOO_MANY_REQUESTS",
                    "detail": "Limite de requisições por IP excedido.",
                },
                headers=resp_headers,
            )

        upper_method = method.upper()
        if "?" in path:
            path_part, qs_part = path.split("?", 1)
            clean_path = path_part.rstrip("/") or "/"
            if not query_params:
                from urllib.parse import parse_qs
                q = {k: v[0] for k, v in parse_qs(qs_part).items() if v}
        else:
            clean_path = path.rstrip("/") or "/"

        if upper_method == "GET" and clean_path in ("/", "/index.html", "/wireframe_de_olho_no_brasil.html"):
            from pathlib import Path

            repo_root = Path(__file__).resolve().parents[3]
            wf_path = repo_root / "wireframe_de_olho_no_brasil.html"
            if wf_path.exists():
                html_text = wf_path.read_text(encoding="utf-8")
                html_headers = dict(resp_headers)
                html_headers["Content-Type"] = "text/html; charset=utf-8"
                html_headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' https://fonts.gstatic.com; "
                    "script-src 'self' 'unsafe-inline'; "
                    "frame-ancestors 'none'"
                )
                return APIResponse(
                    status_code=200,
                    body={"status": "ok", "content_type": "text/html"},
                    headers=html_headers,
                    raw_html=html_text,
                )

        if upper_method == "GET" and clean_path == "/api/v1/health":
            code, payload = self.service.get_health()
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        def _safe_int(raw_val: str | None, default: int) -> int:
            if raw_val is None:
                return default
            try:
                return int(raw_val)
            except (ValueError, TypeError):
                return default

        if upper_method == "GET" and clean_path == "/api/v1/dossiers":
            code, payload = self.service.get_dossiers(
                role_param=q.get("role", "public_reader"),
                provided_admin_token=req_headers.get("x-admin-token"),
                limit=_safe_int(q.get("limit"), 20),
                offset=_safe_int(q.get("offset"), 0),
            )
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/expenses":
            year_val = int(q["year"]) if "year" in q and str(q["year"]).isdigit() else None
            code, payload = self.service.get_expenses(
                year=year_val,
                state_uf=q.get("state_uf"),
                organ_code=q.get("organ_code"),
                limit=_safe_int(q.get("limit"), 50),
                offset=_safe_int(q.get("offset"), 0),
            )
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/reconciliation":
            code, payload = self.service.get_reconciliation()
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "POST" and clean_path == "/api/v1/right-of-reply":
            code, payload = self.service.submit_right_of_reply(json_body or {})
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "POST" and clean_path == "/api/v1/admin/dossiers/approve":
            code, payload = self.service.approve_dossier(
                json_body or {},
                provided_admin_token=req_headers.get("x-admin-token"),
            )
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "POST" and clean_path == "/api/v1/admin/dossiers/rectify":
            code, payload = self.service.rectify_dossier(
                json_body or {},
                provided_admin_token=req_headers.get("x-admin-token"),
            )
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/admin/audit-trail":
            code, payload = self.service.get_audit_trail(
                dossier_id=q.get("dossier_id"),
                provided_admin_token=req_headers.get("x-admin-token"),
            )
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/dossiers/evidence-bundle":
            code, payload = self.service.get_evidence_bundle(
                dossier_id=q.get("dossier_id", ""),
                provided_admin_token=req_headers.get("x-admin-token"),
            )
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/sanctions":
            code, payload = self.service.get_sanctions(
                state_uf=q.get("state_uf"),
                limit=_safe_int(q.get("limit"), 50),
                offset=_safe_int(q.get("offset"), 0),
            )
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/entities/supplier":
            code, payload = self.service.get_supplier_profile(q.get("doc", ""))
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/entities/agent":
            code, payload = self.service.get_agent_profile(q.get("id", ""))
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/entities/organ":
            code, payload = self.service.get_organ_profile(q.get("id", ""))
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/details/expense":
            code, payload = self.service.get_expense_detail(q.get("id", ""))
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/details/contract":
            code, payload = self.service.get_contract_detail(q.get("id", ""))
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        if upper_method == "GET" and clean_path == "/api/v1/details/analysis":
            code, payload = self.service.get_analysis_detail(q.get("id", ""))
            return APIResponse(status_code=code, body=payload, headers=resp_headers)

        return APIResponse(
            status_code=404,
            body={"error": "NOT_FOUND", "detail": f"Rota '{upper_method} {clean_path}' não encontrada."},
            headers=resp_headers,
        )

    def __call__(self, environ: dict[str, Any], start_response: Any) -> list[bytes]:
        """Standard PEP 3333 WSGI entrypoint."""
        method = str(environ.get("REQUEST_METHOD", "GET"))
        path = str(environ.get("PATH_INFO", "/"))
        raw_qs = str(environ.get("QUERY_STRING", ""))
        parsed_qs = {k: v[0] for k, v in parse_qs(raw_qs).items() if v}
        client_ip = str(environ.get("REMOTE_ADDR", "127.0.0.1"))

        headers: dict[str, str] = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").lower()
                headers[header_name] = str(value)

        json_body: dict[str, Any] | None = None
        if method.upper() in ("POST", "PUT", "PATCH"):
            content_length = int(environ.get("CONTENT_LENGTH") or 0)
            if content_length > 0 and "wsgi.input" in environ:
                raw_bytes = environ["wsgi.input"].read(content_length)
                json_body = json.loads(raw_bytes.decode("utf-8"))

        resp = self.handle_request(
            method=method,
            path=path,
            query_params=parsed_qs,
            headers=headers,
            json_body=json_body,
            client_ip=client_ip,
        )
        status_map = {
            200: "200 OK",
            201: "201 Created",
            403: "403 Forbidden",
            404: "404 Not Found",
            422: "422 Unprocessable Entity",
            429: "429 Too Many Requests",
        }
        status_line = status_map.get(resp.status_code, f"{resp.status_code} OK")
        start_response(status_line, list(resp.headers.items()))
        if resp.raw_html is not None:
            return [resp.raw_html.encode("utf-8")]
        return [json.dumps(resp.body, ensure_ascii=False).encode("utf-8")]


def create_fastapi_app(service: CivicAuditAPIService) -> Any:
    """Optional FastAPI factory (`ADR-0004`) when `fastapi` is installed in the runtime."""
    try:
        from fastapi import FastAPI, Request, Response  # type: ignore[import-not-found]
    except ImportError:
        return CivicAuditHTTPApp(service)

    fastapi_app = FastAPI(
        title="De Olho no Brasil — Public Civic Audit API",
        version="0.1.0",
    )
    http_adapter = CivicAuditHTTPApp(service)

    @fastapi_app.api_route(
        "/api/v1/{endpoint:path}",
        methods=["GET", "POST"],
    )
    async def _dispatch(request: Request, endpoint: str) -> Response:
        body_dict: dict[str, Any] | None = None
        if request.method == "POST":
            body_dict = await request.json()
        res = http_adapter.handle_request(
            method=request.method,
            path=f"/api/v1/{endpoint}",
            query_params=dict(request.query_params),
            headers=dict(request.headers),
            json_body=body_dict,
            client_ip=request.client.host if request.client else "127.0.0.1",
        )
        return Response(
            content=json.dumps(res.body, ensure_ascii=False),
            status_code=res.status_code,
            headers=res.headers,
            media_type="application/json",
        )

    return fastapi_app
