"""
1_extrair.py  |  Fase 1: extração e camada Raw

O que este script faz:
  1. Baixa o .zip de Viagens a Serviço do Google Drive e descompacta os 4 CSVs
     na pasta data/ (se os CSVs já estiverem lá, não baixa de novo).
  2. Lê cada CSV em BLOCOS (não carrega o arquivo inteiro na memória).
  3. Grava tudo, sem alterar nada, nas tabelas Raw (todas as colunas são texto).

Pode ser executado várias vezes: cada tabela é esvaziada com TRUNCATE antes da
carga, então rodar de novo nunca duplica registros. Se algo falhar no meio de
uma tabela, o rollback() desfaz o que ainda não foi confirmado.

Como executar:  python 1_extrair.py
"""

import os
import zipfile

import pandas as pd
import requests
from psycopg2.extras import execute_values

from banco import conectar
from config import (
    ARQUIVOS,
    CSV_ENCODING,
    CSV_SEPARADOR,
    DRIVE_FILE_ID,
    PASTA_DADOS,
    TAMANHO_BLOCO,
)


def baixar_dados():
    """Baixa o .zip do Drive e descompacta os CSVs em data/ (só se ainda não existirem)."""
    nomes = [dados["csv"] for dados in ARQUIVOS.values()]
    if all((PASTA_DADOS / nome).exists() for nome in nomes):
        print("Os 4 CSVs já estão em data/. Não é preciso baixar de novo.")
        return

    if DRIVE_FILE_ID.startswith("COLE_AQUI"):
        raise RuntimeError("Cole o ID do arquivo do Drive na variável DRIVE_FILE_ID do config.py.")

    PASTA_DADOS.mkdir(exist_ok=True)
    caminho_zip = PASTA_DADOS / "viagens.zip"
    url = f"https://drive.usercontent.google.com/download?id={DRIVE_FILE_ID}&export=download&confirm=t"

    print("Baixando o zip do Google Drive...")
    resposta = requests.get(url, stream=True, timeout=60)
    resposta.raise_for_status()
    with open(caminho_zip, "wb") as arquivo:
        for pedaco in resposta.iter_content(chunk_size=1024 * 1024):
            arquivo.write(pedaco)

    if not zipfile.is_zipfile(caminho_zip):
        raise RuntimeError(
            "O arquivo baixado não é um .zip. Confira se o link do Drive está compartilhado "
            "como 'Qualquer pessoa com o link'."
        )

    with zipfile.ZipFile(caminho_zip) as pacote:
        pacote.extractall(PASTA_DADOS)

    # Se o zip trouxe uma subpasta, traz os CSVs para dentro de data/
    for pasta, _, arquivos in os.walk(PASTA_DADOS):
        for nome in arquivos:
            if nome.endswith(".csv") and pasta != str(PASTA_DADOS):
                os.replace(os.path.join(pasta, nome), PASTA_DADOS / nome)

    print("CSVs prontos em data/.")


def carregar_raw(conexao, nome_csv, tabela):
    """Esvazia a tabela Raw e carrega o CSV em blocos, sem converter nenhum valor."""
    cursor = conexao.cursor()
    cursor.execute(f"TRUNCATE {tabela}")  # idempotência: rodar de novo não duplica

    total = 0
    blocos = pd.read_csv(
        PASTA_DADOS / nome_csv,
        sep=CSV_SEPARADOR,
        encoding=CSV_ENCODING,
        dtype=str,              # tudo como texto: a Raw é uma cópia fiel
        keep_default_na=False,  # campo vazio continua vazio (não vira NaN)
        chunksize=TAMANHO_BLOCO,
    )
    for bloco in blocos:
        linhas = list(bloco.itertuples(index=False, name=None))
        execute_values(cursor, f"INSERT INTO {tabela} VALUES %s", linhas)
        total += len(linhas)
        print(f"   {total} linhas carregadas")

    return total


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------
dados_prontos = False
try:
    baixar_dados()
    dados_prontos = True
except Exception as erro:
    print(f"ERRO ao obter os dados: {type(erro).__name__}: {erro}")

if dados_prontos:
    conexao = None
    try:
        conexao = conectar()
        resumo = []
        for dados in ARQUIVOS.values():
            nome_csv = dados["csv"]
            tabela = dados["tabela_raw"]
            print(f"\nCarregando {nome_csv} em {tabela}...")
            total_csv = carregar_raw(conexao, nome_csv, tabela)
            conexao.commit()

            cursor = conexao.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
            total_tabela = cursor.fetchone()[0]
            resumo.append((tabela, total_csv, total_tabela))

        print("\nConferência (linhas lidas do CSV x linhas na tabela Raw):")
        for tabela, total_csv, total_tabela in resumo:
            situacao = "OK" if total_csv == total_tabela else "DIFERENTE!"
            print(f"   {tabela:<15} {total_csv:>9} x {total_tabela:>9}  {situacao}")
    except Exception as erro:
        if conexao:
            conexao.rollback()  # desfaz a tabela que estava sendo carregada
        print(f"\nERRO na carga da camada Raw: {type(erro).__name__}: {erro}")
    finally:
        if conexao:
            conexao.close()
