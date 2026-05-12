-- ============================================================
-- Banco de dados: farmacia_monitor
-- ============================================================

CREATE TABLE IF NOT EXISTS farmacias (
    id              SERIAL PRIMARY KEY,
    nome            VARCHAR(120) NOT NULL,
    url_base        VARCHAR(255) NOT NULL,
    email           VARCHAR(120) NOT NULL,
    ativa           BOOLEAN DEFAULT TRUE,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS coletas (
    id                        SERIAL PRIMARY KEY,
    farmacia_id               INTEGER NOT NULL REFERENCES farmacias(id) ON DELETE CASCADE,
    data_coleta               TIMESTAMPTZ DEFAULT NOW(),
    periodo_inicio            DATE NOT NULL,
    periodo_fim               DATE NOT NULL,

    -- 4 badges principais
    aguardando_atendimento    INTEGER DEFAULT 0,
    em_andamento              INTEGER DEFAULT 0,
    atendimentos_finalizados  INTEGER DEFAULT 0,
    total_atendimentos        INTEGER DEFAULT 0,
    -- métricas extras
    vendas_realizadas         INTEGER DEFAULT 0,
    vendas_nao_realizadas     INTEGER DEFAULT 0,
    receita_total             NUMERIC(12, 2) DEFAULT 0,

    -- Métricas calculadas
    taxa_conversao            NUMERIC(6, 2) DEFAULT 0,
    variacao_receita          NUMERIC(8, 2) DEFAULT 0,
    variacao_atendimentos     NUMERIC(8, 2) DEFAULT 0,
    variacao_vendas           NUMERIC(8, 2) DEFAULT 0,

    -- Criticidade
    score_criticidade         NUMERIC(5, 2) DEFAULT 0,
    nivel_alerta              VARCHAR(10) DEFAULT 'verde' CHECK (nivel_alerta IN ('verde', 'amarelo', 'vermelho'))
);

CREATE TABLE IF NOT EXISTS coleta_canais (
    id              SERIAL PRIMARY KEY,
    coleta_id       INTEGER NOT NULL REFERENCES coletas(id) ON DELETE CASCADE,
    canal           VARCHAR(80) NOT NULL,
    atendimentos    INTEGER DEFAULT 0,
    vendas          INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS coleta_conexoes (
    id              SERIAL PRIMARY KEY,
    coleta_id       INTEGER NOT NULL REFERENCES coletas(id) ON DELETE CASCADE,
    conexao         VARCHAR(120) NOT NULL,
    atendimentos    INTEGER DEFAULT 0,
    vendas          INTEGER DEFAULT 0
);

-- ============================================================
-- Índices para queries frequentes do dashboard
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_coletas_farmacia_id   ON coletas(farmacia_id);
CREATE INDEX IF NOT EXISTS idx_coletas_data_coleta   ON coletas(data_coleta DESC);
CREATE INDEX IF NOT EXISTS idx_coletas_nivel_alerta  ON coletas(nivel_alerta);
CREATE INDEX IF NOT EXISTS idx_coletas_score         ON coletas(score_criticidade DESC);
CREATE INDEX IF NOT EXISTS idx_canais_coleta_id      ON coleta_canais(coleta_id);
CREATE INDEX IF NOT EXISTS idx_conexoes_coleta_id    ON coleta_conexoes(coleta_id);

-- ============================================================
-- View: última coleta de cada farmácia com ranking
-- ============================================================

CREATE OR REPLACE VIEW vw_ranking_atual AS
SELECT
    f.id                        AS farmacia_id,
    f.nome                      AS farmacia,
    c.data_coleta,
    c.periodo_inicio,
    c.periodo_fim,
    c.aguardando_atendimento,
    c.em_andamento,
    c.atendimentos_finalizados,
    c.total_atendimentos,
    c.vendas_realizadas,
    c.vendas_nao_realizadas,
    c.receita_total,
    c.taxa_conversao,
    c.variacao_receita,
    c.variacao_atendimentos,
    c.variacao_vendas,
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
-- View: evolução semanal por farmácia (últimas 8 semanas)
-- ============================================================

CREATE OR REPLACE VIEW vw_evolucao_semanal AS
SELECT
    f.id                    AS farmacia_id,
    f.nome                  AS farmacia,
    c.periodo_inicio,
    c.periodo_fim,
    c.receita_total,
    c.total_atendimentos,
    c.vendas_realizadas,
    c.taxa_conversao,
    c.score_criticidade,
    c.nivel_alerta,
    ROW_NUMBER() OVER (
        PARTITION BY f.id
        ORDER BY c.data_coleta DESC
    ) AS semana_numero
FROM farmacias f
JOIN coletas c ON c.farmacia_id = f.id
WHERE f.ativa = TRUE
  AND c.data_coleta >= NOW() - INTERVAL '56 days';
