# 🗂️ Modelo de Dados — Esboço
**Projeto:** GlobalForce · Workforce Management | BI  
**Etapa:** S0 — Planejamento  
**Status:** ✅ Concluído

---

## 1. Tipo de Modelo

**Modelo Estrela (Star Schema)**

Escolhido por ser o padrão ideal para Metabase: alta performance em consultas, fácil criação de queries SQL e leitura intuitiva para o usuário final.

---

## 2. Tabela Fato

### `fato_workforce`
Tabela central do modelo. Cada linha representa um registro mensal de um colaborador em uma alocação.

| Campo | Tipo | Descrição |
|---|---|---|
| `assignment_id` | INT (FK) | Referência para dim_cliente |
| `employee_id` | INT (FK) | Referência para dim_colaborador |
| `date_id` | INT (FK) | Referência para dim_data |
| `region_id` | INT (FK) | Referência para dim_regiao |
| `worked_hours` | FLOAT | Horas efetivamente trabalhadas |
| `planned_hours` | FLOAT | Horas planejadas no período |
| `overtime_hours` | FLOAT | Horas extras registradas |
| `monthly_cost` | FLOAT | Custo do colaborador no período |
| `goal_achievement` | FLOAT | % de atingimento de metas |

---

## 3. Tabelas Dimensão

### `dim_colaborador`
| Campo | Tipo | Descrição |
|---|---|---|
| `employee_id` | INT (PK) | Identificador único |
| `name` | VARCHAR | Nome do colaborador |
| `department` | VARCHAR | Departamento |
| `hire_date` | DATE | Data de admissão |
| `termination_date` | DATE | Data de desligamento (NULL = ativo) |
| `status` | VARCHAR | Active / Terminated |

---

### `dim_data`
| Campo | Tipo | Descrição |
|---|---|---|
| `date_id` | INT (PK) | Identificador único |
| `period` | DATE | Mês de referência (YYYY-MM-01) |
| `month` | INT | Número do mês (1-12) |
| `quarter` | INT | Trimestre (1-4) |
| `year` | INT | Ano |
| `is_current_period` | BOOLEAN | Flag para o período atual |

---

### `dim_regiao`
| Campo | Tipo | Descrição |
|---|---|---|
| `region_id` | INT (PK) | Identificador único |
| `region_name` | VARCHAR | Nome da região |
| `state` | VARCHAR | Estado |
| `country` | VARCHAR | País |
| `timezone` | VARCHAR | Fuso horário |

---

### `dim_cliente`
| Campo | Tipo | Descrição |
|---|---|---|
| `assignment_id` | INT (PK) | Identificador único da alocação |
| `client_id` | INT | Identificador do cliente |
| `client_name` | VARCHAR | Nome do cliente |
| `role` | VARCHAR | Cargo/função do colaborador |
| `status` | VARCHAR | Active / Closed |

---

## 4. Relacionamentos

| De | Para | Cardinalidade |
|---|---|---|
| `dim_colaborador` | `fato_workforce` | 1 : N |
| `dim_data` | `fato_workforce` | 1 : N |
| `dim_regiao` | `fato_workforce` | 1 : N |
| `dim_cliente` | `fato_workforce` | 1 : N |

---

## 5. Queries SQL (principais)

```sql
-- Turnover %
SELECT
  d.period,
  ROUND(COUNT(CASE WHEN c.status = 'Terminated' THEN 1 END) * 100.0 / COUNT(*), 2) AS turnover_pct
FROM fato_workforce f
JOIN dim_colaborador c ON f.employee_id = c.employee_id
JOIN dim_data d ON f.date_id = d.date_id
GROUP BY d.period;

-- Utilização de Capacidade %
SELECT
  d.period,
  ROUND(SUM(f.worked_hours) * 100.0 / SUM(f.planned_hours), 2) AS utilizacao_pct
FROM fato_workforce f
JOIN dim_data d ON f.date_id = d.date_id
GROUP BY d.period;

-- Custo Total por Região
SELECT
  r.region_name,
  SUM(f.monthly_cost) AS custo_total
FROM fato_workforce f
JOIN dim_regiao r ON f.region_id = r.region_id
GROUP BY r.region_name
ORDER BY custo_total DESC;

-- Atingimento de Metas % por Cliente
SELECT
  cl.client_name,
  ROUND(AVG(f.goal_achievement), 2) AS meta_pct
FROM fato_workforce f
JOIN dim_cliente cl ON f.assignment_id = cl.assignment_id
GROUP BY cl.client_name
ORDER BY meta_pct DESC;
```

---

## 6. Próximos Passos (S0 → S1)

- [x] Documentar fluxo completo ponta a ponta
- [x] Definir stack tecnológica final
- [x] Criar mock data baseado nesse modelo (MySQL)
- [ ] Criar as tabelas no MySQL Workbench
- [ ] Conectar o MySQL ao Metabase
- [ ] Criar as primeiras Questions e Dashboard no Metabase
