"""Camada de armazenamento Lakehouse local e reconciliação (Raw, Quarantine e Curated).

Implementa os requisitos da Seção 8:
- Preservação do payload bruto na camada Raw com verificação de hash SHA-256.
- Persistência transacional idempotente (INSERT OR IGNORE / UPSERT controlado por natural_key).
- Isolamento de registros inválidos na tabela `quarantine_records`.
- Reconciliação automática de contagens e somatórios financeiros.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from deolhonobrasil.governance.dossiers import (
    AccessRole,
    AuditDossier,
    DossierStatus,
)
from deolhonobrasil.governance.right_of_reply import (
    RightOfReplyStatus,
    RightOfReplySubmission,
)
from deolhonobrasil.pipeline.connectors.base import IngestionBatchResult
from deolhonobrasil.pipeline.models import (
    CuratedParliamentaryAmendment,
    CuratedPublicContract,
    CuratedPublicExpense,
    CuratedSanctionRecord,
    OfficialSource,
)
from deolhonobrasil.pipeline.privacy import compute_sha256_bytes


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    """Relatório de reconciliação contábil e de qualidade de um lote ingerido."""

    source: OfficialSource
    raw_batch_sha256: str
    valid_records_count: int
    inserted_new_count: int
    deduplicated_skipped_count: int
    quarantined_count: int
    computed_net_total: Decimal
    reported_control_total: Decimal | None
    discrepancy_amount: Decimal
    is_reconciled: bool


class CivicLakehouseStorage:
    """Gerenciador das camadas Raw, Quarantine e Curated com idempotência e proveniência."""

    def __init__(self, data_dir: Path, sqlite_path: Path | None = None) -> None:
        self.data_dir = data_dir
        self.raw_dir = data_dir / "raw"
        self.quarantine_dir = data_dir / "quarantine"
        self.curated_dir = data_dir / "curated"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.curated_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = sqlite_path or (self.curated_dir / "donb_lakehouse.sqlite")
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS raw_batch_manifests (
                    raw_batch_sha256 TEXT PRIMARY KEY CHECK(length(raw_batch_sha256) = 64),
                    source TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    collected_at_utc TEXT NOT NULL,
                    raw_file_path TEXT NOT NULL,
                    byte_size INTEGER NOT NULL CHECK(byte_size > 0),
                    valid_count INTEGER NOT NULL DEFAULT 0,
                    quarantined_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS quarantine_records (
                    quarantine_id TEXT PRIMARY KEY CHECK(length(quarantine_id) = 64),
                    source TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    raw_batch_sha256 TEXT NOT NULL,
                    rejection_reason TEXT NOT NULL,
                    raw_payload_json TEXT NOT NULL,
                    quarantined_at_utc TEXT NOT NULL,
                    FOREIGN KEY (raw_batch_sha256) REFERENCES raw_batch_manifests(raw_batch_sha256)
                );

                CREATE TABLE IF NOT EXISTS curated_expenses (
                    natural_key TEXT PRIMARY KEY CHECK(length(natural_key) = 64),
                    competence_year INTEGER NOT NULL,
                    competence_month INTEGER NOT NULL,
                    issue_date TEXT NOT NULL,
                    sphere TEXT NOT NULL,
                    organ_code TEXT NOT NULL,
                    organ_name TEXT NOT NULL,
                    public_agent_id TEXT NOT NULL,
                    public_agent_name TEXT NOT NULL,
                    party_sigla TEXT NOT NULL,
                    state_uf TEXT NOT NULL,
                    expense_category TEXT NOT NULL,
                    supplier_doc_normalized TEXT NOT NULL,
                    supplier_doc_type TEXT NOT NULL,
                    supplier_name TEXT NOT NULL,
                    document_number TEXT NOT NULL,
                    gross_amount_cents INTEGER NOT NULL,
                    net_amount_cents INTEGER NOT NULL CHECK(net_amount_cents > 0),
                    document_evidence_url TEXT,
                    epistemic_status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    collected_at_utc TEXT NOT NULL,
                    raw_batch_sha256 TEXT NOT NULL,
                    FOREIGN KEY (raw_batch_sha256) REFERENCES raw_batch_manifests(raw_batch_sha256)
                );

                CREATE TABLE IF NOT EXISTS curated_contracts (
                    natural_key TEXT PRIMARY KEY CHECK(length(natural_key) = 64),
                    pncp_control_number TEXT NOT NULL,
                    organ_cnpj TEXT NOT NULL,
                    organ_name TEXT NOT NULL,
                    supplier_doc_normalized TEXT NOT NULL,
                    supplier_doc_type TEXT NOT NULL,
                    supplier_name TEXT NOT NULL,
                    modality_name TEXT NOT NULL,
                    contract_object TEXT NOT NULL,
                    signature_date TEXT NOT NULL,
                    initial_amount_cents INTEGER NOT NULL CHECK(initial_amount_cents > 0),
                    current_amount_cents INTEGER NOT NULL CHECK(current_amount_cents > 0),
                    addendum_count INTEGER NOT NULL CHECK(addendum_count >= 0),
                    source TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    collected_at_utc TEXT NOT NULL,
                    raw_batch_sha256 TEXT NOT NULL,
                    FOREIGN KEY (raw_batch_sha256) REFERENCES raw_batch_manifests(raw_batch_sha256)
                );

                CREATE TABLE IF NOT EXISTS curated_amendments (
                    natural_key TEXT PRIMARY KEY CHECK(length(natural_key) = 64),
                    amendment_code TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    author_id TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    amendment_type TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    municipality_ibge_code TEXT NOT NULL,
                    state_uf TEXT NOT NULL,
                    beneficiary_doc_normalized TEXT NOT NULL,
                    beneficiary_name TEXT NOT NULL,
                    committed_amount_cents INTEGER NOT NULL CHECK(committed_amount_cents >= 0),
                    paid_amount_cents INTEGER NOT NULL CHECK(paid_amount_cents >= 0),
                    source TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    collected_at_utc TEXT NOT NULL,
                    raw_batch_sha256 TEXT NOT NULL,
                    FOREIGN KEY (raw_batch_sha256) REFERENCES raw_batch_manifests(raw_batch_sha256)
                );

                CREATE TABLE IF NOT EXISTS curated_sanctions (
                    natural_key TEXT PRIMARY KEY CHECK(length(natural_key) = 64),
                    sanction_code TEXT NOT NULL,
                    sanctioned_doc_normalized TEXT NOT NULL,
                    sanctioned_doc_type TEXT NOT NULL,
                    sanctioned_name TEXT NOT NULL,
                    sanction_type TEXT NOT NULL,
                    sanctioning_organ TEXT NOT NULL,
                    state_uf TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT,
                    source TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    collected_at_utc TEXT NOT NULL,
                    raw_batch_sha256 TEXT NOT NULL,
                    FOREIGN KEY (raw_batch_sha256) REFERENCES raw_batch_manifests(raw_batch_sha256)
                );

                CREATE TABLE IF NOT EXISTS audit_dossiers (
                    dossier_id TEXT PRIMARY KEY,
                    signal_id TEXT NOT NULL,
                    rule_code TEXT NOT NULL,
                    title TEXT NOT NULL,
                    official_data_block TEXT NOT NULL,
                    statistical_inference_block TEXT NOT NULL,
                    audit_hypothesis_and_limits_block TEXT NOT NULL,
                    epistemic_layer TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value TEXT NOT NULL,
                    threshold_value TEXT NOT NULL,
                    audited_amount TEXT NOT NULL,
                    provenance_hashes TEXT NOT NULL,
                    laya_engine_id TEXT NOT NULL,
                    laya_score TEXT NOT NULL,
                    laya_choice TEXT NOT NULL,
                    laya_noul TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('EM_TRIAGEM_INTERNA', 'PUBLICADO_COM_REVISAO', 'ESCLARECIDO_COM_PROVA', 'ERRO_MATERIAL_RETIFICADO')),
                    reviewer_id TEXT,
                    correction_note TEXT,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    CONSTRAINT chk_published_requires_reviewer CHECK (
                        status NOT IN ('PUBLICADO_COM_REVISAO', 'ESCLARECIDO_COM_PROVA', 'ERRO_MATERIAL_RETIFICADO')
                        OR (reviewer_id IS NOT NULL AND trim(reviewer_id) <> '')
                    )
                );

                CREATE INDEX IF NOT EXISTS idx_audit_dossiers_status_reviewer
                    ON audit_dossiers (status, reviewer_id);

                CREATE INDEX IF NOT EXISTS idx_audit_dossiers_rule_code
                    ON audit_dossiers (rule_code);

                CREATE TABLE IF NOT EXISTS right_of_reply_protocols (
                    protocol_id TEXT PRIMARY KEY,
                    dossier_id TEXT NOT NULL REFERENCES audit_dossiers(dossier_id) ON DELETE RESTRICT,
                    respondent_name TEXT NOT NULL,
                    respondent_document_masked_or_cnpj TEXT NOT NULL,
                    institutional_email_domain TEXT NOT NULL,
                    statement_text TEXT NOT NULL,
                    attachment_sha256 TEXT NOT NULL CHECK(length(attachment_sha256) = 64),
                    status TEXT NOT NULL CHECK(status IN ('RECEBIDO_EM_VALIDACAO', 'PUBLICADO_LADO_A_LADO', 'SOLICITADO_COMPLEMENTO')),
                    equal_visual_prominence INTEGER NOT NULL CHECK(equal_visual_prominence IN (0, 1)) DEFAULT 1,
                    submitted_at_utc TEXT NOT NULL,
                    reviewed_at_utc TEXT,
                    reviewer_id TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_right_of_reply_dossier
                    ON right_of_reply_protocols (dossier_id, status);

                CREATE TABLE IF NOT EXISTS editorial_audit_trail (
                    event_id TEXT PRIMARY KEY,
                    dossier_id TEXT NOT NULL REFERENCES audit_dossiers(dossier_id) ON DELETE RESTRICT,
                    action TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    rationale TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    occurred_at_utc TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_editorial_audit_trail_dossier
                    ON editorial_audit_trail (dossier_id, occurred_at_utc DESC);

                CREATE TRIGGER IF NOT EXISTS trg_prevent_update_editorial_audit_trail
                BEFORE UPDATE ON editorial_audit_trail
                BEGIN
                    SELECT RAISE(ABORT, 'Tabela editorial_audit_trail é estritamente imutável (atualizações proibidas).');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_prevent_delete_editorial_audit_trail
                BEFORE DELETE ON editorial_audit_trail
                BEGIN
                    SELECT RAISE(ABORT, 'Tabela editorial_audit_trail é estritamente imutável (exclusões proibidas).');
                END;
                """
            )

    def archive_raw_payload(
        self,
        *,
        source: OfficialSource,
        source_url: str,
        raw_bytes: bytes,
        collected_at_utc: str,
        extension: str = "dat",
    ) -> Path:
        """Salva de forma imutável os bytes brutos na camada Raw e verifica o SHA-256."""
        sha256_hex = compute_sha256_bytes(raw_bytes)
        source_folder = self.raw_dir / source.value.lower()
        source_folder.mkdir(parents=True, exist_ok=True)
        target_path = source_folder / f"{sha256_hex}.{extension}"

        if not target_path.exists():
            target_path.write_bytes(raw_bytes)
        else:
            existing_hash = compute_sha256_bytes(target_path.read_bytes())
            if existing_hash != sha256_hex:
                raise RuntimeError(
                    f"Corrupção de integridade detectada no arquivo Raw '{target_path}'!"
                )
        return target_path

    def persist_expense_batch(
        self,
        raw_bytes: bytes,
        batch: IngestionBatchResult[CuratedPublicExpense],
        extension: str = "csv",
    ) -> ReconciliationReport:
        """Persiste um lote de despesas com idempotência total e reconciliação financeira."""
        raw_path = self.archive_raw_payload(
            source=batch.source,
            source_url=batch.source_url,
            raw_bytes=raw_bytes,
            collected_at_utc=batch.collected_at_utc,
            extension=extension,
        )

        inserted_new = 0
        deduplicated = 0
        computed_total = Decimal("0.00")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO raw_batch_manifests (
                    raw_batch_sha256, source, source_url, collected_at_utc,
                    raw_file_path, byte_size, valid_count, quarantined_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch.raw_batch_sha256,
                    batch.source.value,
                    batch.source_url,
                    batch.collected_at_utc,
                    str(raw_path),
                    len(raw_bytes),
                    len(batch.valid_records),
                    len(batch.quarantined_records),
                ),
            )

            for q in batch.quarantined_records:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO quarantine_records (
                        quarantine_id, source, source_record_id, raw_batch_sha256,
                        rejection_reason, raw_payload_json, quarantined_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        q.quarantine_id,
                        q.source.value,
                        q.source_record_id,
                        q.raw_batch_sha256,
                        q.rejection_reason,
                        q.raw_payload_json,
                        q.quarantined_at_utc,
                    ),
                )

            for exp in batch.valid_records:
                computed_total += exp.net_amount
                gross_cents = int((exp.gross_amount * 100).to_integral_value())
                net_cents = int((exp.net_amount * 100).to_integral_value())

                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO curated_expenses (
                        natural_key, competence_year, competence_month, issue_date,
                        sphere, organ_code, organ_name, public_agent_id, public_agent_name,
                        party_sigla, state_uf, expense_category, supplier_doc_normalized,
                        supplier_doc_type, supplier_name, document_number,
                        gross_amount_cents, net_amount_cents, document_evidence_url,
                        epistemic_status, source, source_url, source_record_id,
                        collected_at_utc, raw_batch_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        exp.natural_key,
                        exp.competence_year,
                        exp.competence_month,
                        exp.issue_date.isoformat(),
                        exp.sphere,
                        exp.organ_code,
                        exp.organ_name,
                        exp.public_agent_id,
                        exp.public_agent_name,
                        exp.party_sigla,
                        exp.state_uf,
                        exp.expense_category,
                        exp.supplier_doc_normalized,
                        exp.supplier_doc_type,
                        exp.supplier_name,
                        exp.document_number,
                        gross_cents,
                        net_cents,
                        exp.document_evidence_url,
                        exp.epistemic_status.value,
                        exp.provenance.source.value,
                        exp.provenance.source_url,
                        exp.provenance.source_record_id,
                        exp.provenance.collected_at_utc,
                        exp.provenance.raw_batch_sha256,
                    ),
                )
                if cursor.rowcount == 1:
                    inserted_new += 1
                else:
                    deduplicated += 1

        discrepancy = Decimal("0.00")
        is_reconciled = True
        if batch.reported_control_total is not None:
            discrepancy = abs(computed_total - batch.reported_control_total)
            is_reconciled = discrepancy <= Decimal("0.01")

        return ReconciliationReport(
            source=batch.source,
            raw_batch_sha256=batch.raw_batch_sha256,
            valid_records_count=len(batch.valid_records),
            inserted_new_count=inserted_new,
            deduplicated_skipped_count=deduplicated,
            quarantined_count=len(batch.quarantined_records),
            computed_net_total=computed_total,
            reported_control_total=batch.reported_control_total,
            discrepancy_amount=discrepancy,
            is_reconciled=is_reconciled,
        )

    def persist_contract_batch(
        self,
        raw_bytes: bytes,
        batch: IngestionBatchResult[CuratedPublicContract],
    ) -> ReconciliationReport:
        """Persiste um lote de contratos federais (PNCP) com idempotência e reconciliação."""
        raw_path = self.archive_raw_payload(
            source=batch.source,
            source_url=batch.source_url,
            raw_bytes=raw_bytes,
            collected_at_utc=batch.collected_at_utc,
            extension="json",
        )

        inserted_new = 0
        deduplicated = 0
        computed_total = Decimal("0.00")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO raw_batch_manifests (
                    raw_batch_sha256, source, source_url, collected_at_utc,
                    raw_file_path, byte_size, valid_count, quarantined_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch.raw_batch_sha256,
                    batch.source.value,
                    batch.source_url,
                    batch.collected_at_utc,
                    str(raw_path),
                    len(raw_bytes),
                    len(batch.valid_records),
                    len(batch.quarantined_records),
                ),
            )

            for q in batch.quarantined_records:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO quarantine_records (
                        quarantine_id, source, source_record_id, raw_batch_sha256,
                        rejection_reason, raw_payload_json, quarantined_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        q.quarantine_id,
                        q.source.value,
                        q.source_record_id,
                        q.raw_batch_sha256,
                        q.rejection_reason,
                        q.raw_payload_json,
                        q.quarantined_at_utc,
                    ),
                )

            for c in batch.valid_records:
                computed_total += c.current_amount
                init_cents = int((c.initial_amount * 100).to_integral_value())
                curr_cents = int((c.current_amount * 100).to_integral_value())

                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO curated_contracts (
                        natural_key, pncp_control_number, organ_cnpj, organ_name,
                        supplier_doc_normalized, supplier_doc_type, supplier_name,
                        modality_name, contract_object, signature_date,
                        initial_amount_cents, current_amount_cents, addendum_count,
                        source, source_url, source_record_id, collected_at_utc, raw_batch_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        c.natural_key,
                        c.pncp_control_number,
                        c.organ_cnpj,
                        c.organ_name,
                        c.supplier_doc_normalized,
                        c.supplier_doc_type,
                        c.supplier_name,
                        c.modality_name,
                        c.contract_object,
                        c.signature_date.isoformat(),
                        init_cents,
                        curr_cents,
                        c.addendum_count,
                        c.provenance.source.value,
                        c.provenance.source_url,
                        c.provenance.source_record_id,
                        c.provenance.collected_at_utc,
                        c.provenance.raw_batch_sha256,
                    ),
                )
                if cursor.rowcount == 1:
                    inserted_new += 1
                else:
                    deduplicated += 1

        discrepancy = Decimal("0.00")
        is_reconciled = True
        if batch.reported_control_total is not None:
            discrepancy = abs(computed_total - batch.reported_control_total)
            is_reconciled = discrepancy <= Decimal("0.01")

        return ReconciliationReport(
            source=batch.source,
            raw_batch_sha256=batch.raw_batch_sha256,
            valid_records_count=len(batch.valid_records),
            inserted_new_count=inserted_new,
            deduplicated_skipped_count=deduplicated,
            quarantined_count=len(batch.quarantined_records),
            computed_net_total=computed_total,
            reported_control_total=batch.reported_control_total,
            discrepancy_amount=discrepancy,
            is_reconciled=is_reconciled,
        )

    def persist_amendment_batch(
        self,
        raw_bytes: bytes,
        batch: IngestionBatchResult[CuratedParliamentaryAmendment],
    ) -> ReconciliationReport:
        """Persiste um lote de emendas parlamentares (CGU) com idempotência e reconciliação."""
        raw_path = self.archive_raw_payload(
            source=batch.source,
            source_url=batch.source_url,
            raw_bytes=raw_bytes,
            collected_at_utc=batch.collected_at_utc,
            extension="json",
        )

        inserted_new = 0
        deduplicated = 0
        computed_total = Decimal("0.00")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO raw_batch_manifests (
                    raw_batch_sha256, source, source_url, collected_at_utc,
                    raw_file_path, byte_size, valid_count, quarantined_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch.raw_batch_sha256,
                    batch.source.value,
                    batch.source_url,
                    batch.collected_at_utc,
                    str(raw_path),
                    len(raw_bytes),
                    len(batch.valid_records),
                    len(batch.quarantined_records),
                ),
            )

            for q in batch.quarantined_records:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO quarantine_records (
                        quarantine_id, source, source_record_id, raw_batch_sha256,
                        rejection_reason, raw_payload_json, quarantined_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        q.quarantine_id,
                        q.source.value,
                        q.source_record_id,
                        q.raw_batch_sha256,
                        q.rejection_reason,
                        q.raw_payload_json,
                        q.quarantined_at_utc,
                    ),
                )

            for amd in batch.valid_records:
                computed_total += amd.paid_amount
                comm_cents = int((amd.committed_amount * 100).to_integral_value())
                paid_cents = int((amd.paid_amount * 100).to_integral_value())

                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO curated_amendments (
                        natural_key, amendment_code, year, author_id, author_name,
                        amendment_type, function_name, municipality_ibge_code, state_uf,
                        beneficiary_doc_normalized, beneficiary_name,
                        committed_amount_cents, paid_amount_cents,
                        source, source_url, source_record_id, collected_at_utc, raw_batch_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        amd.natural_key,
                        amd.amendment_code,
                        amd.year,
                        amd.author_id,
                        amd.author_name,
                        amd.amendment_type,
                        amd.function_name,
                        amd.municipality_ibge_code,
                        amd.state_uf,
                        amd.beneficiary_doc_normalized,
                        amd.beneficiary_name,
                        comm_cents,
                        paid_cents,
                        amd.provenance.source.value,
                        amd.provenance.source_url,
                        amd.provenance.source_record_id,
                        amd.provenance.collected_at_utc,
                        amd.provenance.raw_batch_sha256,
                    ),
                )
                if cursor.rowcount == 1:
                    inserted_new += 1
                else:
                    deduplicated += 1

        discrepancy = Decimal("0.00")
        is_reconciled = True
        if batch.reported_control_total is not None:
            discrepancy = abs(computed_total - batch.reported_control_total)
            is_reconciled = discrepancy <= Decimal("0.01")

        return ReconciliationReport(
            source=batch.source,
            raw_batch_sha256=batch.raw_batch_sha256,
            valid_records_count=len(batch.valid_records),
            inserted_new_count=inserted_new,
            deduplicated_skipped_count=deduplicated,
            quarantined_count=len(batch.quarantined_records),
            computed_net_total=computed_total,
            reported_control_total=batch.reported_control_total,
            discrepancy_amount=discrepancy,
            is_reconciled=is_reconciled,
        )

    def persist_sanction_batch(
        self,
        raw_bytes: bytes,
        batch: IngestionBatchResult[CuratedSanctionRecord],
    ) -> ReconciliationReport:
        """Persiste lote de sanções administrativas (CEIS/CNEP) com idempotência e quarentena (`SPEC-0007`)."""
        raw_path = self.archive_raw_payload(
            source=batch.source,
            source_url=batch.source_url,
            raw_bytes=raw_bytes,
            collected_at_utc=batch.collected_at_utc,
            extension="json",
        )
        inserted_new = 0
        deduplicated = 0

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO raw_batch_manifests (
                    raw_batch_sha256, source, source_url, collected_at_utc,
                    raw_file_path, byte_size, valid_count, quarantined_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch.raw_batch_sha256,
                    batch.source.value,
                    batch.source_url,
                    batch.collected_at_utc,
                    str(raw_path),
                    len(raw_bytes),
                    len(batch.valid_records),
                    len(batch.quarantined_records),
                ),
            )
            for q in batch.quarantined_records:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO quarantine_records (
                        quarantine_id, source, source_record_id, raw_batch_sha256,
                        rejection_reason, raw_payload_json, quarantined_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        q.quarantine_id,
                        q.source.value,
                        q.source_record_id,
                        q.raw_batch_sha256,
                        q.rejection_reason,
                        q.raw_payload_json,
                        q.quarantined_at_utc,
                    ),
                )

            for sanc in batch.valid_records:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO curated_sanctions (
                        natural_key, sanction_code, sanctioned_doc_normalized,
                        sanctioned_doc_type, sanctioned_name, sanction_type,
                        sanctioning_organ, state_uf, start_date, end_date,
                        source, source_url, source_record_id, collected_at_utc, raw_batch_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sanc.natural_key,
                        sanc.sanction_code,
                        sanc.sanctioned_doc_normalized,
                        sanc.sanctioned_doc_type,
                        sanc.sanctioned_name,
                        sanc.sanction_type,
                        sanc.sanctioning_organ,
                        sanc.state_uf,
                        sanc.start_date.isoformat(),
                        sanc.end_date.isoformat() if sanc.end_date else None,
                        sanc.provenance.source.value,
                        sanc.provenance.source_url,
                        sanc.provenance.source_record_id,
                        sanc.provenance.collected_at_utc,
                        sanc.provenance.raw_batch_sha256,
                    ),
                )
                if cursor.rowcount == 1:
                    inserted_new += 1
                else:
                    deduplicated += 1

        return ReconciliationReport(
            source=batch.source,
            raw_batch_sha256=batch.raw_batch_sha256,
            valid_records_count=len(batch.valid_records),
            inserted_new_count=inserted_new,
            deduplicated_skipped_count=deduplicated,
            quarantined_count=len(batch.quarantined_records),
            computed_net_total=Decimal(len(batch.valid_records)).quantize(Decimal("0.01")),
            reported_control_total=None,
            discrepancy_amount=Decimal("0.00"),
            is_reconciled=True,
        )

    def get_summary_metrics(self) -> dict[str, object]:
        """Retorna métricas consolidadas das camadas Raw, Quarantine e Curated."""
        with self._connect() as conn:
            manifests = conn.execute("SELECT COUNT(*) FROM raw_batch_manifests").fetchone()[0]
            quarantined = conn.execute("SELECT COUNT(*) FROM quarantine_records").fetchone()[0]
            expenses = conn.execute("SELECT COUNT(*), COALESCE(SUM(net_amount_cents), 0) FROM curated_expenses").fetchone()
            contracts = conn.execute("SELECT COUNT(*), COALESCE(SUM(current_amount_cents), 0) FROM curated_contracts").fetchone()
            amendments = conn.execute("SELECT COUNT(*), COALESCE(SUM(paid_amount_cents), 0) FROM curated_amendments").fetchone()
            dossiers_count = conn.execute("SELECT COUNT(*) FROM audit_dossiers").fetchone()[0]

        return {
            "raw_batches_count": manifests,
            "quarantined_records_count": quarantined,
            "curated_expenses_count": expenses[0],
            "curated_expenses_net_total_brl": str(
                (Decimal(expenses[1]) / Decimal(100)).quantize(Decimal("0.01"))
            ),
            "curated_contracts_count": contracts[0],
            "curated_contracts_current_total_brl": str(
                (Decimal(contracts[1]) / Decimal(100)).quantize(Decimal("0.01"))
            ),
            "curated_amendments_count": amendments[0],
            "curated_amendments_paid_total_brl": str(
                (Decimal(amendments[1]) / Decimal(100)).quantize(Decimal("0.01"))
            ),
            "audit_dossiers_count": dossiers_count,
        }

    def upsert_dossier(self, dossier: AuditDossier, actor_id: str = "system_pipeline") -> None:
        """Persiste ou atualiza um dossiê de auditoria, manifestação e registra a trilha editorial."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT status, created_at_utc FROM audit_dossiers WHERE dossier_id = ?",
                (dossier.dossier_id,),
            )
            existing_row = cursor.fetchone()

            if existing_row is None:
                previous_status = None
                created_at_utc = dossier.updated_at_utc
                action = (
                    "SUBMIT_FOR_TRIAGE"
                    if dossier.status == DossierStatus.EM_TRIAGEM_INTERNA
                    else "CREATE_DOSSIER"
                )
                conn.execute(
                    """
                    INSERT INTO audit_dossiers (
                        dossier_id, signal_id, rule_code, title,
                        official_data_block, statistical_inference_block,
                        audit_hypothesis_and_limits_block, epistemic_layer,
                        metric_name, metric_value, threshold_value, audited_amount,
                        provenance_hashes, laya_engine_id, laya_score, laya_choice,
                        laya_noul, status, reviewer_id, correction_note,
                        created_at_utc, updated_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dossier.dossier_id,
                        dossier.signal.signal_id,
                        dossier.signal.rule_code,
                        dossier.signal.title,
                        dossier.grounded_sections.official_data_block,
                        dossier.grounded_sections.statistical_inference_block,
                        dossier.grounded_sections.audit_hypothesis_and_limits_block,
                        dossier.signal.epistemic_layer.value,
                        dossier.signal.metric_name,
                        str(dossier.signal.metric_value),
                        str(dossier.signal.threshold_value),
                        str(dossier.signal.audited_amount),
                        json.dumps(list(dossier.signal.provenance_hashes)),
                        dossier.laya_decision.engine_id,
                        str(dossier.laya_decision.score),
                        dossier.laya_decision.choice.value,
                        dossier.laya_decision.noul_classification,
                        dossier.status.value,
                        dossier.reviewer_id,
                        dossier.correction_note,
                        created_at_utc,
                        dossier.updated_at_utc,
                    ),
                )
            else:
                previous_status = existing_row["status"]
                created_at_utc = existing_row["created_at_utc"]
                if dossier.status == DossierStatus.ERRO_MATERIAL_RETIFICADO:
                    action = "RECTIFY_MATERIAL_ERROR"
                elif dossier.right_of_reply is not None and dossier.status == DossierStatus.ESCLARECIDO_COM_PROVA:
                    action = "ATTACH_RIGHT_OF_REPLY_AND_CLARIFY"
                elif dossier.right_of_reply is not None:
                    action = "ATTACH_RIGHT_OF_REPLY"
                elif previous_status != dossier.status.value:
                    action = f"TRANSITION_TO_{dossier.status.value}"
                else:
                    action = "UPDATE_DOSSIER"

                conn.execute(
                    """
                    UPDATE audit_dossiers SET
                        signal_id = ?,
                        rule_code = ?,
                        title = ?,
                        official_data_block = ?,
                        statistical_inference_block = ?,
                        audit_hypothesis_and_limits_block = ?,
                        epistemic_layer = ?,
                        metric_name = ?,
                        metric_value = ?,
                        threshold_value = ?,
                        audited_amount = ?,
                        provenance_hashes = ?,
                        laya_engine_id = ?,
                        laya_score = ?,
                        laya_choice = ?,
                        laya_noul = ?,
                        status = ?,
                        reviewer_id = ?,
                        correction_note = ?,
                        updated_at_utc = ?
                    WHERE dossier_id = ?
                    """,
                    (
                        dossier.signal.signal_id,
                        dossier.signal.rule_code,
                        dossier.signal.title,
                        dossier.grounded_sections.official_data_block,
                        dossier.grounded_sections.statistical_inference_block,
                        dossier.grounded_sections.audit_hypothesis_and_limits_block,
                        dossier.signal.epistemic_layer.value,
                        dossier.signal.metric_name,
                        str(dossier.signal.metric_value),
                        str(dossier.signal.threshold_value),
                        str(dossier.signal.audited_amount),
                        json.dumps(list(dossier.signal.provenance_hashes)),
                        dossier.laya_decision.engine_id,
                        str(dossier.laya_decision.score),
                        dossier.laya_decision.choice.value,
                        dossier.laya_decision.noul_classification,
                        dossier.status.value,
                        dossier.reviewer_id,
                        dossier.correction_note,
                        dossier.updated_at_utc,
                        dossier.dossier_id,
                    ),
                )

            # Persistir Direito de Resposta se houver
            if dossier.right_of_reply is not None:
                reply = dossier.right_of_reply
                conn.execute(
                    """
                    INSERT INTO right_of_reply_protocols (
                        protocol_id, dossier_id, respondent_name,
                        respondent_document_masked_or_cnpj, institutional_email_domain,
                        statement_text, attachment_sha256, status, equal_visual_prominence,
                        submitted_at_utc, reviewed_at_utc, reviewer_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(protocol_id) DO UPDATE SET
                        respondent_name = excluded.respondent_name,
                        respondent_document_masked_or_cnpj = excluded.respondent_document_masked_or_cnpj,
                        institutional_email_domain = excluded.institutional_email_domain,
                        statement_text = excluded.statement_text,
                        attachment_sha256 = excluded.attachment_sha256,
                        status = excluded.status,
                        equal_visual_prominence = excluded.equal_visual_prominence,
                        reviewed_at_utc = excluded.reviewed_at_utc,
                        reviewer_id = excluded.reviewer_id
                    """,
                    (
                        reply.protocol_id,
                        reply.dossier_id,
                        reply.respondent_name,
                        reply.respondent_document_masked_or_cnpj,
                        reply.institutional_email_domain,
                        reply.statement_text,
                        reply.attachment_sha256,
                        reply.status.value,
                        1 if reply.equal_visual_prominence else 0,
                        reply.submitted_at_utc,
                        dossier.updated_at_utc if dossier.reviewer_id else None,
                        dossier.reviewer_id,
                    ),
                )

            # Registrar trilha imutável em editorial_audit_trail
            actor_role = (
                "system"
                if actor_id == "system_pipeline"
                else AccessRole.REVIEWER_ADMIN.value
            )
            rationale = (
                dossier.correction_note
                if dossier.correction_note
                else dossier.laya_decision.rationale_pt_br
            )
            metadata = {
                "rule_code": dossier.signal.rule_code,
                "metric_name": dossier.signal.metric_name,
                "metric_value": str(dossier.signal.metric_value),
                "score": str(dossier.laya_decision.score),
                "has_right_of_reply": dossier.right_of_reply is not None,
            }
            event_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO editorial_audit_trail (
                    event_id, dossier_id, action, previous_status, new_status,
                    actor_id, actor_role, rationale, metadata_json, occurred_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    dossier.dossier_id,
                    action,
                    previous_status,
                    dossier.status.value,
                    actor_id,
                    actor_role,
                    rationale,
                    json.dumps(metadata, ensure_ascii=False),
                    dossier.updated_at_utc,
                ),
            )

    def list_dossiers_for_role(self, role: AccessRole) -> list[dict[str, object]]:
        """Lista dossiês respeitando estritamente o papel de acesso e as regras RLS."""
        with self._connect() as conn:
            if role == AccessRole.PUBLIC_READER:
                cursor = conn.execute(
                    """
                    SELECT * FROM audit_dossiers
                    WHERE status IN ('PUBLICADO_COM_REVISAO', 'ESCLARECIDO_COM_PROVA', 'ERRO_MATERIAL_RETIFICADO')
                      AND reviewer_id IS NOT NULL
                      AND trim(reviewer_id) <> ''
                    ORDER BY updated_at_utc DESC
                    """
                )
            elif role == AccessRole.REVIEWER_ADMIN:
                cursor = conn.execute(
                    """
                    SELECT * FROM audit_dossiers
                    ORDER BY updated_at_utc DESC
                    """
                )
            else:
                return []

            results: list[dict[str, object]] = []
            for row in cursor.fetchall():
                item = dict(row)
                if isinstance(item.get("provenance_hashes"), str):
                    try:
                        item["provenance_hashes"] = json.loads(item["provenance_hashes"])
                    except Exception:
                        pass
                reply_row = conn.execute(
                    """
                    SELECT * FROM right_of_reply_protocols
                    WHERE dossier_id = ?
                    ORDER BY submitted_at_utc DESC LIMIT 1
                    """,
                    (item["dossier_id"],),
                ).fetchone()
                item["right_of_reply"] = dict(reply_row) if reply_row else None
                results.append(item)
            return results

    def get_dossier(self, dossier_id: str) -> dict[str, object] | None:
        """Obtém um dossiê específico com sua manifestação associada, se houver."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM audit_dossiers WHERE dossier_id = ?",
                (dossier_id,),
            ).fetchone()
            if not row:
                return None
            res = dict(row)
            if isinstance(res.get("provenance_hashes"), str):
                try:
                    res["provenance_hashes"] = json.loads(res["provenance_hashes"])
                except Exception:
                    pass
            reply_row = conn.execute(
                """
                SELECT * FROM right_of_reply_protocols
                WHERE dossier_id = ?
                ORDER BY submitted_at_utc DESC LIMIT 1
                """,
                (dossier_id,),
            ).fetchone()
            res["right_of_reply"] = dict(reply_row) if reply_row else None
            return res

    def get_editorial_audit_trail(self, dossier_id: str | None = None) -> list[dict[str, object]]:
        """Retorna os eventos da trilha de auditoria editorial para um dossiê ou geral."""
        with self._connect() as conn:
            if dossier_id:
                cursor = conn.execute(
                    "SELECT * FROM editorial_audit_trail WHERE dossier_id = ? ORDER BY occurred_at_utc ASC",
                    (dossier_id,),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM editorial_audit_trail ORDER BY occurred_at_utc ASC"
                )
            return [dict(r) for r in cursor.fetchall()]

