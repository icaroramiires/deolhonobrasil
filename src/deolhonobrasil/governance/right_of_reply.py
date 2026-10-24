"""Protocolo de Direito de Resposta com paridade de destaque visual e blindagem anti-injeção.

Implementa os requisitos das Seções 12.2 e 12.3:
- RightOfReplyStatus: estados do fluxo formal de resposta.
- RightOfReplySubmission: modelo imutável submetido pelo representante ou cidadão afetado,
  com higienização estrita contra prompt injection e verificação não-acusatória.
- Garantia de paridade de armas: `equal_visual_prominence = True` obrigatório.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from deolhonobrasil.pipeline.models import assert_non_accusatory_language
from deolhonobrasil.pipeline.privacy import sanitize_untrusted_public_text


class RightOfReplyStatus(StrEnum):
    """Estados do ciclo de vida de uma submissão de Direito de Resposta."""

    RECEBIDO_EM_VALIDACAO = "RECEBIDO_EM_VALIDACAO"
    PUBLICADO_LADO_A_LADO = "PUBLICADO_LADO_A_LADO"
    SOLICITADO_COMPLEMENTO = "SOLICITADO_COMPLEMENTO"


@dataclass(frozen=True, slots=True)
class RightOfReplySubmission:
    """Submissão formal de Direito de Resposta (Seção 12.2)."""

    protocol_id: str
    dossier_id: str
    respondent_name: str
    respondent_document_masked_or_cnpj: str
    institutional_email_domain: str
    statement_text: str
    attachment_sha256: str
    submitted_at_utc: str
    status: RightOfReplyStatus = RightOfReplyStatus.RECEBIDO_EM_VALIDACAO
    equal_visual_prominence: bool = True

    def __post_init__(self) -> None:
        if not self.protocol_id.strip():
            raise ValueError("protocol_id é obrigatório.")
        if not self.dossier_id.strip():
            raise ValueError("dossier_id é obrigatório.")
        if not self.attachment_sha256 or len(self.attachment_sha256) != 64:
            raise ValueError(f"attachment_sha256 deve conter exatamente 64 caracteres hexadecimais: '{self.attachment_sha256}'")

        # Higienização contra injeção indireta (Seção 11 e 12.3)
        clean_text = sanitize_untrusted_public_text(self.statement_text, max_length=5000)
        if not clean_text:
            raise ValueError("O texto da manifestação (statement_text) não pode estar vazio após higienização.")
        object.__setattr__(self, "statement_text", clean_text)

        clean_name = sanitize_untrusted_public_text(self.respondent_name, max_length=150)
        object.__setattr__(self, "respondent_name", clean_name)

        # Verificação da política editorial contra termos acusatórios no texto da resposta
        assert_non_accusatory_language(clean_text)
