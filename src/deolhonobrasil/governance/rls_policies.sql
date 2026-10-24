-- ==============================================================================
-- DE OLHO NO BRASIL - GOVERNANÇA EDITORIAL E ROW-LEVEL SECURITY (RLS)
-- FASE 3: Políticas de Acesso Estrito, 3 Camadas Epistêmicas e Direito de Resposta
-- ==============================================================================

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Roles canônicos da aplicação (caso ainda não definidos)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'public_reader') THEN
        CREATE ROLE public_reader;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'reviewer_admin') THEN
        CREATE ROLE reviewer_admin;
    END IF;
END $$;

-- ------------------------------------------------------------------------------
-- 1. Tabela: audit_dossiers (Dossiês de Auditoria e Narrativas Grounded RAG)
-- ------------------------------------------------------------------------------
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
    metric_value NUMERIC(16, 4) NOT NULL,
    threshold_value NUMERIC(16, 4) NOT NULL,
    audited_amount NUMERIC(16, 2) NOT NULL,
    provenance_hashes TEXT[] NOT NULL,
    laya_engine_id TEXT NOT NULL,
    laya_score NUMERIC(5, 4) NOT NULL,
    laya_choice TEXT NOT NULL,
    laya_noul TEXT NOT NULL,
    status TEXT NOT NULL,
    reviewer_id TEXT,
    correction_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),

    -- Restrições de Integridade Editorial (Seções 7.6 e 12.1)
    CONSTRAINT chk_dossier_status CHECK (
        status IN (
            'EM_TRIAGEM_INTERNA',
            'PUBLICADO_COM_REVISAO',
            'ESCLARECIDO_COM_PROVA',
            'ERRO_MATERIAL_RETIFICADO'
        )
    ),
    CONSTRAINT chk_published_requires_reviewer CHECK (
        status NOT IN ('PUBLICADO_COM_REVISAO', 'ESCLARECIDO_COM_PROVA', 'ERRO_MATERIAL_RETIFICADO')
        OR (reviewer_id IS NOT NULL AND btrim(reviewer_id) <> '')
    ),
    CONSTRAINT chk_laya_score_range CHECK (
        laya_score >= 0.0000 AND laya_score <= 1.0000
    )
);

CREATE INDEX IF NOT EXISTS idx_audit_dossiers_status_reviewer
    ON audit_dossiers (status, reviewer_id);

CREATE INDEX IF NOT EXISTS idx_audit_dossiers_rule_code
    ON audit_dossiers (rule_code);

-- ------------------------------------------------------------------------------
-- 2. Tabela: right_of_reply_protocols (Direito de Resposta - Seção 12.2)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS right_of_reply_protocols (
    protocol_id TEXT PRIMARY KEY,
    dossier_id TEXT NOT NULL REFERENCES audit_dossiers(dossier_id) ON DELETE RESTRICT,
    respondent_name TEXT NOT NULL,
    respondent_document_masked_or_cnpj TEXT NOT NULL,
    institutional_email_domain TEXT NOT NULL,
    statement_text TEXT NOT NULL,
    attachment_sha256 CHAR(64) NOT NULL,
    status TEXT NOT NULL DEFAULT 'RECEBIDO_EM_VALIDACAO',
    equal_visual_prominence BOOLEAN NOT NULL DEFAULT TRUE,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    reviewed_at TIMESTAMPTZ,
    reviewer_id TEXT,

    CONSTRAINT chk_reply_status CHECK (
        status IN (
            'RECEBIDO_EM_VALIDACAO',
            'PUBLICADO_LADO_A_LADO',
            'SOLICITADO_COMPLEMENTO'
        )
    ),
    CONSTRAINT chk_equal_prominence_mandatory CHECK (
        equal_visual_prominence = TRUE
    )
);

CREATE INDEX IF NOT EXISTS idx_right_of_reply_dossier
    ON right_of_reply_protocols (dossier_id, status);

-- ------------------------------------------------------------------------------
-- 3. Tabela: editorial_audit_trail (Trilha Imutável de Decisões e Retificações)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS editorial_audit_trail (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dossier_id TEXT NOT NULL REFERENCES audit_dossiers(dossier_id) ON DELETE RESTRICT,
    action TEXT NOT NULL,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    rationale TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_editorial_audit_trail_dossier
    ON editorial_audit_trail (dossier_id, occurred_at DESC);

-- ------------------------------------------------------------------------------
-- 4. Habilitação de Row-Level Security (RLS)
-- ------------------------------------------------------------------------------
ALTER TABLE audit_dossiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE right_of_reply_protocols ENABLE ROW LEVEL SECURITY;
ALTER TABLE editorial_audit_trail ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------
-- 5. Função de identificação contextual de papel (compatível com Supabase / PostgREST / sessões normais)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION current_app_role()
RETURNS TEXT AS $$
BEGIN
    RETURN coalesce(
        current_setting('request.jwt.claim.role', true),
        current_setting('app.current_role', true),
        session_user
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- ------------------------------------------------------------------------------
-- 6. Políticas RLS: audit_dossiers
-- Regra de Ouro da Seção 12.4:
-- O leitor público (anon / public_reader / authenticated) NUNCA tem acesso a
-- registros em triagem interna (EM_TRIAGEM_INTERNA). Apenas dossiês com revisão
-- humana aprovada são visíveis publicamente.
-- ------------------------------------------------------------------------------

-- Política para Leitor Público / Cidadão Anônimo
DROP POLICY IF EXISTS p_audit_dossiers_public_read ON audit_dossiers;
CREATE POLICY p_audit_dossiers_public_read
    ON audit_dossiers
    FOR SELECT
    TO anon, authenticated, public_reader
    USING (
        status IN ('PUBLICADO_COM_REVISAO', 'ESCLARECIDO_COM_PROVA', 'ERRO_MATERIAL_RETIFICADO')
        AND reviewer_id IS NOT NULL
        AND btrim(reviewer_id) <> ''
    );

-- Política para Revisores e Administradores Editoriais
DROP POLICY IF EXISTS p_audit_dossiers_reviewer_admin ON audit_dossiers;
CREATE POLICY p_audit_dossiers_reviewer_admin
    ON audit_dossiers
    FOR ALL
    TO reviewer_admin
    USING (TRUE)
    WITH CHECK (TRUE);

-- ------------------------------------------------------------------------------
-- 7. Políticas RLS: right_of_reply_protocols
-- Leitores públicos visualizam manifestações aprovadas lado a lado e podem
-- protocolar novas submissões que entram em validação inicial.
-- ------------------------------------------------------------------------------

DROP POLICY IF EXISTS p_right_of_reply_public_read ON right_of_reply_protocols;
CREATE POLICY p_right_of_reply_public_read
    ON right_of_reply_protocols
    FOR SELECT
    TO anon, authenticated, public_reader
    USING (
        status = 'PUBLICADO_LADO_A_LADO'
    );

DROP POLICY IF EXISTS p_right_of_reply_public_submit ON right_of_reply_protocols;
CREATE POLICY p_right_of_reply_public_submit
    ON right_of_reply_protocols
    FOR INSERT
    TO anon, authenticated, public_reader
    WITH CHECK (
        status = 'RECEBIDO_EM_VALIDACAO'
        AND equal_visual_prominence = TRUE
    );

DROP POLICY IF EXISTS p_right_of_reply_reviewer_admin ON right_of_reply_protocols;
CREATE POLICY p_right_of_reply_reviewer_admin
    ON right_of_reply_protocols
    FOR ALL
    TO reviewer_admin
    USING (TRUE)
    WITH CHECK (TRUE);

-- ------------------------------------------------------------------------------
-- 8. Políticas RLS: editorial_audit_trail
-- Trilha restrita exclusivamente ao corpo de revisores e auditores.
-- ------------------------------------------------------------------------------

DROP POLICY IF EXISTS p_editorial_audit_trail_reviewer_admin ON editorial_audit_trail;
CREATE POLICY p_editorial_audit_trail_reviewer_admin
    ON editorial_audit_trail
    FOR ALL
    TO reviewer_admin
    USING (TRUE)
    WITH CHECK (TRUE);
