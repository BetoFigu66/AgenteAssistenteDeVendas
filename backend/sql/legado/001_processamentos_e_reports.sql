-- =============================================================================
-- Migration manual (enquanto o Alembic está indisponível)
-- Cria: processamentos_mensagem, reports_problema
-- Altera: mensagens (adiciona processamento_id)
-- =============================================================================

BEGIN;

-- 1) Tabela processamentos_mensagem -----------------------------------------
CREATE TABLE IF NOT EXISTS processamentos_mensagem (
    id                          SERIAL PRIMARY KEY,
    intencao                    VARCHAR(50),
    confianca                   NUMERIC(3, 2),
    origem_classificacao        VARCHAR(20),  -- 'regra' | 'llm' | 'hibrido'
    entidades                   JSON,
    status_identificacao        VARCHAR(30),
    contato_id_identificado     INTEGER REFERENCES contatos(id),
    empresa_id_identificada     INTEGER REFERENCES empresas(id),
    negociacao_id_ativa         INTEGER REFERENCES negociacoes(id),
    template_usado              VARCHAR(100),
    personalizado_via_llm       BOOLEAN NOT NULL DEFAULT FALSE,
    llm_provider                VARCHAR(30),
    llm_modelo                  VARCHAR(100),
    llm_tokens_input            INTEGER,
    llm_tokens_output           INTEGER,
    llm_latencia_ms             INTEGER,
    llm_raw_resposta            JSON,
    duracao_ms                  INTEGER,
    erro                        TEXT,
    created_at                  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processamentos_intencao
    ON processamentos_mensagem (intencao);

-- 2) Altera mensagens (adiciona FK para processamento) ----------------------
ALTER TABLE mensagens
    ADD COLUMN IF NOT EXISTS processamento_id INTEGER
        REFERENCES processamentos_mensagem(id);

CREATE INDEX IF NOT EXISTS idx_mensagens_processamento
    ON mensagens (processamento_id);

-- 3) Tabela reports_problema -------------------------------------------------
CREATE TABLE IF NOT EXISTS reports_problema (
    id                  SERIAL PRIMARY KEY,
    processamento_id    INTEGER NOT NULL
        REFERENCES processamentos_mensagem(id) ON DELETE CASCADE,
    descricao           TEXT NOT NULL,
    autor               VARCHAR(100),
    resolvido           BOOLEAN NOT NULL DEFAULT FALSE,
    resolucao           TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reports_problema_processamento
    ON reports_problema (processamento_id);

COMMIT;

-- Verificação rápida ---------------------------------------------------------
-- SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'mensagens' AND column_name = 'processamento_id';
-- SELECT COUNT(*) FROM processamentos_mensagem;
-- SELECT COUNT(*) FROM reports_problema;
