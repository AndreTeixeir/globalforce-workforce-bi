"""
=============================================================
GlobalForce · Workforce Management | BI
Script: report_generator.py
Etapa: S3 — Automação, Relatório PDF, E-mail e WhatsApp
Descrição: Gera relatórios executivos em PDF a partir de
           dashboards do Metabase usando Playwright,
           envia o PDF por e-mail e uma notificação por
           WhatsApp para o número de teste configurado.
=============================================================
"""

import json
import os
import re
import smtplib
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

load_dotenv()

# --- CONFIGURAÇÕES ---
# Caminhos absolutos: o script funciona de qualquer diretório.
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR   = os.path.join(BASE_DIR, "reports")
CLIENTS_FILE = os.path.join(BASE_DIR, "clients.json")

# Link público do dashboard no Metabase (fica no .env, não no código)
METABASE_DASHBOARD_URL = os.getenv("METABASE_DASHBOARD_URL")

# Espera pelos gráficos: aguarda a rede ficar ociosa (até o limite) e
# depois uma folga extra configurável para a renderização terminar.
NETWORK_IDLE_TIMEOUT_MS   = 60_000
REPORT_EXTRA_WAIT_SECONDS = float(os.getenv("REPORT_EXTRA_WAIT_SECONDS", "5"))

# Limite para conexões externas (SMTP e CallMeBot) não travarem o pipeline
SEND_TIMEOUT_SECONDS = 30

# SMTP (e-mail)
SMTP_SERVER     = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT       = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL    = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# CallMeBot (WhatsApp) — a chave só envia para o número que a cadastrou,
# por isso a notificação vai para um número de teste definido no .env.
CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY")
CALLMEBOT_PHONE   = os.getenv("CALLMEBOT_PHONE")

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def current_period(now=None):
    """Mês/ano em português, independente do locale do sistema."""
    now = now or datetime.now()
    return f"{MESES[now.month - 1]}/{now.year}"


def safe_filename_part(name):
    """Converte o nome do cliente em um trecho seguro para nome de arquivo."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9-]+", "_", ascii_name).strip("_")
    return cleaned or "cliente"


def load_clients():
    with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_output_dir(log=print):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        log(f"--- Pasta '{OUTPUT_DIR}' criada.")


def generate_report(client_name, region=None, period=None, log=print):
    """Gera o PDF do cliente. Retorna o caminho do arquivo ou None em caso de falha."""
    if not METABASE_DASHBOARD_URL:
        log("--- ❌ METABASE_DASHBOARD_URL não configurada no .env — não é possível gerar o PDF.")
        return None

    ensure_output_dir(log)

    params = {"client": client_name}
    if region:
        params["region"] = region
    if period:
        params["date"] = period
    url_with_filters = f"{METABASE_DASHBOARD_URL}?{urllib.parse.urlencode(params)}"

    filename = f"Relatorio_Executivo_{safe_filename_part(client_name)}_{time.strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)
    # Escreve num arquivo temporário e só renomeia se o PDF terminar:
    # assim uma falha nunca deixa um PDF parcial ou reaproveita um antigo.
    tmp_path = filepath + ".part"

    with sync_playwright() as p:
        log(f"--- Iniciando navegador para: {client_name}...")
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 1600})
            log(f"--- Acessando o dashboard com filtro: {client_name}")
            page.goto(url_with_filters, wait_until="load")

            log("--- Aguardando os gráficos carregarem...")
            try:
                page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                log("--- ⚠️  A página não ficou ociosa no tempo limite — seguindo com a captura.")
            if REPORT_EXTRA_WAIT_SECONDS > 0:
                time.sleep(REPORT_EXTRA_WAIT_SECONDS)

            page.pdf(
                path=tmp_path,
                format="A4",
                print_background=True,
                margin={"top": "20px", "bottom": "20px", "left": "20px", "right": "20px"},
            )
            os.replace(tmp_path, filepath)
        except Exception as e:
            log(f"--- ❌ ERRO ao gerar relatório para {client_name}: {e}")
            return None
        finally:
            browser.close()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    log(f"--- ✅ Relatório gerado: {filename}")
    return filepath


def send_email(to_email, client_name, attachment_path, log=print):
    """Retorna True se enviou, False se falhou e None se o envio não está configurado."""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        log("--- ⚠️  Credenciais de e-mail não configuradas no .env — pulando envio.")
        return None

    period = current_period()
    subject = f"Relatório Executivo Workforce — {client_name} | {period}"
    body = (
        f"Prezados,\n\n"
        f"Segue em anexo o relatório executivo de gestão de força de trabalho "
        f"referente ao período de {period}.\n\n"
        f"O documento contém os principais indicadores:\n"
        f"  • Turnover\n"
        f"  • Capacidade Operacional\n"
        f"  • Custos Regionais\n"
        f"  • Atingimento de Metas\n\n"
        f"Qualquer dúvida estamos à disposição.\n\n"
        f"Atenciosamente,\n"
        f"GlobalForce — Workforce Management BI"
    )

    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=SEND_TIMEOUT_SECONDS) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        log(f"--- 📧 E-mail enviado para: {to_email}")
        return True
    except Exception as e:
        log(f"--- ❌ Falha ao enviar e-mail para {to_email}: {e}")
        return False


def send_whatsapp(client_name, log=print):
    """
    Envia a notificação para o número de teste (CALLMEBOT_PHONE).
    O CallMeBot gratuito só entrega mensagens ao número dono da API key,
    então o WhatsApp cadastrado de cada cliente não é usado aqui.
    Retorna True se enviou, False se falhou e None se não está configurado.
    """
    if not CALLMEBOT_API_KEY or not CALLMEBOT_PHONE:
        log("--- ⚠️  CALLMEBOT_API_KEY/CALLMEBOT_PHONE não configurados no .env — pulando WhatsApp.")
        return None

    message_body = (
        f"📊 GlobalForce | Workforce Management BI\n\n"
        f"Olá! O relatório executivo de {client_name} referente a {current_period()} "
        f"já está disponível.\n\n"
        f"📎 O documento foi enviado por e-mail com os seguintes indicadores:\n"
        f"• Turnover\n"
        f"• Capacidade Operacional\n"
        f"• Custos Regionais\n"
        f"• Atingimento de Metas\n\n"
        f"GlobalForce — Workforce Management BI"
    )

    query = urllib.parse.urlencode({
        "phone": CALLMEBOT_PHONE.lstrip("+"),
        "text": message_body,
        "apikey": CALLMEBOT_API_KEY,
    })
    url = f"https://api.callmebot.com/whatsapp.php?{query}"

    try:
        with urllib.request.urlopen(url, timeout=SEND_TIMEOUT_SECONDS) as response:
            if response.status == 200:
                log(f"--- 💬 Notificação de WhatsApp enviada (relatório de {client_name}).")
                return True
            log(f"--- ❌ Falha ao enviar WhatsApp: status {response.status}")
            return False
    except Exception as e:
        log(f"--- ❌ Falha ao enviar WhatsApp: {e}")
        return False


def run_full_pipeline(targets=None, log=print):
    """
    Executa o pipeline completo para a lista de clientes recebida
    (ou todos do clients.json): Gera PDF → Envia e-mail → Notifica no WhatsApp.

    A falha de um cliente não interrompe os demais.
    Retorna a lista de nomes dos clientes que tiveram alguma falha.
    """
    if targets is None:
        targets = load_clients()

    log(f"--- 📊 Iniciando pipeline para {len(targets)} cliente(s)...")
    failures = []

    for client in targets:
        name  = client.get("name", "?")
        email = client.get("email")

        log("=" * 50)
        log(f"  Cliente: {name}")
        log("=" * 50)

        try:
            filepath = generate_report(name, log=log)
            if not filepath:
                failures.append(name)
                continue

            ok = True
            if email:
                ok = send_email(email, name, filepath, log=log) is not False and ok
            else:
                log("--- ⚠️  Cliente sem e-mail cadastrado — pulando envio.")
            ok = send_whatsapp(name, log=log) is not False and ok
            if not ok:
                failures.append(name)
        except Exception as e:
            log(f"--- ❌ ERRO inesperado no cliente {name}: {e}")
            failures.append(name)

    if failures:
        log(f"--- ⚠️  Pipeline concluído com falhas em: {', '.join(failures)}")
    else:
        log("--- ✅ Pipeline concluído sem falhas!")
    return failures


if __name__ == "__main__":
    # Para rodar para todos os clientes do clients.json:
    failed = run_full_pipeline()
    sys.exit(1 if failed else 0)
