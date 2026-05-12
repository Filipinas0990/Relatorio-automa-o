# PharmaFlow — Automação de Relatórios Semanais

Sistema de coleta, processamento e visualização automática de dados de 70 farmácias clientes de uma agência de marketing, via scraping do painel **PharmaChatBot**.

---

## O Problema

A agência atende 70 farmácias, cada uma com um chatbot de atendimento integrado no **PharmaChatBot**. Toda semana, era necessário entrar manualmente em cada painel para identificar quais farmácias estavam com desempenho abaixo do esperado — um processo lento, manual e impossível de escalar.

## A Solução

Um pipeline 100% automatizado que:

1. **Entra automaticamente** no painel de cada farmácia todo domingo às 22h
2. **Coleta os dados** dos últimos 7 dias
3. **Calcula um score de criticidade** para cada cliente
4. **Salva tudo no banco de dados**
5. Na segunda de manhã, o **dashboard PharmaFlow** já reflete os dados atualizados

---

## Arquitetura

```
farmacias.json (credenciais)
      │
      ▼
main.py — Pipeline (todo domingo 22h)
      │
      ├── Playwright → faz login em cada farmácia
      │               → aplica filtro dos últimos 7 dias
      │               → coleta os 4 badges principais
      │
      ├── Score Calculator → calcula criticidade vs semana anterior
      │
      └── PostgreSQL → salva histórico semanal
                │
                ▼
           FastAPI (API REST)
                │
                ▼
         PharmaFlow (Frontend)
         lê o banco toda segunda via JSON
```

---

## Métricas Coletadas por Farmácia

Extraídas do dashboard do PharmaChatBot após aplicação do filtro de 7 dias:

| Métrica | Descrição |
|---|---|
| **Atendimentos finalizados** | Conversas encerradas no período |
| **Total de atendimentos** | Total de conversas iniciadas |
| **Em andamento** | Atendimentos ainda abertos |
| **Aguardando atendimento** | Fila de espera em tempo real |
| **Vendas realizadas** | Pedidos convertidos |
| **Vendas não realizadas** | Conversas sem conversão |
| **Receita total** | Faturamento gerado pelo chatbot |

### Score de Criticidade (0–100)

Calculado automaticamente comparando com a semana anterior:

| Fator | Peso |
|---|---|
| Queda de atendimentos | 40 pts |
| Queda de vendas | 30 pts |
| Queda de receita | 20 pts |
| Taxa de finalização baixa | 10 pts |

**Níveis de alerta:** 🟢 Verde (0–19) · 🟡 Amarelo (20–49) · 🔴 Vermelho (50+)

---

## Stack Tecnológica

| Camada | Tecnologia | Por quê |
|---|---|---|
| Coleta | Python + Playwright | Automação de browser, lida bem com SPAs |
| Banco de dados | PostgreSQL | Relações entre tabelas, histórico semanal |
| API | FastAPI | Endpoints JSON para o frontend |
| Agendamento (VPS) | Cron Job Linux | Nativo, zero dependência |
| Agendamento (local) | Windows Task Scheduler | Testes locais no Windows |
| Deploy | Docker + Docker Compose | Portável, fácil de subir na VPS |

---

## Estrutura do Projeto

```
AUTOMAÇÂO/
├── config/
│   └── farmacias.json          # credenciais das 70 farmácias (não commitar!)
├── farmacia_monitor/
│   ├── scraper/
│   │   └── pharmachatbot.py    # Playwright: login + filtro + extração
│   ├── database/
│   │   └── db.py               # modelos SQLAlchemy (PostgreSQL)
│   ├── processor/
│   │   └── score.py            # cálculo de score de criticidade
│   └── api/
│       └── main.py             # FastAPI: endpoints JSON para o frontend
├── sql/
│   └── init.sql                # schema, índices e views do banco
├── main.py                     # pipeline principal (scraper → banco)
├── testar_scraper.py           # script de teste com Chrome visível
├── Dockerfile                  # imagem Python + Playwright + Chromium
├── docker-compose.yml          # postgres + api + scraper
├── setup_vps.sh                # setup completo em uma VPS Linux
├── agendar_tarefa.ps1          # agendamento no Windows Task Scheduler
├── requirements.txt
└── .env.example
```

---

## Banco de Dados

### Tabelas

| Tabela | Descrição |
|---|---|
| `farmacias` | Cadastro das 70 farmácias |
| `coletas` | Métricas semanais + score por farmácia |
| `coleta_canais` | Breakdown de atendimentos por canal de divulgação |
| `coleta_conexoes` | Breakdown de atendimentos por conexão |

### Views prontas

- `vw_ranking_atual` — última coleta de cada farmácia com ranking por score
- `vw_evolucao_semanal` — últimas 8 semanas por farmácia (para gráfico de evolução)

---

## API REST (FastAPI)

| Endpoint | Descrição |
|---|---|
| `GET /api/painel` | KPIs gerais da semana (soma de todas as farmácias) |
| `GET /api/farmacias` | Lista de farmácias com status e métricas |
| `GET /api/farmacias/{id}/evolucao` | Histórico semanal de uma farmácia |
| `GET /api/relatorios` | Histórico de execuções semanais |
| `GET /api/relatorios/{data}/xlsx` | Download do relatório em Excel |
| `POST /api/rodar-agora` | Dispara o pipeline manualmente |
| `GET /api/status` | Verifica se o pipeline está rodando |

---

## Como Rodar Localmente

### Pré-requisitos
- Python 3.11+
- Docker Desktop

### 1. Instalar dependências

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Configurar variáveis de ambiente

```bash
copy .env.example .env
# edite o .env com as configurações do banco
```

### 3. Subir o banco de dados

```bash
docker-compose up postgres -d
```

### 4. Testar o scraper (uma farmácia, Chrome visível)

```bash
python testar_scraper.py
```

### 5. Rodar o pipeline completo

```bash
python main.py
```

### 6. Subir a API

```bash
uvicorn farmacia_monitor.api.main:app --reload
# Acesse: http://localhost:8000/docs
```

---

## Deploy na VPS (Linux)

```bash
# 1. Envie o projeto para a VPS
scp -r . root@IP_DA_VPS:/opt/pharmaflow

# 2. Acesse a VPS
ssh root@IP_DA_VPS

# 3. Execute o setup (apenas uma vez)
cd /opt/pharmaflow
bash setup_vps.sh
```

O script `setup_vps.sh` instala o Docker, sobe os containers e registra o cron job automaticamente.

### Verificar que está rodando

```bash
docker compose ps          # containers ativos
crontab -l                 # cron registrado
docker compose logs -f api # logs da API em tempo real
```

### Rodar manualmente fora do domingo

```bash
docker compose run --rm scraper
```

---

## Gerenciar as 70 Farmácias

As credenciais ficam no arquivo `config/farmacias.json`:

```json
[
  {
    "id": 1,
    "nome": "Nome da Farmácia",
    "url_base": "https://app13.pharmachatbot.com.br",
    "email": "email@farmacia.com",
    "senha": "senha",
    "ativa": true
  }
]
```

- `ativa: false` pausa a coleta daquela farmácia sem removê-la
- O arquivo **não deve ser commitado** no Git (está no `.dockerignore`)

---

## O que Está Fora do Escopo (versão atual)

- Envio de e-mail ou WhatsApp com o relatório
- Comparativo por região
- Módulo de metas e projeções
- Integração com CRM
- Tela de cadastro de farmácias pelo dashboard

---

## Status do Projeto

| Fase | Descrição | Status |
|---|---|---|
| Coleta | Playwright: login + filtro + extração dos 4 badges | ✅ Concluído e testado |
| Processamento | Score de criticidade vs semana anterior | ✅ Concluído |
| Banco de dados | PostgreSQL com schema, índices e views | ✅ Concluído |
| API | FastAPI com todos os endpoints + export XLSX | ✅ Concluído |
| Agendamento | Cron Linux (VPS) + Task Scheduler (Windows) | ✅ Concluído |
| Deploy | Docker Compose + script setup_vps.sh | ✅ Concluído |
| Frontend | PharmaFlow (sistema externo integrado via API) | ✅ Existente |
| Credenciais | Preenchimento do farmacias.json com as 70 farmácias | 🔲 Pendente |
