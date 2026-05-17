# GlobalForce · Workforce Management BI

> Projeto desenvolvido no programa **NoCountry** — simulação de ambiente profissional de tecnologia.  
> Equipe: S04-26 | Data Science

---

## Sobre o Projeto

Sistema de Business Intelligence para gestão de força de trabalho que automatiza a geração e entrega de relatórios executivos mensais para clientes corporativos.

O processo que antes levava **3 dias de trabalho manual no Excel** passou a ser executado em **menos de 1 hora**, com envio automático por e-mail e WhatsApp.

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
Envio por E-mail + WhatsApp (CallMeBot)
```

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
| Geração de PDF | Playwright (headless browser) |
| Envio de E-mail | Gmail SMTP (smtplib) |
| Envio de WhatsApp | CallMeBot API (gratuito) |

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

### 3. Configurar credenciais
Copie o arquivo de exemplo e preencha com seus dados:
```bash
cp .env.example .env
```

Edite o `.env`:
```
DB_PASSWORD=sua_senha_mysql
SENDER_EMAIL=seu@gmail.com
SENDER_PASSWORD=sua_senha_de_app
CALLMEBOT_API_KEY=sua_chave_callmebot
```

### 4. Configurar o WhatsApp (CallMeBot)
1. Adicione o contato **+34 613 01 49 37** no seu WhatsApp
2. Envie a mensagem: `I allow callmebot to send me messages`
3. Você receberá sua API key em segundos
4. Cole a chave no `.env` em `CALLMEBOT_API_KEY`

### 5. Subir o Metabase
Baixe o `metabase.jar` em https://www.metabase.com/start/oss/jar.html  
Salve em uma pasta sem acentos ou espaços (ex: `C:\metabase\`) e rode:
```bash
java -jar metabase.jar
```
Acesse `http://localhost:3000` e conecte ao banco `workforce_bi`.

### 6. Popular o banco de dados
```bash
python etl/generate_mock_data.py
```

### 7. Iniciar o sistema
```bash
python globalforce.py
```
O menu principal permite gerenciar clientes e gerar relatórios em um único lugar. Os PDFs são salvos em `reports/` e enviados automaticamente por e-mail e WhatsApp.

---

## Configurar Clientes

Edite o `clients.json` com os dados reais dos seus clientes:
```json
[
  {
    "name": "Nome do Cliente",
    "email": "email@cliente.com",
    "whatsapp": "+5511999990000"
  }
]
```

---

## Estrutura do Projeto

```
globalforce-workforce-bi/
├── globalforce.py             # Ponto de entrada — menu principal
├── etl/
│   ├── pipeline.py            # ETL principal — carga no MySQL
│   ├── generate_mock_data.py  # Geração de dados sintéticos
│   └── report_generator.py   # Geração de PDF + envio email/WhatsApp
├── dashboard/
│   └── 01_metabase_queries.sql  # Queries SQL dos KPIs
├── docs/                      # Documentação técnica completa
├── notebooks/                 # Exploração e prototipagem
├── reports/                   # PDFs gerados (ignorado pelo git)
├── clients.json               # Lista de clientes
├── .env.example               # Modelo de configuração
└── requirements.txt           # Dependências Python
```

---

## Equipe — NoCountry S04-26

| Participante | Contribuição |
|---|---|
| **André Luiz Ribeiro** | Arquitetura do sistema, pipeline ETL, modelagem do banco de dados (star schema) e dashboard Metabase |
| **Arley** | Suporte ao projeto |
| **André Teixeira** | Automação de entrega de relatórios — geração de PDF com Playwright, envio por e-mail (Gmail SMTP) e WhatsApp (CallMeBot) |

---

## Licença

MIT License — veja o arquivo `LICENSE` para mais detalhes.
