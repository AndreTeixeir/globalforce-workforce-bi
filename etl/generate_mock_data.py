"""
=============================================================
GlobalForce · Workforce Management | BI
Script: generate_mock_data.py
Etapa: S1 — Modelagem de Dados
Descrição: Gera dados fictícios realistas e popula as tabelas
           do banco MySQL workforce_bi
=============================================================
"""

import pandas as pd
from faker import Faker
from sqlalchemy import create_engine, text
import random
from datetime import date, timedelta
import warnings
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

warnings.filterwarnings("ignore")

# ── CONFIGURAÇÕES ────────────────────────────────────────────
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "3306")
DB_NAME     = os.getenv("DB_NAME", "workforce_bi")

fake = Faker("pt_BR")
random.seed(42)
Faker.seed(42)

# ── CONEXÃO COM O BANCO ──────────────────────────────────────
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── 1. DIM_DATA ──────────────────────────────────────────────
def generate_dim_data():
    records = []
    date_id = 1
    for year in [2024, 2025]:
        for month in range(1, 13):
            period = date(year, month, 1)
            records.append({
                "date_id": date_id,
                "period": period,
                "month": month,
                "quarter": (month - 1) // 3 + 1,
                "year": year,
                "is_current_period": period == date(2025, 4, 1)
            })
            date_id += 1
    return pd.DataFrame(records)

# ── 2. DIM_REGIAO ────────────────────────────────────────────
def generate_dim_regiao():
    regioes = [
        (1, "São Paulo",       "SP", "Brasil", "America/Sao_Paulo"),
        (2, "Rio de Janeiro",  "RJ", "Brasil", "America/Sao_Paulo"),
        (3, "Belo Horizonte",  "MG", "Brasil", "America/Sao_Paulo"),
        (4, "Curitiba",        "PR", "Brasil", "America/Sao_Paulo"),
        (5, "Porto Alegre",    "RS", "Brasil", "America/Sao_Paulo"),
        (6, "Salvador",        "BA", "Brasil", "America/Bahia"),
        (7, "Recife",          "PE", "Brasil", "America/Recife"),
        (8, "Fortaleza",       "CE", "Brasil", "America/Fortaleza"),
    ]
    return pd.DataFrame(regioes, columns=[
        "region_id", "region_name", "state", "country", "timezone"
    ])

# ── 3. DIM_COLABORADOR ───────────────────────────────────────
def generate_dim_colaborador(n=80):
    departments = ["Tecnologia", "Financeiro", "Operações", "RH", "Comercial"]
    records = []
    for i in range(1, n + 1):
        hire_date = fake.date_between(start_date=date(2018, 1, 1), end_date=date(2024, 6, 1))
        is_terminated = random.random() < 0.12  # 12% de turnover
        termination_date = None
        status = "Active"
        if is_terminated:
            termination_date = fake.date_between(
                start_date=hire_date + timedelta(days=180),
                end_date=date(2025, 3, 31)
            )
            status = "Terminated"
        records.append({
            "employee_id":       i,
            "name":              fake.name(),
            "department":        random.choice(departments),
            "region":            random.choice(["São Paulo", "Rio de Janeiro", "Belo Horizonte",
                                                "Curitiba", "Porto Alegre", "Salvador",
                                                "Recife", "Fortaleza"]),
            "hire_date":         hire_date,
            "termination_date":  termination_date,
            "monthly_cost":      round(random.uniform(4500, 18000), 2),
            "status":            status,
            "goal_achievement":  round(random.uniform(55, 100), 2)
        })
    return pd.DataFrame(records)

# ── 4. DIM_CLIENTE ───────────────────────────────────────────
def generate_dim_cliente(colaboradores_df, n_assignments=200):
    clients = [
        (1, "Empresa Alpha"),
        (2, "Grupo Beta"),
        (3, "Corporação Gamma"),
        (4, "Holding Delta"),
        (5, "Conglomerado Epsilon"),
    ]
    roles = ["Analista Jr.", "Analista Sr.", "Consultor", "Especialista", "Coordenador"]
    records = []
    employee_ids = colaboradores_df["employee_id"].tolist()
    for i in range(1, n_assignments + 1):
        client = random.choice(clients)
        records.append({
            "assignment_id": i,
            "client_id":     client[0],
            "client_name":   client[1],
            "role":          random.choice(roles),
            "status":        random.choice(["Active", "Active", "Active", "Closed"])
        })
    return pd.DataFrame(records)

# ── 5. FATO_WORKFORCE ────────────────────────────────────────
def generate_fato_workforce(colaboradores_df, clientes_df, datas_df, regioes_df):
    records = []
    region_ids = regioes_df["region_id"].tolist()
    date_ids   = datas_df["date_id"].tolist()

    for _, assignment in clientes_df.iterrows():
        # cada alocação tem entre 3 e 12 meses de registros
        n_months = random.randint(3, 12)
        sampled_dates = random.sample(date_ids, min(n_months, len(date_ids)))

        # busca colaborador aleatório ativo
        ativos = colaboradores_df[colaboradores_df["status"] == "Active"]
        employee = ativos.sample(1).iloc[0]

        for date_id in sampled_dates:
            planned = round(random.uniform(140, 176), 1)
            worked  = round(planned * random.uniform(0.75, 1.10), 1)
            overtime = max(0, round(worked - planned, 1))
            records.append({
                "assignment_id":   assignment["assignment_id"],
                "employee_id":     employee["employee_id"],
                "date_id":         date_id,
                "region_id":       random.choice(region_ids),
                "worked_hours":    worked,
                "planned_hours":   planned,
                "overtime_hours":  overtime,
                "monthly_cost":    employee["monthly_cost"],
                "goal_achievement": employee["goal_achievement"],
                "is_terminated":   1 if random.random() < 0.05 else 0
            })
    return pd.DataFrame(records)

# ── EXECUÇÃO PRINCIPAL ───────────────────────────────────────
def main():
    print("=" * 55)
    print("  GlobalForce · Workforce BI — Geração de Mock Data")
    print("=" * 55)

    print("\n[1/5] Gerando dim_data...")
    dim_data = generate_dim_data()
    print(f"      {len(dim_data)} registros gerados.")

    print("[2/5] Gerando dim_regiao...")
    dim_regiao = generate_dim_regiao()
    print(f"      {len(dim_regiao)} registros gerados.")

    print("[3/5] Gerando dim_colaborador...")
    dim_colaborador = generate_dim_colaborador(n=80)
    print(f"      {len(dim_colaborador)} registros gerados.")

    print("[4/5] Gerando dim_cliente (assignments)...")
    dim_cliente = generate_dim_cliente(dim_colaborador, n_assignments=200)
    print(f"      {len(dim_cliente)} registros gerados.")

    print("[5/5] Gerando fato_workforce...")
    fato_workforce = generate_fato_workforce(dim_colaborador, dim_cliente, dim_data, dim_regiao)
    print(f"      {len(fato_workforce)} registros gerados.")

    print("\n Enviando dados ao MySQL...")
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

        # Drop tabelas na ordem correta para evitar conflito de FK
        conn.execute(text("DROP TABLE IF EXISTS fato_workforce"))
        conn.execute(text("DROP TABLE IF EXISTS dim_data"))
        conn.execute(text("DROP TABLE IF EXISTS dim_regiao"))
        conn.execute(text("DROP TABLE IF EXISTS dim_colaborador"))
        conn.execute(text("DROP TABLE IF EXISTS dim_cliente"))

        dim_data.to_sql("dim_data",               conn, if_exists="replace", index=False)
        dim_regiao.to_sql("dim_regiao",           conn, if_exists="replace", index=False)
        dim_colaborador.to_sql("dim_colaborador", conn, if_exists="replace", index=False)
        dim_cliente.to_sql("dim_cliente",         conn, if_exists="replace", index=False)
        fato_workforce.to_sql("fato_workforce",   conn, if_exists="replace", index=False)

        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    print("\n✅ Mock data gerado e carregado com sucesso!")
    print("\n Resumo:")
    print(f"   dim_data:         {len(dim_data):>5} registros")
    print(f"   dim_regiao:       {len(dim_regiao):>5} registros")
    print(f"   dim_colaborador:  {len(dim_colaborador):>5} registros")
    print(f"   dim_cliente:      {len(dim_cliente):>5} registros")
    print(f"   fato_workforce:   {len(fato_workforce):>5} registros")
    print("=" * 55)

if __name__ == "__main__":
    main()
