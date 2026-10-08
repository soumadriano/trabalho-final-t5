# Pipeline ETL — Viagens a Serviço (Portal da Transparência)

Projeto avaliativo do curso **Análise de Dados com Python** (SENAI / LAB365) — Módulo 1, Semana 13.
Um pipeline de dados em **Python + PostgreSQL** que baixa os dados abertos de *Viagens a Serviço* do Governo Federal, guarda o dado bruto sem alterar nada, limpa e organiza esse dado e responde perguntas de negócio com tabelas e gráficos.

## O problema que este projeto resolve

O Portal da Transparência publica os gastos com viagens a serviço, mas o dado chega **bruto**: quatro arquivos CSV grandes (quase 1,9 milhão de linhas), em texto com acentos em codificação antiga, com vírgula como separador decimal, datas escritas como `17/09/2024`, campos vazios e nomes de coluna com pequenos defeitos.
Para transformar isso em informação confiável, o projeto constrói o caminho completo: **extrair**, **guardar o original**, **limpar e tipar**, **agregar** e **responder perguntas**, de forma que possa ser executado quantas vezes for preciso sem duplicar nem quebrar nada.

## Técnicas e tecnologias

- **Python 3** com `pandas`, `psycopg2`, `requests` e `matplotlib`
- **PostgreSQL**: `CREATE TABLE` com `PRIMARY KEY`, `FOREIGN KEY`, `NOT NULL`, `CHECK` e `UNIQUE`; `JOIN`, `GROUP BY`, `HAVING`, `CREATE TABLE AS` e `CREATE VIEW`
- **Arquitetura Medallion** (Raw → Silver → Gold)
- Leitura de arquivos grandes **em blocos** (`chunksize`), carga com `execute_values`
- Carga **idempotente** (`TRUNCATE`) e **resiliente** (`try/except` + `rollback()`)
- Credenciais no arquivo `.env`, fora do código e fora do Git

```text
 CSV (Portal da Transparência)
        │  1_extrair.py    (download + leitura em blocos, cópia fiel)
        ▼
   RAW      raw_viagem · raw_pagamento · raw_passagem · raw_trecho     (tudo texto)
        │  2_transformar.py (texto → decimal/data, colunas calculadas, PK/FK/constraints)
        ▼
   SILVER   silver_viagem (mãe) ← silver_pagamento · silver_passagem · silver_trecho
        │  3_analise.ipynb  (JOIN + GROUP BY, tabelas e views, perguntas, gráficos)
        ▼
   GOLD     gold_pagamento_resumo · gold_trecho_resumo (+ views vw_gold_*)
```

## Estrutura do repositório

| Arquivo | O que faz |
|---|---|
| `0_criar_banco.sql` | Fase 0: cria o banco `transparencia` e as 8 tabelas (4 Raw + 4 Silver) |
| `1_extrair.py` | Fase 1: baixa o `.zip` do Drive, lê os 4 CSVs em blocos e carrega a camada Raw |
| `2_transformar.py` | Fase 2: converte os tipos, calcula colunas e carrega a camada Silver |
| `3_analise.ipynb` | Fase 3: cria a camada Gold, responde as 7 perguntas e desenha os gráficos |
| `config.py` / `banco.py` | parâmetros (lê o `.env`) e conexão com o PostgreSQL |
| `.env.example` | modelo das credenciais |
| `requirements.txt` | bibliotecas do projeto |
| `.gitignore` | mantém `.env`, `data/`, `*.zip` e `*.csv` fora do Git |
| `notebook_colab_aluno.ipynb` | roteiro para executar o projeto inteiro clicando célula por célula |

## Pré-requisitos

- **Python 3** e **VS Code** com a extensão Jupyter (o projeto **não roda no Google Colab**: precisa do PostgreSQL da sua máquina).
- **PostgreSQL** instalado e ligado, com a senha do usuário `postgres` (o mesmo das Semanas 08 a 12).
- Internet para o download dos dados (cerca de 70 MB).

## Como executar (jeito mais fácil: pelo notebook)

1. Baixe o repositório da turma (botão **Code → Download ZIP** no GitHub) e descompacte.
2. No VS Code: **File → Open Folder** → escolha a pasta `T5_Projeto_Final/Aluno`.
3. Abra `notebook_colab_aluno.ipynb`, clique em **Select Kernel** e escolha o Python 3 instalado.
4. No **Passo 2**, troque `SUA_SENHA_AQUI` pela sua senha do PostgreSQL.
5. Execute as células de cima para baixo (**Shift+Enter**). No Passo 6, abra o `3_analise.ipynb` e clique em **Run All**.

O pipeline inteiro leva cerca de 5 minutos.

## Como executar (pelo terminal, arquivo por arquivo)

1. **Ambiente:** `pip install -r requirements.txt`
2. **Credenciais:** copie `.env.example` para `.env` e preencha `POSTGRES_PASSWORD` com a sua senha do PostgreSQL.
3. **Dados:** o arquivo é o `viagens_2025_6meses.zip`, na pasta `data` do Drive do projeto (link no enunciado). O `DRIVE_FILE_ID` do `config.py` já está preenchido com o ID dele; o `1_extrair.py` baixa e descompacta os 4 CSVs em `data/` (cerca de 25 segundos). Se preferir, baixe o `.zip` pelo navegador e coloque os 4 CSVs em `data/`: o script não baixa de novo se eles já estiverem lá.
4. **Banco e tabelas:** o `0_criar_banco.sql` tem **duas partes**. Conectado no banco `postgres`, execute o `CREATE DATABASE`. Depois troque a conexão para o banco `transparencia` (por exemplo, na extensão PostgreSQL do VS Code) e execute o restante do arquivo.
5. **Pipeline:**

   ```bash
   python 1_extrair.py
   python 2_transformar.py
   ```

6. **Análise:** abra `3_analise.ipynb` no VS Code e execute todas as células.

Cada script pode ser executado **várias vezes**: as tabelas são esvaziadas antes de cada carga.

## Decisões de modelagem e de negócio

- **Raw** é uma cópia fiel do CSV: todas as colunas `VARCHAR`, sem restrições, na mesma ordem do arquivo. A carga é posicional (`INSERT INTO tabela VALUES ...`), o que evita problemas com nomes de coluna acentuados ou com espaço escondido (a primeira coluna do arquivo de trechos termina com um espaço).
- **Silver** tem chave primária, chave estrangeira e 2 restrições por tabela, todas dentro do `CREATE TABLE`. A `silver_viagem` (mãe) é carregada primeiro; a Silver é esvaziada com um único `TRUNCATE` que lista mãe e filhas.
- **Conversões** feitas por funções específicas, com Pandas: `texto_para_decimal` (`"1272,97"` → `1272.97`, com `pd.to_numeric`) e `texto_para_data` (`"17/09/2024"` → data, com `pd.to_datetime`). Campo vazio vira `NULL` no banco (por exemplo, as 664 passagens sem data de emissão).
- **`valor_total`** = diárias + passagens + outros gastos − devolução (o gasto líquido). O enunciado não define a fórmula; esta é a regra adotada pela turma.
- **`duracao_dias`** = `(data_fim − data_inicio) + 1`, contando o dia de início e o de fim.
- **Só viagens realizadas** (`situacao = 'Realizada'`) entram nas 7 perguntas.
- **Destinos:** a coluna é texto livre e pode repetir cidades; cada texto igual conta como um destino, e só entram destinos com **100 viagens ou mais**, para a média não ser enganosa.

## Resultado da execução

Todas as linhas dos CSVs chegaram à Raw e à Silver, e as conferências fecharam (executado duas vezes seguidas, sem duplicar):

| Tabela | Linhas no CSV | Raw | Silver |
|---|---:|---:|---:|
| viagem | 341.860 | 341.860 | 341.860 |
| pagamento | 606.916 | 606.916 | 606.916 |
| passagem | 167.260 | 167.260 | 167.260 |
| trecho | 763.349 | 763.349 | 763.349 |

- As 664 datas de emissão vazias da Raw viraram `NULL` na Silver.
- A soma dos pagamentos é idêntica na Raw e na Silver (R$ 1.194.365.457,37).
- Tempo neste computador: `1_extrair.py` ≈ 1 min 10 s; `2_transformar.py` ≈ 1 min 45 s.
- O `0_criar_banco.sql` também pode ser executado de novo depois da análise: ele apaga primeiro as views e tabelas Gold, que dependem das Silver.

## Perguntas de negócio: resultados e conclusões

| # | Pergunta | Resposta |
|---|---|---|
| 1 | 5 órgãos com maior custo total | Justiça e Segurança Pública (R$ 485,7 mi), Defesa (R$ 154,6 mi), Educação (R$ 109,8 mi), Meio Ambiente e Mudança do Clima (R$ 49,3 mi), Previdência Social (R$ 40,2 mi). Só o primeiro equivale a 1,4 vez os outros quatro somados |
| 2 | 3 destinos com maior custo médio por viagem | "Brasília/DF, Brasília/DF" (R$ 27.401,80 · 283 viagens), Genebra/Suíça (R$ 25.469,22 · 242), Nova York/EUA (R$ 21.214,19 · 149) |
| 3 | Viagem de maior duração e custo | viagem `0000000000020699856` (Ministério da Previdência Social): **384 dias** (13/01/2025 a 31/01/2026), custo registrado R$ 0,00 |
| 4 | Tipo de pagamento com maior valor médio | **Diárias**: R$ 2.078,79 por pagamento (passagem: R$ 1.882,32; seguro: R$ 447,26; restituição: R$ 245,70) |
| 5 | Meio de transporte mais usado nos trechos | **Veículo Oficial**: 385.734 trechos (51,0% do total), à frente do aéreo (226.707) |
| 6 | UF de destino em mais trechos | **São Paulo**: 81.727 trechos, seguido do Distrito Federal (77.962) |
| 7 | Órgão que pagou mais no total | **Fundo Nacional de Segurança Pública**: R$ 278,3 mi (o pagador "Sigiloso" vem em seguida, com R$ 199,3 mi) |

Os gráficos correspondentes estão no `3_analise.ipynb`, cada um com título, eixos nomeados e legenda.

## O que os dados mostram sobre a própria base

Três achados da camada Silver que ajudam a ler as respostas com cuidado:

- **18.545 viagens realizadas têm custo total R$ 0,00**, inclusive a viagem mais longa (Pergunta 3). São viagens sem diárias, passagens nem outros gastos registrados neste arquivo (por exemplo, custeadas por outra fonte). O custo zero é o que a base informa, e não um erro da conversão.
- **13.774 viagens terminam depois de 30/06/2025.** O arquivo traz as viagens **iniciadas** de janeiro a junho de 2025; algumas duram meses e terminam no ano seguinte. Por isso existem durações acima de 180 dias.
- **3 viagens têm custo total negativo**, porque a devolução foi maior que a soma dos gastos registrados.

## Limitações e melhorias possíveis

- **Destinos:** separar as cidades da lista em `destinos` (uma linha por destino) para uma comparação mais justa.
- **Pagador "Sigiloso":** não identifica o órgão; a análise mantém a categoria como veio da fonte. O mesmo vale para o meio de transporte "Inválido".
- **Velocidade da carga:** trocar o `INSERT` em lote pelo comando `COPY` do PostgreSQL deixaria a Fase 1 ainda mais rápida.
- **Qualidade:** incluir testes automáticos das funções de conversão e mais validações Raw × Silver.
- **Automação:** agendar a execução do pipeline e incluir os meses seguintes do ano.

## Versionamento com Git: branches e commits

Este projeto de referência fica dentro do repositório da turma. No **seu** repositório, o critério 1 da rubrica (1,5 ponto) pede **uma branch por funcionalidade**, com nomes padronizados, e **commits separados**, com mensagens curtas no imperativo ("implementa X", "corrige Y"). Um fluxo que atende o critério, uma branch por fase do pipeline:

| Branch | O que entra nela | Exemplos de commit |
|---|---|---|
| `main` | estrutura inicial e cada fase já concluída (via merge) | `cria estrutura do projeto e .gitignore` |
| `feature/fase0-banco` | `0_criar_banco.sql` | `cria tabelas raw` · `cria tabelas silver com PK, FK e constraints` |
| `feature/fase1-extracao` | `1_extrair.py` | `implementa download do zip` · `implementa carga raw em blocos com TRUNCATE` |
| `feature/fase2-transformacao` | `2_transformar.py` | `implementa conversão de decimais e datas` · `calcula valor_total e duracao_dias` |
| `feature/fase3-analise` | `3_analise.ipynb` | `cria camada gold com JOIN e GROUP BY` · `responde perguntas 1 a 7 com gráficos` |
| `docs/readme` | `README.md` | `documenta execução, decisões e conclusões` |

Os comandos para cada funcionalidade:

```bash
git checkout -b feature/fase1-extracao   # cria a branch e entra nela
git add 1_extrair.py
git commit -m "implementa download do zip"
git push -u origin feature/fase1-extracao
git checkout main
git merge feature/fase1-extracao          # leva a fase pronta para a main
git push
```

Nunca faça commit do `.env` (a senha) nem da pasta `data/`: o `.gitignore` já impede os dois.

## Rubrica: onde cada critério é atendido

| Critério | Pontos | Onde está |
|---|---:|---|
| 1. Versionamento com branches e commits | 1,5 | no seu repositório, seguindo a seção anterior |
| 2. Organização dos arquivos (`.sql`, `.py` e `README.md`) | 1,0 | arquivos numerados pela ordem de execução (seção "Estrutura do repositório") |
| 3. Extração e camada Raw: download + carga, `try/except`, sem duplicar em reexecuções | 0,5 | `1_extrair.py` (`requests`, `TRUNCATE`, `try/except` + `rollback()`) |
| 4. Tipagem e limpeza: todos os campos convertidos | 1,0 | `2_transformar.py` (`texto_para_decimal`, `texto_para_data`, inteiros) + conferência Raw × Silver |
| 5. Camada Gold com `JOIN` + `GROUP BY` (tabela e view) | 1,0 | `3_analise.ipynb`, Parte B (`gold_*` e `vw_gold_*`) |
| 6. Perguntas de negócio respondidas com evidências | 1,5 | `3_analise.ipynb` (7 perguntas: consulta, tabela, gráfico e conclusão) e seção "Perguntas de negócio" acima |
| 7. Gráficos com título, eixos nomeados e legenda | 1,5 | os 7 gráficos do `3_analise.ipynb` |
| 8. Modelagem Silver: PK, FK e constraints | 2,0 | `0_criar_banco.sql` (4 PK, 3 FK e as 8 constraints do enunciado, dentro do `CREATE TABLE`) |

---
*Projeto de referência do curso Análise de Dados com Python — Prof. Especialista Cláudio F. Neves*
# trabalho-final-t5
