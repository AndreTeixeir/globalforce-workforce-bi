"""
GlobalForce · Workforce Management BI
Interface web Flask — substitui o menu de terminal.
"""

import io
import json
import os
import queue
import re
import sys
import threading

import pymysql
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context

load_dotenv()

app = Flask(__name__)

CLIENTS_FILE = os.path.join(os.path.dirname(__file__), "clients.json")
REPORTS_DIR  = os.path.join(os.path.dirname(__file__), "reports")

_pipeline_queue: queue.Queue = queue.Queue()
_pipeline_running = False


# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "workforce_bi"),
        cursorclass=pymysql.cursors.DictCursor,
    )


# ── Clients helpers ───────────────────────────────────────────────────────────

def load_clients():
    with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_clients(clients):
    with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/kpis")
def get_kpis():
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
        conn.close()
        return jsonify({
            "turnover":    round(row["turnover_pct"]    or 0, 1),
            "utilization": round(row["utilization_pct"] or 0, 1),
            "total_cost":  round(row["total_cost"]      or 0, 0),
            "avg_goal":    round(row["avg_goal"]        or 0, 1),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/clients", methods=["GET"])
def get_clients():
    return jsonify(load_clients())


@app.route("/api/clients", methods=["POST"])
def add_client():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Nome obrigatório"}), 400
    clients = load_clients()
    clients.append({
        "name":     data["name"],
        "email":    data.get("email", ""),
        "whatsapp": data.get("whatsapp", ""),
    })
    save_clients(clients)
    return jsonify({"ok": True})


@app.route("/api/clients/<int:idx>", methods=["PUT"])
def edit_client(idx):
    data = request.get_json()
    clients = load_clients()
    if idx < 0 or idx >= len(clients):
        return jsonify({"error": "Índice inválido"}), 404
    c = clients[idx]
    if data.get("name"):
        c["name"] = data["name"]
    if "email" in data:
        c["email"] = data["email"]
    if "whatsapp" in data:
        c["whatsapp"] = data["whatsapp"]
    save_clients(clients)
    return jsonify({"ok": True})


@app.route("/api/clients/<int:idx>", methods=["DELETE"])
def delete_client(idx):
    clients = load_clients()
    if idx < 0 or idx >= len(clients):
        return jsonify({"error": "Índice inválido"}), 404
    clients.pop(idx)
    save_clients(clients)
    return jsonify({"ok": True})


# ── Pipeline ──────────────────────────────────────────────────────────────────

class _QueueWriter(io.TextIOBase):
    """Redireciona stdout para a fila SSE."""
    def __init__(self, q: queue.Queue):
        self.q = q

    def write(self, s: str) -> int:
        if s.strip():
            self.q.put(s.strip())
        return len(s)


def _run_pipeline(client_names=None):
    global _pipeline_running
    _pipeline_running = True
    old_stdout = sys.stdout
    sys.stdout = _QueueWriter(_pipeline_queue)
    try:
        from etl.report_generator import run_full_pipeline
        run_full_pipeline(clients=client_names)
    except Exception as e:
        _pipeline_queue.put(f"❌ ERRO: {e}")
    finally:
        sys.stdout = old_stdout
        _pipeline_queue.put("__DONE__")
        _pipeline_running = False


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
    global _pipeline_running
    if _pipeline_running:
        return jsonify({"error": "Pipeline já em execução"}), 409
    data = request.get_json() or {}
    client_names = data.get("clients")
    with _pipeline_queue.mutex:
        _pipeline_queue.queue.clear()
    threading.Thread(target=_run_pipeline, args=(client_names,), daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/reports/stream")
def stream_logs():
    def generate():
        while True:
            try:
                msg = _pipeline_queue.get(timeout=60)
                yield f"data: {msg}\n\n"
                if msg == "__DONE__":
                    break
            except queue.Empty:
                yield "data: \n\n"  # keepalive
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
