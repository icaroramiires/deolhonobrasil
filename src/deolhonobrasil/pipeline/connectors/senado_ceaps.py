"""Conector oficial para a Cota para o Exercício da Atividade Parlamentar dos Senadores (CEAPS).

Fonte oficial:
- API Administrativa de Dados Abertos do Senado Federal:
  https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}/csv
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from decimal import Decimal

from deolhonobrasil.pipeline.connectors.base import IngestionBatchResult, build_batch_context
from deolhonobrasil.pipeline.models import (
    CuratedPublicExpense,
    OfficialSource,
    ProvenanceMetadata,
    QuarantinedRecord,
)
from deolhonobrasil.pipeline.privacy import compute_sha256_text


def _parse_senado_date(raw_date: str) -> date:
    """Suporta formato ISO (YYYY-MM-DD) e formato brasileiro (DD/MM/YYYY) do CSV do Senado."""
    cleaned = raw_date.strip()
    if not cleaned:
        raise ValueError("Data de emissão ausente no registro CEAPS do Senado.")
    if "/" in cleaned:
        parts = cleaned[:10].split("/")
        if len(parts) == 3:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
    return date.fromisoformat(cleaned[:10])


def parse_senado_ceaps_csv_batch(
    raw_csv_bytes: bytes,
    *,
    source_url: str,
    collected_at_utc: str | None = None,
    reported_control_total: Decimal | None = None,
) -> IngestionBatchResult[CuratedPublicExpense]:
    """Faz o parsing e validação de um lote CSV oficial da CEAPS (Senado Federal)."""
    batch_sha256, timestamp = build_batch_context(raw_csv_bytes, collected_at_utc)
    result: IngestionBatchResult[CuratedPublicExpense] = IngestionBatchResult(
        source=OfficialSource.SENADO_CEAPS,
        source_url=source_url,
        raw_batch_sha256=batch_sha256,
        collected_at_utc=timestamp,
        reported_control_total=reported_control_total,
    )

    text_content = raw_csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text_content), delimiter=";")

    for idx, row in enumerate(reader, start=1):
        rec_id = str(row.get("COD_DOCUMENTO") or row.get("id") or "").strip()
        fallback_rec_id = rec_id or f"SEN-ROW-{idx}"
        try:
            if not rec_id:
                raise ValueError("Identificador 'COD_DOCUMENTO' ausente no registro CEAPS.")

            issue_dt = _parse_senado_date(str(row.get("DATA") or row.get("data") or ""))

            provenance = ProvenanceMetadata(
                source=OfficialSource.SENADO_CEAPS,
                source_url=source_url,
                source_record_id=rec_id,
                collected_at_utc=timestamp,
                raw_batch_sha256=batch_sha256,
            )

            reimbursed_raw = row.get("VALOR_REEMBOLSADO") or row.get("valorReembolsado")
            expense = CuratedPublicExpense.create_validated(
                competence_year=int(str(row.get("ANO") or row.get("ano") or 0).strip()),
                competence_month=int(str(row.get("MES") or row.get("mes") or 0).strip()),
                issue_date=issue_dt,
                sphere="FEDERAL_LEGISLATIVO",
                organ_code="SENADO_FEDERAL",
                organ_name="Senado Federal",
                public_agent_id=str(row.get("COD_SENADOR") or row.get("codSenador") or "").strip(),
                public_agent_name=str(row.get("SENADOR") or row.get("nomeSenador") or "").strip(),
                party_sigla=str(row.get("PARTIDO") or "N/A").strip(),
                state_uf=str(row.get("UF") or "BR").strip(),
                expense_category=str(row.get("TIPO_DESPESA") or row.get("tipoDespesa") or "").strip(),
                supplier_raw_doc=str(row.get("CNPJ_CPF") or row.get("cnpjCpf") or "").strip(),
                supplier_name=str(row.get("FORNECEDOR") or row.get("fornecedor") or "").strip(),
                document_number=str(row.get("DOCUMENTO") or row.get("documento") or "").strip(),
                gross_amount_raw=reimbursed_raw,
                net_amount_raw=reimbursed_raw,
                document_evidence_url=None,
                provenance=provenance,
            )
            result.valid_records.append(expense)
        except Exception as exc:
            q_id = compute_sha256_text(f"{batch_sha256}|{fallback_rec_id}|{idx}")
            result.quarantined_records.append(
                QuarantinedRecord(
                    quarantine_id=q_id,
                    source=OfficialSource.SENADO_CEAPS,
                    source_record_id=fallback_rec_id,
                    raw_batch_sha256=batch_sha256,
                    rejection_reason=str(exc),
                    raw_payload_json=json.dumps(row, ensure_ascii=False),
                    quarantined_at_utc=timestamp,
                )
            )

    return result
