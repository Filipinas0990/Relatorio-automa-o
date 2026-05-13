"""
Funções de criptografia para proteger as credenciais das farmácias.
Usa Fernet (AES-128 + HMAC-SHA256) — simétrico, chave no .env.
"""

import json
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken


def gerar_chave() -> str:
    """Gera uma nova chave aleatória. Use apenas uma vez."""
    return Fernet.generate_key().decode()


def _fernet() -> Fernet:
    chave = os.getenv("FARMACIAS_KEY", "").strip()
    if not chave:
        raise RuntimeError(
            "Variavel FARMACIAS_KEY nao encontrada no .env\n"
            "Execute: python gerar_chave.py"
        )
    return Fernet(chave.encode())


def criptografar_arquivo(json_path: str, enc_path: str):
    """Lê farmacias.json e salva farmacias.enc criptografado."""
    texto = Path(json_path).read_text(encoding="utf-8")
    enc   = _fernet().encrypt(texto.encode("utf-8"))
    Path(enc_path).write_bytes(enc)
    print(f"Criptografado: {enc_path}")


def decriptografar_arquivo(enc_path: str) -> list[dict]:
    """Lê farmacias.enc e devolve a lista de farmácias."""
    try:
        enc  = Path(enc_path).read_bytes()
        texto = _fernet().decrypt(enc).decode("utf-8")
        return json.loads(texto)
    except InvalidToken:
        raise RuntimeError("Chave incorreta ou arquivo corrompido.")
    except FileNotFoundError:
        raise RuntimeError(
            f"Arquivo {enc_path} nao encontrado.\n"
            "Execute: python criptografar.py"
        )


def carregar_farmacias(base_dir: str) -> list[dict]:
    """
    Carrega farmácias priorizando o arquivo criptografado (.enc).
    Fallback para .json apenas em desenvolvimento local.
    """
    enc_path  = os.path.join(base_dir, "config", "farmacias.enc")
    json_path = os.path.join(base_dir, "config", "farmacias.json")

    if os.path.exists(enc_path):
        todas = decriptografar_arquivo(enc_path)
    elif os.path.exists(json_path):
        # Avisa que está rodando sem criptografia
        print("[AVISO] Usando farmacias.json sem criptografia.")
        with open(json_path, encoding="utf-8") as f:
            todas = json.load(f)
    else:
        raise RuntimeError("Nenhum arquivo de farmácias encontrado.")

    return [fa for fa in todas if fa.get("ativa", True)]
