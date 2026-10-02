"""
=============================================================
GlobalForce · Workforce Management | BI
Script: pipeline.py
Etapa: S1 — Modelagem de Dados
Descrição: Processa o CSV de 3.1M de registros e popula o
           modelo estrela no MySQL (Normalização).

Carga segura: tudo é gravado em tabelas *_staging e só no fim
as tabelas são trocadas com um único RENAME TABLE (atômico).
Se algo falhar no meio, as tabelas em produção ficam intactas.
=============================================================
"""

import os
import sys
import time

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# --- CONFIGURACOES ---
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_NAME     = os.getenv("DB_NAME", "workforce_bi")
CSV_PATH    = os.getenv("CSV_PATH", os.path.join(BASE_DIR, "globalforce_usa_3years_2023_2025.csv"))
CHUNK_SIZE  = 500_000
RANDOM_SEED = 42  # assignments simulados reprodutíveis entre execuções

TABLES  = ["dim_regiao", "dim_data", "dim_colaborador", "dim_cliente", "fato_workforce"]
STAGING = "_staging"
OLD     = "_old"

DIM_COLUMNS = ["period", "employee_id", "region", "state", "department", "role", "monthly_cost"]

CLIENTES = [
    (1, "GlobalForce Internal"),
    (2, "Alpha Group"),
    (3, "Beta Corp"),
    (4, "Delta Solutions"),
    (5, "Epsilon Inc"),
]


def get_engine():
    # URL.create escapa caracteres especiais da senha (@, :, /) e trata senha vazia
    url = URL.create(
        "mysql+pymysql",
        username=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=DB_NAME,
    )
    return create_engine(url)


def build_dimensions(chunks):
    """
    Monta dim_regiao, dim_data e dim_colaborador lendo o CSV em pedaços,
    sem carregar o arquivo inteiro na memória.
    """
    regioes, periodos, colaboradores = [], [], []
    for chunk in chunks:
        regioes.append(chunk[["region", "state"]].drop_duplicates())
        periodos.append(pd.Series(chunk["period"].unique()))
        # mantém só o registro mais recente de cada colaborador neste pedaço
        colaboradores.append(
            chunk.sort_values("period", kind="stable").drop_duplicates("employee_id", keep="last")
        )

    dim_regiao = pd.concat(regioes).drop_duplicates().reset_index(drop=True)
    dim_regiao.columns = ["region_name", "state"]
    dim_regiao["region_id"] = dim_regiao.index + 1
    dim_regiao["country"] = "USA"

    periods = pd.DatetimeIndex(sorted(pd.to_datetime(pd.concat(periodos).unique())))
    dim_data = pd.DataFrame({
        "period": periods,
        "date_id": range(1, len(periods) + 1),
        "month": periods.month,
        "quarter": (periods.month - 1) // 3 + 1,
        "year": periods.year,
    })
    dim_data["is_current_period"] = dim_data["period"] == dim_data["period"].max()

    dim_colaborador = (
        pd.concat(colaboradores)
        .sort_values("period", kind="stable")
        .drop_duplicates("employee_id", keep="last")
        [["employee_id", "department", "region", "role", "monthly_cost"]]
        .reset_index(drop=True)
    )
    return dim_regiao, dim_data, dim_colaborador


def build_dim_cliente():
    # Simulada para cumprir o requisito do Dashboard
    dim_cliente = pd.DataFrame(CLIENTES, columns=["client_id", "client_name"])
    dim_cliente["assignment_id"] = dim_cliente["client_id"]
    dim_cliente["status"] = "Active"
    return dim_cliente


def build_fact_chunk(chunk, regiao_map, data_map, rng):
    chunk = chunk.copy()
    chunk["region_id"] = chunk.set_index(["region", "state"]).index.map(regiao_map)
    chunk["date_id"] = pd.to_datetime(chunk["period"]).dt.strftime("%Y-%m-%d").map(data_map)

    sem_chave = chunk["region_id"].isna() | chunk["date_id"].isna()
    if sem_chave.any():
        raise ValueError(f"{int(sem_chave.sum())} linha(s) sem região ou período correspondente nas dimensões")

    chunk["assignment_id"] = rng.integers(1, len(CLIENTES) + 1, size=len(chunk))
    # Flag de desligamento no mes
    chunk["is_terminated"] = (chunk["status_in_month"] == "Terminated").astype(int)

    return chunk[[
        "assignment_id", "employee_id", "date_id", "region_id",
        "worked_hours", "planned_hours", "overtime_hours",
        "monthly_cost", "goal_achievement", "is_terminated",
    ]].astype({"region_id": "int64", "date_id": "int64"})


def drop_tables(engine, suffix):
    with engine.begin() as conn:
        for table in TABLES:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}{suffix}"))


def create_indexes(engine, suffix=""):
    """Chaves primárias nas dimensões e índices nas chaves da fato (usadas nos JOINs)."""
    s = suffix
    statements = [
        f"ALTER TABLE dim_regiao{s} ADD PRIMARY KEY (region_id)",
        f"ALTER TABLE dim_data{s} ADD PRIMARY KEY (date_id)",
        f"ALTER TABLE dim_colaborador{s} ADD PRIMARY KEY (employee_id)",
        f"ALTER TABLE dim_cliente{s} ADD PRIMARY KEY (assignment_id)",
        (
            f"ALTER TABLE fato_workforce{s} "
            "ADD INDEX idx_fato_date (date_id), "
            "ADD INDEX idx_fato_region (region_id), "
            "ADD INDEX idx_fato_assignment (assignment_id), "
            "ADD INDEX idx_fato_employee (employee_id)"
        ),
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def swap_tables(engine):
    """Troca staging -> produção num único RENAME TABLE (atômico no MySQL)."""
    existing = set(inspect(engine).get_table_names())
    drop_tables(engine, OLD)

    pairs = []
    for table in TABLES:
        if table in existing:
            pairs.append(f"{table} TO {table}{OLD}")
        pairs.append(f"{table}{STAGING} TO {table}")

    with engine.begin() as conn:
        conn.execute(text("RENAME TABLE " + ", ".join(pairs)))
    drop_tables(engine, OLD)


def run_pipeline():
    start_time = time.time()
    engine = get_engine()

    print("--- Iniciando Pipeline ETL...")
    print(f"--- Lendo arquivo: {CSV_PATH}")

    # 1. Dimensões (leitura em pedaços, só das colunas necessárias)
    print("--- Montando dimensões...")
    dim_regiao, dim_data, dim_colaborador = build_dimensions(
        pd.read_csv(CSV_PATH, chunksize=CHUNK_SIZE, usecols=DIM_COLUMNS)
    )
    dim_cliente = build_dim_cliente()

    regiao_map = dim_regiao.set_index(["region_name", "state"])["region_id"].to_dict()
    data_map = dict(zip(dim_data["period"].dt.strftime("%Y-%m-%d"), dim_data["date_id"]))

    try:
        drop_tables(engine, STAGING)

        print("--- Gravando dimensões em staging...")
        with engine.begin() as conn:
            dim_regiao.to_sql(f"dim_regiao{STAGING}", conn, if_exists="replace", index=False)
            dim_data.to_sql(f"dim_data{STAGING}", conn, if_exists="replace", index=False)
            dim_colaborador.to_sql(f"dim_colaborador{STAGING}", conn, if_exists="replace", index=False)
            dim_cliente.to_sql(f"dim_cliente{STAGING}", conn, if_exists="replace", index=False)

        # 2. Fato (processamento em chunks)
        print("--- Processando fato_workforce...")
        rng = np.random.default_rng(RANDOM_SEED)
        total_rows = 0
        for chunk in pd.read_csv(CSV_PATH, chunksize=CHUNK_SIZE):
            fato_chunk = build_fact_chunk(chunk, regiao_map, data_map, rng)
            fato_chunk.to_sql(f"fato_workforce{STAGING}", engine, if_exists="append", index=False)
            total_rows += len(fato_chunk)
            print(f"--- {total_rows:,} registros processados...")

        print("--- Criando chaves e índices...")
        create_indexes(engine, STAGING)

        print("--- Publicando as novas tabelas...")
        swap_tables(engine)
    except Exception:
        print("--- Falha: removendo tabelas de staging (produção não foi alterada).")
        drop_tables(engine, STAGING)
        raise

    end_time = time.time()
    print("\n--- ETL CONCLUIDO COM SUCESSO!")
    print(f"--- Tempo total: {round((end_time - start_time) / 60, 2)} minutos")
    print(f"--- Total de linhas na Fato: {total_rows:,}")
    print(f"--- O banco de dados '{DB_NAME}' esta pronto para o Metabase.")


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        print(f"--- ERRO NO PIPELINE: {e}")
        sys.exit(1)
