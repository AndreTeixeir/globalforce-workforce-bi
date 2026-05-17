# 📊 Definição e Validação de KPIs
**Projeto:** GlobalForce · Workforce Management | BI  
**Etapa:** S0 — Planejamento  
**Status:** ✅ Concluído

---

## 1. Stakeholders Envolvidos

| Stakeholder | Perfil | Necessidade Principal |
|---|---|---|
| **Analista GlobalForce** | Técnico | Dados precisos, atualizados e fáceis de carregar |
| **Gerente de Conta** | Negócio | Visão executiva clara para apresentar ao cliente |
| **Cliente Corporativo** | Executivo | Resumo do status da força de trabalho no período |

---

## 2. KPIs Definidos

### 🔴 KPI 1 — Turnover
> Taxa de rotatividade de colaboradores no período analisado.

| Atributo | Detalhe |
|---|---|
| **Fórmula** | `(Nº de desligamentos no período / Headcount médio do período) * 100` |
| **Fonte** | `headcount.csv` → campo `termination_date` e `status` |
| **Unidade** | % (percentual) |
| **Frequência** | Mensal |
| **Meta de referência** | < 5% ao mês (benchmark mercado) |
| **Alerta** | > 5% → sinalizar em vermelho no dashboard |
| **Stakeholder principal** | Gerente de Conta / Cliente |

---

### 🟡 KPI 2 — Custo por Região
> Distribuição do custo total da força de trabalho por região geográfica.

| Atributo | Detalhe |
|---|---|
| **Fórmula** | `SUM(monthly_cost) GROUP BY region` |
| **Fonte** | `headcount.csv` → campo `monthly_cost` + `region` |
| **Unidade** | R$ (reais) |
| **Frequência** | Mensal |
| **Visão adicional** | % de participação de cada região no custo total |
| **Stakeholder principal** | Gerente de Conta / Cliente |

---

### 🟢 KPI 3 — Utilização de Capacidade
> Percentual de aproveitamento da capacidade disponível da força de trabalho.

| Atributo | Detalhe |
|---|---|
| **Fórmula** | `(SUM(worked_hours) / SUM(planned_hours)) * 100` |
| **Fonte** | `hours.csv` → campos `worked_hours` e `planned_hours` |
| **Unidade** | % (percentual) |
| **Frequência** | Mensal |
| **Meta de referência** | Entre 75% e 95% (abaixo = ociosidade / acima = sobrecarga) |
| **Alertas** | < 75% → ociosidade / > 95% → risco de sobrecarga |
| **Stakeholder principal** | Analista GlobalForce / Gerente de Conta |

---

### 🔵 KPI 4 — Atingimento de Metas
> Percentual médio de atingimento das metas estabelecidas por colaborador/cliente.

| Atributo | Detalhe |
|---|---|
| **Fórmula** | `AVG(goal_achievement) GROUP BY client_id` |
| **Fonte** | `headcount.csv` → campo `goal_achievement` |
| **Unidade** | % (percentual) |
| **Frequência** | Mensal |
| **Meta de referência** | > 80% considerado satisfatório |
| **Alerta** | < 80% → sinalizar atenção no relatório executivo |
| **Stakeholder principal** | Gerente de Conta / Cliente |

---

## 3. KPIs Secundários (Complementares)

Além dos 4 KPIs principais, os seguintes indicadores agregam valor ao relatório executivo:

| KPI | Fórmula | Fonte | Utilidade |
|---|---|---|---|
| **Headcount Total** | `COUNT(employee_id) WHERE status = 'Active'` | headcount | Visão geral do quadro ativo |
| **Horas Extras** | `SUM(overtime_hours)` | hours | Identificar sobrecarga por região |
| **Custo por Colaborador** | `SUM(monthly_cost) / COUNT(employee_id)` | headcount | Benchmark de custo médio |
| **Novas Contratações** | `COUNT WHERE hire_date no período` | headcount | Crescimento do quadro |

---

## 4. Matriz de Prioridade dos KPIs

| KPI | Impacto no Negócio | Complexidade Técnica | Prioridade |
|---|---|---|---|
| Turnover | 🔴 Alto | 🟡 Média | 1 |
| Utilização de Capacidade | 🔴 Alto | 🟡 Média | 2 |
| Custo por Região | 🔴 Alto | 🟢 Baixa | 3 |
| Atingimento de Metas | 🟡 Médio | 🟢 Baixa | 4 |
| KPIs Secundários | 🟡 Médio | 🟢 Baixa | 5 |

---

## 5. Implementação no Metabase

Cada KPI será implementado como uma **Metabase Question** (query SQL salva) e agrupada em um **Dashboard** com filtros interativos.

### Queries SQL dos KPIs principais

```sql
-- KPI 1: Turnover %
SELECT
  d.period,
  ROUND(
    COUNT(CASE WHEN c.status = 'Terminated' THEN 1 END) * 100.0 / COUNT(*), 2
  ) AS turnover_pct
FROM fato_workforce f
JOIN dim_colaborador c ON f.employee_id = c.employee_id
JOIN dim_data d ON f.date_id = d.date_id
GROUP BY d.period
ORDER BY d.period;

-- KPI 2: Custo por Região
SELECT
  r.region_name,
  SUM(f.monthly_cost) AS custo_total
FROM fato_workforce f
JOIN dim_regiao r ON f.region_id = r.region_id
GROUP BY r.region_name
ORDER BY custo_total DESC;

-- KPI 3: Utilização de Capacidade %
SELECT
  d.period,
  ROUND(SUM(f.worked_hours) * 100.0 / SUM(f.planned_hours), 2) AS utilizacao_pct
FROM fato_workforce f
JOIN dim_data d ON f.date_id = d.date_id
GROUP BY d.period
ORDER BY d.period;

-- KPI 4: Atingimento de Metas %
SELECT
  cl.client_name,
  ROUND(AVG(f.goal_achievement), 2) AS meta_pct
FROM fato_workforce f
JOIN dim_cliente cl ON f.assignment_id = cl.assignment_id
GROUP BY cl.client_name
ORDER BY meta_pct DESC;
```

### Layout Sugerido do Dashboard

```
┌─────────────────────────────────────────────────────────┐
│  FILTROS: Período | Região | Cliente  (Metabase filters) │
├──────────┬──────────┬──────────────┬────────────────────┤
│ Turnover │ Custo    │ Utilização   │ Atingimento        │
│   3,2%   │ $450k    │   87%        │   91%              │
├──────────┴──────────┴──────────────┴────────────────────┤
│  Gráfico de linha — Evolução mensal dos KPIs             │
├─────────────────────────┬───────────────────────────────┤
│  Custo por Região       │  Utilização por Departamento  │
│  (bar chart Metabase)   │  (bar chart Metabase)         │
├─────────────────────────┴───────────────────────────────┤
│  Tabela detalhada — Por cliente / região / período       │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Validação com Stakeholders

| KPI | Analista GlobalForce | Gerente de Conta | Status |
|---|---|---|---|
| Turnover | ✅ Aprovado | ✅ Aprovado | ✅ Validado |
| Custo por Região | ✅ Aprovado | ✅ Aprovado | ✅ Validado |
| Utilização de Capacidade | ✅ Aprovado | ✅ Aprovado | ✅ Validado |
| Atingimento de Metas | ✅ Aprovado | ✅ Aprovado | ✅ Validado |
| KPIs Secundários | ✅ Aprovado | 🟡 Revisar na demo | 🟡 Pendente |

---

## 7. Próximos Passos (S0 → S1)

- [x] Esboçar modelo de dados (tabelas fato e dimensão)
- [x] Documentar fluxo completo ponta a ponta
- [x] Definir stack tecnológica final
- [x] Criar mock data para validação do pipeline ETL
