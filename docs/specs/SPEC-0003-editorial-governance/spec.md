# SPEC-0003 — Governança Editorial Híbrida, Direito de Resposta, Retificação e Row-Level Security

**Última Atualização:** 2026-10-23  
**Status:** Verificado  
**Versão:** 1.0.0  
**Autor:** Arquitetura & Governança De Olho no Brasil  

---

## 1. Identificador e Título
- **ID:** `SPEC-0003`
- **Título:** Governança Editorial Híbrida, Direito de Resposta, Retificação e Row-Level Security

## 2. Status e Versão
- **Status:** `Verificado`
- **Versão:** 1.0.0

## 3. Problema e Motivação
O ecossistema **De Olho no Brasil** processa e publica dados de despesas públicas, emendas parlamentares e contratos federais. A publicação automatizada de inferências estatísticas e achados de auditoria exige um rigoroso mecanismo de governança editorial para evitar danos reputacionais infundados, garantir conformidade jurídica e cumprir o direito constitucional de resposta e retificação de erros materiais, mantendo uma trilha de auditoria imutável.

## 4. Objetivos e Não-Objetivos
### Objetivos
- Estabelecer fluxos de revisão editorial para dossiês e achados de auditoria.
- Garantir o Direito de Resposta e Retificação de Erro Material com paridade visual (`equal_visual_prominence=True`).
- Implementar Row-Level Security (RLS) e isolamento estrito de status de rascunho/triagem.
- Manter trilha de auditoria editorial (`editorial_audit_trail`) append-only e criptograficamente rastreável.

### Não-Objetivos
- Substituir tribunais ou emitir sentenças judiciais automatizadas.
- Permitir edição arbitrária ou exclusão de registros históricos na trilha de auditoria.

## 5. Atores e Permissões
- `public_reader`: Leitor público. Apenas acessa dossiês publicados (`status = 'PUBLISHED'`), visualiza direitos de resposta atrelados e notas de retificação.
- `reviewer_admin`: Revisor/Administrador editorial. Pode criar, editar, alterar status (`EM_TRIAGEM_INTERNA`, `PENDING_REVIEW`, `PUBLISHED`, `RECTIFIED`), aprovar respostas e aplicar retificações.

## 6. Fluxos Principais
1. **Criação de Dossiê:** Criado em rascunho (`EM_TRIAGEM_INTERNA` / `PENDING_REVIEW`).
2. **Revisão e Publicação:** `reviewer_admin` valida o achado e altera para `PUBLISHED`.
3. **Submissão de Direito de Resposta:** Entidade externa submete resposta, que passa por triagem e é publicada com igual destaque visual (`equal_visual_prominence=True`).
4. **Retificação de Erro Material:** `reviewer_admin` executa `rectify_material_error`, gerando registro na trilha de auditoria.

## 7. Cenários Alternativos e de Erro
- Tentativa de acesso a dossiê em triagem por `public_reader`: Retorna vazio ou erro de permissão (RLS bloqueia).
- Submissão de Direito de Resposta com linguagem acusatória ou injuriosa: Rejeitado pelas regras de validação (`assert_non_accusatory_language`).
- Tentativa de alteração direta na tabela de auditoria: Bloqueado por gatilho append-only.

## 8. Requisitos Funcionais
- **FR-008:** Direito de Resposta lado a lado com o dossiê original, garantindo `equal_visual_prominence=True`.
- **FR-009:** Retificação estruturada de Erro Material via função `rectify_material_error`.

## 9. Requisitos Não Funcionais
- **NFR-005:** A trilha de auditoria deve preservar integridade append-only sem perda de registros em operações concorrentes.

## 10. Regras de Negócio e Dados
- **DATA-005:** A tabela `editorial_audit_trail` deve ser imutável, aceitando apenas inserções via triggers ou funções controladas.

## 11. Requisitos de Segurança e Privacidade
- **SEC-004:** Ocultação estrita de status `EM_TRIAGEM_INTERNA` para `public_reader` tanto no código de repositório quanto em `rls_policies.sql`.
- **SEC-005:** Sanitização rigorosa de textos de resposta contra XSS e injeção de comandos.

## 12. Critérios de Aceite
- **AC-010:** RLS bloqueia corretamente leitores públicos em rascunhos.
- **AC-011:** Direito de resposta é exibido com paridade visual.
- **AC-012:** Retificação registra o evento na trilha de auditoria imutável.
- **AC-013:** Validação bloqueia textos acusatórios em respostas.

## 13. Dependências
- SPEC-0001 (Invariantes e Core ETL)
- SPEC-0002 (Lakehouse e Armazenamento)

## 14. Riscos e Limitações
- Conflitos de concorrência na submissão de múltiplas retificações sobre o mesmo dossiê.

## 15. Estratégia de Testes e Test Anchors
Os testes unitários e de integração validam as regras descritas nesta spec.

### Test Anchors
- `tests/test_audit_and_governance.py::TestGovernanceAndRightOfReply::test_visibility_governance_rls`
- `tests/test_audit_and_governance.py::TestGovernanceAndRightOfReply::test_published_dossier_requires_reviewer`
- `tests/test_audit_and_governance.py::TestGovernanceAndRightOfReply::test_right_of_reply_attachment_and_clarification`
- `tests/test_audit_and_governance.py::TestGovernanceAndRightOfReply::test_rectify_material_error`
- `tests/test_audit_and_governance.py::TestGovernanceAndRightOfReply::test_right_of_reply_prompt_injection_sanitization`
- `tests/test_audit_and_governance.py::TestGovernanceAndRightOfReply::test_right_of_reply_rejects_accusatory_text`
- `tests/test_audit_and_governance.py::TestRLSPoliciesFile::test_rls_sql_file_exists_and_contains_policies`
- `tests/test_audit_and_governance.py::TestLakehouseStorageAuditIntegration::test_dossier_upsert_and_role_visibility_filtering`
- `tests/test_audit_and_governance.py::TestLakehouseStorageAuditIntegration::test_right_of_reply_persistence_and_clarification`
- `tests/test_audit_and_governance.py::TestLakehouseStorageAuditIntegration::test_material_error_rectification_persistence`
- `tests/test_audit_and_governance.py::TestLakehouseStorageAuditIntegration::test_editorial_audit_trail_immutability`
- `tests/test_audit_and_governance.py::TestLakehouseStorageAuditIntegration::test_cli_run_audit_pipeline`

## 16. Questões Pendentes
- Nenhuma pendência crítica para o Checkpoint 2.
