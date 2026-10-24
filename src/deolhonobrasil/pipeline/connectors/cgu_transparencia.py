"""Conector oficial para o Portal da Transparência do Governo Federal (CGU).

Cobre:
- Emendas Parlamentares (API `/api-de-dados/emendas` e dumps CSV).
- Cadastros de Sanções Vigentes (CEIS e CNEP) para cruzamento determinístico de fornecedores.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from deolhonobrasil.pipeline.connectors.base import IngestionBatchResult, build_batch_context
from deolhonobrasil.pipeline.models import (
    CuratedParliamentaryAmendment,
    CuratedSanctionRecord,
    OfficialSource,
    ProvenanceMetadata,
    QuarantinedRecord,
)
from deolhonobrasil.pipeline.privacy import compute_sha256_text


def parse_cgu_amendments_json_batch(
    raw_json_bytes: bytes,
    *,
    source_url: str,
    collected_at_utc: str | None = None,
    reported_control_total: Decimal | None = None,
) -> IngestionBatchResult[CuratedParliamentaryAmendment]:
    """Faz o parsing e validação de um lote JSON de Emendas Parlamentares da CGU."""
    batch_sha256, timestamp = build_batch_context(raw_json_bytes, collected_at_utc)
    result: IngestionBatchResult[CuratedParliamentaryAmendment] = IngestionBatchResult(
        source=OfficialSource.CGU_EMENDAS,
        source_url=source_url,
        raw_batch_sha256=batch_sha256,
        collected_at_utc=timestamp,
        reported_control_total=reported_control_total,
    )

    items = json.loads(raw_json_bytes.decode("utf-8"))
    if not isinstance(items, list):
        raise ValueError("Payload JSON da CGU deve ser uma lista de objetos de emendas.")

    for idx, item in enumerate(items, start=1):
        code = str(item.get("codigoEmenda") or "").strip()
        fallback_id = code or f"CGU-EMD-{idx}"
        try:
            if not code or code.upper() == "S/I":
                raise ValueError("Código da emenda ('codigoEmenda') ausente ou sem informação ('S/I').")

            provenance = ProvenanceMetadata(
                source=OfficialSource.CGU_EMENDAS,
                source_url=source_url,
                source_record_id=code,
                collected_at_utc=timestamp,
                raw_batch_sha256=batch_sha256,
            )

            amendment = CuratedParliamentaryAmendment.create_validated(
                amendment_code=code,
                year=int(item.get("ano") or 0),
                author_id=str(item.get("codigoAutor") or "").strip(),
                author_name=str(item.get("nomeAutor") or item.get("autor") or "").strip(),
                amendment_type=str(item.get("tipoEmenda") or "").strip(),
                function_name=str(item.get("funcao") or "").strip(),
                municipality_ibge_code=str(item.get("codigoIBGEMunicipio") or "NACIONAL").strip(),
                state_uf=str(item.get("uf") or "BR").strip(),
                beneficiary_raw_doc=str(item.get("cnpjFavorecido") or item.get("cpfCnpjFavorecido") or "").strip(),
                beneficiary_name=str(item.get("nomeFavorecido") or "").strip(),
                committed_amount_raw=item.get("valorEmpenhado"),
                paid_amount_raw=item.get("valorPago"),
                provenance=provenance,
            )
            result.valid_records.append(amendment)
        except Exception as exc:
            q_id = compute_sha256_text(f"{batch_sha256}|{fallback_id}|{idx}")
            result.quarantined_records.append(
                QuarantinedRecord(
                    quarantine_id=q_id,
                    source=OfficialSource.CGU_EMENDAS,
                    source_record_id=fallback_id,
                    raw_batch_sha256=batch_sha256,
                    rejection_reason=str(exc),
                    raw_payload_json=json.dumps(item, ensure_ascii=False),
                    quarantined_at_utc=timestamp,
                )
            )

    return result


def parse_cgu_ceis_cnep_json_batch(
    raw_json_bytes: bytes,
    *,
    source_url: str,
    collected_at_utc: str | None = None,
) -> IngestionBatchResult[CuratedSanctionRecord]:
    """Faz o parsing e validação de um lote JSON de sanções administrativas (CEIS/CNEP - `SPEC-0007`)."""
    batch_sha256, timestamp = build_batch_context(raw_json_bytes, collected_at_utc)
    result: IngestionBatchResult[CuratedSanctionRecord] = IngestionBatchResult(
        source=OfficialSource.CGU_CEIS_CNEP,
        source_url=source_url,
        raw_batch_sha256=batch_sha256,
        collected_at_utc=timestamp,
        reported_control_total=None,
    )

    items = json.loads(raw_json_bytes.decode("utf-8"))
    if not isinstance(items, list):
        raise ValueError("Payload JSON CEIS/CNEP deve ser uma lista de objetos de sanção.")

    for idx, item in enumerate(items, start=1):
        code = str(item.get("codigoSancao") or "").strip()
        fallback_id = code or f"CGU-CEIS-{idx}"
        try:
            if not code:
                raise ValueError("Código da sanção ('codigoSancao') ausente.")

            start_raw = str(item.get("dataInicioSancao") or "").strip()
            if not start_raw:
                raise ValueError("Data de início da sanção ('dataInicioSancao') ausente.")
            start_dt = date.fromisoformat(start_raw[:10])

            end_raw = str(item.get("dataFimSancao") or "").strip()
            end_dt = date.fromisoformat(end_raw[:10]) if end_raw else None

            provenance = ProvenanceMetadata(
                source=OfficialSource.CGU_CEIS_CNEP,
                source_url=source_url,
                source_record_id=code,
                collected_at_utc=timestamp,
                raw_batch_sha256=batch_sha256,
            )

            sanction = CuratedSanctionRecord.create_validated(
                sanction_code=code,
                sanctioned_raw_doc=str(item.get("cpfCnpjSancionado") or "").strip(),
                sanctioned_name=str(item.get("nomeSancionado") or "").strip(),
                sanction_type=str(item.get("tipoSancao") or "").strip(),
                sanctioning_organ=str(item.get("orgaoSancionador") or "N/A").strip(),
                state_uf=str(item.get("ufOrgaoSancionador") or "BR").strip(),
                start_date=start_dt,
                end_date=end_dt,
                provenance=provenance,
            )
            result.valid_records.append(sanction)
        except Exception as exc:
            q_id = compute_sha256_text(f"{batch_sha256}|{fallback_id}|{idx}")
            result.quarantined_records.append(
                QuarantinedRecord(
                    quarantine_id=q_id,
                    source=OfficialSource.CGU_CEIS_CNEP,
                    source_record_id=fallback_id,
                    raw_batch_sha256=batch_sha256,
                    rejection_reason=str(exc),
                    raw_payload_json=json.dumps(item, ensure_ascii=False),
                    quarantined_at_utc=timestamp,
                )
            )

    return result

