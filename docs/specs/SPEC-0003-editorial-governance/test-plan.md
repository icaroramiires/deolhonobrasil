# Plano de Testes: SPEC-0003

## Cobertura de Testes
Os testes cobrem exaustivamente as suítes definidas em `tests/test_audit_and_governance.py`:
1. Visibilidade e RLS (`test_visibility_governance_rls`).
2. Exigência de revisor para publicação (`test_published_dossier_requires_reviewer`).
3. Direito de resposta e esclarecimento (`test_right_of_reply_attachment_and_clarification`).
4. Retificação de erro material (`test_rectify_material_error`).
5. Sanitização contra prompt injection e linguagem acusatória.
6. Imutabilidade da trilha de auditoria.
