# 📖 Dicionário de Dados
**Projeto:** GlobalForce · Workforce Management | BI  
**Etapa:** S1 — Modelagem de Dados  
**Status:** ✅ Concluído

---

## 1. Visão Geral

Este dicionário documenta todas as tabelas, campos, tipos e regras de negócio do banco de dados `workforce_bi`. Serve como referência para desenvolvedores, analistas e stakeholders que interagem com os dados do projeto.

| Tabela | Tipo | Descrição |
|---|---|---|
| `fato_workforce` | Fato | Registros mensais de alocação, horas e custos |
| `dim_colaborador` | Dimensão | Cadastro de colaboradores |
| `dim_data` | Dimensão | Calendário de períodos |
| `dim_regiao` | Dimensão | Regiões geográficas |
| `dim_cliente` | Dimensão | Alocações e clientes |

---

## 2. Tabela Fato

### `fato_workforce`
Tabela central do modelo. Cada linha representa um registro mensal de um colaborador em uma alocação específica.

| Campo | Tipo | Nulo | Descrição | Exemplo |
|---|---|---|---|---|
| `id` | INT | Não | Chave primária auto-incremental | 1 |
| `assignment_id` | INT | Não | FK → dim_cliente.assignment_id | 42 |
| `employee_id` | INT | Não | FK → dim_colaborador.employee_id | 15 |
| `date_id` | INT | Não | FK → dim_data.date_id | 7 |
| `region_id` | INT | Não | FK → dim_regiao.region_id | 3 |
| `worked_hours` | FLOAT | Não | Horas efetivamente trabalhadas no período | 152.5 |
| `planned_hours` | FLOAT | Não | Horas planejadas para o período | 160.0 |
| `overtime_hours` | FLOAT | Não | Horas extras (worked - planned, mín. 0) | 8.0 |
| `monthly_cost` | FLOAT | Não | Custo mensal do colaborador em USD | 8500.00 |
| `goal_achievement` | FLOAT | Não | % de atingimento de metas (0-100) | 87.5 |

**Regras de negócio:**
- `overtime_hours` = MAX(0, `worked_hours` - `planned_hours`)
- `goal_achievement` entre 0 e 100
- Um colaborador pode ter múltiplos registros por período (uma linha por alocação)

---

## 3. Tabelas Dimensão

### `dim_colaborador`
Cadastro completo dos colaboradores da GlobalForce.

| Campo | Tipo | Nulo | Descrição | Exemplo |
|---|---|---|---|---|
| `employee_id` | INT | Não | Chave primária | 15 |
| `name` | VARCHAR(100) | Não | Nome completo | João Silva |
| `department` | VARCHAR(100) | Não | Departamento | Tecnologia |
| `region` | VARCHAR(100) | Não | Região de atuação | São Paulo |
| `hire_date` | DATE | Não | Data de admissão | 2021-03-15 |
| `termination_date` | DATE | Sim | Data de desligamento (NULL = ativo) | 2024-06-30 |
| `monthly_cost` | FLOAT | Não | Custo mensal em USD | 8500.00 |
| `status` | VARCHAR(20) | Não | Status atual | Active / Terminated |
| `goal_achievement` | FLOAT | Não | % médio de atingimento de metas | 87.5 |

**Regras de negócio:**
- `termination_date` NULL indica colaborador ativo
- `status` = "Active" quando `termination_date` é NULL
- `status` = "Terminated" quando `termination_date` está preenchida
- Turnover é calculado com base nos colaboradores com `status` = "Terminated" no período

---

### `dim_data`
Tabela calendário para análise temporal dos KPIs.

| Campo | Tipo | Nulo | Descrição | Exemplo |
|---|---|---|---|---|
| `date_id` | INT | Não | Chave primária | 7 |
| `period` | DATE | Não | Primeiro dia do mês de referência | 2024-07-01 |
| `month` | INT | Não | Número do mês (1-12) | 7 |
| `quarter` | INT | Não | Trimestre (1-4) | 3 |
| `year` | INT | Não | Ano | 2024 |
| `is_current_period` | BOOL | Não | TRUE apenas para o período atual | TRUE / FALSE |

**Regras de negócio:**
- `period` sempre representa o primeiro dia do mês (YYYY-MM-01)
- Apenas um registro pode ter `is_current_period` = TRUE
- `quarter` = ((month - 1) / 3) + 1

---

### `dim_regiao`
Regiões geográficas de atuação (Padrão US Census).

| Campo | Tipo | Nulo | Descrição | Exemplo |
|---|---|---|---|---|
| `region_id` | INT | Não | Chave primária | 1 |
| `region_name` | VARCHAR(100) | Não | Nome da região macro | Northeast |
| `state` | VARCHAR(10) | Não | Estado (sigla) | NY |
| `country` | VARCHAR(100) | Não | País | USA |

**Regiões cadastradas:**

| region_id | region_name | Estados (Exemplos) |
|---|---|---|
| 1 | Northeast | NY, MA, PA, NJ, CT |
| 2 | Midwest | IL, OH, MI, IN, WI |
| 3 | South | TX, FL, GA, NC, VA |
| 4 | West | CA, WA, AZ, CO, OR |

---

### `dim_cliente`
Alocações de colaboradores por cliente e função.

| Campo | Tipo | Nulo | Descrição | Exemplo |
|---|---|---|---|---|
| `assignment_id` | INT | Não | Chave primária | 42 |
| `client_id` | INT | Não | Identificador do cliente | 1 |
| `client_name` | VARCHAR(100) | Não | Nome do cliente | Empresa Alpha |
| `role` | VARCHAR(100) | Não | Cargo/função na alocação | Analista Sr. |
| `status` | VARCHAR(20) | Não | Status da alocação | Active / Closed |

**Clientes cadastrados:**

| client_id | client_name |
|---|---|
| 1 | Empresa Alpha |
| 2 | Grupo Beta |
| 3 | Corporação Gamma |
| 4 | Holding Delta |
| 5 | Conglomerado Epsilon |

**Funções disponíveis:** Associate · Specialist · Senior · Manager · Director

---

## 4. Relacionamentos

```
dim_colaborador (employee_id) ──────────────┐
                                             ↓
dim_cliente (assignment_id) ──────→ fato_workforce
                                             ↑
dim_data (date_id) ──────────────────────────┤
                                             │
dim_regiao (region_id) ──────────────────────┘
```

| Origem | Campo | Destino | Campo | Tipo |
|---|---|---|---|---|
| fato_workforce | employee_id | dim_colaborador | employee_id | N:1 |
| fato_workforce | assignment_id | dim_cliente | assignment_id | N:1 |
| fato_workforce | date_id | dim_data | date_id | N:1 |
| fato_workforce | region_id | dim_regiao | region_id | N:1 |

---

## 5. Glossário

| Termo | Definição |
|---|---|
| **Turnover** | Taxa de desligamento de colaboradores em relação ao headcount total do período |
| **Headcount** | Número total de colaboradores ativos em um determinado período |
| **Utilização de Capacidade** | Percentual de horas trabalhadas em relação às horas planejadas |
| **Horas Extras** | Horas trabalhadas acima do planejado (worked_hours - planned_hours) |
| **Custo por Região** | Soma do custo mensal de todos os colaboradores de uma região |
| **Atingimento de Metas** | Percentual médio de cumprimento das metas estabelecidas por colaborador |
| **Alocação (Assignment)** | Vínculo entre um colaborador e um cliente em um determinado período |
| **Período** | Mês de referência dos dados (granularidade mínima = 1 mês) |
| **Mock Data** | Dados fictícios gerados para desenvolvimento e testes |

---

## 6. Próximos Passos (S1)

- [x] Criar modelo de dados unificado
- [x] Criar mock data e popular as tabelas
- [x] Documentar dicionário de dados
- [x] Construir pipeline ETL em Python conectando os CSVs ao MySQL
- [x] Validar integridade e qualidade dos dados
