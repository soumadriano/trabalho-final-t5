"""
banco.py
--------
"""

import psycopg2
from psycopg2 import Error

from config import POSTGRES_CONFIG


def conectar():
    """
    Abre uma conexao com o PostgreSQL (no database configurado no .env) e a
    retorna. Em caso de falha, lanca um erro claro (tratado por quem chama).
    """
    try:
        return psycopg2.connect(**POSTGRES_CONFIG)
    except (Error, UnicodeDecodeError) as erro:
        # Num PostgreSQL instalado em português, a mensagem de erro do servidor tem
        # acento ("autenticação", "não existe") e o psycopg2 falha ao lê-la com um
        # UnicodeDecodeError. Por isso capturamos os dois tipos de erro aqui.
        raise RuntimeError(
            f"Nao foi possivel conectar ao PostgreSQL em "
            f"{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']} / database "
            f"'{POSTGRES_CONFIG['dbname']}'. Verifique o .env e se voce ja rodou "
            f"o script '0_criar_banco.sql'. Detalhe: {erro}"
        )


def executar(conexao, sql):
    """Executa um comando SQL simples (CREATE, DROP, INSERT...SELECT, etc.)."""
    cursor = conexao.cursor()
    cursor.execute(sql)
    conexao.commit()
    cursor.close()


def inserir_em_lote(conexao, sql_insert, linhas):
    """
    Insere varias linhas de uma vez (mais rapido que uma a uma).
    'linhas' e uma lista de tuplas; 'sql_insert' usa %s nos valores.
    """
    if not linhas:
        return
    cursor = conexao.cursor()
    cursor.executemany(sql_insert, linhas)
    conexao.commit()
    cursor.close()
