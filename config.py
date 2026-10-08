"""
config.py
---------
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos do projeto
# ---------------------------------------------------------------------------
# PASTA_RAIZ = a pasta do projeto (onde está este arquivo)
PASTA_RAIZ = Path(__file__).resolve().parent
# onde o .zip e os .csv ficam (ignorada pelo Git)
PASTA_DADOS = PASTA_RAIZ / "data"


# ---------------------------------------------------------------------------
# Leitura simples do arquivo .env (sem biblioteca externa)
# ---------------------------------------------------------------------------
def carregar_env():
    """Le o arquivo .env (se existir) e joga as variaveis para os.environ."""
    arquivo_env = PASTA_RAIZ / ".env"
    if not arquivo_env.exists():
        return
    for linha in arquivo_env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        # ignora linhas vazias e comentarios
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())


carregar_env()


# ---------------------------------------------------------------------------
# Credenciais do PostgreSQL (vem do .env)
# ---------------------------------------------------------------------------
POSTGRES_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "123456"),
    "dbname": os.environ.get("POSTGRES_DATABASE", "transparencia"),
}


# ---------------------------------------------------------------------------
# O que vamos baixar e processar
# ---------------------------------------------------------------------------
ANO = "2025"

# ---- De onde baixar o .zip ----
# O arquivo (enxuto, so com jan-jun de 2025) fica no Google Drive da escola.
# ID do arquivo no Google Drive:
# Como obter: no Drive clique em "Compartilhar" -> "Qualquer pessoa com o link";
# o link fica .../file/d/ESTE_TRECHO_E_O_ID/view -> copie o ID e cole abaixo.
DRIVE_FILE_ID = "1R6re1574aCeqNfwJXQ_T7BwHCEsPfgvc"  # viagens_2025_6meses.zip, pasta data do Drive do projeto

# Tamanho do bloco de leitura/insercao (numero de linhas por vez).
# Ler tudo de uma vez estouraria a memoria; por isso lemos em "pedacos".
TAMANHO_BLOCO = 50_000


# ---------------------------------------------------------------------------
# Mapeamento: cada arquivo CSV dentro do .zip -> tabela RAW correspondente
# (o nome do CSV usa o ANO como prefixo, ex.: 2025_Viagem.csv)
# ---------------------------------------------------------------------------
ARQUIVOS = {
    "viagem":     {"csv": f"{ANO}_Viagem.csv",     "tabela_raw": "raw_viagem"},
    "pagamento":  {"csv": f"{ANO}_Pagamento.csv",  "tabela_raw": "raw_pagamento"},
    "passagem":   {"csv": f"{ANO}_Passagem.csv",   "tabela_raw": "raw_passagem"},
    "trecho":     {"csv": f"{ANO}_Trecho.csv",     "tabela_raw": "raw_trecho"},
}

# Caracteristicas dos arquivos CSV do Portal da Transparencia:
CSV_SEPARADOR = ";"
CSV_ENCODING = "latin-1"   # acentuacao no padrao ISO-8859-1
