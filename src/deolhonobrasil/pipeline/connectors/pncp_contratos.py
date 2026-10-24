"""Conector oficial para o Portal Nacional de Contratações Públicas (PNCP - Lei 14.133/2021).

Fonte oficial:
- API de Consulta Pública PNCP (`/api/consulta/v1/contratos`)
  https://pncp.gov.br/api/consulta/swagger-ui/index.html
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from deolhonobrasil.pipeline.connectors.base import IngestionBatchResult, build_batch_context
from deolhonobrasil.pipeline.models import (
    CuratedPublicContract,
    OfficialSource,
    ProvenanceMetadata,
    QuarantinedRecord,
)
from deolhonobrasil.pipeline.privacy import compute_sha256_text


def parse_pncp_contracts_json_batch(
    raw_json_bytes: bytes,
    *,
    source_url: str,
    collected_at_utc: str | None = None,
    reported_control_total: Decimal | None = None,
) -> IngestionBatchResult[CuratedPublicContract]:
    """Faz o parsing e validação de um lote JSON de Contratos Públicos do PNCP."""
    batch_sha256, timestamp = build_batch_context(raw_json_bytes, collected_at_utc)
    result: IngestionBatchResult[CuratedPublicContract] = IngestionBatchResult(
        source=OfficialSource.PNCP_CONTRATOS,
        source_url=source_url,
        raw_batch_sha256=batch_sha256,
        collected_at_utc=timestamp,
        reported_control_total=reported_control_total,
    )

    payload = json.loads(raw_json_bytes.decode("utf-8"))
    items = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("Payload do PNCP deve conter uma lista de contratos.")

    for idx, item in enumerate(items, start=1):
        control_num = str(item.get("numeroControlePNCP") or "").strip()
        fallback_id = control_num or f"PNCP-ROW-{idx}"
        try:
            if not control_num:
                raise ValueError("Campo 'numeroControlePNCP' obrigatório ausente.")

            raw_sig_date = str(item.get("dataAssinatura") or "").strip()
            if not raw_sig_date:
                raise ValueError("Campo 'dataAssinatura' obrigatório ausente no contrato PNCP.")
            sig_date = date.fromisoformat(raw_sig_date[:10])

            organ_obj = item.get("orgaoEntidade") or {}
            organ_cnpj = str(organ_obj.get("cnpj") or item.get("cnpjOrgao") or "").strip()
            organ_name = str(organ_obj.get("razaoSocial") or item.get("nomeOrgao") or "").strip()

            provenance = ProvenanceMetadata(
                source=OfficialSource.PNCP_CONTRATOS,
                source_url=source_url,
                source_record_id=control_num,
                collected_at_utc=timestamp,
                raw_batch_sha256=batch_sha256,
            )

            contract = CuratedPublicContract.create_validated(
                pncp_control_number=control_num,
                organ_cnpj_raw=organ_cnpj,
                organ_name=organ_name,
                supplier_raw_doc=str(item.get("niFornecedor") or "").strip(),
                supplier_name=str(item.get("nomeRazaoSocialFornecedor") or "").strip(),
                modality_name=str(item.get("categoriaProcesso") or item.get("modalidadeNome") or "").strip(),
                contract_object=str(item.get("objetoContrato") or "").strip(),
                signature_date=sig_date,
                initial_amount_raw=item.get("valorInicial"),
                current_amount_raw=item.get("valorGlobal") or item.get("valorAcumulado"),
                addendum_count=int(item.get("numeroRetificacao") or item.get("quantidadeAditivos") or 0),
                provenance=provenance,
            )
            result.valid_records.append(contract)
        except Exception as exc:
            q_id = compute_sha256_text(f"{batch_sha256}|{fallback_id}|{idx}")
            result.quarantined_records.append(
                QuarantinedRecord(
                    quarantine_id=q_id,
                    source=OfficialSource.PNCP_CONTRATOS,
                    source_record_id=fallback_id,
                    raw_batch_sha256=batch_sha256,
                    rejection_reason=str(exc),
                    raw_payload_json=json.dumps(item, ensure_ascii=False),
                    quarantined_at_utc=timestamp,
                )
            )

    return result
