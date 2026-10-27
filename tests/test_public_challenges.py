"""Protocolo de contestação pública (SPEC-0023)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from deolhonobrasil.api.service import CivicAuditAPIService, CivicAuditHTTPApp
from deolhonobrasil.governance.challenges import (
    decide_challenge,
    get_admin_challenge,
    get_public_challenge,
    submit_challenge,
)
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


class TestPublicChallenges(unittest.TestCase):
    """AC-092 a AC-097."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.storage = CivicLakehouseStorage(Path(self._tmp.name))
        self.now = datetime(2026, 10, 26, 18, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_submission_masks_cpf_and_starts_received(self) -> None:
        status, body = submit_challenge(
            self.storage,
            {
                "category": "DADO_PESSOAL",
                "status": "DECIDIDO",
                "statement": "O registro exibe o CPF 529.982.247-25 de uma pessoa física.",
                "contact": "cidada@example.org",
                "related_record_ref": "despesa-local-1",
            },
            now=self.now,
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["status"], "RECEBIDO")
        self.assertFalse(body["published"])
        self.assertNotIn("statement_text", body)
        self.assertNotIn("529.982.247-25", json.dumps(body))
        self.assertEqual(body["internal_target_review_by_utc"], "2026-10-28T18:00:00Z")

        admin_status, admin = get_admin_challenge(self.storage, body["challenge_id"])
        self.assertEqual(admin_status, 200)
        self.assertIn("***.982.247-**", admin["statement_text"])
        self.assertNotIn("52998224725", admin["statement_text"])
        self.assertEqual(admin["contact_channel"], "cidada@example.org")
        self.assertEqual(len(admin["events"]), 1)

    def test_public_read_hides_statement_even_when_it_quotes_a_forbidden_term(self) -> None:
        status, created = submit_challenge(
            self.storage,
            {
                "category": "ALEGACAO_DIFAMATORIA",
                "statement": "O texto publicado usa a expressão fraude comprovada.",
            },
            now=self.now,
        )
        self.assertEqual(status, 201)
        public_status, public = get_public_challenge(self.storage, created["challenge_id"])
        rendered = json.dumps(public, ensure_ascii=False).lower()
        self.assertEqual(public_status, 200)
        self.assertNotIn("fraude comprovada", rendered)
        self.assertFalse(public["statement_disclosed"])
        missing_status, missing = get_public_challenge(self.storage, "cont-inexistente")
        self.assertEqual(missing_status, 404)

    def test_decision_appends_event_and_received_text_cannot_be_rewritten_or_deleted(self) -> None:
        _, created = submit_challenge(
            self.storage,
            {"category": "ERRO_FACTUAL", "statement": "O valor exibido não fecha com a fonte."},
            now=self.now,
        )
        status, decided = decide_challenge(
            self.storage,
            {
                "challenge_id": created["challenge_id"],
                "status": "EM_ANALISE",
                "note": "Encaminhado para conferência do hash e da fonte oficial.",
            },
            actor_id="revisor-01",
            now=self.now,
        )
        self.assertEqual(status, 200)
        self.assertEqual(decided["status"], "EM_ANALISE")
        self.assertEqual([event["event_type"] for event in decided["events"]], ["RECEBIDO", "EM_ANALISE"])

        with self.storage._connect() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "UPDATE civic_challenges SET statement_text = ? WHERE challenge_id = ?",
                    ("texto trocado", created["challenge_id"]),
                )
        with self.storage._connect() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "DELETE FROM civic_challenges WHERE challenge_id = ?",
                    (created["challenge_id"],),
                )
        with self.storage._connect() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM civic_challenge_events")

    def test_decision_note_rejects_forbidden_language_and_invalid_contact(self) -> None:
        _, created = submit_challenge(
            self.storage,
            {"category": "METODOLOGIA", "statement": "O conjunto de comparação não foi descrito."},
            now=self.now,
        )
        self.assertEqual(created["internal_target_review_by_utc"], "2026-11-10T18:00:00Z")
        blocked, body = decide_challenge(
            self.storage,
            {
                "challenge_id": created["challenge_id"],
                "status": "DECIDIDO",
                "note": "Isso é fraude comprovada.",
            },
            actor_id="revisor-01",
        )
        self.assertEqual(blocked, 422)
        self.assertEqual(body["error"], "EDITORIAL_POLICY")
        self.assertNotIn("fraude comprovada", json.dumps(body).lower())

        contact_status, contact_body = submit_challenge(
            self.storage,
            {
                "category": "METODOLOGIA",
                "statement": "Falta a descrição do método.",
                "contact": "529.982.247-25",
            },
            now=self.now,
        )
        self.assertEqual(contact_status, 422)
        self.assertEqual(contact_body["error"], "VALIDATION_ERROR")

    def test_http_routes_require_admin_token_for_the_full_record(self) -> None:
        service = CivicAuditAPIService(storage=self.storage, admin_token="token-contestacao-teste")
        app = CivicAuditHTTPApp(service)
        created = app.handle_request(
            "POST",
            "/api/v1/challenges",
            json_body={"category": "DOCUMENTO_INCORRETO", "statement": "O anexo aponta para outra versão."},
        )
        self.assertEqual(created.status_code, 201)
        challenge_id = created.body["challenge_id"]
        public = app.handle_request("GET", f"/api/v1/challenges/{challenge_id}")
        self.assertEqual(public.status_code, 200)
        self.assertNotIn("statement_text", public.body)

        forbidden = app.handle_request("GET", "/api/v1/admin/challenges", query_params={"id": challenge_id})
        self.assertEqual(forbidden.status_code, 403)
        allowed = app.handle_request(
            "GET",
            "/api/v1/admin/challenges",
            query_params={"id": challenge_id},
            headers={"X-Admin-Token": "token-contestacao-teste"},
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertIn("anexo", allowed.body["statement_text"])

        page = app.handle_request("GET", "/")
        html = page.raw_html or ""
        self.assertIn('id="form-public-challenge"', html)
        self.assertIn("/api/v1/challenges", html)
        sql = Path(__file__).resolve().parents[1] / "src/deolhonobrasil/governance/rls_policies.sql"
        policies = sql.read_text(encoding="utf-8")
        self.assertIn("p_civic_challenges_public_insert", policies)
        self.assertIn("p_civic_challenge_events_reviewer_admin", policies)
        self.assertIn("civic_challenges_public", policies)
