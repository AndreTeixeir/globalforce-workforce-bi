# 📂 Mapeamento de Fontes de Dados
**Projeto:** GlobalForce · Workforce Management | BI  
**Etapa:** S0 — Planejamento  
**Status:** ✅ Concluído

---

## 1. Visão Geral das Fontes

O pipeline de dados do projeto é alimentado por três fontes principais, todas internas à GlobalForce:

| Fonte | Arquivo | Formato | Frequência de Atualização |
|---|---|---|---|
| Assignments | `assignments.csv` | CSV | Mensal |
| Hours | `hours.csv` | CSV | Mensal |
| Headcount | `headcount.csv` | CSV | Mensal |

---

## 2. Detalhamento por Fonte

### 📄 assignments.csv — Alocações de Colaboradores
Registra as alocações de cada colaborador por cliente, região e período.

| Campo | Tipo | Descrição | Exemplo |
|---|---|---|---|
| `assignment_id` | INT | Identificador único da alocação | 1001 |
| `employee_id` | INT | Identificador do colaborador | 5042 |
| `client_id` | INT | Identificador do cliente | 301 |
| `region` | VARCHAR | Região de alocação | Northeast |
| `start_date` | DATE | Data de início da alocação | 2024-01-01 |
| `end_date` | DATE | Data de fim da alocação | 2024-01-31 |
| `role` | VARCHAR | Cargo/função do colaborador | Senior |
| `status` | VARCHAR | Status da alocação | Active / Closed |

---

### ⏱️ hours.csv — Horas Trabalhadas
Registra as horas trabalhadas por colaborador por período.

| Campo | Tipo | Descrição | Exemplo |
|---|---|---|---|
| `hour_id` | INT | Identificador único do registro | 8801 |
| `employee_id` | INT | Identificador do colaborador | 5042 |
| `assignment_id` | INT | Alocação referente | 1001 |
| `period` | DATE | Mês de referência | 2024-01-01 |
| `planned_hours` | FLOAT | Horas planejadas no período | 160.0 |
| `worked_hours` | FLOAT | Horas efetivamente trabalhadas | 152.5 |
| `overtime_hours` | FLOAT | Horas extras registradas | 8.0 |

---

### 👥 headcount.csv — Quadro de Colaboradores
Registra informações dos colaboradores e seus custos associados.

| Campo | Tipo | Descrição | Exemplo |
|---|---|---|---|
| `employee_id` | INT | Identificador único do colaborador | 5042 |
| `name` | VARCHAR | Nome do colaborador | John Smith |
| `department` | VARCHAR | Departamento | Engineering |
| `region` | VARCHAR | Região de atuação | Northeast |
| `hire_date` | DATE | Data de admissão | 2021-03-15 |
| `termination_date` | DATE | Data de desligamento (se houver) | NULL |
| `monthly_cost` | FLOAT | Custo mensal do colaborador (USD) | 12000.00 |
| `status` | VARCHAR | Status atual | Active / Terminated |
| `goal_achievement` | FLOAT | % de atingimento de metas | 87.5 |

---

## 3. Relacionamentos entre as Fontes

```
headcount (employee_id) ─────┐
                              ├──→ assignments (employee_id, assignment_id)
hours (employee_id,           │
       assignment_id) ────────┘
```

- **headcount → assignments:** 1 colaborador pode ter N alocações
- **assignments → hours:** 1 alocação pode ter N registros de horas (1 por mês)
- **headcount → hours:** 1 colaborador pode ter N registros de horas

---

## 4. Regras de Negócio Identificadas

| Regra | Descrição |
|---|---|
| **Turnover** | Colaboradores com `termination_date` preenchida no período analisado |
| **Capacidade** | `worked_hours / planned_hours * 100` = % de utilização |
| **Custo por Região** | Soma de `monthly_cost` agrupada por `region` |
| **Atingimento de Metas** | Média de `goal_achievement` por cliente/região |

---

## 5. Qualidade e Riscos dos Dados

| Risco | Impacto | Ação |
|---|---|---|
| `termination_date` nula para ativos | Cálculo incorreto de turnover | Filtrar por `status = 'Active'` |
| `worked_hours` zerada | Distorção na utilização | Tratar como NULL no ETL |
| `monthly_cost` inconsistente | Custo por região incorreto | Validar outliers com DESVPAD |
| Colaborador sem alocação | Headcount sem assignment | LEFT JOIN para preservar registros |

---

## 6. Próximos Passos (S1)

- [x] Criar dados sintéticos de exemplo para cada fonte (mock data)
- [ ] Desenvolver script ETL em Python para leitura e tratamento
- [ ] Construir modelo estrela no MySQL e conectar ao Metabase
- [x] Documentar dicionário de dados completo
