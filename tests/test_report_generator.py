import os
import time
import urllib.parse
from datetime import datetime

import pytest

import etl.report_generator as rg


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(rg, "OUTPUT_DIR", str(tmp_path / "reports"))
    monkeypatch.setattr(rg, "METABASE_DASHBOARD_URL", "http://metabase.local/public/dashboard/x")
    monkeypatch.setattr(rg, "REPORT_EXTRA_WAIT_SECONDS", 0)


# ── Playwright falso ──────────────────────────────────────────────────────────

class FakePage:
    def __init__(self, pdf_error=None):
        self.pdf_error = pdf_error
        self.visited = None

    def goto(self, url, wait_until=None):
        self.visited = url

    def wait_for_load_state(self, state, timeout=None):
        pass

    def pdf(self, path, **kwargs):
        with open(path, "wb") as f:
            f.write(b"%PDF parcial")
        if self.pdf_error:
            raise self.pdf_error


class FakeBrowser:
    def __init__(self, page):
        self.page, self.closed = page, False

    def new_page(self, **kwargs):
        return self.page

    def close(self):
        self.closed = True


class FakePlaywright:
    def __init__(self, browser):
        self.chromium = self
        self.browser = browser

    def launch(self, **kwargs):
        return self.browser

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def use_fake_browser(monkeypatch, page):
    browser = FakeBrowser(page)
    monkeypatch.setattr(rg, "sync_playwright", lambda: FakePlaywright(browser))
    return browser


def todays_file(name="Alpha_Group"):
    return os.path.join(rg.OUTPUT_DIR, f"Relatorio_Executivo_{name}_{time.strftime('%Y%m%d')}.pdf")


# ── Testes ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name, expected", [
    ("Alpha Group", "Alpha_Group"),
    ("Ação & Cia.", "Acao_Cia"),
    ("../../etc/passwd", "etc_passwd"),
    ("x');alert(1);('", "x_alert_1"),
    ("///", "cliente"),
])
def test_safe_filename_part(name, expected):
    assert rg.safe_filename_part(name) == expected


def test_current_period_in_portuguese():
    assert rg.current_period(datetime(2026, 3, 15)) == "Março/2026"


def test_generate_report_success(monkeypatch):
    page = FakePage()
    browser = use_fake_browser(monkeypatch, page)
    path = rg.generate_report("Alpha Group", log=lambda m: None)
    assert path == todays_file()
    assert os.path.exists(path) and not os.path.exists(path + ".part")
    assert browser.closed
    assert urllib.parse.parse_qs(urllib.parse.urlparse(page.visited).query) == {"client": ["Alpha Group"]}


def test_pdf_failure_returns_none_even_with_stale_file(monkeypatch):
    """C2: falha no page.pdf não pode devolver caminho nem reaproveitar PDF antigo."""
    os.makedirs(rg.OUTPUT_DIR)
    with open(todays_file(), "wb") as f:
        f.write(b"%PDF antigo")
    browser = use_fake_browser(monkeypatch, FakePage(pdf_error=RuntimeError("crash")))

    assert rg.generate_report("Alpha Group", log=lambda m: None) is None
    assert not os.path.exists(todays_file() + ".part")
    assert browser.closed


def test_missing_dashboard_url(monkeypatch):
    monkeypatch.setattr(rg, "METABASE_DASHBOARD_URL", None)
    assert rg.generate_report("Alpha Group", log=lambda m: None) is None


def test_pipeline_continues_after_failures(monkeypatch):
    calls = []

    def fake_generate(name, log=print):
        if name == "Quebra":
            raise RuntimeError("navegador não abriu")
        if name == "Sem PDF":
            return None
        return f"/tmp/{name}.pdf"

    monkeypatch.setattr(rg, "generate_report", fake_generate)
    monkeypatch.setattr(rg, "send_email", lambda to, name, path, log=print: calls.append(("email", name)) or True)
    monkeypatch.setattr(rg, "send_whatsapp", lambda name, log=print: calls.append(("whats", name)) or True)

    failures = rg.run_full_pipeline([
        {"name": "Quebra", "email": "a@example.com"},
        {"name": "Sem PDF", "email": "b@example.com"},
        {"name": "Ok", "email": "c@example.com"},
    ], log=lambda m: None)

    assert failures == ["Quebra", "Sem PDF"]
    assert calls == [("email", "Ok"), ("whats", "Ok")]


def test_send_failure_marks_client_as_failed(monkeypatch):
    monkeypatch.setattr(rg, "generate_report", lambda name, log=print: "/tmp/x.pdf")
    monkeypatch.setattr(rg, "send_email", lambda *a, **k: False)
    monkeypatch.setattr(rg, "send_whatsapp", lambda *a, **k: None)  # não configurado não é falha
    assert rg.run_full_pipeline([{"name": "A", "email": "a@example.com"}], log=lambda m: None) == ["A"]


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.timeout, self.sent = timeout, []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        pass

    def send_message(self, msg):
        self.sent.append(msg)


def test_send_email_uses_timeout_and_handles_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(rg, "SENDER_EMAIL", "bot@example.com")
    monkeypatch.setattr(rg, "SENDER_PASSWORD", "x")
    monkeypatch.setattr(rg.smtplib, "SMTP", FakeSMTP)
    FakeSMTP.instances.clear()

    pdf = tmp_path / "r.pdf"
    pdf.write_bytes(b"%PDF")
    assert rg.send_email("c@example.com", "Alpha", str(pdf), log=lambda m: None) is True
    assert FakeSMTP.instances[0].timeout == rg.SEND_TIMEOUT_SECONDS

    assert rg.send_email("c@example.com", "Alpha", str(tmp_path / "nao-existe.pdf"), log=lambda m: None) is False


def test_send_email_not_configured(monkeypatch):
    monkeypatch.setattr(rg, "SENDER_EMAIL", None)
    assert rg.send_email("c@example.com", "Alpha", "/x.pdf", log=lambda m: None) is None


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_whatsapp_goes_to_test_number_with_timeout(monkeypatch):
    seen = {}

    def fake_urlopen(url, timeout=None):
        seen["url"], seen["timeout"] = url, timeout
        return FakeResponse()

    logs = []
    monkeypatch.setattr(rg, "CALLMEBOT_API_KEY", "chave-secreta")
    monkeypatch.setattr(rg, "CALLMEBOT_PHONE", "+5511900000000")
    monkeypatch.setattr(rg.urllib.request, "urlopen", fake_urlopen)

    assert rg.send_whatsapp("Alpha Group", log=logs.append) is True
    query = urllib.parse.parse_qs(urllib.parse.urlparse(seen["url"]).query)
    assert query["phone"] == ["5511900000000"]
    assert "Alpha Group" in query["text"][0]
    assert seen["timeout"] == rg.SEND_TIMEOUT_SECONDS
    assert not any("chave-secreta" in m or "5511900000000" in m for m in logs)


@pytest.mark.parametrize("key, phone", [(None, "+55119"), ("k", None)])
def test_whatsapp_not_configured(monkeypatch, key, phone):
    monkeypatch.setattr(rg, "CALLMEBOT_API_KEY", key)
    monkeypatch.setattr(rg, "CALLMEBOT_PHONE", phone)
    assert rg.send_whatsapp("Alpha", log=lambda m: None) is None
