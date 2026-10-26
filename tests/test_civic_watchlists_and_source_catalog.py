from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from deolhonobrasil.api.service import CivicAuditHTTPApp
from deolhonobrasil.pipeline.models import (
    CivicWatchlistEvent,
    CivicWatchlistSubscription,
    DataSourceSpecification,
    assert_non_accusatory_language,
    get_official_data_source_catalog,
)
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


class TestCivicWatchlistsAndSourceCatalog(unittest.TestCase):
    """Testes formais para SPEC-0021 (Acompanhamentos Cívicos e Catálogo de Fontes)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = CivicLakehouseStorage(data_dir=Path(self.temp_dir.name))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_watchlist_subscription_model_and_event_generation(self) -> None:
        """Test Anchor 1: Validação dos modelos imutáveis de acompanhamento, evento e catálogo."""
        sub = CivicWatchlistSubscription(
            subscription_id="sub-test-01",
            entity_type="FORNECEDOR",
            entity_id="12.345.678/0001-90",
            entity_name="Tecnologia e Serviços Brasil Ltda",
            monitored_events=("NOVO_DOCUMENTO", "ALTERACAO_VALOR"),
            frequency="DIARIA",
            channel="NAVEGADOR_LOCAL",
            is_active=True,
            created_at="2026-10-26T18:00:00Z",
            sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )
        self.assertEqual(sub.subscription_id, "sub-test-01")
        self.assertEqual(sub.entity_type, "FORNECEDOR")
        self.assertEqual(len(sub.monitored_events), 2)
        self.assertTrue(sub.is_active)

        # Imutabilidade (frozen=True)
        with self.assertRaises(Exception):
            sub.is_active = False  # type: ignore

        # Validação de tipo de entidade inválido
        with self.assertRaises(ValueError):
            CivicWatchlistSubscription(
                subscription_id="sub-bad",
                entity_type="TIPO_INVALIDO",
                entity_id="123",
                entity_name="Invalido",
                monitored_events=("NOVO_DOCUMENTO",),
                frequency="DIARIA",
                channel="NAVEGADOR_LOCAL",
            )

        # Modelo de Evento
        event = CivicWatchlistEvent(
            event_id="evt-01",
            subscription_id="sub-test-01",
            entity_type="FORNECEDOR",
            entity_id="12.345.678/0001-90",
            event_type="ALTERACAO_VALOR",
            title="Termo Aditivo Publicado",
            description="Publicação de termo aditivo com alteração de valor contratual registrado no PNCP.",
            occurred_at="2026-10-26T14:30:00Z",
            payload_sha256="4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
            is_read=False,
        )
        self.assertEqual(event.event_id, "evt-01")
        self.assertFalse(event.is_read)
        self.assertEqual(len(event.payload_sha256), 64)

        # Imutabilidade do evento
        with self.assertRaises(Exception):
            event.is_read = True  # type: ignore

        # Validação do Catálogo de Fontes
        catalog = get_official_data_source_catalog()
        self.assertGreaterEqual(len(catalog), 8)
        source_ids = [s.source_id for s in catalog]
        expected_sources = [
            "CAMARA_CEAP",
            "SENADO_CEAPS",
            "CGU_EMENDAS",
            "PNCP_CONTRATOS",
            "CGU_CEIS",
            "CGU_CNEP",
            "TSE_ELEICOES",
            "RECEITA_FEDERAL_CNPJ",
        ]
        for src in expected_sources:
            self.assertIn(src, source_ids)

        # Verificação de não-acusatório nas descrições do catálogo
        for spec in catalog:
            self.assertTrue(len(spec.governing_body) > 0)
            self.assertTrue(len(spec.epistemic_limitations) > 0)
            for limitation in spec.epistemic_limitations:
                assert_non_accusatory_language(limitation)

    def test_storage_watchlist_crud_lifecycle_and_events(self) -> None:
        """Test Anchor 2: Persistência no Lakehouse, integridade referencial e ciclo CRUD."""
        sub = CivicWatchlistSubscription(
            subscription_id="sub-crud-01",
            entity_type="MANDATARIO",
            entity_id="DEP-9988",
            entity_name="Deputado Exemplar",
            monitored_events=("NOVO_DOCUMENTO", "NOVO_PAGAMENTO"),
            frequency="IMEDIATA",
            channel="NAVEGADOR_LOCAL",
            is_active=True,
            created_at="2026-10-26T18:10:00Z",
            sha256="a" * 64,
        )

        # 1. Inserção
        created = self.storage.upsert_watchlist_subscription(sub)
        self.assertEqual(created.subscription_id, "sub-crud-01")

        # 2. Leitura
        fetched = self.storage.get_watchlist_subscription("sub-crud-01")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.entity_id, "DEP-9988")  # type: ignore
        self.assertTrue(fetched.is_active)  # type: ignore

        # 3. Listagem
        subs = self.storage.list_watchlist_subscriptions()
        self.assertEqual(len(subs), 1)

        # 4. Inserção de evento
        evt = CivicWatchlistEvent(
            event_id="evt-crud-10",
            subscription_id="sub-crud-01",
            entity_type="MANDATARIO",
            entity_id="DEP-9988",
            event_type="NOVO_DOCUMENTO",
            title="Despesa Registrada",
            description="Apresentação de documento fiscal de consultoria técnica.",
            occurred_at="2026-10-26T18:15:00Z",
            payload_sha256="b" * 64,
            is_read=False,
        )
        self.storage.insert_watchlist_event(evt)

        events = self.storage.list_watchlist_events("sub-crud-01")
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0].is_read)

        # 5. Marcar evento como lido
        self.storage.mark_watchlist_event_read("evt-crud-10")
        events_updated = self.storage.list_watchlist_events("sub-crud-01")
        self.assertTrue(events_updated[0].is_read)

        # 6. Atualizar status (pausar)
        self.storage.update_watchlist_subscription_status("sub-crud-01", is_active=False)
        paused = self.storage.get_watchlist_subscription("sub-crud-01")
        self.assertFalse(paused.is_active)  # type: ignore

        # 6b. Atualizar status com frequência inválida deve levantar ValueError
        with self.assertRaises(ValueError):
            self.storage.update_watchlist_subscription_status("sub-crud-01", is_active=True, frequency="DESCONHECIDA")

        # 7. Deleção e cascata
        self.storage.delete_watchlist_subscription("sub-crud-01")
        self.assertIsNone(self.storage.get_watchlist_subscription("sub-crud-01"))
        self.assertEqual(len(self.storage.list_watchlist_events("sub-crud-01")), 0)

    def test_api_watchlist_and_sources_catalog_endpoints(self) -> None:
        """Test Anchor 3: Resposta dos endpoints REST WSGI com performance sub-50ms."""
        app = CivicAuditHTTPApp(self.storage)

        # 1. GET /api/v1/sources/catalog
        t0 = time.perf_counter()
        status_cat, headers_cat, body_cat = app.handle_request("GET", "/api/v1/sources/catalog", b"")
        elapsed_cat = time.perf_counter() - t0

        self.assertEqual(status_cat, 200)
        self.assertLess(elapsed_cat, 0.05, "Catálogo deve responder em tempo sub-50ms")
        cat_json = json.loads(body_cat.decode("utf-8"))
        self.assertEqual(cat_json["total_sources"], 8)
        self.assertEqual(len(cat_json["sources"]), 8)

        # 2. POST /api/v1/watchlists
        payload = json.dumps(
            {
                "entity_type": "ORGAO",
                "entity_id": "MIN-SAUDE-01",
                "entity_name": "Ministério da Saúde",
                "monitored_events": ["NOVO_DOCUMENTO", "NOVO_PAGAMENTO"],
                "frequency": "SEMANAL",
                "channel": "NAVEGADOR_LOCAL",
            }
        ).encode("utf-8")

        status_post, headers_post, body_post = app.handle_request("POST", "/api/v1/watchlists", payload)
        self.assertEqual(status_post, 201)
        created_json = json.loads(body_post.decode("utf-8"))
        sub_id = created_json["subscription_id"]
        self.assertTrue(sub_id.startswith("sub-"))
        self.assertEqual(created_json["entity_name"], "Ministério da Saúde")

        # 3. GET /api/v1/watchlists
        status_get, headers_get, body_get = app.handle_request("GET", "/api/v1/watchlists", b"")
        self.assertEqual(status_get, 200)
        list_json = json.loads(body_get.decode("utf-8"))
        self.assertEqual(list_json["total"], 1)
        self.assertEqual(len(list_json["subscriptions"]), 1)

        # 4. PUT /api/v1/watchlists/{id}
        put_payload = json.dumps({"is_active": False, "frequency": "DIARIA"}).encode("utf-8")
        status_put, headers_put, body_put = app.handle_request(
            "PUT", f"/api/v1/watchlists/{sub_id}", put_payload
        )
        self.assertEqual(status_put, 200)
        put_json = json.loads(body_put.decode("utf-8"))
        self.assertFalse(put_json["is_active"])
        self.assertEqual(put_json["frequency"], "DIARIA")

        # 4b. Regressão VULN-02: PUT com frequência inválida deve retornar HTTP 422 sem corromper o banco
        bad_put_payload = json.dumps({"frequency": "FREQUENCIA_INVALIDA"}).encode("utf-8")
        status_bad, _, body_bad = app.handle_request(
            "PUT", f"/api/v1/watchlists/{sub_id}", bad_put_payload
        )
        self.assertEqual(status_bad, 422)
        bad_json = json.loads(body_bad.decode("utf-8"))
        self.assertEqual(bad_json["error"], "VALIDATION_ERROR")

        # Garantir que o registro permaneceu íntegro e legível após tentativa inválida
        status_verify, _, body_verify = app.handle_request("GET", "/api/v1/watchlists", b"")
        self.assertEqual(status_verify, 200)
        verify_json = json.loads(body_verify.decode("utf-8"))
        self.assertEqual(verify_json["subscriptions"][0]["frequency"], "DIARIA")

        # 5. DELETE /api/v1/watchlists/{id}
        status_del, headers_del, body_del = app.handle_request("DELETE", f"/api/v1/watchlists/{sub_id}", b"")
        self.assertEqual(status_del, 200)
        del_json = json.loads(body_del.decode("utf-8"))
        self.assertEqual(del_json["status"], "deleted")

    def test_ui_watchlist_and_catalog_markup_and_interactions(self) -> None:
        """Test Anchor 4: Verificação de marcação HTML, modais acessíveis e conformidade léxica."""
        wireframe_path = Path(__file__).resolve().parents[1] / "wireframe_de_olho_no_brasil.html"
        self.assertTrue(wireframe_path.exists())
        content = wireframe_path.read_text(encoding="utf-8")

        # Seção de Acompanhamentos e Catálogo de Fontes
        self.assertIn('data-nav="acompanhamentos"', content)
        self.assertIn('id="view-acompanhamentos"', content)
        self.assertIn('role="dialog"', content)
        self.assertIn('aria-modal="true"', content)
        self.assertIn("modal-watchlist", content)
        self.assertIn("modal-catalog", content)

        # Regressão VULN-01: Verificação de escape de HTML contra XSS e Focus Trap
        self.assertIn("escapeHtml", content)
        self.assertIn("escapeHtml(entityName)", content)

        # Conformidade léxica
        assert_non_accusatory_language(content)


if __name__ == "__main__":
    unittest.main()
