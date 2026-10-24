# Test Plan — SPEC-0006

## Mapeamento de Requisitos para Test Anchors
| Requisito / Critério | Test Anchor |
| :--- | :--- |
| `FR-014`, `SEC-009`, `AC-022` | `tests/test_admin_and_evidence_bundle.py::TestEditorialAdminAndEvidenceBundle::test_admin_approve_dossier_requires_token_and_publishes_to_public` |
| `FR-014`, `AC-024` | `tests/test_admin_and_evidence_bundle.py::TestEditorialAdminAndEvidenceBundle::test_admin_rectify_material_error_updates_status_and_blocks_accusatory_note` |
| `FR-014` | `tests/test_admin_and_evidence_bundle.py::TestEditorialAdminAndEvidenceBundle::test_admin_audit_trail_endpoint_returns_immutable_history` |
| `FR-015`, `SEC-009`, `AC-023` | `tests/test_admin_and_evidence_bundle.py::TestEditorialAdminAndEvidenceBundle::test_evidence_bundle_blocks_unreviewed_dossier_for_public_reader` |
| `NFR-009`, `DATA-008`, `AC-025` | `tests/test_admin_and_evidence_bundle.py::TestEditorialAdminAndEvidenceBundle::test_verifiable_evidence_bundle_canonical_sha256_integrity` |

## Estratégia de Execução
Os testes devem ser executados via pytest com cobertura isolada para garantir que nenhum endpoint administrativo vaze dados não aprovados.
