"""
Criptografa farmacias.json → farmacias.enc

Execute sempre que editar o farmacias.json:
    python criptografar.py

Pré-requisito: FARMACIAS_KEY definida no .env
"""

import os
from dotenv import load_dotenv
from farmacia_monitor.cripto import criptografar_arquivo

load_dotenv()

BASE     = os.path.dirname(__file__)
JSON_IN  = os.path.join(BASE, "config", "farmacias.json")
ENC_OUT  = os.path.join(BASE, "config", "farmacias.enc")

if not os.getenv("FARMACIAS_KEY"):
    print("ERRO: FARMACIAS_KEY nao encontrada no .env")
    print("Execute primeiro: python gerar_chave.py")
    exit(1)

criptografar_arquivo(JSON_IN, ENC_OUT)
print("Pronto! Envie o farmacias.enc para o servidor.")
print("NUNCA envie o farmacias.json.")
