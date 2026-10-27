"""Protocolo público de contestação. O texto recebido não é publicado e não pode ser apagado.

Os prazos gravados são metas internas de triagem. Não são prazos legais.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum
import re
import sqlite3
import uuid

from deolhonobrasil.pipeline.models import assert_non_accusatory_language
from deolhonobrasil.pipeline.privacy import (
    compute_sha256_text,
    mask_cpf_in_free_text,
    sanitize_untrusted_text,
)
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


class ChallengeCategory(StrEnum):
    ERRO_FACTUAL = "ERRO_FACTUAL"
    DOCUMENTO_INCORRETO = "DOCUMENTO_INCORRETO"
    DADO_PESSOAL = "DADO_PESSOAL"
    DIREITO_AUTORAL = "DIREITO_AUTORAL"
    ALEGACAO_DIFAMATORIA = "ALEGACAO_DIFAMATORIA"
    METODOLOGIA = "METODOLOGIA"
    SOLICITACAO_LEGAL = "SOLICITACAO_LEGAL"


class ChallengeStatus(StrEnum):
    RECEBIDO = "RECEBIDO"
    EM_ANALISE = "EM_ANALISE"
    AGUARDANDO_COMPLEMENTO = "AGUARDANDO_COMPLEMENTO"
    DECIDIDO = "DECIDIDO"
    ESCALADO_JURIDICO = "ESCALADO_JURIDICO"


_DECISION_STATUSES = {
    ChallengeStatus.EM_ANALISE,
    ChallengeStatus.AGUARDANDO_COMPLEMENTO,
    ChallengeStatus.DECIDIDO,
    ChallengeStatus.ESCALADO_JURIDICO,
}
_URGENT_CATEGORIES = {
    ChallengeCategory.DADO_PESSOAL,
    ChallengeCategory.ALEGACAO_DIFAMATORIA,
    ChallengeCategory.SOLICITACAO_LEGAL,
}
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

PUBLIC_ACK = (
    "Protocolo registrado. O texto não é publicado automaticamente e não altera "
    "registros de auditoria. O prazo informado é uma meta interna de triagem, não um prazo legal."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _stamp(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _public_payload(row: sqlite3.Row) -> dict[str, object]:
    return {
        "challenge_id": row["challenge_id"],
        "category": row["category"],
        "status": row["status"],
        "received_at_utc": row["received_at_utc"],
        "internal_target_review_by_utc": row["internal_target_review_by_utc"],
        "published": False,
        "statement_disclosed": False,
        "message": PUBLIC_ACK,
    }


def submit_challenge(
    storage: CivicLakehouseStorage,
    payload: dict[str, object],
    *,
    now: datetime | None = None,
) -> tuple[int, dict[str, object]]:
    """Registra uma contestação em RECEBIDO. Ignora qualquer status enviado pelo cliente."""
    raw_category = str(payload.get("category", "")).strip().upper()
    try:
        category = ChallengeCategory(raw_category)
    except ValueError:
        return 422, {
            "error": "VALIDATION_ERROR",
            "detail": "Categoria de contestação não reconhecida.",
        }

    statement = mask_cpf_in_free_text(sanitize_untrusted_text(str(payload.get("statement", "")), 4000))
    if not statement.strip():
        return 422, {
            "error": "VALIDATION_ERROR",
            "detail": "Descreva o pedido depois da higienização do texto.",
        }

    contact_raw = str(payload.get("contact", "") or "").strip()
    if not contact_raw:
        contact = "nao_informado"
    elif _EMAIL_RE.match(contact_raw) and len(contact_raw) <= 120:
        contact = contact_raw.casefold()
    else:
        return 422, {
            "error": "VALIDATION_ERROR",
            "detail": "O contato, se informado, deve ser um e-mail. Não envie documento pessoal nesse campo.",
        }

    related = sanitize_untrusted_text(str(payload.get("related_record_ref", "") or ""), 180) or None
    moment = now or _utcnow()
    days = 2 if category in _URGENT_CATEGORIES else 15
    target = moment + timedelta(days=days)
    challenge_id = f"cont-{uuid.uuid4().hex[:12]}"
    received = _stamp(moment)
    digest = compute_sha256_text(f"{challenge_id}|{category.value}|{statement}|{received}")
    event_id = f"evt-{uuid.uuid4().hex[:12]}"

    with storage._connect() as conn:
        conn.execute(
            """
            INSERT INTO civic_challenges (
                challenge_id, category, status, related_record_ref, statement_text,
                contact_channel, received_at_utc, internal_target_review_by_utc, sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                challenge_id,
                category.value,
                ChallengeStatus.RECEBIDO.value,
                related,
                statement,
                contact,
                received,
                _stamp(target),
                digest,
            ),
        )
        conn.execute(
            """
            INSERT INTO civic_challenge_events (
                event_id, challenge_id, event_type, actor_id, note, occurred_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                challenge_id,
                ChallengeStatus.RECEBIDO.value,
                "public_submitter",
                "Protocolo recebido. Texto não publicado.",
                received,
            ),
        )
        row = conn.execute(
            "SELECT * FROM civic_challenges WHERE challenge_id = ?",
            (challenge_id,),
        ).fetchone()
    body = _public_payload(row)
    body["internal_target_days"] = days
    return 201, body


def get_public_challenge(storage: CivicLakehouseStorage, challenge_id: str) -> tuple[int, dict[str, object]]:
    clean_id = sanitize_untrusted_text(challenge_id, 40)
    with storage._connect() as conn:
        row = conn.execute(
            "SELECT * FROM civic_challenges WHERE challenge_id = ?",
            (clean_id,),
        ).fetchone()
    if row is None:
        return 404, {"error": "NOT_FOUND", "detail": "Protocolo não encontrado."}
    return 200, _public_payload(row)


def get_admin_challenge(
    storage: CivicLakehouseStorage,
    challenge_id: str,
) -> tuple[int, dict[str, object]]:
    clean_id = sanitize_untrusted_text(challenge_id, 40)
    with storage._connect() as conn:
        row = conn.execute(
            "SELECT * FROM civic_challenges WHERE challenge_id = ?",
            (clean_id,),
        ).fetchone()
        if row is None:
            return 404, {"error": "NOT_FOUND", "detail": "Protocolo não encontrado."}
        events = conn.execute(
            """
            SELECT event_id, event_type, actor_id, note, occurred_at_utc
            FROM civic_challenge_events
            WHERE challenge_id = ?
            ORDER BY occurred_at_utc ASC, rowid ASC
            """,
            (clean_id,),
        ).fetchall()
    return 200, {
        "challenge_id": row["challenge_id"],
        "category": row["category"],
        "status": row["status"],
        "related_record_ref": row["related_record_ref"],
        "statement_text": row["statement_text"],
        "contact_channel": row["contact_channel"],
        "received_at_utc": row["received_at_utc"],
        "internal_target_review_by_utc": row["internal_target_review_by_utc"],
        "sha256": row["sha256"],
        "events": [dict(event) for event in events],
    }


def decide_challenge(
    storage: CivicLakehouseStorage,
    payload: dict[str, object],
    *,
    actor_id: str,
    now: datetime | None = None,
) -> tuple[int, dict[str, object]]:
    """Acrescenta uma decisão. Não reescreve o texto recebido nem apaga eventos."""
    challenge_id = sanitize_untrusted_text(str(payload.get("challenge_id", "")), 40)
    try:
        new_status = ChallengeStatus(str(payload.get("status", "")).strip().upper())
    except ValueError:
        return 422, {"error": "VALIDATION_ERROR", "detail": "Status de decisão não reconhecido."}
    if new_status not in _DECISION_STATUSES:
        return 422, {
            "error": "VALIDATION_ERROR",
            "detail": "O recebimento inicial não pode ser relançado por esta rota.",
        }
    note = sanitize_untrusted_text(str(payload.get("note", "")), 2000)
    if not note:
        return 422, {"error": "VALIDATION_ERROR", "detail": "A nota de decisão é obrigatória."}
    try:
        assert_non_accusatory_language(note)
    except ValueError:
        return 422, {
            "error": "EDITORIAL_POLICY",
            "detail": "A nota de decisão contém linguagem vedada pela política editorial.",
        }
    clean_actor = sanitize_untrusted_text(actor_id, 80)
    if not clean_actor:
        return 422, {"error": "VALIDATION_ERROR", "detail": "O responsável pela decisão é obrigatório."}

    moment = _stamp(now or _utcnow())
    event_id = f"evt-{uuid.uuid4().hex[:12]}"
    with storage._connect() as conn:
        existing = conn.execute(
            "SELECT challenge_id FROM civic_challenges WHERE challenge_id = ?",
            (challenge_id,),
        ).fetchone()
        if existing is None:
            return 404, {"error": "NOT_FOUND", "detail": "Protocolo não encontrado."}
        conn.execute(
            "UPDATE civic_challenges SET status = ? WHERE challenge_id = ?",
            (new_status.value, challenge_id),
        )
        conn.execute(
            """
            INSERT INTO civic_challenge_events (
                event_id, challenge_id, event_type, actor_id, note, occurred_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, challenge_id, new_status.value, clean_actor, note, moment),
        )
    return get_admin_challenge(storage, challenge_id)
