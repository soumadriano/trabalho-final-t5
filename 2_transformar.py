"""
2_transformar.py  |  Fase 2: transformação (Raw -> Silver)

O que este script faz:
  1. Lê cada tabela Raw (tudo texto) em blocos, com pd.read_sql.
  2. Converte os campos com funções específicas:
       texto_para_decimal:  "1272,97"    -> 1272.97
       texto_para_data:     "17/09/2024" -> data 2024-09-17
     Campo vazio vira NaN/NaT no Pandas e é gravado como NULL no banco.
  3. Calcula duas colunas novas em silver_viagem:
       valor_total  = diárias + passagens + outros gastos - devolução
       duracao_dias = (data_fim - data_inicio) + 1   (conta o dia de início e o de fim)
  4. Grava nas tabelas Silver. A silver_viagem (mãe) é carregada PRIMEIRO, porque
     as outras três têm FOREIGN KEY apontando para ela.

Pode ser executado várias vezes: as tabelas Silver são esvaziadas antes da carga.
Tudo é confirmado de uma vez só (commit no fim); se algo falhar, o rollback()
desfaz tudo e as tabelas Silver ficam como estavam.

Como executar:  python 2_transformar.py   (depois do 1_extrair.py)
"""

import warnings

import pandas as pd
from psycopg2.extras import execute_values

from banco import conectar
from config import TAMANHO_BLOCO

# O Pandas avisa que prefere a biblioteca SQLAlchemy, mas funciona com psycopg2.
warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")


# ---------------------------------------------------------------------------
# Funções de conversão (recebem uma coluna inteira do DataFrame)
# ---------------------------------------------------------------------------
def limpar_texto(coluna):
    """Tira os espaços das pontas. Texto vazio vira NaN (NULL no banco)."""
    coluna = coluna.str.strip()
    return coluna.where(coluna != "")


def texto_para_decimal(coluna):
    """'1272,97' -> 1272.97. No CSV o decimal é a vírgula. Texto vazio vira NaN."""
    coluna = coluna.str.strip().str.replace(",", ".")
    return pd.to_numeric(coluna, errors="coerce")


def texto_para_data(coluna):
    """'17/09/2024' -> data. O format diz que vem dia/mês/ano. Texto vazio vira NaT."""
    return pd.to_datetime(coluna.str.strip(), format="%d/%m/%Y", errors="coerce")


# ---------------------------------------------------------------------------
# O que cada tabela lê da Raw e como cada coluna é convertida.
# A ORDEM importa: silver_viagem (mãe) primeiro, as filhas depois.
# ---------------------------------------------------------------------------
TABELAS = [
    {
        "raw": "raw_viagem",
        "silver": "silver_viagem",
        "textos": ["id_viagem", "num_proposta", "situacao", "viagem_urgente", "cod_orgao_superior",
                   "nome_orgao_superior", "nome_viajante", "cargo", "destinos", "motivo"],
        "valores": ["valor_diarias", "valor_passagens", "valor_devolucao", "valor_outros_gastos"],
        "datas": ["data_inicio", "data_fim"],
        "inteiros": [],
    },
    {
        "raw": "raw_pagamento",
        "silver": "silver_pagamento",
        "textos": ["id_viagem", "num_proposta", "nome_orgao_pagador", "nome_ug_pagadora", "tipo_pagamento"],
        "valores": ["valor"],
        "datas": [],
        "inteiros": [],
    },
    {
        "raw": "raw_passagem",
        "silver": "silver_passagem",
        "textos": ["id_viagem", "meio_transporte", "pais_origem_ida", "uf_origem_ida", "cidade_origem_ida",
                   "pais_destino_ida", "uf_destino_ida", "cidade_destino_ida"],
        "valores": ["valor_passagem", "taxa_servico"],
        "datas": ["data_emissao"],
        "inteiros": [],
    },
    {
        "raw": "raw_trecho",
        "silver": "silver_trecho",
        "textos": ["id_viagem", "origem_uf", "origem_cidade", "destino_uf", "destino_cidade", "meio_transporte"],
        "valores": ["numero_diarias"],
        "datas": ["origem_data", "destino_data"],
        "inteiros": ["sequencia_trecho"],
    },
]


def transformar(bloco, tabela):
    """Converte um bloco da Raw. Na viagem, também calcula valor_total e duracao_dias."""
    for coluna in tabela["textos"]:
        bloco[coluna] = limpar_texto(bloco[coluna])
    for coluna in tabela["valores"]:
        bloco[coluna] = texto_para_decimal(bloco[coluna])
    for coluna in tabela["datas"]:
        bloco[coluna] = texto_para_data(bloco[coluna])
    for coluna in tabela["inteiros"]:
        bloco[coluna] = pd.to_numeric(bloco[coluna], errors="coerce")

    if tabela["silver"] == "silver_viagem":
        bloco["valor_total"] = (
            bloco["valor_diarias"].fillna(0)
            + bloco["valor_passagens"].fillna(0)
            + bloco["valor_outros_gastos"].fillna(0)
            - bloco["valor_devolucao"].fillna(0)
        ).round(2)
        bloco["duracao_dias"] = (bloco["data_fim"] - bloco["data_inicio"]).dt.days + 1

    # NaN e NaT não são aceitos pelo banco: trocamos por None, que vira NULL
    return bloco.astype(object).where(pd.notna(bloco), None)


def carregar_silver(conexao, tabela):
    """Lê a Raw em blocos, transforma e grava na Silver. Devolve quantas linhas gravou."""
    colunas = tabela["textos"] + tabela["valores"] + tabela["datas"] + tabela["inteiros"]
    blocos = pd.read_sql(
        f"SELECT {', '.join(colunas)} FROM {tabela['raw']}", conexao, chunksize=TAMANHO_BLOCO
    )
    cursor = conexao.cursor()
    total = 0
    for bloco in blocos:
        bloco = transformar(bloco, tabela)
        linhas = list(bloco.itertuples(index=False, name=None))
        execute_values(
            cursor,
            f"INSERT INTO {tabela['silver']} ({', '.join(bloco.columns)}) VALUES %s",
            linhas,
        )
        total += len(linhas)
        print(f"   {total} linhas gravadas")
    return total


def conferir(conexao):
    """Compara Raw x Silver: mesma quantidade de linhas, mesmos vazios e mesma soma de valores."""
    cursor = conexao.cursor()

    def um_valor(sql):
        cursor.execute(sql)
        return cursor.fetchone()[0]

    conferencias = []
    for tabela in TABELAS:
        conferencias.append((
            f"linhas {tabela['raw']} x {tabela['silver']}",
            um_valor(f"SELECT COUNT(*) FROM {tabela['raw']}"),
            um_valor(f"SELECT COUNT(*) FROM {tabela['silver']}"),
        ))
    conferencias.append((
        "datas de emissão vazias (Raw) x NULL (Silver)",
        um_valor("SELECT COUNT(*) FROM raw_passagem WHERE data_emissao = ''"),
        um_valor("SELECT COUNT(*) FROM silver_passagem WHERE data_emissao IS NULL"),
    ))
    conferencias.append((
        "soma dos pagamentos Raw x Silver",
        um_valor("SELECT SUM(REPLACE(NULLIF(valor, ''), ',', '.')::NUMERIC) FROM raw_pagamento"),
        um_valor("SELECT SUM(valor) FROM silver_pagamento"),
    ))

    print("\nConferência Raw x Silver:")
    for descricao, origem, destino in conferencias:
        situacao = "OK" if origem == destino else "DIFERENTE!"
        print(f"   {descricao:<48} {origem} x {destino}  {situacao}")


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------
conexao = None
try:
    conexao = conectar()
    cursor = conexao.cursor()

    # Esvazia a Silver: mãe e filhas no MESMO comando (exigência da FOREIGN KEY)
    cursor.execute(
        "TRUNCATE silver_pagamento, silver_passagem, silver_trecho, silver_viagem RESTART IDENTITY"
    )

    for tabela in TABELAS:
        print(f"\nTransformando {tabela['raw']} -> {tabela['silver']}...")
        carregar_silver(conexao, tabela)

    conexao.commit()
    conferir(conexao)
except Exception as erro:
    if conexao:
        conexao.rollback()
    print(f"\nERRO na transformação: {type(erro).__name__}: {erro}")
finally:
    if conexao:
        conexao.close()
