import json
import os
import re

import numpy as np
import pandas as pd
import pytest

import etl.generate_mock_data as mock
import etl.pipeline as pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sample_csv_frame():
    return pd.DataFrame({
        "period":          ["2023-01-01", "2023-01-01", "2023-02-01", "2023-02-01", "2023-03-01"],
        "employee_id":     [1, 2, 1, 2, 1],
        "region":          ["West", "South", "West", "South", "West"],
        "state":           ["CA", "TX", "CA", "TX", "CA"],
        "department":      ["HR", "Sales", "HR", "Sales", "Finance"],
        "role":            ["Senior", "Manager", "Senior", "Manager", "Director"],
        "monthly_cost":    [100.0, 200.0, 110.0, 210.0, 300.0],
        "planned_hours":   [160.0] * 5,
        "worked_hours":    [150.0, 160.0, 155.0, 170.0, 140.0],
        "overtime_hours":  [0.0, 0.0, 0.0, 10.0, 0.0],
        "goal_achievement": [90.0, 80.0, 95.0, 85.0, 70.0],
        "status_in_month": ["Active", "Active", "Active", "Terminated", "Active"],
    })


def test_dimensions_from_chunks_match_single_pass():
    df = sample_csv_frame()
    chunked = pipeline.build_dimensions([df.iloc[:2], df.iloc[2:4], df.iloc[4:]])
    single = pipeline.build_dimensions([df])
    for a, b in zip(chunked, single):
        pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))

    dim_regiao, dim_data, dim_colaborador = chunked
    assert list(dim_data["date_id"]) == [1, 2, 3] and dim_data["is_current_period"].tolist() == [False, False, True]
    # colaborador 1 deve vir do registro mais recente (março)
    assert dim_colaborador.set_index("employee_id").loc[1, "role"] == "Director"


def maps_for(df):
    dim_regiao, dim_data, _ = pipeline.build_dimensions([df])
    regiao_map = dim_regiao.set_index(["region_name", "state"])["region_id"].to_dict()
    data_map = dict(zip(dim_data["period"].dt.strftime("%Y-%m-%d"), dim_data["date_id"]))
    return regiao_map, data_map


def test_fact_chunk_is_reproducible():
    df = sample_csv_frame()
    regiao_map, data_map = maps_for(df)
    a = pipeline.build_fact_chunk(df, regiao_map, data_map, np.random.default_rng(42))
    b = pipeline.build_fact_chunk(df, regiao_map, data_map, np.random.default_rng(42))
    pd.testing.assert_frame_equal(a, b)
    assert a["is_terminated"].tolist() == [0, 0, 0, 1, 0]
    assert a["assignment_id"].between(1, len(pipeline.CLIENTES)).all()


def test_fact_chunk_rejects_unknown_keys():
    df = sample_csv_frame()
    regiao_map, data_map = maps_for(df.iloc[:2])  # dimensões sem fevereiro/março
    with pytest.raises(ValueError, match="sem região ou período"):
        pipeline.build_fact_chunk(df, regiao_map, data_map, np.random.default_rng(0))


@pytest.mark.parametrize("module", [pipeline, mock])
def test_engine_url_handles_special_password(module, monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "p@ss:w/rd")
    monkeypatch.setenv("DB_HOST", "db.local")
    engine = module.get_engine()
    assert engine.url.password == "p@ss:w/rd"
    assert engine.url.host == "db.local"


def test_client_names_match_dashboard_data():
    """M1: o PDF filtra o dashboard pelo nome — clients.json precisa existir nas duas fontes de dados."""
    with open(os.path.join(ROOT, "clients.json"), encoding="utf-8") as f:
        names = {c["name"] for c in json.load(f)}
    assert names <= {n for _, n in pipeline.CLIENTES}
    assert names <= {n for _, n in mock.CLIENTES}


def test_metabase_queries_join_every_filtered_table():
    """C1: cada filtro usado numa query exige o JOIN da tabela correspondente."""
    with open(os.path.join(ROOT, "dashboard", "01_metabase_queries.sql"), encoding="utf-8") as f:
        sql = re.sub(r"/\*.*?\*/", "", f.read(), flags=re.S)
    queries = [q for q in sql.split(";") if "SELECT" in q]
    assert len(queries) == 4
    required = {"client": "dim_cliente", "region": "dim_regiao", "date": "dim_data"}
    for q in queries:
        for flt, table in required.items():
            if "{{" + flt + "}}" in q:
                assert re.search(rf"JOIN\s+{table}\b", q), f"query sem JOIN {table}:\n{q}"
