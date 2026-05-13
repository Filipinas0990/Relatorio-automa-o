"""
Cria o primeiro gestor administrador no banco de dados.
Execute UMA ÚNICA VEZ após o deploy inicial.

    python criar_admin.py

Pré-requisito: DATABASE_URL definido no .env
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from farmacia_monitor.database.db import init_db, SessionLocal, GestorTrafego
import bcrypt as _bcrypt


def criar_admin():
    init_db()
    db = SessionLocal()
    try:
        total = db.query(GestorTrafego).count()
        if total > 0:
            print(f"Ja existem {total} gestor(es) cadastrados.")
            print("Use a API (POST /api/gestores) para criar novos gestores.")
            return

        print("=== Criar primeiro Administrador ===\n")
        nome  = input("Nome completo: ").strip()
        email = input("Email de login: ").strip()
        senha = input("Senha: ").strip()

        if not nome or not email or not senha:
            print("ERRO: Todos os campos sao obrigatorios.")
            sys.exit(1)

        admin = GestorTrafego(
            nome=nome,
            email=email,
            senha_hash=_bcrypt.hashpw(senha.encode(), _bcrypt.gensalt()).decode(),
            is_admin=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        print(f"\nAdministrador criado com sucesso!")
        print(f"  ID:    {admin.id}")
        print(f"  Nome:  {admin.nome}")
        print(f"  Email: {admin.email}")
        print(f"\nUse estas credenciais para fazer login no PharmaFlow.")

    finally:
        db.close()


if __name__ == "__main__":
    criar_admin()
