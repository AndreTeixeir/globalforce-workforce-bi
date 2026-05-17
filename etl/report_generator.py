"""
=============================================================
GlobalForce · Workforce Management | BI
Script: report_generator.py
Etapa: S3 — Automação, Relatório PDF, E-mail e WhatsApp
Descrição: Gera relatórios executivos em PDF a partir de
           dashboards do Metabase usando Playwright,
           e envia automaticamente por e-mail e WhatsApp.
=============================================================
"""

import os
import json
import time
import smtplib
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÕES ---
METABASE_DASHBOARD_URL = "http://localhost:3000/public/dashboard/b323dde1-1cc4-487e-bee7-a2ecfb7a0a29"
OUTPUT_DIR = "reports"
CLIENTS_FILE = "clients.json"

# SMTP (e-mail)
SMTP_SERVER   = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL  = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# CallMeBot (WhatsApp)
CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY")


def load_clients():
    with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"--- Pasta '{OUTPUT_DIR}' criada.")


def generate_report(client_name, region=None, period=None):
    ensure_output_dir()

    with sync_playwright() as p:
        print(f"--- Iniciando navegador para: {client_name}...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 1600})
        page = context.new_page()

        params = {"client": client_name}
        if region:
            params["region"] = region
        if period:
            params["date"] = period

        url_with_filters = f"{METABASE_DASHBOARD_URL}?{urllib.parse.urlencode(params)}"
        print(f"--- Acessando: {url_with_filters}")

        filepath = None
        try:
            page.goto(url_with_filters, wait_until="load")
            print("--- Aguardando processamento dos dados (20s)...")
            time.sleep(20)

            filename = f"Relatorio_Executivo_{client_name.replace(' ', '_')}_{time.strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(OUTPUT_DIR, filename)

            page.pdf(
                path=filepath,
                format="A4",
                print_background=True,
                margin={"top": "20px", "bottom": "20px", "left": "20px", "right": "20px"}
            )
            print(f"--- ✅ Relatório gerado: {filepath}")

        except Exception as e:
            print(f"--- ❌ ERRO ao gerar relatório para {client_name}: {e}")

        finally:
            browser.close()

    return filepath


def send_email(to_email, client_name, attachment_path):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("--- ⚠️  Credenciais de e-mail não configuradas no .env — pulando envio.")
        return

    period = datetime.now().strftime("%B/%Y")
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

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with open(attachment_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print(f"--- 📧 E-mail enviado para: {to_email}")
    except Exception as e:
        print(f"--- ❌ Falha ao enviar e-mail para {to_email}: {e}")


def send_whatsapp(to_number, client_name, attachment_path):
    if not CALLMEBOT_API_KEY:
        print("--- ⚠️  CALLMEBOT_API_KEY não configurada no .env — pulando WhatsApp.")
        return

    period = datetime.now().strftime("%B/%Y")
    message_body = (
        f"📊 GlobalForce | Workforce Management BI\n\n"
        f"Olá! O relatório executivo de {client_name} referente a {period} "
        f"já está disponível.\n\n"
        f"📎 O documento foi enviado por e-mail com os seguintes indicadores:\n"
        f"• Turnover\n"
        f"• Capacidade Operacional\n"
        f"• Custos Regionais\n"
        f"• Atingimento de Metas\n\n"
        f"GlobalForce — Workforce Management BI"
    )

    # número sem o +
    phone = to_number.lstrip("+")
    encoded_msg = urllib.parse.quote(message_body)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_msg}&apikey={CALLMEBOT_API_KEY}"

    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                print(f"--- 💬 WhatsApp enviado para: {to_number}")
            else:
                print(f"--- ❌ Falha ao enviar WhatsApp para {to_number}: status {response.status}")
    except Exception as e:
        print(f"--- ❌ Falha ao enviar WhatsApp para {to_number}: {e}")


def run_full_pipeline(clients=None):
    """
    Executa o pipeline completo para todos os clientes (ou lista específica):
    Gera PDF → Envia e-mail → Envia WhatsApp.
    """
    all_clients = load_clients()

    if clients:
        targets = [c for c in all_clients if c["name"] in clients]
    else:
        targets = all_clients

    print(f"\n--- 📊 Iniciando pipeline para {len(targets)} cliente(s)...\n")

    for client in targets:
        name  = client["name"]
        email = client.get("email")
        phone = client.get("whatsapp")

        print(f"\n{'='*50}")
        print(f"  Cliente: {name}")
        print(f"{'='*50}")

        filepath = generate_report(name)

        if filepath:
            if email:
                send_email(email, name, filepath)
            if phone:
                send_whatsapp(phone, name, filepath)

    print("\n--- ✅ Pipeline concluído!\n")


if __name__ == "__main__":
    # Para rodar para todos os clientes do clients.json:
    run_full_pipeline()

    # Para rodar apenas para clientes específicos, descomente:
    # run_full_pipeline(clients=["Alpha Group", "Beta Corp"])
