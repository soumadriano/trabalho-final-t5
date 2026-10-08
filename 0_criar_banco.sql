-- =============================================================================
-- 0_criar_banco.sql  |  Fase 0: banco de dados e tabelas (Raw + Silver)
-- Projeto: Viagens a Serviço (Portal da Transparência)  |  PostgreSQL
--
-- COMO EXECUTAR (são duas partes, porque o CREATE DATABASE não troca de banco):
--   PARTE 1: conectado no banco "postgres", execute só o CREATE DATABASE.
--   PARTE 2: troque a conexão para o banco "transparencia" e execute o restante.
-- Pode rodar de novo quando quiser: as tabelas são apagadas e recriadas.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- PARTE 1  (conexão: banco "postgres")
-- -----------------------------------------------------------------------------
CREATE DATABASE transparencia;


-- -----------------------------------------------------------------------------
-- PARTE 2  (conexão: banco "transparencia")
-- -----------------------------------------------------------------------------

-- Apaga a camada Gold (criada pelo 3_analise.ipynb), se já existir. As views
-- dependem das tabelas Silver: sem apagá-las antes, o DROP das Silver é recusado.
DROP VIEW IF EXISTS vw_gold_pagamento_resumo;
DROP VIEW IF EXISTS vw_gold_trecho_resumo;
DROP TABLE IF EXISTS gold_pagamento_resumo;
DROP TABLE IF EXISTS gold_trecho_resumo;

-- Apaga as tabelas antigas: primeiro as filhas (que têm FOREIGN KEY), depois a mãe.
DROP TABLE IF EXISTS silver_pagamento;
DROP TABLE IF EXISTS silver_passagem;
DROP TABLE IF EXISTS silver_trecho;
DROP TABLE IF EXISTS silver_viagem;
DROP TABLE IF EXISTS raw_pagamento;
DROP TABLE IF EXISTS raw_passagem;
DROP TABLE IF EXISTS raw_trecho;
DROP TABLE IF EXISTS raw_viagem;


-- =============================================================================
-- CAMADA RAW: cópia fiel do CSV. Todas as colunas VARCHAR, sem chaves e sem
-- constraints. As colunas seguem a MESMA ORDEM do arquivo CSV.
-- =============================================================================

CREATE TABLE raw_viagem (
    id_viagem              VARCHAR(255),
    num_proposta           VARCHAR(255),
    situacao               VARCHAR(255),
    viagem_urgente         VARCHAR(255),
    justificativa_urgencia VARCHAR(4000),
    cod_orgao_superior     VARCHAR(255),
    nome_orgao_superior    VARCHAR(255),
    cod_orgao_solicitante  VARCHAR(255),
    nome_orgao_solicitante VARCHAR(255),
    cpf_viajante           VARCHAR(255),
    nome_viajante          VARCHAR(255),
    cargo                  VARCHAR(255),
    funcao                 VARCHAR(255),
    descricao_funcao       VARCHAR(255),
    data_inicio            VARCHAR(255),
    data_fim               VARCHAR(255),
    destinos               VARCHAR(4000),
    motivo                 VARCHAR(4000),
    valor_diarias          VARCHAR(255),
    valor_passagens        VARCHAR(255),
    valor_devolucao        VARCHAR(255),
    valor_outros_gastos    VARCHAR(255)
);

CREATE TABLE raw_pagamento (
    id_viagem           VARCHAR(255),
    num_proposta        VARCHAR(255),
    cod_orgao_superior  VARCHAR(255),
    nome_orgao_superior VARCHAR(255),
    cod_orgao_pagador   VARCHAR(255),
    nome_orgao_pagador  VARCHAR(255),
    cod_ug_pagadora     VARCHAR(255),
    nome_ug_pagadora    VARCHAR(255),
    tipo_pagamento      VARCHAR(255),
    valor               VARCHAR(255)
);

CREATE TABLE raw_passagem (
    id_viagem            VARCHAR(255),
    num_proposta         VARCHAR(255),
    meio_transporte      VARCHAR(255),
    pais_origem_ida      VARCHAR(255),
    uf_origem_ida        VARCHAR(255),
    cidade_origem_ida    VARCHAR(255),
    pais_destino_ida     VARCHAR(255),
    uf_destino_ida       VARCHAR(255),
    cidade_destino_ida   VARCHAR(255),
    pais_origem_volta    VARCHAR(255),
    uf_origem_volta      VARCHAR(255),
    cidade_origem_volta  VARCHAR(255),
    pais_destino_volta   VARCHAR(255),
    uf_destino_volta     VARCHAR(255),
    cidade_destino_volta VARCHAR(255),
    valor_passagem       VARCHAR(255),
    taxa_servico         VARCHAR(255),
    data_emissao         VARCHAR(255),
    hora_emissao         VARCHAR(255)
);

CREATE TABLE raw_trecho (
    id_viagem        VARCHAR(255),
    num_proposta     VARCHAR(255),
    sequencia_trecho VARCHAR(255),
    origem_data      VARCHAR(255),
    origem_pais      VARCHAR(255),
    origem_uf        VARCHAR(255),
    origem_cidade    VARCHAR(255),
    destino_data     VARCHAR(255),
    destino_pais     VARCHAR(255),
    destino_uf       VARCHAR(255),
    destino_cidade   VARCHAR(255),
    meio_transporte  VARCHAR(255),
    numero_diarias   VARCHAR(255),
    missao           VARCHAR(255)
);


-- =============================================================================
-- CAMADA SILVER: dado limpo e tipado, com chave primária (PK), chave
-- estrangeira (FK) e 2 constraints por tabela, todas dentro do CREATE TABLE.
-- A tabela mãe (silver_viagem) vem primeiro; as filhas apontam para ela.
-- =============================================================================

CREATE TABLE silver_viagem (
    id_viagem            VARCHAR(20)  NOT NULL,
    num_proposta         VARCHAR(20),
    situacao             VARCHAR(50),
    viagem_urgente       VARCHAR(5),
    cod_orgao_superior   VARCHAR(20),
    nome_orgao_superior  VARCHAR(255) NOT NULL,           -- constraint 1: NOT NULL
    nome_viajante        VARCHAR(255),
    cargo                VARCHAR(255),
    data_inicio          DATE,
    data_fim             DATE,
    destinos             VARCHAR(4000),
    motivo               VARCHAR(4000),
    valor_diarias        DECIMAL(10,2),
    valor_passagens      DECIMAL(10,2),
    valor_devolucao      DECIMAL(10,2),
    valor_outros_gastos  DECIMAL(10,2),
    valor_total          DECIMAL(12,2),                   -- calculada
    duracao_dias         INT,                             -- calculada
    PRIMARY KEY (id_viagem),
    CONSTRAINT ck_viagem_valor_diarias CHECK (valor_diarias >= 0)   -- constraint 2: CHECK
);

CREATE TABLE silver_pagamento (
    id_pagamento       SERIAL,
    id_viagem          VARCHAR(20)  NOT NULL,
    num_proposta       VARCHAR(20),
    nome_orgao_pagador VARCHAR(255),
    nome_ug_pagadora   VARCHAR(255),
    tipo_pagamento     VARCHAR(50)  NOT NULL,             -- constraint 2: NOT NULL
    valor              DECIMAL(10,2),
    PRIMARY KEY (id_pagamento),
    CONSTRAINT fk_pagamento_viagem FOREIGN KEY (id_viagem) REFERENCES silver_viagem (id_viagem),
    CONSTRAINT ck_pagamento_valor CHECK (valor >= 0)      -- constraint 1: CHECK
);

CREATE TABLE silver_passagem (
    id_passagem        SERIAL,
    id_viagem          VARCHAR(20)  NOT NULL,
    meio_transporte    VARCHAR(50),
    pais_origem_ida    VARCHAR(60),
    uf_origem_ida      VARCHAR(40),
    cidade_origem_ida  VARCHAR(80),
    pais_destino_ida   VARCHAR(60),
    uf_destino_ida     VARCHAR(40),
    cidade_destino_ida VARCHAR(80),
    valor_passagem     DECIMAL(10,2),
    taxa_servico       DECIMAL(10,2),
    data_emissao       DATE,
    PRIMARY KEY (id_passagem),
    CONSTRAINT fk_passagem_viagem FOREIGN KEY (id_viagem) REFERENCES silver_viagem (id_viagem),
    CONSTRAINT ck_passagem_valor CHECK (valor_passagem >= 0),   -- constraint 1: CHECK
    CONSTRAINT ck_passagem_taxa CHECK (taxa_servico >= 0)       -- constraint 2: CHECK
);

CREATE TABLE silver_trecho (
    id_trecho        SERIAL,
    id_viagem        VARCHAR(20)  NOT NULL,
    sequencia_trecho INT,
    origem_data      DATE,
    origem_uf        VARCHAR(40),
    origem_cidade    VARCHAR(80),
    destino_data     DATE,
    destino_uf       VARCHAR(40),
    destino_cidade   VARCHAR(80),
    meio_transporte  VARCHAR(50),
    numero_diarias   DECIMAL(10,2),
    PRIMARY KEY (id_trecho),
    CONSTRAINT fk_trecho_viagem FOREIGN KEY (id_viagem) REFERENCES silver_viagem (id_viagem),
    CONSTRAINT ck_trecho_diarias CHECK (numero_diarias >= 0),                  -- constraint 1: CHECK
    CONSTRAINT uq_trecho_viagem_sequencia UNIQUE (id_viagem, sequencia_trecho) -- constraint 2: UNIQUE
);
