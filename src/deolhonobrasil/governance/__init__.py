"""Módulo de Governança Editorial, Direito de Resposta e Políticas RLS.

Exporta as interfaces públicas da Fase 3:
- Papéis e Estados: AccessRole, DossierStatus, RightOfReplyStatus.
- Dossiês e Protocolos: AuditDossier, RightOfReplySubmission.
- Transições de Governança: is_visible_to_role, approve_dossier_for_publication, attach_right_of_reply, rectify_material_error.
"""

from deolhonobrasil.governance.dossiers import (
    AccessRole,
    AuditDossier,
    DossierStatus,
    approve_dossier_for_publication,
    attach_right_of_reply,
    is_visible_to_role,
    rectify_material_error,
)
from deolhonobrasil.governance.right_of_reply import (
    RightOfReplyStatus,
    RightOfReplySubmission,
)

__all__ = [
    "AccessRole",
    "AuditDossier",
    "DossierStatus",
    "RightOfReplyStatus",
    "RightOfReplySubmission",
    "approve_dossier_for_publication",
    "attach_right_of_reply",
    "is_visible_to_role",
    "rectify_material_error",
]
