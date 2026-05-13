"""
Migra as farmácias do farmacias.enc para o banco de dados PostgreSQL.
Execute UMA ÚNICA VEZ após o deploy da versão 2.

    python migrar_farmacias.py

Pré-requisito: DATABASE_URL e FARMACIAS_KEY definidos no .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

from farmacia_monitor.cripto import carregar_farmacias as _carregar_enc, _fernet
from farmacia_monitor.database.db import init_db, SessionLocal, Farmacia


def migrar():
    init_db()

    print("Lendo farmacias.enc...")
    farmacias_enc = _carregar_enc(os.path.dirname(__file__))
    print(f"  {len(farmacias_enc)} farmacias encontradas no arquivo")

    db = SessionLocal()
    try:
        migradas  = 0
        atualizadas = 0
        ignoradas = 0

        for f in farmacias_enc:
            nome = f.get("nome", "").strip()
            if not nome:
                continue

            existente = db.query(Farmacia).filter(Farmacia.nome == nome).first()

            senha_raw = f.get("senha", "")
            senha_enc = _fernet().encrypt(senha_raw.encode()).decode() if senha_raw else None

            if not existente:
                db.add(Farmacia(
                    nome=nome,
                    url_base=f.get("url", f.get("url_base", "")),
                    email=f.get("email", ""),
                    senha_enc=senha_enc,
                    ativa=f.get("ativa", True),
                ))
                migradas += 1
            elif not existente.senha_enc and senha_enc:
                existente.senha_enc = senha_enc
                if not existente.url_base:
                    existente.url_base = f.get("url", f.get("url_base", ""))
                atualizadas += 1
            else:
                ignoradas += 1

        db.commit()
        print(f"\nResultado:")
        print(f"  Migradas (novas):    {migradas}")
        print(f"  Atualizadas (senha): {atualizadas}")
        print(f"  Ja existiam:         {ignoradas}")
        print(f"\nMigracao concluida!")

    finally:
        db.close()


if __name__ == "__main__":
    migrar()
