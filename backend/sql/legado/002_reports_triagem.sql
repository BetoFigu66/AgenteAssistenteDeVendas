-- =============================================================================
-- Migration manual: adiciona campos de triagem em reports_problema
--   categoria, severidade, status, resolvido_por, resolvido_em
-- =============================================================================

BEGIN;

ALTER TABLE reports_problema
    ADD COLUMN IF NOT EXISTS categoria VARCHAR(20) NOT NULL DEFAULT 'outro',
    ADD COLUMN IF NOT EXISTS severidade VARCHAR(10) NOT NULL DEFAULT 'media',
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'aberto',
    ADD COLUMN IF NOT EXISTS resolvido_por VARCHAR(100),
    ADD COLUMN IF NOT EXISTS resolvido_em TIMESTAMP;

-- Sincroniza reports já existentes que tinham resolvido=true
UPDATE reports_problema
   SET status = 'resolvido'
 WHERE resolvido = TRUE AND status = 'aberto';

CREATE INDEX IF NOT EXISTS idx_reports_problema_status
    ON reports_problema (status);

CREATE INDEX IF NOT EXISTS idx_reports_problema_categoria
    ON reports_problema (categoria);

COMMIT;

-- Verificação --------------------------------------------------------------
-- SELECT id, status, categoria, severidade, resolvido
--   FROM reports_problema ORDER BY id DESC;
