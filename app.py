"""
GlobalForce · Workforce Management BI
Interface web Flask — substitui o menu de terminal.
"""

import hmac
import os
import queue
import re
import threading

import pymysql
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context

import clients_store

load_dotenv()

app = Flask(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")

_pipeline_queue: queue.Queue = queue.Queue()
_pipeline_lock = threading.Lock()

DONE_OK    = "__DONE__:ok"
DONE_ERROR = "__DONE__:error"

MAX_FIELD_LENGTH = 200
EMAIL_RE    = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
WHATSAPP_RE = re.compile(r"^\+?[0-9 ()-]{8,20}$")


# ── Autenticação (HTTP Basic) ─────────────────────────────────────────────────

def _credentials_ok(auth):
    expected_user = os.getenv("APP_USERNAME", "")
    expected_pass = os.getenv("APP_PASSWORD", "")
    if not auth or auth.type != "basic":
        return False
    # Comparação em tempo constante para não vazar informação pelo tempo de resposta
    user_ok = hmac.compare_digest((auth.username or "").encode(), expected_user.encode())
    pass_ok = hmac.compare_digest((auth.password or "").encode(), expected_pass.encode())
    return user_ok and pass_ok


@app.before_request
def require_login():
    if not os.getenv("APP_USERNAME") or not os.getenv("APP_PASSWORD"):
        app.logger.error("APP_USERNAME/APP_PASSWORD não configurados no .env")
        return Response(
            "Autenticação não configurada: defina APP_USERNAME e APP_PASSWORD no arquivo .env.",
            503,
            mimetype="text/plain; charset=utf-8",
        )
    if not _credentials_ok(request.authorization):
        return Response(
            "Login necessário.",
            401,
            {"WWW-Authenticate": 'Basic realm="GlobalForce BI", charset="UTF-8"'},
            mimetype="text/plain; charset=utf-8",
        )
    return None


# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "workforce_bi"),
        cursorclass=pymysql.cursors.DictCursor,
    )


# ── Validação ─────────────────────────────────────────────────────────────────

def _validate_client_payload(data, partial=False):
    """Retorna (campos_limpos, mensagem_de_erro)."""
    if not isinstance(data, dict):
        return None, "Corpo da requisição deve ser um objeto JSON"

    fields = {}
    for key in ("name", "email", "whatsapp"):
        if key not in data:
            continue
        value = data[key]
        if not isinstance(value, str):
            return None, f"Campo '{key}' deve ser texto"
        value = value.strip()
        if len(value) > MAX_FIELD_LENGTH:
            return None, f"Campo '{key}' excede {MAX_FIELD_LENGTH} caracteres"
        fields[key] = value

    if "name" in fields and not fields["name"]:
        return None, "Nome obrigatório"
    if not partial and "name" not in fields:
        return None, "Nome obrigatório"
    if fields.get("email") and not EMAIL_RE.match(fields["email"]):
        return None, "E-mail inválido"
    if fields.get("whatsapp") and not WHATSAPP_RE.match(fields["whatsapp"]):
        return None, "WhatsApp inválido"
    return fields, None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/kpis")
def get_kpis():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (SUM(is_terminated) * 100.0 / COUNT(employee_id)) AS turnover_pct,
                    (SUM(worked_hours) * 100.0 / SUM(planned_hours))  AS utilization_pct,
                    SUM(monthly_cost)                                  AS total_cost,
                    AVG(goal_achievement)                              AS avg_goal
                FROM fato_workforce
            """)
            row = cur.fetchone()
        return jsonify({
            "turnover":    round(float(row["turnover_pct"]    or 0), 1),
            "utilization": round(float(row["utilization_pct"] or 0), 1),
            "total_cost":  round(float(row["total_cost"]      or 0), 0),
            "avg_goal":    round(float(row["avg_goal"]        or 0), 1),
        })
    except Exception:
        # Detalhes (host, usuário, SQL) ficam só no log do servidor
        app.logger.exception("Falha ao consultar KPIs")
        return jsonify({"error": "Não foi possível carregar os KPIs"}), 500
    finally:
        if conn is not None:
            conn.close()


@app.route("/api/clients", methods=["GET"])
def get_clients():
    return jsonify(clients_store.load_clients())


@app.route("/api/clients", methods=["POST"])
def add_client():
    fields, error = _validate_client_payload(request.get_json(silent=True))
    if error:
        return jsonify({"error": error}), 400
    client = clients_store.add_client(
        fields["name"], fields.get("email", ""), fields.get("whatsapp", "")
    )
    return jsonify(client), 201


@app.route("/api/clients/<client_id>", methods=["PUT"])
def edit_client(client_id):
    fields, error = _validate_client_payload(request.get_json(silent=True), partial=True)
    if error:
        return jsonify({"error": error}), 400
    client = clients_store.update_client(client_id, fields)
    if client is None:
        return jsonify({"error": "Cliente não encontrado"}), 404
    return jsonify(client)


@app.route("/api/clients/<client_id>", methods=["DELETE"])
def delete_client(client_id):
    if not clients_store.delete_client(client_id):
        return jsonify({"error": "Cliente não encontrado"}), 404
    return jsonify({"ok": True})


# ── Pipeline ──────────────────────────────────────────────────────────────────

def _log(msg):
    """Envia cada linha do log para a fila do SSE."""
    for line in str(msg).splitlines():
        if line.strip():
            _pipeline_queue.put(line.rstrip())


def _run_pipeline(targets):
    """Roda em thread separada. Assume que _pipeline_lock já foi adquirido."""
    status = DONE_ERROR
    try:
        from etl.report_generator import run_full_pipeline
        failures = run_full_pipeline(targets, log=_log)
        status = DONE_ERROR if failures else DONE_OK
    except Exception as e:
        app.logger.exception("Falha no pipeline")
        _log(f"❌ ERRO: {e}")
    finally:
        _pipeline_queue.put(status)
        _pipeline_lock.release()


def _format_sse(msg):
    # Cada linha precisa do prefixo "data:"; uma linha em branco fecha o evento
    lines = str(msg).splitlines() or [""]
    return "".join(f"data: {line}\n" for line in lines) + "\n"


@app.route("/api/reports/list")
def list_reports():
    if not os.path.exists(REPORTS_DIR):
        return jsonify([])
    pattern = re.compile(r"Relatorio_Executivo_(.+)_(\d{8})\.pdf$")
    files = []
    for fname in os.listdir(REPORTS_DIR):
        m = pattern.match(fname)
        if m:
            client   = m.group(1).replace("_", " ")
            date_raw = m.group(2)
            files.append({
                "filename": fname,
                "client":   client,
                "date":     f"{date_raw[6:8]}/{date_raw[4:6]}/{date_raw[:4]}",
                "date_raw": date_raw,
            })
    files.sort(key=lambda x: (x["date_raw"], x["client"]), reverse=True)
    return jsonify(files)


@app.route("/reports/file/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORTS_DIR, filename, mimetype="application/pdf")


@app.route("/api/reports/run", methods=["POST"])
def run_reports():
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return jsonify({"error": "Corpo da requisição deve ser um objeto JSON"}), 400

    all_clients = clients_store.load_clients()
    client_ids = data.get("client_ids")
    if client_ids is None:
        targets = all_clients
    else:
        if not isinstance(client_ids, list) or not all(isinstance(i, str) for i in client_ids):
            return jsonify({"error": "client_ids deve ser uma lista de ids"}), 400
        targets = [c for c in all_clients if c["id"] in client_ids]
        if not targets:
            return jsonify({"error": "Nenhum cliente encontrado para os ids informados"}), 400

    # Verificação e reserva numa única operação atômica: dois cliques
    # simultâneos nunca iniciam dois pipelines.
    if not _pipeline_lock.acquire(blocking=False):
        return jsonify({"error": "Pipeline já em execução"}), 409
    try:
        with _pipeline_queue.mutex:
            _pipeline_queue.queue.clear()
        threading.Thread(target=_run_pipeline, args=(targets,), daemon=True).start()
    except Exception:
        _pipeline_lock.release()
        raise
    return jsonify({"ok": True})


@app.route("/api/reports/stream")
def stream_logs():
    def generate():
        while True:
            try:
                msg = _pipeline_queue.get(timeout=60)
                yield _format_sse(msg)
                if msg in (DONE_OK, DONE_ERROR):
                    break
            except queue.Empty:
                yield ": keepalive\n\n"
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    # debug só quando FLASK_DEBUG=1; o servidor escuta apenas na máquina local
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    port = int(os.getenv("APP_PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=debug)
