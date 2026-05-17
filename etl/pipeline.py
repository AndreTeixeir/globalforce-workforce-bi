"""
=============================================================
GlobalForce · Workforce Management | BI
Script: pipeline.py
Etapa: S1 — Modelagem de Dados
Descrição: Processa o CSV de 3.1M de registros e popula o 
           modelo estrela no MySQL (Normalização).
=============================================================
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import time
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# --- CONFIGURACOES DE CONEXAO ---
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "3306")
DB_NAME     = os.getenv("DB_NAME", "workforce_bi")
CSV_PATH    = "globalforce_usa_3years_2023_2025.csv"

def get_engine():
    return create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def run_pipeline():
    start_time = time.time()
    engine = get_engine()
    
    print("--- Iniciando Pipeline ETL...")
    print(f"--- Lendo arquivo: {CSV_PATH}")

    # 1. Carregar uma amostra para extrair as Dimensoes
    df_full = pd.read_csv(CSV_PATH)
    
    with engine.begin() as conn:
        print("--- Limpando tabelas antigas...")
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in ["fato_workforce", "dim_colaborador", "dim_regiao", "dim_data", "dim_cliente"]:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

        # --- 2. DIM_REGIAO ---
        print("--- Criando dim_regiao...")
        dim_regiao = df_full[['region', 'state']].drop_duplicates().reset_index(drop=True)
        dim_regiao.columns = ['region_name', 'state']
        dim_regiao['region_id'] = dim_regiao.index + 1
        dim_regiao['country'] = 'USA'
        dim_regiao.to_sql("dim_regiao", conn, if_exists="replace", index=False)

        # --- 3. DIM_DATA ---
        print("--- Criando dim_data...")
        periods = pd.to_datetime(df_full['period'].unique())
        dim_data = pd.DataFrame({
            'period': periods,
            'date_id': range(1, len(periods) + 1),
            'month': periods.month,
            'quarter': (periods.month - 1) // 3 + 1,
            'year': periods.year
        })
        dim_data['is_current_period'] = (dim_data['period'] == dim_data['period'].max())
        dim_data.to_sql("dim_data", conn, if_exists="replace", index=False)

        # --- 4. DIM_COLABORADOR ---
        print("--- Criando dim_colaborador (Dados unicos)...")
        dim_colaborador = df_full.sort_values('period').drop_duplicates('employee_id', keep='last')
        dim_colaborador = dim_colaborador[['employee_id', 'department', 'region', 'role', 'monthly_cost']]
        dim_colaborador.to_sql("dim_colaborador", conn, if_exists="replace", index=False)

        # --- 5. DIM_CLIENTE (Simulada para cumprir o requisito do Dashboard) ---
        print("--- Criando dim_cliente (Assignments simulados)...")
        clientes = [
            (1, "GlobalForce Internal"),
            (2, "Alpha Group"),
            (3, "Beta Corp"),
            (4, "Delta Solutions"),
            (5, "Epsilon Inc")
        ]
        dim_cliente = pd.DataFrame(clientes, columns=['client_id', 'client_name'])
        dim_cliente['assignment_id'] = dim_cliente['client_id']
        dim_cliente['status'] = 'Active'
        dim_cliente.to_sql("dim_cliente", conn, if_exists="replace", index=False)

    # --- 6. FATO_WORKFORCE (Processamento em Chunks) ---
    print("--- Processando fato_workforce (3.1M registros)...")
    
    regiao_map = dim_regiao.set_index(['region_name', 'state'])['region_id'].to_dict()
    data_map = dim_data.set_index(pd.to_datetime(dim_data['period']).dt.strftime('%Y-%m-%d'))['date_id'].to_dict()

    chunk_size = 500000
    total_rows = 0
    
    for chunk in pd.read_csv(CSV_PATH, chunksize=chunk_size):
        chunk['region_id'] = chunk.set_index(['region', 'state']).index.map(regiao_map)
        chunk['date_id'] = chunk['period'].map(data_map)
        chunk['assignment_id'] = np.random.randint(1, 6, size=len(chunk))
        
        # Flag de desligamento no mes
        chunk['is_terminated'] = (chunk['status_in_month'] == 'Terminated').astype(int)
        
        fato_chunk = chunk[[
            'assignment_id', 'employee_id', 'date_id', 'region_id',
            'worked_hours', 'planned_hours', 'overtime_hours',
            'monthly_cost', 'goal_achievement', 'is_terminated'
        ]]
        
        fato_chunk.to_sql("fato_workforce", engine, if_exists="append", index=False)
        total_rows += len(fato_chunk)
        print(f"--- {total_rows:,} registros processados...")

    end_time = time.time()
    print(f"\n--- ETL CONCLUIDO COM SUCESSO!")
    print(f"--- Tempo total: {round((end_time - start_time)/60, 2)} minutos")
    print(f"--- Total de linhas na Fato: {total_rows:,}")
    print(f"--- O banco de dados '{DB_NAME}' esta pronto para o Metabase.")

if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        print(f"--- ERRO NO PIPELINE: {e}")
