# 📧 Guia: Automação de Envio de E-mails
**Projeto:** GlobalForce · Workforce Management | BI  
**Status:** 📅 Planejado para Futura Implementação

Este documento descreve como implementar o envio automático dos relatórios executivos (PDF) gerados pelo sistema diretamente para os stakeholders via e-mail.

---

## 1. Visão Geral do Fluxo

```
Gerador de PDF (report_generator.py)
        ↓
Arquivo .pdf salvo em /reports
        ↓
Função send_email_with_attachment()
        ↓
Servidor SMTP (Gmail/Outlook/Empresa)
        ↓
Caixa de entrada do Cliente
```

---

## 2. Implementação Sugerida (Python)

Abaixo está o código-base que deve ser integrado ao `etl/report_generator.py`.

### Bibliotecas Necessárias
Não é necessário instalar bibliotecas externas, pois o Python já possui suporte nativo ao protocolo SMTP.

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

def send_email_with_attachment(to_email, subject, body, attachment_path):
    # Configurações do Servidor (Recomendado usar Variáveis de Ambiente)
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    # Criação da mensagem
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Anexa o PDF
    with open(attachment_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)

    # Envio
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls() # Inicia conexão segura
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print(f"--- 📧 E-mail enviado com sucesso para: {to_email}")
    except Exception as e:
        print(f"--- ❌ Falha ao enviar e-mail: {e}")
```

---

## 3. Como Configurar (Setup)

### Passo 1: Obter Credenciais SMTP
- **Gmail**: É necessário criar uma "Senha de App" nas configurações de segurança da conta Google.
- **Outlook/Office 365**: Use `smtp.office365.com` na porta 587.

### Passo 2: Criar arquivo `.env`
Para segurança, nunca coloque senhas diretamente no código. Crie um arquivo `.env` na raiz do projeto:
```env
SENDER_EMAIL=seu-email@gmail.com
SENDER_PASSWORD=sua-senha-de-app
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### Passo 3: Integrar no Loop
No script `report_generator.py`, após a linha `page.pdf(...)`, basta chamar a função:
```python
# Exemplo de integração
filepath = "reports/Relatorio_Alpha.pdf"
send_email_with_attachment(
    to_email="cliente@empresa.com",
    subject="Relatório Executivo Workforce - GlobalForce",
    body="Olá, segue em anexo o relatório atualizado.",
    attachment_path=filepath
)
```

---

## 4. Próximos Passos Recomendados
- [ ] Criar uma tabela no MySQL ou um arquivo JSON para mapear `Nome do Cliente` -> `E-mail do Stakeholder`.
- [ ] Implementar logs de envio para auditoria.
- [ ] Adicionar tratamento para e-mails que retornarem (Bounce).
