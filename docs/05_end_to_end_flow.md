# 🔄 Fluxo Completo Ponta a Ponta
**Projeto:** GlobalForce · Workforce Management | BI  
**Etapa:** S0 — Planejamento  
**Status:** ✅ Concluído

---

## 1. Visão Geral do Fluxo

```
┌─────────────────────────────────────────────────────────────────┐
│                        FONTES DE DADOS                          │
│         assignments.csv  │  hours.csv  │  headcount.csv         │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                        ETL (Python)                             │
│   Extração → Limpeza → Transformação → Carga no banco           │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                   BANCO DE DADOS (MySQL)                        │
│   fato_workforce │ dim_colaborador │ dim_data │ dim_regiao       │
│                  │                             │ dim_cliente     │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                        METABASE                                 │
│   Questions (queries) → Dashboard → Filtros interativos         │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     RELATÓRIO EXECUTIVO                         │
│         Exportação PDF com 1 clique → Envio ao cliente          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Detalhamento de Cada Etapa

### Etapa 1 — Carga de Dados
**Responsável:** Analista GlobalForce  
**Frequência:** Mensal

| Ação | Detalhe |
|---|---|
| Receber os arquivos | `assignments.csv`, `hours.csv`, `headcount.csv` do período |
| Validar os arquivos | Verificar se os arquivos estão completos e no formato esperado |
| Depositar na pasta | Copiar para `/data/raw/YYYY-MM/` no repositório |

---

### Etapa 2 — Pipeline ETL (Python)
**Script:** `etl/pipeline.py`  
**Trigger:** Manual ou agendado (cron job mensal)

| Passo | Descrição | Biblioteca |
|---|---|---|
| Extração | Leitura do CSV consolidado de 3.1M de registros | Pandas |
| Transformação | Normalização dos dados e criação das dimensões (Colaborador, Região, Data) | Pandas |
| Cliente | Atribuição de registros a clientes para permitir filtros no dashboard | NumPy |
| Carga | Inserção otimizada via chunks no MySQL | SQLAlchemy + PyMySQL |
| Log | Registro de progresso a cada 500k registros processados | Print/Console |

---

### Etapa 3 — Banco de Dados (MySQL)
**Ambiente:** MySQL Community Edition (local)

| Ação | Detalhe |
|---|---|
| Modelo estrela | Tabelas criadas conforme `docs/03_data_model.md` |
| Atualização | ETL faz upsert (insert or update) para não duplicar dados |
| Backup | Dump mensal antes de cada nova carga (`mysqldump`) |

---

### Etapa 4 — Metabase (Dashboard)
**Acesso:** http://localhost:3000 (dev) / URL do servidor (produção)

| Ação | Detalhe |
|---|---|
| Conexão | Metabase conectado ao MySQL via configuração de banco |
| Questions | Queries SQL salvas para cada KPI (Turnover, Custo, Utilização, Metas) |
| Dashboard | Painel executivo com filtros de Período, Região e Cliente |
| Atualização | Metabase re-executa as queries automaticamente ao abrir o dashboard |

---

### Etapa 5 — Revisão e Exportação
**Responsável:** Analista GlobalForce / Gerente de Conta

| Ação | Detalhe |
|---|---|
| Revisão | Analista verifica os KPIs no dashboard após a carga |
| Filtros | Define os parâmetros no script de geração |
| Exportação | Executa `python globalforce.py` e seleciona a opção de geração de relatórios |
| Envio | Gerente de Conta envia o PDF ao cliente por e-mail |

---

## 3. Diagrama de Responsabilidades

| Etapa | Analista GlobalForce | Gerente de Conta | Sistema (Automático) |
|---|---|---|---|
| Receber arquivos CSV | ✅ | | |
| Executar pipeline ETL | ✅ | | |
| Atualizar banco de dados | | | ✅ |
| Atualizar dashboard | | | ✅ |
| Revisar KPIs | ✅ | | |
| Exportar PDF | ✅ | | |
| Enviar ao cliente | | ✅ | |

---

## 4. Tratamento de Erros

| Cenário | Ação |
|---|---|
| Arquivo CSV ausente ou corrompido | Pipeline aborta e gera log de erro |
| Dados fora do formato esperado | Pipeline registra linhas com problema e continua |
| Falha na conexão com o banco | Pipeline tenta reconectar 3x antes de abortar |
| Dashboard sem dados novos | Metabase exibe aviso de "última atualização em XX/XX" |

---

## 5. Checklist de Execução Mensal

```
[x] Validar a presença do arquivo globalforce_usa_3years_2023_2025.csv
[x] Executar: python etl/pipeline.py
[x] Verificar log de execução (confirmação de 3.1M de registros)
[ ] Acessar o Metabase e confirmar atualização dos KPIs
[ ] Executar: python globalforce.py → opção [5] ou [6]
[ ] Validar arquivos PDF na pasta /reports
[ ] Enviar ao cliente
```

---

## 6. Ambiente de Desenvolvimento

| Componente | Versão recomendada |
|---|---|
| Python | 3.11+ |
| Pandas | 2.x |
| SQLAlchemy | 2.x |
| PyMySQL | 1.x (conector Python → MySQL) |
| MySQL | Community Edition 8.x |
| Metabase | Open Source — latest |
| Docker | Para subir o Metabase localmente |

### Subindo o ambiente local com Docker

```bash
# Clonar o repositório
git clone https://github.com/S04-26-Equipe44-DataScience/workforce-management-bi
cd workforce-management-bi

# Subir Metabase via Docker
docker run -d -p 3000:3000 --name metabase metabase/metabase

# Instalar dependências Python
pip install pandas numpy sqlalchemy pymysql faker

# Executar o pipeline ETL (Processamento e Carga)
python etl/pipeline.py
```

---

## 7. Resumo da S0 — Entregáveis Concluídos

| Entregável | Arquivo | Status |
|---|---|---|
| Mapeamento de fontes | `docs/01_data_sources_mapping.md` | ✅ |
| Definição de KPIs | `docs/02_kpi_definition.md` | ✅ |
| Modelo de dados | `docs/03_data_model.md` | ✅ |
| Fluxo ponta a ponta | `docs/05_end_to_end_flow.md` | ✅ |
| Stack tecnológica | Definida (Python + MySQL + Metabase) | ✅ |

**S0 concluída. Próxima etapa: S1 — Modelagem de Dados.**
