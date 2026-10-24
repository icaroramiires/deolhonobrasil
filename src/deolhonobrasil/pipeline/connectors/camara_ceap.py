"""Conector oficial para a Cota para o Exercício da Atividade Parlamentar (CEAP) da Câmara.

Fontes suportadas:
- Arquivos em lote CSV (separados por ';' com cabeçalho oficial da Câmara):
  https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip
- Respostas JSON da API Dados Abertos v2:
  https://dadosabertos.camara.leg.br/api/v2/deputados/{id}/despesas
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


def parse_camara_ceap_csv_batch(
    raw_csv_bytes: bytes,
    *,
    source_url: str,
    collected_at_utc: str | None = None,
    reported_control_total: Decimal | None = None,
) -> IngestionBatchResult[CuratedPublicExpense]:
    """Faz o parsing e validação de um lote CSV oficial da CEAP (Câmara dos Deputados)."""
    batch_sha256, timestamp = build_batch_context(raw_csv_bytes, collected_at_utc)
    result: IngestionBatchResult[CuratedPublicExpense] = IngestionBatchResult(
        source=OfficialSource.CAMARA_CEAP,
        source_url=source_url,
        raw_batch_sha256=batch_sha256,
        collected_at_utc=timestamp,
        reported_control_total=reported_control_total,
    )

    text_content = raw_csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text_content), delimiter=";")

    for idx, row in enumerate(reader, start=1):
        rec_id = str(row.get("ideDocumento") or row.get("codDocumento") or "").strip()
        fallback_rec_id = rec_id or f"ROW-{idx}"
        try:
            if not rec_id:
                raise ValueError("Campo identificador 'ideDocumento'/'codDocumento' ausente na CEAP.")

            raw_date_str = str(row.get("datEmissao") or row.get("dataEmissao") or "").strip()
            if not raw_date_str:
                raise ValueError("Data de emissão ('datEmissao') ausente.")
            issue_dt = date.fromisoformat(raw_date_str[:10])

            provenance = ProvenanceMetadata(
                source=OfficialSource.CAMARA_CEAP,
                source_url=source_url,
                source_record_id=rec_id,
                collected_at_utc=timestamp,
                raw_batch_sha256=batch_sha256,
            )

            expense = CuratedPublicExpense.create_validated(
                competence_year=int(str(row.get("numAno") or row.get("ano") or 0).strip()),
                competence_month=int(str(row.get("numMes") or row.get("mes") or 0).strip()),
                issue_date=issue_dt,
                sphere="FEDERAL_LEGISLATIVO",
                organ_code="CAMARA_DEPUTADOS",
                organ_name="Câmara dos Deputados",
                public_agent_id=str(row.get("ideCadastro") or row.get("idDeputado") or "").strip(),
                public_agent_name=str(row.get("txNomeParlamentar") or row.get("nomeParlamentar") or "").strip(),
                party_sigla=str(row.get("sgPartido") or row.get("siglaPartido") or "").strip(),
                state_uf=str(row.get("sgUF") or row.get("siglaUf") or "").strip(),
                expense_category=str(row.get("txtDescricao") or row.get("tipoDespesa") or "").strip(),
                supplier_raw_doc=str(row.get("txtCNPJCPF") or row.get("cnpjCpfFornecedor") or "").strip(),
                supplier_name=str(row.get("txtFornecedor") or row.get("nomeFornecedor") or "").strip(),
                document_number=str(row.get("txtNumero") or row.get("numDocumento") or "").strip(),
                gross_amount_raw=row.get("vlrDocumento") or row.get("valorDocumento"),
                net_amount_raw=row.get("vlrLiquido") or row.get("valorLiquido"),
                document_evidence_url=(
                    str(row.get("urlDocumento") or "").strip() or None
                ),
                provenance=provenance,
            )
            result.valid_records.append(expense)
        except Exception as exc:
            q_id = compute_sha256_text(f"{batch_sha256}|{fallback_rec_id}|{idx}")
            result.quarantined_records.append(
                QuarantinedRecord(
                    quarantine_id=q_id,
                    source=OfficialSource.CAMARA_CEAP,
                    source_record_id=fallback_rec_id,
                    raw_batch_sha256=batch_sha256,
                    rejection_reason=str(exc),
                    raw_payload_json=json.dumps(row, ensure_ascii=False),
                    quarantined_at_utc=timestamp,
                )
            )

    return result
