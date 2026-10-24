"""Unit and integration tests for SPEC-0005 (Resilient Government HTTP Collectors, SSRF Guard & Live Ingestion)."""

from __future__ import annotations

from decimal import Decimal
import io
from pathlib import Path
import tempfile
import unittest

from deolhonobrasil.pipeline.cli import (
    SAMPLE_CAMARA_CSV,
    SAMPLE_CGU_AMENDMENTS_JSON,
    SAMPLE_PNCP_CONTRACTS_JSON,
    SAMPLE_SENADO_CSV,
    main as cli_main,
)
from deolhonobrasil.pipeline.http_client import (
    HTTPCollectorConfig,
    HTTPFetchManifest,
    LiveGovernmentIngestionService,
    PayloadTooLargeError,
    ResilientGovernmentHTTPClient,
    SSRFProtectionError,
    TransientHTTPError,
    validate_official_government_url,
)
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


class TestResilientGovernmentHTTPCollectors(unittest.TestCase):
    """Verifies SPEC-0005 requirements FR-012, FR-013, NFR-008, DATA-007, SEC-008 and AC-018..021."""

    def test_ssrf_guard_blocks_non_https_and_untrusted_hosts(self) -> None:
        config = HTTPCollectorConfig()
        # 1. Valid official HTTPS .leg.br and .gov.br URLs pass
        validate_official_government_url(
            "https://dadosabertos.camara.leg.br/arquivos/cotas/Ano-2026.csv",
            config,
        )
        validate_official_government_url(
            "https://pncp.gov.br/api/consulta/v1/contratos?pagina=1",
            config,
        )

        # 2. Non-HTTPS schemes must be blocked (SSRFProtectionError)
        for bad_scheme_url in (
            "http://dadosabertos.camara.leg.br/arquivos/Ano-2026.csv",
            "file:///etc/passwd",
            "ftp://pncp.gov.br/file.csv",
        ):
            with self.assertRaises(SSRFProtectionError):
                validate_official_government_url(bad_scheme_url, config)

        # 3. Untrusted domains, localhost, private IPs or embedded credentials must be blocked
        for untrusted_url in (
            "https://127.0.0.1/api/v1/secret",
            "https://169.254.169.254/latest/meta-data/",
            "https://evil-attacker.com/camara.leg.br",
            "https://user:pass@pncp.gov.br/api",
        ):
            with self.assertRaises(SSRFProtectionError):
                validate_official_government_url(untrusted_url, config)

    def test_payload_size_limit_prevents_memory_exhaustion(self) -> None:
        tiny_config = HTTPCollectorConfig(max_response_bytes=64, max_retries=1)

        def _oversized_transport(url: str, timeout: float) -> tuple[int, dict[str, str], bytes]:
            return 200, {"Content-Type": "text/csv"}, b"X" * 128

        client = ResilientGovernmentHTTPClient(
            config=tiny_config,
            transport=_oversized_transport,
        )
        with self.assertRaises(PayloadTooLargeError):
            client.fetch_bytes("https://dadosabertos.camara.leg.br/arquivos/Ano-2026.csv")

    def test_exponential_retry_recovers_from_transient_503(self) -> None:
        attempts_counter = {"count": 0}
        sleeps_recorded: list[float] = []

        def _flaky_transport(url: str, timeout: float) -> tuple[int, dict[str, str], bytes]:
            attempts_counter["count"] += 1
            if attempts_counter["count"] < 3:
                raise TransientHTTPError(status_code=503, url=url, message="Service Unavailable")
            return 200, {"Content-Type": "text/csv; charset=utf-8"}, b"id;valor\n1;100,00\n"

        config = HTTPCollectorConfig(
            max_retries=3,
            base_backoff_seconds=0.05,
        )
        client = ResilientGovernmentHTTPClient(
            config=config,
            transport=_flaky_transport,
            sleep_fn=sleeps_recorded.append,
        )
        raw_bytes, manifest = client.fetch_bytes(
            "https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/2026/csv"
        )
        self.assertIsInstance(manifest, HTTPFetchManifest)
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(manifest.attempts, 3)
        self.assertEqual(len(sleeps_recorded), 2)
        self.assertEqual(len(manifest.sha256_hex), 64)
        self.assertEqual(manifest.byte_length, len(raw_bytes))

    def test_live_ingestion_service_persists_and_reconciles_batches(self) -> None:
        routes: dict[str, tuple[int, dict[str, str], bytes]] = {
            "https://www.camara.leg.br/cotas/Ano-2026.csv.zip": (
                200,
                {"Content-Type": "text/csv"},
                SAMPLE_CAMARA_CSV.encode("utf-8"),
            ),
            "https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/2026/csv": (
                200,
                {"Content-Type": "text/csv"},
                SAMPLE_SENADO_CSV.encode("utf-8"),
            ),
            "https://api.portaldatransparencia.gov.br/api-de-dados/emendas?ano=2026": (
                200,
                {"Content-Type": "application/json"},
                SAMPLE_CGU_AMENDMENTS_JSON.encode("utf-8"),
            ),
            "https://pncp.gov.br/api/consulta/v1/contratos?dataInicial=20260901&dataFinal=20260930": (
                200,
                {"Content-Type": "application/json"},
                SAMPLE_PNCP_CONTRACTS_JSON.encode("utf-8"),
            ),
        }

        def _mock_gov_transport(url: str, timeout: float) -> tuple[int, dict[str, str], bytes]:
            return routes[url]

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = CivicLakehouseStorage(Path(tmp_dir))
            client = ResilientGovernmentHTTPClient(transport=_mock_gov_transport)
            service = LiveGovernmentIngestionService(storage=storage, http_client=client)
            result = service.ingest_all_default_sources(
                control_totals={
                    "CAMARA_CEAP": Decimal("16700.50"),
                    "SENADO_CEAPS": Decimal("3410.20"),
                    "CGU_EMENDAS": Decimal("250000.00"),
                    "PNCP_CONTRATOS": Decimal("1820000.00"),
                }
            )
            self.assertEqual(len(result["manifests"]), 4)
            self.assertTrue(all(r.is_reconciled for r in result["reconciliation_reports"]))
            summary = storage.get_summary_metrics()
            self.assertEqual(summary["curated_expenses_net_total_brl"], "20110.70")
            self.assertEqual(summary["curated_contracts_current_total_brl"], "1820000.00")

    def test_cli_fetch_live_subcommand_executes_cleanly(self) -> None:
        import contextlib

        with tempfile.TemporaryDirectory() as tmp_dir:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exit_code = cli_main(
                    [
                        "fetch-live",
                        "--data-dir",
                        tmp_dir,
                        "--use-offline-transport",
                        "--verify-reconciliation",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertIn("fetch_manifests", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
