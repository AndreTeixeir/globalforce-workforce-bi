"""
GlobalForce · Workforce Management BI
Armazenamento de clientes (clients.json) compartilhado pela interface
web (app.py) e pelo menu de terminal (globalforce.py).

- Cada cliente tem um "id" fixo; registros antigos sem id recebem um
  automaticamente na primeira leitura.
- A gravação é atômica: escreve num arquivo temporário e troca com
  os.replace, para que uma falha no meio nunca deixe o JSON corrompido.
- Um lock serializa leitura+escrita dentro do mesmo processo.
"""

import json
import os
import tempfile
import threading
import uuid

CLIENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clients.json")

_lock = threading.RLock()


def _new_id():
    return uuid.uuid4().hex[:12]


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(path, clients):
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(prefix=".clients-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(clients, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def load_clients(path=None):
    """Retorna a lista de clientes, garantindo que todos tenham id."""
    path = path or CLIENTS_FILE
    with _lock:
        clients = _read(path)
        missing = [c for c in clients if not c.get("id")]
        if missing:
            for c in missing:
                c["id"] = _new_id()
            _write(path, clients)
        return clients


def save_clients(clients, path=None):
    with _lock:
        _write(path or CLIENTS_FILE, clients)


def get_client(client_id, path=None):
    for c in load_clients(path):
        if c["id"] == client_id:
            return c
    return None


def add_client(name, email="", whatsapp="", path=None):
    with _lock:
        clients = load_clients(path)
        client = {"id": _new_id(), "name": name, "email": email, "whatsapp": whatsapp}
        clients.append(client)
        save_clients(clients, path)
        return client


def update_client(client_id, fields, path=None):
    """Atualiza os campos informados. Retorna o cliente ou None se não existir."""
    with _lock:
        clients = load_clients(path)
        for c in clients:
            if c["id"] == client_id:
                for key in ("name", "email", "whatsapp"):
                    if key in fields:
                        c[key] = fields[key]
                save_clients(clients, path)
                return c
        return None


def delete_client(client_id, path=None):
    """Remove o cliente. Retorna True se removeu, False se não existia."""
    with _lock:
        clients = load_clients(path)
        remaining = [c for c in clients if c["id"] != client_id]
        if len(remaining) == len(clients):
            return False
        save_clients(remaining, path)
        return True
