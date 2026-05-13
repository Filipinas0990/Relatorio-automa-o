"""
Gera a FARMACIAS_KEY e adiciona ao .env automaticamente.
Execute UMA ÚNICA VEZ na configuração inicial.

    python gerar_chave.py
"""

import os
from pathlib import Path
from farmacia_monitor.cripto import gerar_chave

chave    = gerar_chave()
env_path = Path(".env")

# Lê .env atual ou cria novo
conteudo = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

if "FARMACIAS_KEY" in conteudo:
    print("AVISO: FARMACIAS_KEY ja existe no .env — nao sobrescrevendo.")
    print("Para gerar nova chave, remova a linha FARMACIAS_KEY do .env primeiro.")
else:
    with open(env_path, "a", encoding="utf-8") as f:
        f.write(f"\nFARMACIAS_KEY={chave}\n")
    print("Chave gerada e salva no .env!")
    print(f"  FARMACIAS_KEY={chave[:20]}...  (guarde uma cópia segura)")

print("\nProximos passos:")
print("  1. python criptografar.py   (gera farmacias.enc)")
print("  2. Envie farmacias.enc para o servidor")
print("  3. No servidor, adicione FARMACIAS_KEY ao .env")
