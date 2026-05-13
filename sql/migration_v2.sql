-- Migration v2: Adiciona suporte a Gestores de Tráfego e credenciais no banco
-- Execute no servidor após o git pull:
--   docker compose exec postgres psql -U farmacia_user -d farmacia_monitor -f /app/sql/migration_v2.sql

-- 1. Criar tabela de gestores
CREATE TABLE IF NOT EXISTS gestores_trafego (
    id         SERIAL PRIMARY KEY,
    nome       VARCHAR(120) NOT NULL,
    email      VARCHAR(120) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    ativo      BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- 2. Adicionar colunas na tabela farmacias (se ainda não existirem)
ALTER TABLE farmacias
    ADD COLUMN IF NOT EXISTS senha_enc TEXT,
    ADD COLUMN IF NOT EXISTS gestor_id INTEGER REFERENCES gestores_trafego(id) ON DELETE SET NULL;

-- 3. Índice para filtro por gestor
CREATE INDEX IF NOT EXISTS idx_farmacias_gestor ON farmacias(gestor_id);

-- 4. Confirmar
SELECT 'Migration v2 aplicada com sucesso!' AS resultado;
