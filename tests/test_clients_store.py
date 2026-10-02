import json
import os

import pytest

import clients_store


def test_migration_assigns_stable_ids(tmp_path):
    path = tmp_path / "clients.json"
    path.write_text(json.dumps([{"name": "Sem Id"}, {"id": "keep", "name": "Com Id"}]), encoding="utf-8")

    first = clients_store.load_clients(str(path))
    second = clients_store.load_clients(str(path))

    assert first[0]["id"] and first[1]["id"] == "keep"
    assert [c["id"] for c in first] == [c["id"] for c in second]
    assert json.loads(path.read_text(encoding="utf-8"))[0]["id"] == first[0]["id"]


def test_add_update_delete_by_id(clients_file):
    new = clients_store.add_client("Gamma", "g@example.com", "")
    assert clients_store.get_client(new["id"])["name"] == "Gamma"

    updated = clients_store.update_client("aaa111", {"email": "novo@example.com"})
    assert updated["email"] == "novo@example.com" and updated["name"] == "Alpha Group"

    assert clients_store.delete_client("bbb222") is True
    assert [c["id"] for c in clients_store.load_clients()] == ["aaa111", new["id"]]


def test_unknown_id(clients_file):
    assert clients_store.update_client("nao-existe", {"name": "X"}) is None
    assert clients_store.delete_client("nao-existe") is False


def test_failed_write_keeps_original_file(clients_file, monkeypatch):
    original = clients_file.read_text(encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(clients_store.json, "dump", boom)
    with pytest.raises(OSError):
        clients_store.add_client("Gamma")

    assert clients_file.read_text(encoding="utf-8") == original
    assert os.listdir(clients_file.parent) == ["clients.json"]  # nenhum temporário sobrando
