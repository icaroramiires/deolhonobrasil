"""Resilient Government HTTP Collectors, SSRF Guard & Streaming SHA-256 Manifests (`SPEC-0005`).

Implements `FR-012`, `FR-013`, `NFR-008`, `DATA-007`, and `SEC-008`:
- Strict SSRF protection (`https://` only, official `.gov.br` / `.leg.br` suffix allowlist, blocks literal IPs and credentials).
- Configurable maximum payload byte ceiling (`max_response_bytes`) to prevent OOM / zip bombs.
- Deterministic exponential backoff retry for transient government portal HTTP errors (`429`, `502`, `503`, `504`).
- Immediate `SHA-256` manifest generation (`HTTPFetchManifest`) at the HTTP ingestion boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
import ipaddress
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
import urllib.request

from deolhonobrasil.pipeline.connectors.camara_ceap import parse_camara_ceap_csv_batch
from deolhonobrasil.pipeline.connectors.cgu_transparencia import (
    parse_cgu_amendments_json_batch,
)
from deolhonobrasil.pipeline.connectors.pncp_contratos import (
    parse_pncp_contracts_json_batch,
)
from deolhonobrasil.pipeline.connectors.senado_ceaps import parse_senado_ceaps_csv_batch
from deolhonobrasil.pipeline.privacy import compute_sha256_bytes
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage, ReconciliationReport


TransportCallable = Callable[[str, float], tuple[int, dict[str, str], bytes]]


class SSRFProtectionError(ValueError):
    """Raised when a target URL violates the official `.gov.br`/`.leg.br` HTTPS allowlist (`SEC-008`)."""


class PayloadTooLargeError(ValueError):
    """Raised when a response payload exceeds `HTTPCollectorConfig.max_response_bytes` (`NFR-008`)."""


class TransientHTTPError(RuntimeError):
    """Raised when an upstream government portal returns a transient error (`429`, `502`, `503`, `504`)."""

    def __init__(self, status_code: int, url: str, message: str = "") -> None:
        super().__init__(f"HTTP {status_code} for {url}: {message}")
        self.status_code = status_code
        self.url = url


@dataclass(frozen=True, slots=True)
class HTTPCollectorConfig:
    """Immutable configuration for `ResilientGovernmentHTTPClient` (`SPEC-0005`)."""

    allowed_host_suffixes: tuple[str, ...] = (".gov.br", ".leg.br")
    max_response_bytes: int = 50 * 1024 * 1024
    timeout_seconds: float = 15.0
    max_retries: int = 3
    base_backoff_seconds: float = 0.5
    user_agent: str = "DeOlhoNoBrasil-CivicAuditBot/0.3 (+https://github.com/deolhonobrasil)"


@dataclass(frozen=True, slots=True)
class HTTPFetchManifest:
    """Immutable cryptographic receipt produced at the HTTP ingestion boundary (`DATA-007`)."""

    url: str
    status_code: int
    sha256_hex: str
    byte_length: int
    content_type: str
    fetched_at_utc: str
    attempts: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_official_government_url(
    url: str,
    config: HTTPCollectorConfig | None = None,
) -> str:
    """Validates that `url` uses `https://`, contains no credentials/IPs, and matches `.gov.br`/`.leg.br`."""
    cfg = config or HTTPCollectorConfig()
    cleaned = (url or "").strip()
    if not cleaned:
        raise SSRFProtectionError("URL de coleta não pode ser vazia.")

    parsed = urlparse(cleaned)
    if parsed.scheme.lower() != "https":
        raise SSRFProtectionError(
            f"Esquema inseguro '{parsed.scheme}' bloqueado (exigido https://): {cleaned}"
        )

    if parsed.username or parsed.password:
        raise SSRFProtectionError(f"Credenciais embutidas na URL são proibidas: {cleaned}")

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        raise SSRFProtectionError(f"Hostname ausente na URL: {cleaned}")

    if hostname in {"localhost", "127.0.0.1", "::1"}:
        raise SSRFProtectionError(f"Host local bloqueado pela guarda Anti-SSRF: {hostname}")

    try:
        ipaddress.ip_address(hostname)
        raise SSRFProtectionError(f"Endereço IP literal bloqueado pela guarda Anti-SSRF: {hostname}")
    except ValueError:
        pass

    if not any(hostname.endswith(suffix) for suffix in cfg.allowed_host_suffixes):
        raise SSRFProtectionError(
            f"Domínio '{hostname}' fora da allowlist oficial {cfg.allowed_host_suffixes}"
        )

    return cleaned


class ResilientGovernmentHTTPClient:
    """HTTP client enforcing SSRF guard, max byte limits, exponential retry, and SHA-256 receipts."""

    def __init__(
        self,
        config: HTTPCollectorConfig | None = None,
        transport: TransportCallable | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config or HTTPCollectorConfig()
        self._transport = transport or self._default_urllib_transport
        self._sleep_fn = sleep_fn

    def _default_urllib_transport(
        self,
        url: str,
        timeout: float,
    ) -> tuple[int, dict[str, str], bytes]:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "application/json, text/csv, */*",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = int(getattr(resp, "status", 200))
                headers = {k.lower(): v for k, v in resp.headers.items()}
                data = resp.read(self.config.max_response_bytes + 1)
                return status_code, headers, data
        except HTTPError as exc:
            if exc.code in {429, 502, 503, 504}:
                raise TransientHTTPError(exc.code, url, str(exc.reason)) from exc
            raise
        except URLError as exc:
            raise TransientHTTPError(503, url, str(exc.reason)) from exc

    def fetch_bytes(self, url: str) -> tuple[bytes, HTTPFetchManifest]:
        """Fetches bytes from an official government URL with retry/backoff and returns `(bytes, HTTPFetchManifest)`."""
        validated_url = validate_official_government_url(url, self.config)
        max_attempts = max(1, self.config.max_retries)
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                status_code, headers, payload = self._transport(
                    validated_url,
                    self.config.timeout_seconds,
                )
                if status_code in {429, 502, 503, 504}:
                    raise TransientHTTPError(status_code, validated_url, "Transient status")

                if len(payload) > self.config.max_response_bytes:
                    raise PayloadTooLargeError(
                        f"Payload de {len(payload)} bytes excede o limite de {self.config.max_response_bytes} bytes."
                    )

                norm_headers = {k.lower(): v for k, v in headers.items()}
                content_type = norm_headers.get("content-type", "application/octet-stream")
                manifest = HTTPFetchManifest(
                    url=validated_url,
                    status_code=status_code,
                    sha256_hex=compute_sha256_bytes(payload),
                    byte_length=len(payload),
                    content_type=content_type,
                    fetched_at_utc=datetime.now(timezone.utc).isoformat(),
                    attempts=attempt,
                )
                return payload, manifest
            except TransientHTTPError as exc:
                last_error = exc
                if attempt >= max_attempts:
                    raise
                backoff = self.config.base_backoff_seconds * (2 ** (attempt - 1))
                self._sleep_fn(backoff)

        assert last_error is not None
        raise last_error


class LiveGovernmentIngestionService:
    """Orchestrates HTTP collection from the 4 federal transparency portals into `CivicLakehouseStorage`."""

    DEFAULT_ENDPOINTS: Mapping[str, str] = {
        "CAMARA_CEAP": "https://www.camara.leg.br/cotas/Ano-2026.csv.zip",
        "SENADO_CEAPS": "https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/2026/csv",
        "CGU_EMENDAS": "https://api.portaldatransparencia.gov.br/api-de-dados/emendas?ano=2026",
        "PNCP_CONTRATOS": "https://pncp.gov.br/api/consulta/v1/contratos?dataInicial=20260901&dataFinal=20260930",
    }

    def __init__(
        self,
        storage: CivicLakehouseStorage,
        http_client: ResilientGovernmentHTTPClient,
    ) -> None:
        self.storage = storage
        self.http_client = http_client

    def ingest_all_default_sources(
        self,
        control_totals: Mapping[str, Decimal] | None = None,
    ) -> dict[str, list[Any]]:
        totals = control_totals or {}
        manifests: list[HTTPFetchManifest] = []
        reports: list[ReconciliationReport] = []

        # 1. Câmara CEAP
        camara_url = self.DEFAULT_ENDPOINTS["CAMARA_CEAP"]
        camara_bytes, camara_manifest = self.http_client.fetch_bytes(camara_url)
        manifests.append(camara_manifest)
        camara_batch = parse_camara_ceap_csv_batch(
            camara_bytes,
            source_url=camara_url,
            reported_control_total=totals.get("CAMARA_CEAP"),
        )
        reports.append(self.storage.persist_expense_batch(camara_bytes, camara_batch))

        # 2. Senado CEAPS
        senado_url = self.DEFAULT_ENDPOINTS["SENADO_CEAPS"]
        senado_bytes, senado_manifest = self.http_client.fetch_bytes(senado_url)
        manifests.append(senado_manifest)
        senado_batch = parse_senado_ceaps_csv_batch(
            senado_bytes,
            source_url=senado_url,
            reported_control_total=totals.get("SENADO_CEAPS"),
        )
        reports.append(self.storage.persist_expense_batch(senado_bytes, senado_batch))

        # 3. CGU Emendas
        cgu_url = self.DEFAULT_ENDPOINTS["CGU_EMENDAS"]
        cgu_bytes, cgu_manifest = self.http_client.fetch_bytes(cgu_url)
        manifests.append(cgu_manifest)
        cgu_batch = parse_cgu_amendments_json_batch(
            cgu_bytes,
            source_url=cgu_url,
            reported_control_total=totals.get("CGU_EMENDAS"),
        )
        reports.append(self.storage.persist_amendment_batch(cgu_bytes, cgu_batch))

        # 4. PNCP Contratos
        pncp_url = self.DEFAULT_ENDPOINTS["PNCP_CONTRATOS"]
        pncp_bytes, pncp_manifest = self.http_client.fetch_bytes(pncp_url)
        manifests.append(pncp_manifest)
        pncp_batch = parse_pncp_contracts_json_batch(
            pncp_bytes,
            source_url=pncp_url,
            reported_control_total=totals.get("PNCP_CONTRATOS"),
        )
        reports.append(self.storage.persist_contract_batch(pncp_bytes, pncp_batch))

        return {
            "manifests": manifests,
            "reconciliation_reports": reports,
        }
