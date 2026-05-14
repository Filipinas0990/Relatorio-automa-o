-- ============================================================
-- Banco de dados: farmacia_monitor
-- ============================================================

CREATE TABLE IF NOT EXISTS gestores_trafego (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(120) NOT NULL,
    email       VARCHAR(120) UNIQUE NOT NULL,
    senha_hash  VARCHAR(255) NOT NULL,
    is_admin    BOOLEAN DEFAULT FALSE NOT NULL,
    ativo       BOOLEAN DEFAULT TRUE,
    criado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS farmacias (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(120) NOT NULL,
    url_base    VARCHAR(255) NOT NULL,
    email       VARCHAR(120) NOT NULL,
    senha_enc   TEXT,
    gestor_id   INTEGER REFERENCES gestores_trafego(id) ON DELETE SET NULL,
    ativa       BOOLEAN DEFAULT TRUE,
    criado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS coletas (
    id                      SERIAL PRIMARY KEY,
    farmacia_id             INTEGER NOT NULL REFERENCES farmacias(id) ON DELETE CASCADE,
    data_coleta             TIMESTAMPTZ DEFAULT NOW(),
    periodo_inicio          DATE NOT NULL,
    periodo_fim             DATE NOT NULL,

    clientes_google         INTEGER DEFAULT 0,
    clientes_facebook       INTEGER DEFAULT 0,
    clientes_grupos_oferta  INTEGER DEFAULT 0,
    total_atendimentos      INTEGER DEFAULT 0,

    vendas_realizadas       INTEGER DEFAULT 0,
    receita_total           NUMERIC(12, 2) DEFAULT 0,

    variacao_google         NUMERIC(8, 2) DEFAULT 0,
    variacao_facebook       NUMERIC(8, 2) DEFAULT 0,
    variacao_grupos         NUMERIC(8, 2) DEFAULT 0,
    variacao_vendas         NUMERIC(8, 2) DEFAULT 0,
    variacao_receita        NUMERIC(8, 2) DEFAULT 0,

    score_criticidade       NUMERIC(5, 2) DEFAULT 0,
    nivel_alerta            VARCHAR(10) DEFAULT 'verde'
        CHECK (nivel_alerta IN ('verde', 'amarelo', 'vermelho'))
);

CREATE TABLE IF NOT EXISTS coleta_canais (
    id              SERIAL PRIMARY KEY,
    coleta_id       INTEGER NOT NULL REFERENCES coletas(id) ON DELETE CASCADE,
    canal           VARCHAR(80) NOT NULL,
    atendimentos    INTEGER DEFAULT 0
);

-- ============================================================
-- Índices
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_coletas_farmacia_id  ON coletas(farmacia_id);
CREATE INDEX IF NOT EXISTS idx_coletas_data_coleta  ON coletas(data_coleta DESC);
CREATE INDEX IF NOT EXISTS idx_coletas_nivel_alerta ON coletas(nivel_alerta);
CREATE INDEX IF NOT EXISTS idx_coletas_score        ON coletas(score_criticidade DESC);
CREATE INDEX IF NOT EXISTS idx_canais_coleta_id     ON coleta_canais(coleta_id);

-- ============================================================
-- View: ranking atual (última coleta de cada farmácia)
-- ============================================================

CREATE OR REPLACE VIEW vw_ranking_atual AS
SELECT
    f.id                        AS farmacia_id,
    f.nome                      AS farmacia,
    c.data_coleta,
    c.periodo_inicio,
    c.periodo_fim,
    c.clientes_google,
    c.clientes_facebook,
    c.clientes_grupos_oferta,
    c.total_atendimentos,
    c.vendas_realizadas,
    c.receita_total,
    c.variacao_google,
    c.variacao_facebook,
    c.variacao_grupos,
    c.variacao_vendas,
    c.variacao_receita,
    c.score_criticidade,
    c.nivel_alerta,
    RANK() OVER (ORDER BY c.score_criticidade DESC) AS posicao_ranking
FROM farmacias f
JOIN coletas c ON c.id = (
    SELECT id FROM coletas
    WHERE farmacia_id = f.id
    ORDER BY data_coleta DESC
    LIMIT 1
)
WHERE f.ativa = TRUE;

-- ============================================================
-- View: evolução semanal (últimas 8 semanas por farmácia)
-- ============================================================

CREATE OR REPLACE VIEW vw_evolucao_semanal AS
SELECT
    f.id            AS farmacia_id,
    f.nome          AS farmacia,
    c.periodo_inicio,
    c.periodo_fim,
    c.clientes_google,
    c.clientes_facebook,
    c.clientes_grupos_oferta,
    c.vendas_realizadas,
    c.receita_total,
    c.score_criticidade,
    c.nivel_alerta,
    ROW_NUMBER() OVER (
        PARTITION BY f.id ORDER BY c.data_coleta DESC
    ) AS semana_numero
FROM farmacias f
JOIN coletas c ON c.farmacia_id = f.id
WHERE f.ativa = TRUE
  AND c.data_coleta >= NOW() - INTERVAL '56 days';
