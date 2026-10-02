import json

import pytest

import clients_store

SAMPLE_CLIENTS = [
    {"id": "aaa111", "name": "Alpha Group", "email": "a@example.com", "whatsapp": "+5511999990001"},
    {"id": "bbb222", "name": "Beta Corp", "email": "b@example.com", "whatsapp": ""},
]


@pytest.fixture
def clients_file(tmp_path, monkeypatch):
    """clients.json temporário — os testes nunca tocam o arquivo real."""
    path = tmp_path / "clients.json"
    path.write_text(json.dumps(SAMPLE_CLIENTS), encoding="utf-8")
    monkeypatch.setattr(clients_store, "CLIENTS_FILE", str(path))
    return path
