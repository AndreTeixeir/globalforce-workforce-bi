import base64
import threading
from decimal import Decimal

import pytest

import app as app_module
import etl.report_generator as report_generator

USER, PASSWORD = "admin", "s3nha-forte"


def auth_header(user=USER, password=PASSWORD):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def client(clients_file, tmp_path, monkeypatch):
    monkeypatch.setenv("APP_USERNAME", USER)
    monkeypatch.setenv("APP_PASSWORD", PASSWORD)
    monkeypatch.setattr(app_module, "REPORTS_DIR", str(tmp_path / "reports"))
    with app_module.app.test_client() as c:
        c.environ_base.update({"HTTP_AUTHORIZATION": auth_header()["Authorization"]})
        yield c


@pytest.fixture
def anon(clients_file, monkeypatch):
    monkeypatch.setenv("APP_USERNAME", USER)
    monkeypatch.setenv("APP_PASSWORD", PASSWORD)
    return app_module.app.test_client()


# ── Autenticação ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/", "/api/clients", "/api/kpis", "/api/reports/list", "/reports/file/x.pdf"])
def test_requires_login(anon, path):
    r = anon.get(path)
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"].startswith("Basic")


def test_wrong_password_rejected(anon):
    assert anon.get("/api/clients", headers=auth_header(password="errada")).status_code == 401
    assert anon.get("/api/clients", headers=auth_header(user="outro")).status_code == 401


def test_correct_login(anon):
    assert anon.get("/api/clients", headers=auth_header()).status_code == 200


def test_fails_closed_when_not_configured(clients_file, monkeypatch):
    monkeypatch.delenv("APP_USERNAME", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    r = app_module.app.test_client().get("/api/clients", headers=auth_header("", ""))
    assert r.status_code == 503


# ── Clientes ──────────────────────────────────────────────────────────────────

def test_crud_by_id(client):
    r = client.post("/api/clients", json={"name": "Gamma", "email": "g@example.com"})
    assert r.status_code == 201
    new_id = r.get_json()["id"]

    r = client.put(f"/api/clients/{new_id}", json={"whatsapp": "+55 11 99999-0000"})
    assert r.status_code == 200 and r.get_json()["name"] == "Gamma"

    assert client.delete("/api/clients/aaa111").status_code == 200
    ids = [c["id"] for c in client.get("/api/clients").get_json()]
    assert ids == ["bbb222", new_id]


def test_unknown_id_returns_404(client):
    assert client.put("/api/clients/nao-existe", json={"name": "X"}).status_code == 404
    assert client.delete("/api/clients/nao-existe").status_code == 404


@pytest.mark.parametrize("body", [
    {},
    {"name": ""},
    {"name": "   "},
    {"name": ["lista"]},
    {"name": "A" * 201},
    {"name": "Ok", "email": "sem-arroba"},
    {"name": "Ok", "whatsapp": "abc"},
])
def test_create_validation(client, body):
    r = client.post("/api/clients", json=body)
    assert r.status_code == 400
    assert "error" in r.get_json()


@pytest.mark.parametrize("raw", ["null", "[1, 2]", "nao é json"])
def test_invalid_bodies_return_400(client, raw):
    for method, url in (("post", "/api/clients"), ("put", "/api/clients/aaa111")):
        r = getattr(client, method)(url, data=raw, content_type="application/json")
        assert r.status_code == 400


# ── KPIs ──────────────────────────────────────────────────────────────────────

class FakeCursor:
    def __init__(self, row, error=None):
        self.row, self.error = row, error

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql):
        if self.error:
            raise self.error

    def fetchone(self):
        return self.row


class FakeConn:
    def __init__(self, row=None, error=None):
        self.row, self.error, self.closed = row, error, False

    def cursor(self):
        return FakeCursor(self.row, self.error)

    def close(self):
        self.closed = True


def test_kpis_returns_numbers(client, monkeypatch):
    conn = FakeConn({"turnover_pct": Decimal("4.84"), "utilization_pct": Decimal("93.71"),
                     "total_cost": Decimal("1234567.89"), "avg_goal": Decimal("87.25")})
    monkeypatch.setattr(app_module, "get_db", lambda: conn)
    r = client.get("/api/kpis")
    assert r.get_json() == {"turnover": 4.8, "utilization": 93.7, "total_cost": 1234568.0, "avg_goal": 87.2}
    assert conn.closed


def test_kpis_error_is_generic_and_closes_connection(client, monkeypatch):
    conn = FakeConn(error=RuntimeError("Access denied for user 'root'@'10.0.0.5'"))
    monkeypatch.setattr(app_module, "get_db", lambda: conn)
    r = client.get("/api/kpis")
    assert r.status_code == 500
    assert "10.0.0.5" not in r.get_data(as_text=True)
    assert conn.closed


# ── Pipeline ──────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_pipeline(monkeypatch):
    """Substitui o pipeline real por um controlável pelo teste."""
    state = {"release": threading.Event(), "targets": None, "result": []}

    def fake_run(targets, log=print):
        state["targets"] = targets
        log("linha 1\nlinha 2")
        state["release"].wait(timeout=5)
        if isinstance(state["result"], Exception):
            raise state["result"]
        return state["result"]

    monkeypatch.setattr(report_generator, "run_full_pipeline", fake_run)
    yield state
    state["release"].set()


def read_stream(client):
    return client.get("/api/reports/stream").get_data(as_text=True)


def test_second_run_is_rejected_while_running(client, fake_pipeline):
    assert client.post("/api/reports/run", json={}).status_code == 200
    assert client.post("/api/reports/run", json={}).status_code == 409
    fake_pipeline["release"].set()
    assert "data: __DONE__:ok" in read_stream(client)
    # depois de terminar, pode rodar de novo
    assert client.post("/api/reports/run", json={}).status_code == 200
    fake_pipeline["release"].set()
    read_stream(client)


def test_concurrent_requests_start_only_one_pipeline(clients_file, monkeypatch, fake_pipeline):
    monkeypatch.setenv("APP_USERNAME", USER)
    monkeypatch.setenv("APP_PASSWORD", PASSWORD)
    barrier = threading.Barrier(8)
    codes = []

    def hit():
        c = app_module.app.test_client()
        barrier.wait()
        codes.append(c.post("/api/reports/run", json={}, headers=auth_header()).status_code)

    threads = [threading.Thread(target=hit) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(codes) == [200] + [409] * 7
    fake_pipeline["release"].set()
    c = app_module.app.test_client()
    c.get("/api/reports/stream", headers=auth_header())


def test_run_selected_client_by_id(client, fake_pipeline):
    fake_pipeline["release"].set()
    assert client.post("/api/reports/run", json={"client_ids": ["bbb222"]}).status_code == 200
    read_stream(client)
    assert [c["name"] for c in fake_pipeline["targets"]] == ["Beta Corp"]


@pytest.mark.parametrize("body", [{"client_ids": "bbb222"}, {"client_ids": [1]}, {"client_ids": ["nao-existe"]}])
def test_run_rejects_invalid_ids(client, body):
    assert client.post("/api/reports/run", json=body).status_code == 400


def test_stream_splits_multiline_and_reports_failure(client, fake_pipeline):
    fake_pipeline["result"] = ["Alpha Group"]
    fake_pipeline["release"].set()
    client.post("/api/reports/run", json={})
    body = read_stream(client)
    assert "data: linha 1\n\n" in body and "data: linha 2\n\n" in body
    assert body.rstrip().endswith("data: __DONE__:error")


def test_pipeline_exception_reports_error_and_releases_lock(client, fake_pipeline):
    fake_pipeline["result"] = RuntimeError("quebrou")
    fake_pipeline["release"].set()
    client.post("/api/reports/run", json={})
    body = read_stream(client)
    assert "quebrou" in body and "__DONE__:error" in body
    assert not app_module._pipeline_lock.locked()


def test_format_sse_prefixes_every_line():
    assert app_module._format_sse("a\nb") == "data: a\ndata: b\n\n"


# ── Relatórios / front-end ────────────────────────────────────────────────────

def test_list_reports(client, tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "Relatorio_Executivo_Alpha_Group_20261001.pdf").write_bytes(b"%PDF")
    (reports / "outro.txt").write_text("x")
    data = client.get("/api/reports/list").get_json()
    assert data == [{"filename": "Relatorio_Executivo_Alpha_Group_20261001.pdf", "client": "Alpha Group",
                     "date": "01/10/2026", "date_raw": "20261001"}]


def test_template_does_not_inline_filenames_in_js(client):
    html = client.get("/").get_data(as_text=True)
    assert "openReport('${" not in html
    assert 'data-filename="${esc(rep.filename)}"' in html
    assert "&#39;" in html  # esc() também escapa aspas simples
