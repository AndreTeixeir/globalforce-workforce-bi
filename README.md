# GlobalForce · Workforce Management BI

[![tests](https://github.com/AndreTeixeir/globalforce-workforce-bi/actions/workflows/tests.yml/badge.svg)](https://github.com/AndreTeixeir/globalforce-workforce-bi/actions/workflows/tests.yml)

> Projeto desenvolvido no programa **NoCountry** — simulação de ambiente profissional de tecnologia.
> Equipe: S04-26 | Data Science

---

## Sobre o Projeto

Sistema de Business Intelligence para gestão de força de trabalho que automatiza a geração e entrega de relatórios executivos mensais para clientes corporativos.

O processo que antes levava **3 dias de trabalho manual no Excel** passou a ser executado em **menos de 1 hora**, com envio automático do PDF por e-mail e notificação por WhatsApp.

O sistema pode ser operado por uma **interface web (Flask)** ou por um **menu de terminal (CLI)** — ambos permitem gerenciar clientes e disparar a geração e o envio dos relatórios.

---

## Fluxo do Sistema

```
Dados (CSV)
    ↓
ETL Python → MySQL (star schema)
    ↓
Dashboard Metabase (KPIs interativos)
    ↓
Geração de PDF automática (Playwright)
    ↓
Envio do PDF por E-mail + notificação por WhatsApp (CallMeBot, número de teste)
```

A geração e o envio são disparados pela interface web ou pela CLI, que consomem os dados do MySQL e orquestram o pipeline.

---

## KPIs Monitorados

| Indicador | Descrição | Benchmark |
|---|---|---|
| Turnover % | Taxa de rotatividade mensal | < 5% |
| Custo por Região | Distribuição de custos (USD) | — |
| Capacidade Operacional | Horas trabalhadas / planejadas | 75–95% |
| Atingimento de Metas | Performance vs. metas por cliente | > 80% |

---

## Stack Tecnológica

| Etapa | Ferramenta |
|---|---|
| ETL | Python 3.11, Pandas, SQLAlchemy |
| Banco de Dados | MySQL 8.x |
| Modelagem | Star schema (1 fato + 4 dimensões) |
| Dashboard | Metabase (open source) |
| Interface Web | Flask (API REST + painel com atualização em tempo real via SSE) |
| Interface CLI | Menu de terminal em Python |
| Geração de PDF | Playwright (headless browser) |
| Envio de E-mail | Gmail SMTP (smtplib) |
| Envio de WhatsApp | CallMeBot API (gratuito — notificação para número de teste) |
| Testes | pytest + GitHub Actions |

---

## Como Configurar e Rodar

### 1. Pré-requisitos
- Python 3.11+
- MySQL 8.x rodando localmente
- Java 11+ (para o Metabase)
- Conta Gmail com Senha de App ativada

### 2. Instalar dependências
```bash
pip install -r requirements.txt
playwright install chromium
```
As versões estão fixadas em `requirements.txt` (testadas com Python 3.11 e 3.12).

### 3. Configurar credenciais
Copie o arquivo de exemplo e preencha com seus dados:
```bash
cp .env.example .env
```

Edite o `.env` (o arquivo é ignorado pelo git — credenciais nunca vão para o repositório):
```
APP_USERNAME=admin                      # login da interface web
APP_PASSWORD=uma_senha_forte
DB_PASSWORD=sua_senha_mysql
METABASE_DASHBOARD_URL=http://localhost:3000/public/dashboard/SEU-UUID
SENDER_EMAIL=seu@gmail.com
SENDER_PASSWORD=sua_senha_de_app
CALLMEBOT_API_KEY=sua_chave_callmebot
CALLMEBOT_PHONE=+55DDDSEUNUMERO         # número que cadastrou a chave
```
Todas as variáveis disponíveis estão descritas em `.env.example`.

### 4. Configurar o WhatsApp (CallMeBot)
1. Adicione o contato **+34 613 01 49 37** no seu WhatsApp
2. Envie a mensagem: `I allow callmebot to send me messages`
3. Você receberá sua API key em segundos
4. Cole a chave no `.env` em `CALLMEBOT_API_KEY` e o seu número em `CALLMEBOT_PHONE`

> **Ambiente de teste:** a API gratuita do CallMeBot só entrega mensagens ao número que gerou a chave. Por isso, neste projeto o WhatsApp funciona como **notificação para um número de teste** (definido apenas no `.env`, fora do código e do git), avisando que o relatório de cada cliente foi gerado e enviado por e-mail. O campo `whatsapp` do cadastro de clientes não é usado no envio. Enviar para os clientes exigiria a API oficial do WhatsApp Business.

### 5. Subir o Metabase
Baixe o `metabase.jar` em https://www.metabase.com/start/oss/jar.html
Salve em uma pasta sem acentos ou espaços (ex: `C:\metabase\`) e rode:
```bash
java -jar metabase.jar
```
Acesse `http://localhost:3000` e conecte ao banco `workforce_bi`.

As queries dos KPIs estão em `dashboard/01_metabase_queries.sql`. Ao atualizar esse arquivo, **cole a nova versão na pergunta correspondente dentro do Metabase** — o Metabase guarda a própria cópia do SQL. Depois, gere o link público do dashboard e coloque-o em `METABASE_DASHBOARD_URL` no `.env`.

### 6. Popular o banco de dados
Escolha **uma** das opções (cada uma recria as tabelas):
```bash
python etl/generate_mock_data.py   # base pequena de demonstração
python etl/pipeline.py             # base completa a partir do CSV (~3,1M linhas)
```
O `pipeline.py` grava tudo em tabelas temporárias e só troca as tabelas no final: se a carga falhar no meio, os dados anteriores continuam intactos e o script termina com código de erro.

### 7. Iniciar o sistema

**Opção A — Interface web (Flask):**
```bash
python app.py
```
Acesse `http://localhost:5000` e entre com o `APP_USERNAME`/`APP_PASSWORD` do `.env`. Por segurança, o servidor escuta apenas na própria máquina (`127.0.0.1`) e o modo debug fica desligado (ative com `FLASK_DEBUG=1` só durante o desenvolvimento). O painel permite gerenciar clientes, acompanhar os KPIs e gerar/enviar relatórios, com progresso do pipeline exibido em tempo real.

**Opção B — Menu de terminal (CLI):**
```bash
python globalforce.py
```
O menu principal permite gerenciar clientes e gerar relatórios em um único lugar.

Em ambos os modos, os PDFs são salvos em `reports/`, enviados por e-mail e notificados por WhatsApp (número de teste). A falha de um cliente não interrompe os demais, e o resumo final indica quais clientes tiveram problema.

### 8. Rodar os testes
```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```
Os testes não precisam de MySQL, Metabase, e-mail nem WhatsApp (tudo é simulado) e rodam automaticamente no GitHub Actions a cada push.

---

## Configurar Clientes

Gerencie os clientes pela interface web ou pelo menu de terminal, ou edite o `clients.json` diretamente. **Use dados de exemplo/teste** — evite expor e-mails e telefones reais em um repositório público.

Cada cliente tem um `id` fixo, usado pela API (`/api/clients/<id>`). Se você adicionar um cliente à mão sem `id`, ele recebe um automaticamente na próxima leitura. O nome precisa ser igual ao `client_name` cadastrado no banco, pois é o filtro usado no dashboard.
```json
[
  {
    "id": "a1f3c9e20b47",
    "name": "Nome do Cliente",
    "email": "contato@exemplo.com",
    "whatsapp": "+5511999990000"
  }
]
```

---

## Estrutura do Projeto

```
globalforce-workforce-bi/
├── app.py                     # Interface web (Flask) — API REST + painel
├── globalforce.py             # Interface CLI — menu de terminal
├── clients_store.py           # Leitura/gravação segura do clients.json
├── templates/
│   └── index.html            # Front-end do painel web
├── etl/
│   ├── pipeline.py            # ETL principal — carga no MySQL
│   ├── generate_mock_data.py  # Geração de dados sintéticos
│   └── report_generator.py   # Geração de PDF + envio email/WhatsApp
├── dashboard/
│   └── 01_metabase_queries.sql  # Queries SQL dos KPIs
├── docs/                      # Documentação técnica completa
├── notebooks/                 # Exploração e prototipagem
├── reports/                   # PDFs gerados (ignorado pelo git)
├── tests/                     # Testes automatizados (pytest)
├── .github/workflows/         # CI — lint e testes a cada push
├── clients.json               # Lista de clientes
├── .env.example               # Modelo de configuração
├── pyproject.toml             # Configuração do ruff e do pytest
├── requirements.txt           # Dependências Python (versões fixadas)
└── requirements-dev.txt       # Dependências de desenvolvimento (testes e lint)
```

---

## Equipe — NoCountry S04-26

| Participante | Contribuição |
|---|---|
| **André Luiz Ribeiro** | Arquitetura do sistema, pipeline ETL, modelagem do banco de dados (star schema) e dashboard Metabase |
| **Arley** | Suporte ao projeto |
| **André Teixeira** | Interface web (Flask — API REST com CRUD de clientes e painel em tempo real), menu CLI unificado e automação de entrega de relatórios: geração de PDF com Playwright e envio por e-mail (Gmail SMTP) e WhatsApp (CallMeBot) |

---

## Licença

MIT License — veja o arquivo `LICENSE` para mais detalhes.
