-- Migration v3: Adiciona coluna is_admin na tabela gestores_trafego
-- Execute no servidor após o git pull:
--   docker compose exec postgres psql -U farmacia_user -d farmacia_monitor -f /app/sql/migration_v3.sql

ALTER TABLE gestores_trafego
    ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

SELECT 'Migration v3 aplicada com sucesso!' AS resultado;
