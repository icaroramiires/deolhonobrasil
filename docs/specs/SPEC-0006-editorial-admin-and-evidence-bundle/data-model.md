# Data Model Contracts — SPEC-0006

## 1. VerifiableEvidenceBundle (`DATA-008`, `NFR-009`)
```python
from dataclasses import dataclass, field
import json
import hashlib
from typing import Dict, Any, List

@dataclass(frozen=True)
class VerifiableEvidenceBundle:
    dossier_id: str
    official_data_layer: Dict[str, Any]
    statistical_inference_layer: Dict[str, Any]
    audit_hypothesis_layer: Dict[str, Any]
    right_of_reply: List[Dict[str, Any]]
    editorial_status: str
    audit_trail: List[Dict[str, Any]]
    bundle_sha256: str = field(default="")

    def __post_init__(self):
        if not self.bundle_sha256:
            payload = {
                "dossier_id": self.dossier_id,
                "official_data_layer": self.official_data_layer,
                "statistical_inference_layer": self.statistical_inference_layer,
                "audit_hypothesis_layer": self.audit_hypothesis_layer,
                "right_of_reply": self.right_of_reply,
                "editorial_status": self.editorial_status,
                "audit_trail": self.audit_trail,
            }
            canonical_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            computed_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
            object.__setattr__(self, "bundle_sha256", computed_hash)
```

## 2. API Endpoints Contract (`FR-014`, `FR-015`, `SEC-009`)
- `POST /api/v1/admin/dossiers/approve`: Headers: `X-Admin-Token`. Body: `{"dossier_id": "string", "reviewer_id": "string"}`. Response: `200 OK` with status update.
- `POST /api/v1/admin/dossiers/rectify`: Headers: `X-Admin-Token`. Body: `{"dossier_id": "string", "rectification_note": "string"}`. Response: `200 OK` or `422` if accusatory.
- `GET /api/v1/admin/audit-trail`: Headers: `X-Admin-Token`. Response: `200 OK` with immutable history list.
- `GET /api/v1/dossiers/evidence-bundle?dossier_id=string`: Query Param: `dossier_id`. Response: `200 OK` with `VerifiableEvidenceBundle` JSON payload including `bundle_sha256`, or `403/404` if unreviewed.
