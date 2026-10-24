"""Gestão de dossiês de auditoria, governança editorial escalonada e controle de visibilidade RLS.

Implementa os requisitos das Seções 12.1, 12.2 e 12.4:
- AccessRole: papéis de acesso (PUBLIC_READER e REVIEWER_ADMIN).
- DossierStatus: estados do ciclo editorial (EM_TRIAGEM_INTERNA, PUBLICADO_COM_REVISAO, ESCLARECIDO_COM_PROVA, ERRO_MATERIAL_RETIFICADO).
- AuditDossier: agregador canônico imutável de sinal, decisão de triagem Laya, narrativa em 3 camadas e contraditório.
- is_visible_to_role: governança estrita de visibilidade para leitores anônimos/públicos.
- Transições de estado auditáveis com registro de revisor e carimbo de tempo UTC.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
import json
from typing import Any

from deolhonobrasil.audit.laya_engine import System1Decision
from deolhonobrasil.audit.rag_narrator import GroundedDossierSection
from deolhonobrasil.audit.rules import AuditSignal
from deolhonobrasil.governance.right_of_reply import (
    RightOfReplyStatus,
    RightOfReplySubmission,
)
from deolhonobrasil.pipeline.models import assert_non_accusatory_language
from deolhonobrasil.pipeline.privacy import (
    compute_sha256_text,
    sanitize_untrusted_public_text,
)


class AccessRole(StrEnum):
    """Papéis de controle de acesso aos dossiês e protocolos de auditoria."""

    PUBLIC_READER = "public_reader"
    REVIEWER_ADMIN = "reviewer_admin"


class DossierStatus(StrEnum):
    """Estados do ciclo de publicação editorial de um dossiê cívico."""

    EM_TRIAGEM_INTERNA = "EM_TRIAGEM_INTERNA"
    PUBLICADO_COM_REVISAO = "PUBLICADO_COM_REVISAO"
    ESCLARECIDO_COM_PROVA = "ESCLARECIDO_COM_PROVA"
    ERRO_MATERIAL_RETIFICADO = "ERRO_MATERIAL_RETIFICADO"


_PUBLISHED_STATUSES: frozenset[DossierStatus] = frozenset(
    {
        DossierStatus.PUBLICADO_COM_REVISAO,
        DossierStatus.ESCLARECIDO_COM_PROVA,
        DossierStatus.ERRO_MATERIAL_RETIFICADO,
    }
)


@dataclass(frozen=True, slots=True)
class AuditDossier:
    """Dossiê de auditoria integrando sinal, decisão de máquina, narrativa epistêmica e contraditório."""

    dossier_id: str
    signal: AuditSignal
    laya_decision: System1Decision
    grounded_sections: GroundedDossierSection
    status: DossierStatus
    reviewer_id: str | None
    right_of_reply: RightOfReplySubmission | None
    correction_note: str | None
    updated_at_utc: str

    def __post_init__(self) -> None:
        if not self.dossier_id.strip():
            raise ValueError("dossier_id é obrigatório.")

        # Invariante de publicação: dossiês publicados exigem revisor humano identificado
        if self.status in _PUBLISHED_STATUSES and not (self.reviewer_id and self.reviewer_id.strip()):
            raise ValueError(
                f"Dossiê em estado público '{self.status.value}' exige obrigatoriamente um 'reviewer_id' responsável."
            )

        if self.correction_note:
            assert_non_accusatory_language(self.correction_note)


@dataclass(frozen=True, slots=True)
class VerifiableEvidenceBundle:
    """Pacote autocontido e criptograficamente verificável (`SPEC-0006` / `DATA-008` / `NFR-009`)."""

    dossier_id: str
    rule_code: str
    title: str
    status: str
    reviewer_id: str
    epistemic_layer: str
    official_data_block: str
    statistical_inference_block: str
    audit_hypothesis_and_limits_block: str
    provenance_hashes: tuple[str, ...]
    right_of_reply: dict[str, Any] | None
    correction_note: str | None
    updated_at_utc: str
    bundle_sha256: str

    @staticmethod
    def compute_canonical_hash(payload_without_hash: dict[str, Any]) -> str:
        canonical = json.dumps(
            payload_without_hash,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return compute_sha256_text(canonical)

    @classmethod
    def from_dossier_row(cls, row: dict[str, Any]) -> VerifiableEvidenceBundle:
        prov_raw = row.get("provenance_hashes") or ()
        if isinstance(prov_raw, str):
            prov_tuple = tuple(json.loads(prov_raw))
        else:
            prov_tuple = tuple(str(h) for h in prov_raw)

        base_dict: dict[str, Any] = {
            "dossier_id": str(row["dossier_id"]),
            "rule_code": str(row["rule_code"]),
            "title": str(row["title"]),
            "status": str(row["status"]),
            "reviewer_id": str(row.get("reviewer_id") or ""),
            "epistemic_layer": str(row["epistemic_layer"]),
            "official_data_block": str(row["official_data_block"]),
            "statistical_inference_block": str(row["statistical_inference_block"]),
            "audit_hypothesis_and_limits_block": str(row["audit_hypothesis_and_limits_block"]),
            "provenance_hashes": list(prov_tuple),
            "right_of_reply": row.get("right_of_reply"),
            "correction_note": row.get("correction_note"),
            "updated_at_utc": str(row["updated_at_utc"]),
        }
        digest = cls.compute_canonical_hash(base_dict)
        return cls(
            dossier_id=base_dict["dossier_id"],
            rule_code=base_dict["rule_code"],
            title=base_dict["title"],
            status=base_dict["status"],
            reviewer_id=base_dict["reviewer_id"],
            epistemic_layer=base_dict["epistemic_layer"],
            official_data_block=base_dict["official_data_block"],
            statistical_inference_block=base_dict["statistical_inference_block"],
            audit_hypothesis_and_limits_block=base_dict["audit_hypothesis_and_limits_block"],
            provenance_hashes=prov_tuple,
            right_of_reply=base_dict["right_of_reply"],
            correction_note=base_dict["correction_note"],
            updated_at_utc=base_dict["updated_at_utc"],
            bundle_sha256=digest,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerifiableEvidenceBundle:
        return cls(
            dossier_id=str(data["dossier_id"]),
            rule_code=str(data["rule_code"]),
            title=str(data["title"]),
            status=str(data["status"]),
            reviewer_id=str(data["reviewer_id"]),
            epistemic_layer=str(data["epistemic_layer"]),
            official_data_block=str(data["official_data_block"]),
            statistical_inference_block=str(data["statistical_inference_block"]),
            audit_hypothesis_and_limits_block=str(data["audit_hypothesis_and_limits_block"]),
            provenance_hashes=tuple(str(x) for x in data.get("provenance_hashes", [])),
            right_of_reply=data.get("right_of_reply"),
            correction_note=data.get("correction_note"),
            updated_at_utc=str(data["updated_at_utc"]),
            bundle_sha256=str(data["bundle_sha256"]),
        )

    def verify_integrity(self) -> bool:
        expected = self.compute_canonical_hash(
            {
                "dossier_id": self.dossier_id,
                "rule_code": self.rule_code,
                "title": self.title,
                "status": self.status,
                "reviewer_id": self.reviewer_id,
                "epistemic_layer": self.epistemic_layer,
                "official_data_block": self.official_data_block,
                "statistical_inference_block": self.statistical_inference_block,
                "audit_hypothesis_and_limits_block": self.audit_hypothesis_and_limits_block,
                "provenance_hashes": list(self.provenance_hashes),
                "right_of_reply": self.right_of_reply,
                "correction_note": self.correction_note,
                "updated_at_utc": self.updated_at_utc,
            }
        )
        return expected == self.bundle_sha256

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["provenance_hashes"] = list(self.provenance_hashes)
        return d


def is_visible_to_role(dossier: AuditDossier, role: AccessRole) -> bool:
    """Aplica as regras de visibilidade da Governança Editorial (Seção 12.4).

    - REVIEWER_ADMIN: visualiza todos os registros em qualquer estado.
    - PUBLIC_READER: visualiza EXCLUSIVAMENTE dossiês com revisão humana aprovada
      (PUBLICADO_COM_REVISAO, ESCLARECIDO_COM_PROVA ou ERRO_MATERIAL_RETIFICADO)
      onde reviewer_id esteja preenchido.
      Dossiês EM_TRIAGEM_INTERNA são estritamente inacessíveis ao público externo.
    """
    if role == AccessRole.REVIEWER_ADMIN:
        return True

    if role == AccessRole.PUBLIC_READER:
        return dossier.status in _PUBLISHED_STATUSES and bool(
            dossier.reviewer_id and dossier.reviewer_id.strip()
        )

    return False


def approve_dossier_for_publication(
    dossier: AuditDossier,
    reviewer_id: str,
    timestamp_utc: str,
) -> AuditDossier:
    """Aprova um dossiê em triagem para publicação pública pelo revisor humano."""
    clean_rev = sanitize_untrusted_public_text(reviewer_id, 80)
    if not clean_rev:
        raise ValueError("Identificador do revisor humano (reviewer_id) é obrigatório para aprovação.")

    return replace(
        dossier,
        status=DossierStatus.PUBLICADO_COM_REVISAO,
        reviewer_id=clean_rev,
        updated_at_utc=timestamp_utc,
    )


def attach_right_of_reply(
    dossier: AuditDossier,
    reply: RightOfReplySubmission,
    reviewer_id: str,
    reclassify_as_clarified: bool,
    timestamp_utc: str,
) -> AuditDossier:
    """Vincula a manifestação formal de Direito de Resposta ao dossiê com paridade de destaque."""
    clean_rev = sanitize_untrusted_public_text(reviewer_id, 80)
    if not clean_rev:
        raise ValueError("Identificador do revisor humano (reviewer_id) é obrigatório para vincular resposta.")

    if reply.dossier_id != dossier.dossier_id:
        raise ValueError(
            f"Divergência de chave: a manifestação refere-se ao dossiê '{reply.dossier_id}', "
            f"mas o dossiê alvo é '{dossier.dossier_id}'."
        )

    # Atualiza o status da manifestação para lado a lado
    published_reply = replace(
        reply,
        status=RightOfReplyStatus.PUBLICADO_LADO_A_LADO,
        equal_visual_prominence=True,
    )

    new_status = (
        DossierStatus.ESCLARECIDO_COM_PROVA
        if reclassify_as_clarified
        else (
            dossier.status
            if dossier.status in _PUBLISHED_STATUSES
            else DossierStatus.PUBLICADO_COM_REVISAO
        )
    )

    return replace(
        dossier,
        status=new_status,
        reviewer_id=clean_rev,
        right_of_reply=published_reply,
        updated_at_utc=timestamp_utc,
    )


def rectify_material_error(
    dossier: AuditDossier,
    reviewer_id: str,
    correction_note: str,
    timestamp_utc: str,
) -> AuditDossier:
    """Registra uma retificação explícita por erro material ou atualização cadastral oficial."""
    clean_rev = sanitize_untrusted_public_text(reviewer_id, 80)
    if not clean_rev:
        raise ValueError("Identificador do revisor humano (reviewer_id) é obrigatório para retificação.")

    clean_note = sanitize_untrusted_public_text(correction_note, 2000)
    if not clean_note:
        raise ValueError("Nota explicativa da retificação (correction_note) é obrigatória.")

    assert_non_accusatory_language(clean_note)

    return replace(
        dossier,
        status=DossierStatus.ERRO_MATERIAL_RETIFICADO,
        reviewer_id=clean_rev,
        correction_note=clean_note,
        updated_at_utc=timestamp_utc,
    )
