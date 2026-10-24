"""Interface base para conectores de fontes oficiais com cálculo de SHA-256 e quarentena."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Generic, TypeVar

from deolhonobrasil.pipeline.models import OfficialSource, QuarantinedRecord
from deolhonobrasil.pipeline.privacy import compute_sha256_bytes

T = TypeVar("T")


@dataclass(slots=True)
class IngestionBatchResult(Generic[T]):
    """Resultado auditável da execução de um conector sobre um lote bruto."""

    source: OfficialSource
    source_url: str
    raw_batch_sha256: str
    collected_at_utc: str
    valid_records: list[T] = field(default_factory=list)
    quarantined_records: list[QuarantinedRecord] = field(default_factory=list)
    reported_control_total: Decimal | None = None

    @property
    def total_processed(self) -> int:
        return len(self.valid_records) + len(self.quarantined_records)

    @property
    def quarantine_rate(self) -> float:
        if self.total_processed == 0:
            return 0.0
        return len(self.quarantined_records) / self.total_processed


def build_batch_context(raw_bytes: bytes, collected_at_utc: str | None = None) -> tuple[str, str]:
    """Calcula o SHA-256 do payload bruto e retorna (sha256_hex, collected_at_utc)."""
    sha256_hex = compute_sha256_bytes(raw_bytes)
    timestamp = collected_at_utc or datetime.now(UTC).isoformat()
    return sha256_hex, timestamp
