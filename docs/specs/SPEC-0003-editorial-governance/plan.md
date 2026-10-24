# Design Técnico: SPEC-0003 — Governança Editorial

**Versão:** 1.0.0  
**Status:** Aprovado  

## 1. Visão Geral
Este documento detalha a arquitetura técnica dos módulos `dossiers.py`, `right_of_reply.py`, das políticas de segurança em `rls_policies.sql` e dos mecanismos de persistência imutável em SQLite / PostgreSQL.

## 2. Componentes Principais
- **`src/deolhonobrasil/governance/dossiers.py`**: Gerenciamento de ciclo de vida de dossiês (`EM_TRIAGEM_INTERNA`, `PENDING_REVIEW`, `PUBLISHED`, `RECTIFIED`).
- **`src/deolhonobrasil/governance/right_of_reply.py`**: Processamento, sanitização e validação de direito de resposta e retificações.
- **`src/deolhonobrasil/governance/rls_policies.sql`**: Políticas de Row-Level Security para PostgreSQL e visões equivalentes para SQLite.
- **`editorial_audit_trail`**: Tabela append-only para registro de todas as alterações editoriais.

## 3. Fluxo de Dados e Segurança
1. Consultas públicas filtram automaticamente `status = 'PUBLISHED'`.
2. Tentativas de inserção de texto acusatório geram exceção imediata.
3. Trilha de auditoria registra hash SHA-256 de cada modificação.
