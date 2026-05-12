#!/bin/bash
# =============================================================
# PharmaFlow — Setup completo para VPS Linux (Ubuntu/Debian)
# Execute UMA VEZ na VPS:  bash setup_vps.sh
# =============================================================

set -e  # Para em qualquer erro

VERDE="\e[32m"
AMARELO="\e[33m"
AZUL="\e[34m"
RESET="\e[0m"

ok()   { echo -e "${VERDE}[OK]${RESET} $1"; }
info() { echo -e "${AZUL}[..] $1${RESET}"; }
warn() { echo -e "${AMARELO}[!!] $1${RESET}"; }

echo ""
echo "======================================================"
echo "   PharmaFlow — Setup VPS"
echo "======================================================"
echo ""

# ── 1. Verifica root ──────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
  echo "Execute como root: sudo bash setup_vps.sh"
  exit 1
fi
ok "Rodando como root"

# ── 2. Atualiza sistema ───────────────────────────────────
info "Atualizando pacotes do sistema..."
apt-get update -qq
apt-get upgrade -y -qq
ok "Sistema atualizado"

# ── 3. Instala dependências base ──────────────────────────
info "Instalando dependências base..."
apt-get install -y -qq \
    curl wget git ca-certificates gnupg lsb-release cron
ok "Dependências instaladas"

# ── 4. Instala Docker ─────────────────────────────────────
if command -v docker &>/dev/null; then
    warn "Docker já instalado: $(docker --version)"
else
    info "Instalando Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
      > /etc/apt/sources.list.d/docker.list

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    ok "Docker instalado: $(docker --version)"
fi

# ── 5. Localiza pasta do projeto ──────────────────────────
PROJETO_DIR="$(cd "$(dirname "$0")" && pwd)"
info "Pasta do projeto: $PROJETO_DIR"

# ── 6. Cria .env se não existir ───────────────────────────
if [ ! -f "$PROJETO_DIR/.env" ]; then
    warn ".env não encontrado — criando a partir do .env.example"
    cp "$PROJETO_DIR/.env.example" "$PROJETO_DIR/.env"

    # Gera senha aleatória segura para o banco
    SENHA_DB=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
    sed -i "s/farmacia123/$SENHA_DB/g" "$PROJETO_DIR/.env"

    echo ""
    warn "ATENÇÃO: edite o arquivo .env com suas configurações:"
    warn "  nano $PROJETO_DIR/.env"
    echo ""
    read -p "Pressione Enter após editar o .env (ou Enter para continuar com os padrões)..."
fi
ok ".env pronto"

# ── 7. Cria pasta de logs ─────────────────────────────────
mkdir -p "$PROJETO_DIR/logs"
ok "Pasta de logs criada"

# ── 8. Build e sobe postgres + api ────────────────────────
info "Fazendo build das imagens Docker..."
cd "$PROJETO_DIR"
docker compose build --quiet
ok "Build concluído"

info "Subindo PostgreSQL e API..."
docker compose up -d postgres api
ok "Containers rodando"

# Aguarda banco ficar saudável
info "Aguardando PostgreSQL ficar pronto..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U farmacia -q 2>/dev/null; then
        ok "PostgreSQL pronto"
        break
    fi
    sleep 2
done

# ── 9. Registra cron job ──────────────────────────────────
info "Configurando cron job (todo domingo às 22:00)..."

CRON_CMD="cd $PROJETO_DIR && docker compose run --rm scraper >> $PROJETO_DIR/logs/pipeline.log 2>&1"
CRON_LINE="0 22 * * 0 $CRON_CMD"

# Remove linha antiga se existir e adiciona nova
(crontab -l 2>/dev/null | grep -v "PharmaFlow\|farmacia_monitor\|docker compose run --rm scraper"; \
 echo "# PharmaFlow — coleta semanal domingo 22h"; \
 echo "$CRON_LINE") | crontab -

ok "Cron job registrado"

# ── 10. Verifica tudo ─────────────────────────────────────
echo ""
echo "======================================================"
echo "   Status final"
echo "======================================================"
docker compose ps
echo ""
echo "Cron jobs ativos:"
crontab -l | grep -A1 "PharmaFlow"
echo ""

# ── 11. Resumo ────────────────────────────────────────────
echo -e "${VERDE}"
echo "======================================================"
echo "   Setup concluído com sucesso!"
echo "======================================================"
echo -e "${RESET}"
echo "  Banco de dados : PostgreSQL rodando no container"
echo "  API            : http://$(curl -s ifconfig.me 2>/dev/null || echo 'IP_DA_VPS'):8000"
echo "  Cron           : Todo domingo às 22:00 (horário da VPS)"
echo "  Logs           : $PROJETO_DIR/logs/pipeline.log"
echo ""
echo "  Comandos úteis:"
echo "    Ver containers   →  docker compose ps"
echo "    Ver logs da API  →  docker compose logs -f api"
echo "    Rodar agora      →  docker compose run --rm scraper"
echo "    Ver cron         →  crontab -l"
echo ""
echo "  IMPORTANTE: verifique o fuso horário da VPS:"
echo "    timedatectl"
echo "    sudo timedatectl set-timezone America/Sao_Paulo"
echo ""
