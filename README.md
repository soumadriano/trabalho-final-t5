# Pipeline ETL — Viagens a Serviço (Portal da Transparência)

Projeto do Módulo 1 (Semana 13) do curso **Análise de Dados com Python — SENAI / LAB365**.
Um pipeline completo em **Python + PostgreSQL** que baixa dados abertos de *Viagens a Serviço* do Governo Federal, preserva o dado bruto, limpa e tipa, agrega e responde perguntas de negócio com tabelas e gráficos.

Autor: {{ Adriano da Conceição Santos }}
Repositório: {{ https://github.com/soumadriano/trabalho-final-t5 }}

---

## 1. O problema que este projeto resolve

O Portal da Transparência publica os gastos com viagens a serviço em arquivos CSV grandes e sem tratamento. Os arquivos têm cerca de 1,9 milhão de linhas no total e chegam com vírgula como separador decimal, datas no formato `DD/MM/AAAA`, acentuação em codificação antiga (latin-1), campos vazios e nomes de coluna com pequenos defeitos (por exemplo, espaço escondido no fim do primeiro nome).

Para que esse material vire informação útil para tomada de decisão, ele precisa passar por quatro etapas: **extrair**, **guardar o original sem alterar**, **limpar e tipar** e **agregar para responder perguntas**. Este projeto faz exatamente esse caminho, de forma que pode ser executado quantas vezes for preciso sem duplicar dados nem quebrar o banco.

---

## 2. Tecnologias e técnicas utilizadas

- **Linguagem:** Python 3
- **Banco de dados:** PostgreSQL
- **Bibliotecas:** `pandas`, `psycopg2-binary`, `requests`, `matplotlib`, `ipykernel`
- **Arquitetura:** Medallion (Raw → Silver → Gold)
- **Técnicas:**
  - Leitura de CSVs grandes em blocos (`chunksize`) para não estourar a memória
  - Carga idempotente (`TRUNCATE` antes de cada INSERT)
  - Carga resiliente (`try/except` + `rollback()`)
  - SQL com `JOIN`, `GROUP BY`, `HAVING`, `CREATE TABLE AS` e `CREATE VIEW`
  - Uso de `PRIMARY KEY`, `FOREIGN KEY`, `NOT NULL`, `CHECK` e `UNIQUE`
  - Credenciais em arquivo `.env`, fora do código e fora do Git

---

## 3. Arquitetura do pipeline

```
   CSV (Portal da Transparência)
          │
          │  1_extrair.py      →  download + leitura em blocos + cópia fiel
          ▼
   RAW   raw_viagem · raw_pagamento · raw_passagem · raw_trecho       (tudo texto)
          │
          │  2_transformar.py  →  conversão de tipos + colunas calculadas
          ▼
   SILVER silver_viagem (mãe)  ←  silver_pagamento · silver_passagem · silver_trecho
          │
          │  3_analise.ipynb   →  JOIN + GROUP BY + gráficos + respostas
          ▼
   GOLD   gold_pagamento_resumo · gold_trecho_resumo
          (+ views vw_gold_pagamento_resumo · vw_gold_trecho_resumo)
```

---

## 4. Estrutura do repositório

| Arquivo | Descrição |
|---|---|
| `0_criar_banco.sql` | Cria o banco `transparencia` e as 8 tabelas (4 Raw + 4 Silver) |
| `1_extrair.py` | Baixa o `.zip`, lê os 4 CSVs em blocos e carrega a camada Raw |
| `2_transformar.py` | Converte tipos, calcula colunas e carrega a camada Silver |
| `3_analise.ipynb` | Cria a camada Gold, responde as **10 perguntas** (7 do enunciado + 3 extras) e gera os gráficos |
| `config.py` | Parâmetros do projeto (lê o `.env` e guarda o `DRIVE_FILE_ID`) |
| `banco.py` | Funções utilitárias de conexão com o PostgreSQL |
| `.env.example` | Modelo de credenciais (copiar para `.env` e preencher) |
| `requirements.txt` | Lista de dependências do projeto |
| `.gitignore` | Impede que `.env`, `data/`, `*.zip` e `*.csv` vão para o Git |
| `README.md` | Este documento |

---

## 5. Pré-requisitos

- Python 3 instalado
- VS Code com a extensão Jupyter (o projeto **não roda no Google Colab** — precisa do PostgreSQL local)
- PostgreSQL instalado e em execução (mesma instalação usada nas Semanas 08 a 12)
- Conexão com a internet para baixar o `.zip` dos dados

---

## 6. Como executar

### 6.1 Pelo notebook guiado (mais simples)

1. Faça o download do repositório e descompacte.
2. No VS Code: **File → Open Folder** e escolha a pasta do projeto.
3. Abra `notebook_colab_aluno.ipynb` e escolha o Python instalado em **Select Kernel**.
4. Execute as células de cima para baixo (**Shift+Enter**). No Passo 2, troque `SUA_SENHA_AQUI` pela sua senha do PostgreSQL.
5. No Passo 6, abra `3_analise.ipynb` e clique em **Run All**.

Tempo total estimado: **cerca de 5 minutos**.

### 6.2 Pelo terminal (arquivo por arquivo)

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar credenciais
cp .env.example .env
# edite o .env e coloque sua senha real do PostgreSQL em POSTGRES_PASSWORD

# 3. Criar o banco e as tabelas
#    (o 0_criar_banco.sql tem duas partes — veja a seção 8)

# 4. Rodar o pipeline
python 1_extrair.py
python 2_transformar.py

# 5. Abrir a análise
#    abra 3_analise.ipynb no VS Code e execute todas as células
```

Cada script pode rodar quantas vezes você quiser: as tabelas são esvaziadas antes de cada carga.

---

## 7. Modelagem das camadas

### Camada Raw
Cópia fiel do CSV. Todas as colunas são `VARCHAR`, sem chave e sem constraint, na mesma ordem do arquivo original. A carga é **posicional** (`INSERT INTO tabela VALUES ...`), o que evita problemas com nomes de coluna acentuados ou com espaços escondidos no cabeçalho.

### Camada Silver
Dados limpos e tipados, com `PRIMARY KEY`, `FOREIGN KEY` e 2 constraints extras por tabela (conforme o enunciado). A `silver_viagem` é a **tabela mãe** — as outras três têm FK apontando para ela. Por isso a viagem é carregada primeiro, e o `TRUNCATE` da Silver lista mãe e filhas num único comando.

### Camada Gold
Tabelas e views **agregadas**, criadas a partir de `JOIN` + `GROUP BY` entre as tabelas Silver. Cada agregação existe em duas formas:

| | Tabela (`CREATE TABLE AS`) | View (`CREATE VIEW AS`) |
|---|---|---|
| O que guarda | o resultado, gravado uma vez | só a consulta, recalculada a cada leitura |
| Quando a origem muda | mantém o valor antigo até ser recriada | acompanha a mudança automaticamente |

---

## 8. Decisões de modelagem e de negócio

- **`valor_total`** = `valor_diarias + valor_passagens + valor_outros_gastos − valor_devolucao`. O enunciado não define a fórmula — esta é a regra adotada.
- **`duracao_dias`** = `(data_fim − data_inicio) + 1`, contando tanto o dia de início quanto o de fim.
- **Conversões por funções específicas** (requisito do enunciado): `texto_para_decimal()` (`"1272,97"` → `1272.97`) e `texto_para_data()` (`"17/09/2024"` → data). Campo vazio vira `NULL` no banco.
- **Filtro de viagens realizadas:** todas as perguntas consideram apenas `situacao = 'Realizada'`. Viagens que não aconteceram não representam gasto nem deslocamento.
- **Destinos (Pergunta 2):** a coluna `destinos` é texto livre e pode listar várias cidades na mesma viagem. Cada texto idêntico conta como um destino, e só entram destinos com **100 viagens ou mais** — sem isso, uma única viagem caríssima a um destino raro lideraria o ranking e distorceria a média.
- **Média de valor por tipo de pagamento (Pergunta 4):** calculada como `SUM(total_pago) / SUM(qtd_pagamentos)`. Fazer a média das médias daria resultado errado, porque cada linha da Gold tem uma quantidade diferente de pagamentos.
- **Órgão pagador × órgão superior:** as Perguntas 1 e 7 usam colunas diferentes. O órgão superior é quem **gastou**; o órgão pagador é quem efetivamente **pagou** — nem sempre são o mesmo.
- **Pergunta extra 1 (viajantes que mais viajaram):** os destinos são juntados com `STRING_AGG(DISTINCT destinos, ' | ')`. O `DISTINCT` evita repetir o mesmo texto e o `|` separa visualmente cada destino.
- **Pergunta extra 2 (viajantes que mais gastaram):** a métrica é a soma de `valor_total` por pessoa, não a contagem de viagens — são métricas diferentes que podem ter rankings diferentes.
- **Pergunta extra 3 (meses com mais viagens):** agrupamento por mês usa `TO_CHAR(data_inicio, 'YYYY-MM')`, que transforma a data no texto `2025-01`, `2025-02`, etc., permitindo agrupar sem perder o ano.
- **Banco `transparencia`:** o `0_criar_banco.sql` tem duas partes. A Parte 1 (`CREATE DATABASE`) roda conectado no banco `postgres`; a Parte 2 (`CREATE TABLE ...`) roda conectado no banco `transparencia`.

---

## 9. Resultados da execução

Todos os registros dos CSVs chegaram íntegros às camadas Raw e Silver, com as conferências fechando (executado mais de uma vez, sem duplicar):

| Tabela | Linhas no CSV | Raw | Silver |
|---|---:|---:|---:|
| viagem | 341.860 | 341.860 | 341.860 |
| pagamento | 606.916 | 606.916 | 606.916 |
| passagem | 167.260 | 167.260 | 167.260 |
| trecho | 763.349 | 763.349 | 763.349 |

- As 664 datas de emissão vazias na Raw viraram `NULL` na Silver.
- A soma dos pagamentos é idêntica nas duas camadas (R$ 1.194.365.457,37).
- Tempo aproximado nesta máquina: `1_extrair.py` ≈ 1 min 10 s; `2_transformar.py` ≈ 1 min 45 s.

---

## 10. Respostas das perguntas de negócio

### 10.1 Perguntas do enunciado (7)

| # | Pergunta | Resposta | Insight |
|---|---|---|---|
| 1 | 5 órgãos com maior custo total | Justiça e Segurança Pública (R$ 485,7 mi), Defesa (R$ 154,6 mi), Educação (R$ 109,8 mi), Meio Ambiente (R$ 49,3 mi), Previdência Social (R$ 40,2 mi) | O primeiro órgão sozinho gasta 1,4 vez o que os outros quatro do ranking somam — concentração forte |
| 2 | 3 destinos com maior custo médio por viagem | "Brasília/DF, Brasília/DF" (R$ 27.401,80 · 283 viagens), Genebra/Suíça (R$ 25.469,22 · 242), Nova York/EUA (R$ 21.214,19 · 149) | Destinos internacionais e Brasília puxam a média para cima — deslocamentos longos e diárias caras |
| 3 | Viagem de maior duração e seu custo | ID `0000000000020699856` (Previdência Social), 384 dias, custo registrado R$ 0,00 | Existem viagens longas sem custo registrado; provavelmente custeadas por outra fonte |
| 4 | Tipo de pagamento com maior valor médio | Diárias (R$ 2.078,79), seguido por Passagem (R$ 1.882,32), Seguro (R$ 447,26) e Restituição (R$ 245,70) | Diárias e passagens são os dois maiores componentes de custo por viagem |
| 5 | Meio de transporte mais usado nos trechos | Veículo Oficial (385.734 trechos, 51,0%), seguido por Aéreo (226.707) | Mais da metade dos trechos é feita com veículo oficial, não com avião |
| 6 | UF de destino em mais trechos | São Paulo (81.727), seguido do Distrito Federal (77.962) | SP e DF concentram o fluxo; ambos são grandes polos administrativos e econômicos |
| 7 | Órgão que pagou mais no total | Fundo Nacional de Segurança Pública (R$ 278,3 mi); o pagador "Sigiloso" vem em seguida (R$ 199,3 mi) | Existe um pagador identificado apenas como "Sigiloso", o que limita a análise |

### 10.2 Perguntas extras (3)

| # | Pergunta | Resposta | Insight |
|---|---|---|---|
| 8 | 10 viajantes que mais viajaram e seus destinos | {{ preencher com o resultado da sua execução }} | Mostra o perfil dos servidores com maior volume de deslocamentos — alguns concentram dezenas de viagens em seis meses |
| 9 | 10 viajantes que mais gastaram dinheiro | {{ preencher com o resultado da sua execução }} | Ranking por custo total, não por quantidade: uma pessoa com poucas viagens caras pode gastar mais do que outra com muitas viagens baratas |
| 10 | 5 meses com mais viagens iniciadas | {{ preencher com o resultado da sua execução }} | Ajuda a enxergar sazonalidade dentro dos seis meses do dataset — se todos os meses tiverem volume parecido, não há concentração temporal |

> **Como preencher as linhas 8, 9 e 10:** rode as três células extras no `3_analise.ipynb` e copie a primeira linha de cada tabela (que aparece depois do gráfico). Também vale substituir o `{{ ... }}` do Insight por uma frase curta sua, olhando o gráfico.

Os gráficos de todas as 10 perguntas estão no `3_analise.ipynb`, todos com título, eixos nomeados e legenda.

---

## 11. O que os dados revelam sobre a própria base

Três achados da camada Silver que ajudam a ler os resultados com o cuidado necessário:

1. **18.545 viagens realizadas têm custo total R$ 0,00**, incluindo a viagem mais longa (Pergunta 3). São viagens sem diárias, passagens e outros gastos registrados neste arquivo. O custo zero é o que a base informa — não é erro da conversão.
2. **13.774 viagens terminam depois de 30/06/2025.** O arquivo traz as viagens *iniciadas* de janeiro a junho de 2025; algumas duram meses e terminam no ano seguinte. Por isso existem durações acima de 180 dias.
3. **3 viagens têm custo total negativo**, porque a devolução foi maior que a soma dos gastos registrados.

---

## 12. Limitações e melhorias possíveis

- **Destinos:** separar a lista de cidades da coluna `destinos` em uma linha por destino tornaria a comparação mais justa.
- **Pagador "Sigiloso":** não identifica o órgão; a análise mantém a categoria como veio da fonte. O mesmo vale para o meio de transporte "Inválido".
- **Velocidade da carga:** trocar o `INSERT` em lote pelo comando `COPY` do PostgreSQL tornaria a Fase 1 ainda mais rápida.
- **Testes automatizados:** incluir testes das funções de conversão e validações adicionais Raw × Silver.
- **Automação:** agendar a execução do pipeline e incluir os meses seguintes do ano.
- **Análises extras possíveis:** custo médio por cargo, sazonalidade diária (dia da semana), distribuição de viagens urgentes por órgão, viagens mais longas em número de trechos.

---

## 13. Versionamento com Git

O projeto foi versionado com **uma branch por fase**, com nomes padronizados, e commits curtos no imperativo. Estrutura:

| Branch | Conteúdo | Exemplos de commit |
|---|---|---|
| `main` | estrutura inicial + merges de cada fase | `cria estrutura do projeto` |
| `feature/fase0-banco` | `0_criar_banco.sql` | `cria tabelas raw` · `cria tabelas silver com pk fk e constraints` |
| `feature/fase1-extracao` | `1_extrair.py` | `implementa download do zip` · `implementa carga raw em blocos` |
| `feature/fase2-transformacao` | `2_transformar.py` | `implementa conversao de decimais e datas` · `calcula valor_total e duracao_dias` |
| `feature/fase3-analise` | `3_analise.ipynb` | `cria camada gold com join e group by` · `responde perguntas com graficos` · `adiciona 3 perguntas extras` |
| `docs/readme` | `README.md` | `documenta execucao e decisoes` |

Fluxo usado:

```bash
git checkout -b feature/fase1-extracao
git add 1_extrair.py
git commit -m "implementa download do zip"
git push -u origin feature/fase1-extracao
git checkout main
git merge feature/fase1-extracao
git push
```

O `.gitignore` impede que `.env`, `data/`, `*.zip` e `*.csv` sejam versionados.

---

## 14. Mapeamento com a rubrica

| Critério | Pontos | Onde está no projeto |
|---|---:|---|
| 1. Versionamento com branches e commits | 1,5 | histórico do repositório (seção 13) |
| 2. Organização dos arquivos (`.sql`, `.py`, `.ipynb`, `README.md`) | 1,0 | arquivos numerados pela ordem de execução (seção 4) |
| 3. Extração + Raw (download, `try/except`, idempotência) | 0,5 | `1_extrair.py` |
| 4. Tipagem e limpeza (todos os campos convertidos) | 1,0 | `2_transformar.py` |
| 5. Gold com `JOIN` + `GROUP BY` (tabela e view) | 1,0 | `3_analise.ipynb`, Parte B |
| 6. Perguntas de negócio respondidas com evidências | 1,5 | seção 10 + `3_analise.ipynb` (7 do enunciado + 3 extras) |
| 7. Gráficos com título, eixos e legenda | 1,5 | 10 gráficos do `3_analise.ipynb` (7 + 3 extras) |
| 8. Modelagem Silver (PK, FK e constraints) | 2,0 | `0_criar_banco.sql` |

---

## 15. Referências

- Portal da Transparência — Viagens a Serviço: https://portaldatransparencia.gov.br/viagens
- Documentação `pandas`: https://pandas.pydata.org/docs/
- Documentação `psycopg2`: https://www.psycopg.org/docs/
- Documentação PostgreSQL: https://www.postgresql.org/docs/